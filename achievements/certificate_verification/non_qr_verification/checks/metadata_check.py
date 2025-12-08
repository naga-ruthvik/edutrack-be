#!/usr/bin/env python3
"""
metadata_only.py
"""

import fitz  # PyMuPDF
import json
import sys
import os


def extract_metadata(pdf_bytes: bytes):
    """ Extract metadata using PyMuPDF (always stable). """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    doc.close()

    # Normalize keys to lowercase
    clean_meta = {k.lower(): v for k, v in meta.items()}
    return clean_meta


def score_metadata(meta: dict):
    """ Modified scoring → ONLY 0 or 100 based on editing. """

    producer = (meta.get("producer") or "").lower()
    creator = (meta.get("creator") or "").lower()

    reasons = []

    # Suspicious editors = FAKE (score = 0)
    suspicious_tools = ["canva", "photoshop", "gimp", "word", "ppt", "illustrator"]

    if any(x in producer for x in suspicious_tools):
        return {
            "score": 0,
            "producer": producer,
            "creator": creator,
            "metadata_raw": meta,
            "reasons": [f"Suspicious editing software detected: {producer}"]
        }

    # Missing producer also = edited/fake
    if producer.strip() == "":
        return {
            "score": 0,
            "producer": producer,
            "creator": creator,
            "metadata_raw": meta,
            "reasons": ["Producer metadata missing (often in edited files)."]
        }

    # Otherwise → 100 (GENUINE)
    return {
        "score": 100,
        "producer": producer,
        "creator": creator,
        "metadata_raw": meta,
        "reasons": ["Metadata clean. No editing indicators."]
    }


def run_metadata_check(path: str):
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}

    with open(path, "rb") as f:
        pdf_bytes = f.read()

    meta = extract_metadata(pdf_bytes)
    scored = score_metadata(meta)

    # new verdict logic
    verdict = "GENUINE" if scored["score"] == 100 else "FAKE"

    return {
        "verdict": verdict,
        "final_score": scored["score"],
        "metadata_check": scored
    }


def main():
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("Enter path to PDF: ").strip()

    result = run_metadata_check(pdf_path)

    print("\n==== RESULT (JSON) ====\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
