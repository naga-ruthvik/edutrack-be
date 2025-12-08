# file: extractor_llm_pipeline.py
import os
import re
import sys
import asyncio
import json
import time
import pathlib
import mimetypes
import tempfile
import urllib.parse
import requests
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from pprint import pprint
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Setup Logger for Scraper
logger = logging.getLogger("CertificateVerifier.Scraper")


# HTML rendering
from playwright.sync_api import sync_playwright

# PDF parsing
from pypdf import PdfReader  # fast text extraction for text-based PDFs
# For scanned PDFs, consider: pip install pytesseract pdf2image; then OCR fallback.

# Load API key from env
from dotenv import load_dotenv
load_dotenv()
CERTIFICATE_VERIFICATION_API_KEY=os.getenv("CERTIFICATE_VERIFICATION_API_KEY")
# -------------------------------
# Config
# -------------------------------
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# DOWNLOAD_DIR = pathlib.Path("downloads")
# DOWNLOAD_DIR.mkdir(exist_ok=True)

# -------------------------------
# Data models
# -------------------------------
@dataclass
class ExtractedDocument:
    source_url: str
    content_type: str  # "html" or "pdf"
    text: str
    metadata: Dict[str, str]

@dataclass
class LLMExtractionSpec:
    # Customize fields expected from the LLM
    instruction: str
    schema: Dict[str, str]  # key -> description

# -------------------------------
# Utilities
# -------------------------------
def normalize_url(base_url: str, href: str) -> Optional[str]:
    if not href:
        return None
    return urllib.parse.urljoin(base_url, href)

def is_pdf_link(url: str) -> bool:
    if not url:
        return False
    # extension or explicit PDF content type later
    return ".pdf" in urllib.parse.urlparse(url).path.lower()

def save_binary(content: bytes, filename: str, download_dir: pathlib.Path) -> pathlib.Path:
    path = download_dir / filename
    path.write_bytes(content)
    return path

# -------------------------------
# HTML rendering & extraction
# -------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def render_and_get_html(url: str, timeout_ms: int = 20000) -> Tuple[str, Dict[str, str]]:
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="networkidle")
        # Some sites need a tiny wait for late JS
        time.sleep(1.0)
        html = page.content()
        # Capture metadata
        meta = {
            "title": page.title(),
            "final_url": page.url,
        }
        context.close()
        browser.close()
        return html, meta

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style/nav/footer
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    # Prefer main if present
    main = soup.find("main")
    text = (main.get_text(separator="\n") if main else soup.get_text(separator="\n"))
    # Clean
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def check_link_is_pdf(url: str) -> bool:
    try:
        # Fast HEAD request to check Content-Type
        logger.debug(f"Checking if link is PDF (HEAD): {url}")
        resp = requests.head(url, headers=DEFAULT_HEADERS, timeout=5, allow_redirects=True)
        ctype = resp.headers.get("Content-Type", "").lower()
        is_pdf = "application/pdf" in ctype
        logger.debug(f"Link {url} Content-Type: {ctype} -> Is PDF: {is_pdf}")
        return is_pdf
    except Exception as e:
        logger.warning(f"HEAD request failed for {url}: {e}")
        return False

def find_pdf_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    
    # 1. Standard .pdf extension check
    for a in soup.find_all("a", href=True):
        candidate = normalize_url(base_url, a["href"])
        if not candidate or candidate in seen:
            continue
            
        if is_pdf_link(candidate):
            logger.info(f"Found explicit PDF link: {candidate}")
            links.append(candidate)
            seen.add(candidate)
        else:
            # 2. Keyword + Content-Type check (for hidden PDFs)
            text = a.get_text(separator=" ", strip=True).lower()
            keywords = ["download", "certificate", "statement", "score card", "print"]
            if any(k in text for k in keywords):
                logger.info(f"Checking candidate link (keyword match '{text}'): {candidate}")
                if check_link_is_pdf(candidate):
                    logger.info(f"Confirmed hidden PDF link: {candidate}")
                    links.append(candidate)
                    seen.add(candidate)

    logger.info(f"Total PDF links found: {len(links)}")
    return sorted(list(links))

# -------------------------------
# PDF download & text extraction
# -------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def fetch_url(url: str) -> requests.Response:
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    return resp

def ensure_pdf(url: str, download_dir: pathlib.Path) -> pathlib.Path:
    resp = fetch_url(url)
    ctype = resp.headers.get("Content-Type", "")
    filename = pathlib.Path(urllib.parse.urlparse(url).path).name or f"file_{int(time.time())}.pdf"
    if not filename.lower().endswith(".pdf"):
        # Try to infer
        ext = mimetypes.guess_extension(ctype.split(";")[0].strip()) or ".pdf"
        filename = filename + ext
    return save_binary(resp.content, filename, download_dir)

def pdf_to_text(pdf_path: pathlib.Path) -> str:
    text_parts = []
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except Exception as e:
        text_parts.append(f"[PDF parse error: {e}]")
    text = "\n".join(text_parts).strip()
    # If empty (scanned PDFs), consider OCR fallback (pytesseract + pdf2image)
    final_text = text or "[Empty or scanned PDF without text layer]"
    logger.info(f"PDF Text Extracted ({len(final_text)} chars). Preview: {final_text[:200]}...")
    return final_text

# -------------------------------
# Orchestrator: extract from URL (HTML + PDFs)
# -------------------------------
def extract_from_website(url: str, download_dir: pathlib.Path = None, include_pdfs: bool = True, max_pdfs: int = 5) -> List[ExtractedDocument]:
    if download_dir is None:
        download_dir = pathlib.Path("downloads")
        download_dir.mkdir(exist_ok=True)

    docs: List[ExtractedDocument] = []
    
    # Optimization: If URL is directly a PDF, skip Playwright rendering
    if url.lower().endswith(".pdf"):
        try:
            pdf_path = ensure_pdf(url, download_dir)
            pdf_text = pdf_to_text(pdf_path)
            docs.append(ExtractedDocument(
                source_url=url,
                content_type="pdf",
                text=pdf_text,
                metadata={"filename": str(pdf_path.name)}
            ))
            return docs
        except Exception as e:
            # If download fails, maybe it's not a PDF or needs headers?
            # We can fall back to the generic flow, or just report error.
            print(f"[WARN] Direct PDF download failed: {e}")
            pass

    # Try rendering dynamic page
    try:
        html, meta = render_and_get_html(url)
        text = html_to_text(html)
        docs.append(ExtractedDocument(
            source_url=meta.get("final_url", url),
            content_type="html",
            text=text,
            metadata=meta
        ))
        if include_pdfs:
            pdf_links = find_pdf_links(html, meta.get("final_url", url))
            for i, pdf_url in enumerate(pdf_links[:max_pdfs]):
                pdf_path = ensure_pdf(pdf_url, download_dir)
                pdf_text = pdf_to_text(pdf_path)
                docs.append(ExtractedDocument(
                    source_url=pdf_url,
                    content_type="pdf",
                    text=pdf_text,
                    metadata={"filename": str(pdf_path.name)}
                ))
    except Exception as e:
        # Fallback: static GET and parse
        resp = fetch_url(url)
        ctype = resp.headers.get("Content-Type", "")
        if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
            pdf_name = pathlib.Path(urllib.parse.urlparse(url).path).name or "download.pdf"
            path = save_binary(resp.content, pdf_name, download_dir)
            pdf_text = pdf_to_text(path)
            docs.append(ExtractedDocument(
                source_url=url,
                content_type="pdf",
                text=pdf_text,
                metadata={"filename": str(path.name)}
            ))
        else:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = html_to_text(str(soup))
            docs.append(ExtractedDocument(
                source_url=url,
                content_type="html",
                text=text,
                metadata={"final_url": url, "title": soup.title.string if soup.title else ""}
            ))
            
            # Found fallback HTML, now look for PDFs in it (since Playwright failed)
            if include_pdfs:
                try:
                    logger.info("Fallback: Searching for PDFs in static HTML...")
                    pdf_links = find_pdf_links(str(soup), url)
                    for i, pdf_url in enumerate(pdf_links[:max_pdfs]):
                        try:
                            logger.info(f"Fallback: Attempting to download PDF: {pdf_url}")
                            pdf_path = ensure_pdf(pdf_url, download_dir)
                            pdf_text = pdf_to_text(pdf_path)
                            docs.append(ExtractedDocument(
                                source_url=pdf_url,
                                content_type="pdf",
                                text=pdf_text,
                                metadata={"filename": str(pdf_path.name)}
                            ))
                            logger.info(f"Successfully extracted PDF: {pdf_url}")
                        except Exception as pdf_err:
                            logger.warning(f"Failed to download PDF {pdf_url}: {pdf_err}. Continuing with HTML content only.")
                            # Don't fail the entire extraction - we still have HTML
                            continue
                except Exception as e:
                    logger.warning(f"PDF link detection failed: {e}. Using HTML content only.")
    return docs

# -------------------------------
# Send to LLM for structured parsing
# -------------------------------
from typing import List,Any
# KEEP THIS CORRECT VERSION
@dataclass
class ExtractedDocument:
    source_url: str
    content_type: str  # "html" or "pdf"
    text: str
    metadata: Dict[str, str]

@dataclass
class LLMExtractionSpec:
    # Customize fields expected from the LLM
    instruction: str
    schema: Dict[str, str]  # key -> description

def build_prompt(
    docs: List[Any],      # Now correctly handles a list of objects like ExtractedDocument
    spec: Any,            # Handles the LLMExtractionSpec object
    pdf_data: str         # JSON string of reference data for verification
) -> str:
    """
    Build a unified prompt for extraction and per-field verification from multiple 
    sources, including source URLs in the output.
    
    Args:
        docs: List of ExtractedDocument objects.
        spec: An LLMExtractionSpec object containing the schema.
        pdf_data: A JSON string containing reference data for verification.
    
    Returns:
        str: A full prompt for the LLM.
    """
    # Concatenate document content with source information and separators
    blocks = []
    source_urls = []
    for d in docs:
        # Using dot notation to access object attributes
        # Limit to 5000 chars to avoid safety filters
        content_preview = d.text[:5000]
        blocks.append(f"=== SOURCE: {d.source_url} ({d.content_type}) ===\n{content_preview}\n\n")
        source_urls.append(d.source_url)
    
    # [FIX 1] Access the .schema attribute of the spec object before calling .items()
    schema_desc = "\n".join([f"- {k}: {v}" for k, v in spec.schema.items()])

    # Dynamically build the JSON structure for the 'extracted_data' field
    field_verification_examples = []
    for key in spec.schema.keys():
        field_example = f"""            "{key}": {{
                "value": "<extracted value for {key} or null>",
                "is_verified": <boolean>,
                "reasoning": "<Explain why this specific field matches or mismatches the reference data.>"
            }}"""
        field_verification_examples.append(field_example)
    
    extracted_data_format = ",\n".join(field_verification_examples)

    # Assemble the final prompt
    prompt = rf"""
You are a strict certificate verification system that detects certificate forgery. 
You will be given two pieces of text:
1. Data extracted from an uploaded certificate (PDF).
2. Data scraped from the official verification URL.

Your job:
- Parse EACH text INDEPENDENTLY into structured fields: {{ "name", "course", "issuer", "date", "certificate_id" }}
- **CRITICAL**: Do NOT copy values from PDF to Website or vice versa. Extract each field ONLY from its respective source.
- If a field is missing in a source, mark it as null. DO NOT fill it with data from the other source.
- If you cannot find a name in the website text, return "null" for website name. DO NOT use the PDF name.

**HOW TO EXTRACT:**
1. For "parsed_pdf_data", ONLY look at the "PDF Extracted Text" section
2. For "parsed_site_data", ONLY look at the "Scraped Website Text" section
3. DO NOT mix data between these two sections

Rules for verification:
- If certificate_id exists in both sources, check for exact match or containment (one ID contains the other).
- **Special Rule for NPTEL**: NPTEL certificates extracted from the web often have messy, unstructured text.
    - The **Name** is usually a standalone line of UPPERCASE text (e.g., "NAGA RUTHVIK") appearing near the score or roll number.
    - The **Certificate ID** on the website (e.g. ...30098185) is longer than the PDF (e.g. ...362). **Count this as a MATCH**.
- Issuer must match exactly (case-insensitive).
- Course title must match with at least 90% similarity.
- Name must match with at least 80% similarity (to allow for small variations like initials).
- Date must match exactly if present.
- **CRITICAL**: If the names are COMPLETELY DIFFERENT (e.g., "ANVESH REDDY" vs "NAGA RUTHVIK"), mark verified as FALSE.
- If majority of critical fields (issuer + course + certificate_id + name) match, then "verified" = true. Otherwise false.

Output must be ONLY in the following JSON format:

{{
    "parsed_pdf_data": {{ ... }},
    "parsed_site_data": {{ ... }},
    "verified": true/false,
    "score": 0.0-1.0,
    "reason": "Short explanation of why it was verified or rejected"
}}

Example (NPTEL):
{{
    "parsed_pdf_data": {{
        "name": "NAGA RUTHVIK",
        "course": "Programming in Python",
        "issuer": "NPTEL",
        "certificate_id": "NPTEL24CS78S436801880"
    }},
    "parsed_site_data": {{
        "name": "NAGA RUTHVIK",
        "course": "Programming in Python",
        "issuer": "NPTEL",
        "certificate_id": "NPTEL24CS78S43680188002689171" 
    }},
    "verified": true,
    "score": 0.95,
    "reason": "ID match (containment) and Name match."
}}

Now compare the following:

PDF Extracted Text:
<<<{pdf_data}>>>

Scraped Website Text:
<<<{"".join(blocks)}>>>
"""


    return prompt



def call_llm_extract(prompt: str) -> Dict:
    """
    Example with OpenAI-compatible clients. Replace with preferred LLM provider.
    """
    """
    Sends a prompt to the Gemini API and gets a JSON response.
    """
    import google.generativeai as genai
    genai.configure(api_key=CERTIFICATE_VERIFICATION_API_KEY)

    model = genai.GenerativeModel(
        # Use Gemini 1.5 Pro (free tier, much more capable than Flash)
        model_name="gemini-2.5-flash",
        system_instruction="""You are a certificate verification expert specializing in NPTEL certificates.
        
EXTRACTION RULES:
        1. For NPTEL website data, names appear as UPPERCASE text (e.g., 'NAGA RUTHVIK') near scores/IDs
        2. Extract data EXACTLY as written - do not copy between PDF and Website sections
        3. If a field is missing, return null - DO NOT guess or copy from other source
        4. Return ONLY valid JSON with no additional text
        """
        )

    # 2. `temperature` and `response_format` are set in `generation_config`.
    generation_config = {
        "temperature": 0,
        "response_mime_type": "application/json",
        "temperature": 0.0,
        "top_p": 0.9,
        "top_k": 5,           
        "max_output_tokens": 1000,
        "candidate_count": 1

    }
    
    # 3. Configure safety settings to be less restrictive
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]

    # 4. The API call with safety settings
    logger.debug(f"--- LLM PROMPT START ---\n{prompt}\n--- LLM PROMPT END ---")
    response = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    # 4. Handle blocked responses (safety filter, etc)
    try:
        raw_json_text = response.text
        return json.loads(raw_json_text)
    except ValueError as e:
        # Model was blocked (safety filter, recitation, etc)
        logger.error(f"Gemini blocked response. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'UNKNOWN'}")
        # Return minimal valid structure
        return {
            "parsed_pdf_data": {"name": None, "course": None, "issuer": None, "date": None, "certificate_id": None},
            "parsed_site_data": {"name": None, "course": None, "issuer": None, "date": None, "certificate_id": None},
            "verified": False,
            "score": 0.0,
            "reason": f"LLM response blocked (safety filter). Finish reason: {response.candidates[0].finish_reason if response.candidates else 'UNKNOWN'}"
        }

import json
from pprint import pprint

# if __name__ == "__main__":
#     # --- 1. Define Inputs ---
    
#     # The URL of a certificate or course page to verify.
#     # Using a Coursera certificate page as a good, complex example.
#     TEST_URL = "https://archive.nptel.ac.in/content/noc/NOC24/SEM2/Ecertificates/106/noc24-cs78/Course/NPTEL24CS78S43680188002689171.pdf"

#     # This is the reference text, as if it were extracted from a PDF the user uploaded.
#     # We will check if the TEST_URL contains matching information.
#     REFERENCE_PDF_TEXT = """
#     No. of credits recommended: 2 or 3
#     To verify the certificate
#     Roll No:
#     Jul-Sep 2024
#     (8 week course)
#     Programming, Data Structures and Algorithms using Python
#     NAGA RUTHVIK
#     17.71/25
#     39.38/75
#     57
#     2068
#     NPTEL24CS78S436801880
#     """

#     # Define the schema of what we want the LLM to find and verify.
#     EXTRACTION_SPEC = LLMExtractionSpec(
#         instruction="Extract certificate details and verify them against the reference text.",
#         schema={
#             "student_name": "The full name of the student who completed the course.",
#             "issuing_organization": "The name of the company that created the course (e.g., Google, IBM).",
#             "completion_date": "The month and year the course was completed.",
#             "score": "The final score or percentage achieved, if available."
#         }
#     )

#     # --- 2. Run the Extraction Pipeline ---
#     print(f"[*] Starting extraction from URL: {TEST_URL}")
    
#     # Fetches the website content (and any linked PDFs, though this example URL has none).
#     documents = extract_from_website(TEST_URL, include_pdfs=False) # Set to False for this test
    
#     if not documents:
#         print("[!] No documents were extracted. Exiting.")
#     else:
#         print(f"[*] Extracted {len(documents)} document(s) successfully.")
#         print(f"documents: {documents}")
        
#         # --- 3. Build the Prompt ---
#         print("[*] Building prompt for the LLM...")
#         prompt = build_prompt(
#             docs=documents,
#             spec=EXTRACTION_SPEC,
#             pdf_data=REFERENCE_PDF_TEXT
#         )

#         # Optional: Uncomment the line below to see the full prompt sent to the LLM.
#         # print(prompt)

#         # --- 4. Call the LLM and Print Results ---
#         print("[*] Calling Gemini API for structured extraction and verification...")
#         try:
#             structured_data = call_llm_extract(prompt)
#             print("\n✅ LLM Extraction Complete. Result:")
#             pprint(structured_data)
#         except Exception as e:
#             print(f"\n❌ An error occurred while calling the LLM: {e}")
