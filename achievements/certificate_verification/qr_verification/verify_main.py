import pprint
from scraper_test.scraping import extract_from_website, build_prompt, call_llm_extract
from main import extract_content_from_pdf
import os
import re
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

@dataclass
class LLMExtractionSpec:
    # Customize fields expected from the LLM
    instruction: str
    schema: Dict[str, str]  # key -> description

import logging

logger = logging.getLogger("CertificateVerifier") # Use same logger name

def verify_qr(pdf_path, target_url, output_dir=None):
    try:
        text_content, image_paths = extract_content_from_pdf(pdf_path, output_dir=output_dir)
    except Exception as e:
        logger.error(f"Failed to extract content from PDF in verify_qr: {e}")
        return {"error": f"Failed to extract content from PDF: {str(e)}"}

    spec = LLMExtractionSpec(
        instruction=(
            "You are a precise information extractor. "
            "Fill the schema fields using the provided documents. "
            "If a field is not present, use null."
        ),
        schema={
            "title": "Main title or document/course/article heading",
            "issuer": "Publishing or issuing organization (e.g., Meta, IEEE, Govt.)",
            "author_or_name": "Person or entity name if available",
            "date": "Completion or publication date in ISO if possible",
            "duration_or_pages": "Hours for courses or page count for PDFs",
            "description": "1-3 sentence summary",
            "skills_or_topics": "Array of key skills/topics mentioned",
            "source_urls": "Array of source URLs from which the data was extracted"
        }
    )

    try:
        docs = extract_from_website(target_url, download_dir=output_dir, include_pdfs=True, max_pdfs=5)
        # print("docs:", docs)
        prompt = build_prompt(docs, spec, text_content)
        extracted = call_llm_extract(prompt)
    except Exception as e:
        extracted = {"error": str(e), "fallback": {"title": "", "source": target_url}}

    return extracted

if __name__ == "__main__":
    target_url="https://archive.nptel.ac.in/content/noc/NOC24/SEM2/Ecertificates/106/noc24-cs78/Course/NPTEL24CS78S43680188002689171.pdf"
    pdf_document_path = "certificate_3.pdf"
    if os.path.exists(pdf_document_path):
        res = verify_qr(pdf_document_path, target_url)
        pprint(res)
    else:
        print(f"File not found: {pdf_document_path}")