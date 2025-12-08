import os
import sys
import json
import re
import fitz
import cv2
import numpy as np
from PIL import Image
import io
import importlib.util
import tempfile
import shutil
import requests
import logging
from typing import Union, BinaryIO

# Add subdirectories to sys.path to allow imports within them to work
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT, "qr_verification"))
sys.path.append(os.path.join(ROOT, "non_qr_verification"))

# Import Non-QR Verifier
try:
    from non_qr_verification.main import run_non_qr_checks
except ImportError:
    # Fallback if direct import fails (e.g. if __init__.py is missing)
    spec = importlib.util.spec_from_file_location("non_qr_main", os.path.join(ROOT, "non_qr_verification", "main.py"))
    non_qr_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(non_qr_mod)
    run_non_qr_checks = non_qr_mod.run_non_qr_checks

# Import QR Verifier
try:
    from qr_verification.verify_main import verify_qr
except ImportError:
    spec = importlib.util.spec_from_file_location("qr_verify_main", os.path.join(ROOT, "qr_verification", "verify_main.py"))
    qr_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qr_mod)
    verify_qr = qr_mod.verify_qr

# Setup Logging
logger = logging.getLogger("CertificateVerifier")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Prevent double logging if Celery intercepts

# Clear existing handlers to avoid duplicates on reload
if logger.hasHandlers():
    logger.handlers.clear()

# 1. File Handler (Requested by user)
log_file_path = os.path.join(ROOT, "certificate_debug.log")
try:
    fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    print(f"Failed to set up file logging: {e}")

# 2. Stream Handler (For Celery Console)
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.INFO) # Keep console less verbose
sh.setFormatter(formatter)
logger.addHandler(sh)





def detect_qr(pdf_path):
    detector = cv2.QRCodeDetector()
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Could not open PDF for QR detection: {e}")
        print(f"[ERROR] Could not open PDF for QR detection: {e}")
        return None

    for page in doc:
        for img in page.get_images(full=True):
            try:
                xref = img[0]
                base = doc.extract_image(xref)
                pil = Image.open(io.BytesIO(base["image"])).convert("RGB")
                np_img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

                data, _, _ = detector.detectAndDecode(np_img)
                if data and data.strip():
                    logger.info(f"QR Code detected: {data.strip()}")
                    return data.strip()
            except Exception as e:
                logger.debug(f"Error checking image for QR: {e}")
                pass
    logger.info("No QR code detected.")
    return None


def detect_url(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except:
        return None
        
    for page in doc:
        text = page.get_text()
        # Simple regex for URL
        # Simple regex for URL
        match = re.search(r"(https?://[^\s]+)", text)
        if match:
            url = match.group(0)
            logger.info(f"URL detected in text: {url}")
            return url
    logger.info("No URL detected in text.")
    return None


def calculate_academic_year(date_str: str) -> str:
    """
    Calculate academic year from a date string.
    Academic year: June-May (e.g., "2024" means June 2023 - May 2024)
    """
    if not date_str:
        return None
    
    try:
        # Try parsing common date formats
        import datetime
        
        # Handle formats like "Jul-Sep 2024", "July 2024", "2024-07-15"
        month_year = re.search(r'(\w+[-/]?\w*)\s*(\d{4})', date_str)
        if month_year:
            year = int(month_year.group(2))
            month_part = month_year.group(1).lower()
            
            # Determine if it's in first half (Jan-May) or second half (Jun-Dec)
            first_half_months = ['jan', 'feb', 'mar', 'apr', 'may']
            if any(m in month_part for m in first_half_months):
                return f"{year - 1}-{year}"
            else:
                return f"{year}-{year + 1}"
        
        # Fallback: just year
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            year = int(year_match.group(1))
            return f"{year}-{year + 1}"
    except:
        pass
    
    return ""


def safe_parse_json(text: str) -> dict:
    """
    Helper to safely parse JSON from LLM output.
    Strips markdown code blocks if present.
    """
    try:
        # Strip markdown json ...  if present
        if "```" in text:
            # simple split to get content between backticks
            parts = text.split("```")
            for part in parts:
                if part.strip().startswith("json"):
                    text = part.strip()[4:]
                    break
                elif part.strip().startswith("{"):
                    text = part.strip()
                    break
        
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # If strict parsing fails, return raw text or empty dict based on preference
        return {"_raw_text": text}

def call_llm_extract_local(prompt: str) -> dict:
    # ---------------------------------------------------------
    # CONFIGURATION: Update this URL when you restart Ngrok
    # ---------------------------------------------------------
    NGROK_BASE_URL = "http://localhost:11434/" 
    MODEL_NAME = "gpt-oss:20b"
    # ---------------------------------------------------------

    try:
        # 1. Construct Endpoint
        # Remove trailing slash if accidentally added, append chat API endpoint
        api_url = f"{NGROK_BASE_URL.rstrip('/')}/api/chat"

        # 2. Construct Payload
        # We use 'format': 'json' to force Ollama to adhere to JSON structure
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON. No explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,  # Get full response at once
            "format": "json", # Enforce JSON mode (Ollama feature)
            "options": {
                "temperature": 0, # Deterministic (0 is best for extraction)
                "num_ctx": 4096   # Context window size
            }
        }

        # 3. Prepare Headers
        # 'ngrok-skip-browser-warning' is REQUIRED for free Ngrok accounts
        # otherwise requests returns an HTML warning page instead of JSON.
        headers = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true" 
        }

        # 4. Execute Request
        # We use a timeout to prevent hanging if the local LLM is stuck
        response = requests.post(api_url, json=payload, headers=headers, timeout=120)
        
        # Check for HTTP errors (404, 500, etc)
        if response.status_code != 200:
            logger.error(f"[ERROR] HTTP {response.status_code}: {response.text}")
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return {}

        # 5. Parse Response
        result_json = response.json()
        
        # Ollama returns content nested in 'message' -> 'content'
        content_text = result_json.get("message", {}).get("content", "")

        parsed = safe_parse_json(content_text)
        
        if not isinstance(parsed, dict):
            logger.warning(f"[WARN] LLM returned JSON that is not an object; parsed type: {type(parsed)}")
            print("[WARN] LLM returned JSON that is not an object; parsed type:", type(parsed))
            return {"_raw_parsed": parsed}
            
        return parsed

    except requests.exceptions.ConnectionError:
        logger.error(f"[ERROR] Could not connect to {NGROK_BASE_URL}. Is Ngrok running?")
        print(f"[ERROR] Could not connect to {NGROK_BASE_URL}. Is Ngrok running?")
        return {}
    except Exception as e:
        logger.error(f"[ERROR] call_llm_extract_local failed: {e}")
        print("[ERROR] call_llm_extract_local failed:", e)
        # traceback.print_exc() # traceback not imported, relying on logger
        return {}


def extract_metadata_with_llm(pdf_text: str) -> dict:
    """
    Use Local LLM (Ollama) to extract category, level, rank, skills, and summary from certificate text.
    """
    
    prompt = f"""Extract the following information from this certificate text.

CERTIFICATE TEXT:
{pdf_text[:3000]}

Extract and classify:

1. **category**: Choose ONE from:
   - SPORTS (if sports/athletics/games related)
   - CULTURAL (if arts/music/drama/cultural)
   - EXTENSION (if NSS/NCC/social service)
   - MOOC (if online course from NPTEL/Coursera/edX/Udemy/etc)
   - INTERNSHIP (if internship/work experience)
   - PROJECT (if project/field work)
   - TECHNICAL (if hackathon/coding competition/technical event)
   - RESEARCH (if research paper/patent/publication)
   - OTHER (if none of the above)

2. **level**: Choose ONE from:
   - COLLEGE (if college-level or inter-collegiate)
   - STATE (if state-level or university-level)
   - NATIONAL (if national-level)
   - INTERNATIONAL (if international-level)

3. **rank**: Choose ONE from:
   - PARTICIPATION (if just participation/completion certificate)
   - FIRST (if 1st prize/gold/winner/topper)
   - SECOND (if 2nd prize/silver/runner-up)
   - THIRD (if 3rd prize/bronze)
   - WINNER (if winner but position unclear)

4. **skills**: Extract 3-5 relevant technical or domain skills (e.g., ["Python", "Data Structures", "Algorithms"])

5. **summary**: Write a 1-2 sentence summary of the achievement

Return ONLY a JSON object:
{{
    "category": "...",
    "level": "...",
    "rank": "...",
    "skills": ["...", "..."],
    "summary": "..."
}}
"""
    
    try:
        metadata = call_llm_extract_local(prompt)
        logger.info(f"Extracted metadata: {metadata}")
        
        # Merge with default structure to ensure all keys exist if LLM missed some
        defaults = {
            "category": "OTHER",
            "level": "COLLEGE",
            "rank": "PARTICIPATION",
            "skills": [],
            "summary": "Certificate verification completed"
        }
        # Python 3.9+ dictionary merge (defaults | metadata), but sticking to update for compatibility
        final_meta = defaults.copy()
        if isinstance(metadata, dict):
            final_meta.update(metadata)
            
        return final_meta
        
    except Exception as e:
        logger.error(f"LLM metadata extraction failed: {e}")
        return {
            "category": "OTHER",
            "level": "COLLEGE",
            "rank": "PARTICIPATION",
            "skills": [],
            "summary": "Certificate verification completed"
        }


def verify_certificate(file_input: Union[str, BinaryIO], user_provided_url: str = None):
    logger.info("Entered verify_certificate")
    
    # Create a temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix="cert_verify_")
    temp_pdf_path = None
    
    try:
        # Handle input: if it's a file object, save it to a temp file
        if hasattr(file_input, "read"):
            logger.info("Input is a file object.")
            temp_pdf_path = os.path.join(temp_dir, "uploaded_certificate.pdf")
            with open(temp_pdf_path, "wb") as f:
                f.write(file_input.read())
            file_path = temp_pdf_path
        elif isinstance(file_input, str) and file_input.startswith(("http://", "https://")):
            logger.info(f"Input is a URL: {file_input}")
            # Download file from URL (e.g. S3)
            temp_pdf_path = os.path.join(temp_dir, "downloaded_certificate.pdf")
            response = requests.get(file_input, stream=True)
            response.raise_for_status()
            with open(temp_pdf_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_path = temp_pdf_path
        else:
            logger.info(f"Input is a local file path: {file_input}")
            file_path = file_input
            if not os.path.exists(file_path):
                logger.error("File not found.")
                return {"error": "File not found"}

        logger.info(f"Processing file at: {file_path}")

        results = {
            "certificate_path": "uploaded_file" if temp_pdf_path else file_path,
            "verification_type": "unknown",
            "qr_data": None,
            "qr_verification_result": None,
            "non_qr_verification_result": None,
            "final_verdict": "UNKNOWN",
            "final_score": 0.0
        }

        # 1. Detect QR or URL
        qr_data = detect_qr(file_path)
        url_data = detect_url(file_path)
        verification_url = qr_data or url_data

        if qr_data:
             logger.info(f"QR detected: {qr_data}")
        if url_data:
             logger.info(f"URL detected: {url_data}")

        results["qr_data"] = verification_url

        if verification_url:
            results["verification_type"] = "QR/URL"
            logger.info(f"Verification URL found: {verification_url}")
            
            # Run QR Verification with temp output dir
            try:
                qr_res = verify_qr(file_path, verification_url, output_dir=temp_dir)
                results["qr_verification_result"] = qr_res
                logger.info(f"QR Verification Result: {qr_res}")
            except Exception as e:
                logger.error(f"QR verify failed: {e}")
                results["qr_verification_result"] = {"error": str(e)}

            # Run Non-QR Verification as well (forensic)
            try:
                non_qr_res = run_non_qr_checks(file_path)
                results["non_qr_verification_result"] = non_qr_res
                logger.debug(f"Non-QR (Forensic) Result: {non_qr_res}")
            except Exception as e:
                logger.error(f"Non-QR (forensic) failed: {e}")
                results["non_qr_verification_result"] = {"error": str(e)}

            # Combine logic (simple heuristic)
            qr_verified = False
            if results["qr_verification_result"] and isinstance(results["qr_verification_result"], dict):
                 qr_verified = results["qr_verification_result"].get("verified", False)
            
            if qr_verified:
                results["final_verdict"] = "VERIFIED"
                results["final_score"] = results["qr_verification_result"].get("score", 1.0) * 100
            else:
                # Fallback to Non-QR score
                if results["non_qr_verification_result"] and "final_score" in results["non_qr_verification_result"]:
                    results["final_score"] = results["non_qr_verification_result"]["final_score"]
                    results["final_verdict"] = results["non_qr_verification_result"]["final_verdict"]
                else:
                     results["final_verdict"] = "FAILED"

        else:
            results["verification_type"] = "NON-QR"
            logger.info("No Verification URL found. Running Non-QR checks.")
            
            try:
                non_qr_res = run_non_qr_checks(file_path)
                results["non_qr_verification_result"] = non_qr_res
                
                if "final_score" in non_qr_res:
                    results["final_score"] = non_qr_res["final_score"]
                    results["final_verdict"] = non_qr_res["final_verdict"]
                logger.info(f"Non-QR Result: {non_qr_res}")
            except Exception as e:
                logger.error(f"Non-QR failed: {e}")
                results["non_qr_verification_result"] = {"error": str(e)}

        # === BUILD UNIFIED OUTPUT ===
        logger.info("Building unified output...")
        
        # Extract PDF text for LLM metadata extraction
        pdf_text = ""
        try:
            pdf = fitz.open(file_path)
            for page in pdf:
                pdf_text += page.get_text()
            pdf.close()
        except Exception as e:
            logger.warning(f"Could not extract PDF text: {e}")
        
        # Extract metadata using LLM
        metadata = extract_metadata_with_llm(pdf_text)
        
        # Get QR result data (prioritized)
        qr_result = results.get("qr_verification_result", {})
        if isinstance(qr_result, dict) and "error" not in qr_result:
            parsed_pdf_data = qr_result.get("parsed_pdf_data", {})
            qr_score = qr_result.get("score", 0)
            qr_verified = qr_result.get("verified", False)
        else:
            parsed_pdf_data = {}
            qr_score = 0
            qr_verified = False
        
        # Get non-QR score
        non_qr_result = results.get("non_qr_verification_result", {})
        non_qr_score = non_qr_result.get("final_score", 0) if isinstance(non_qr_result, dict) else 0
        
        # Determine final status
        # Status = verified if QR score > 0.7 AND non-QR score > 70
        final_status = "verified" if (qr_score > 0.7 and non_qr_score > 70) else "rejected"
        
        # Determine rejection reason
        rejection_reason = None
        if final_status == "rejected":
            if qr_score <= 0.7 and non_qr_score <= 70:
                rejection_reason = f"Both QR verification (score: {qr_score:.2f}/1.0) and non-QR forensic analysis (score: {non_qr_score:.1f}/100) failed to meet thresholds."
            elif qr_score <= 0.7:
                rejection_reason = f"QR verification failed (score: {qr_score:.2f}/1.0, threshold: 0.7). {qr_result.get('reason', 'No details available.')}"
            elif non_qr_score <= 70:
                rejection_reason = f"Non-QR forensic analysis failed (score: {non_qr_score:.1f}/100, threshold: 70). {non_qr_result.get('overall_reason', 'No details available.')}"
        
        # Build unified output
        unified_output = {
            "title": parsed_pdf_data.get("course") or "Unknown Certificate",
            "issuing_organization": parsed_pdf_data.get("issuer") or "Unknown",
            "verification_url": results.get("qr_data"),
            "category": metadata.get("category", "OTHER"),
            "level": metadata.get("level", "COLLEGE"),
            "rank": metadata.get("rank", "PARTICIPATION"),
            "date_of_event": parsed_pdf_data.get("date"),
            "academic_year": calculate_academic_year(parsed_pdf_data.get("date")),
            "ai_summary": metadata.get("summary", "Certificate processed"),
            "status": final_status,
            "rejection_reason": rejection_reason,
            "reason": rejection_reason or qr_result.get("reason"), # Generic reason field
            "skills": metadata.get("skills", [])
        }
        
        # Add unified output to results
        results["unified_output"] = unified_output

        logger.info(f"Final Results: {results}")
        return results

    except Exception as e:
        logger.error(f"Error in verify_certificate: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

if __name__ == "__main__":
    # Test run
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # path = input("Enter certificate path: ").strip()
        path = "test.pdf"
    
    if os.path.exists(path):
        print(json.dumps(verify_certificate(path), indent=2))
    else:
        print("Usage: python backend_interface.py <path_to_pdf>")
