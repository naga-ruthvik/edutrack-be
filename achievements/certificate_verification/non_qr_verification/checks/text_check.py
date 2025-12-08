#!/usr/bin/env python3
"""
text_check.py
Strong Hybrid Text + Gemini Semantic Verification
"""

import re
import json
import base64
import requests
import sys
import os
from PyPDF2 import PdfReader

# ------------------------------------------------------------
# YOUR MODEL & API KEY (AS YOU PROVIDED)
# ------------------------------------------------------------
API_KEY = "AIzaSyApVVAscT2-5jucxd_draFZSIRPqcoQa7o"
API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key="

# ---------------------------
# PDF Text Extraction
# ---------------------------
def extract_text(path):
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return None


# ---------------------------
# Heuristic Rules
# ---------------------------
REAL_KEYWORDS = [
    "certificate", "course", "has successfully completed",
    "organized by", "credits", "grade", "completion"
]

SUSPICIOUS_KEYWORDS = [
    "lorem ipsum", "dummy", "template", "sample", "demo"
]


def heuristic_analysis(text):
    text_lower = text.lower()

    real_hits = [w for w in REAL_KEYWORDS if w in text_lower]
    suspicious_hits = [w for w in SUSPICIOUS_KEYWORDS if w in text_lower]

    # extract names-like phrases (A B, John Doe, etc.)
    names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", text)

    score = 50  # base neutral

    score += len(real_hits) * 10
    score -= len(suspicious_hits) * 15

    # too many names → suspicious editing
    if len(names) >= 2:
        score -= 15

    # random noise pattern (like NJ ZWGZG)
    noise_count = len(re.findall(r"\b[A-Z]{2,}\s+[A-Z]{2,}\b", text))
    score -= noise_count * 10

    # clamp 0–100
    score = max(0, min(100, score))

    return {
        "heuristic_score": score,
        "real_keyword_hits": real_hits,
        "suspicious_keyword_hits": suspicious_hits,
        "unique_names": names,
        "text_length": len(text),
        "reasons": [
            f"Found {len(real_hits)} certificate keywords.",
            f"Found {len(suspicious_hits)} suspicious keywords.",
            f"Detected {len(names)} names.",
            f"Noise patterns detected: {noise_count}"
        ]
    }


# ---------------------------
# Gemini Semantic Check
# ---------------------------
def gemini_semantic_check(text):
    prompt = f"""
You are a Certificate Authenticity Inspector.

Analyze the certificate text and classify it STRICTLY.

Return ONLY JSON in this exact format:

{{
  "verdict": "ORIGINAL" | "FAKE" | "UNCERTAIN",
  "confidence": 0-100,
  "reasons": ["reason1", "reason2"]
}}

Rules:
- Random uppercase sequences (e.g., 'NJ ZWGZG') → FAKE
- Inconsistent names → FAKE
- Missing institution name → FAKE
- Looks auto-generated → FAKE
- If text clearly matches academic/official certificate → ORIGINAL
- If text unclear but not fake → UNCERTAIN

Text:
\"\"\"{text[:5000]}\"\"\"
"""

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        r = requests.post(
            API_URL + API_KEY,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=40
        )
        r.raise_for_status()

        j = r.json()
        reply = j["candidates"][0]["content"]["parts"][0]["text"]

        # extract JSON from Gemini output
        m = re.search(r"(\{[\s\S]*\})", reply)
        if not m:
            return {"status": "error", "verdict": "Unknown", "confidence": 50,
                    "reasons": ["Could not parse AI output."]}

        return json.loads(m.group(1))

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "verdict": "Unknown",
            "confidence": 50,
            "reasons": ["AI request failed."]
        }


# ---------------------------
# FINAL COMBINED RESULT
# ---------------------------
def combined_text_check(path):
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}

    text = extract_text(path)
    if not text:
        return {"error": "Unable to read text from PDF"}

    heuristic = heuristic_analysis(text)
    ai = gemini_semantic_check(text)

    # combined weighted score
    final_score = (heuristic["heuristic_score"] * 0.4) + (ai.get("confidence", 50) * 0.6)
    final_score = round(final_score, 2)

    if ai.get("verdict") == "FAKE":
        final_verdict = "FAKE"
    elif ai.get("verdict") == "ORIGINAL" and heuristic["heuristic_score"] >= 60:
        final_verdict = "ORIGINAL"
    elif final_score < 40:
        final_verdict = "FAKE"
    else:
        final_verdict = "UNCERTAIN"

    return {
        "final_verdict": final_verdict,
        "final_score": final_score,
        "heuristic": heuristic,
        "ai_semantic": ai
    }


# ---------------------------
# MAIN
# ---------------------------
def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = input("Enter path to PDF: ").strip()

    result = combined_text_check(path)

    print("\n==== SEMANTIC TEXT CHECK RESULT (HYBRID) ====\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
