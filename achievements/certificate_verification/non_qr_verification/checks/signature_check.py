#!/usr/bin/env python3
"""
signature_advanced_check.py

Ultra Forensic PDF Signature & Structural Integrity Check

Run with:
    python signature_advanced_check.py
or:
    python signature_advanced_check.py path/to/file.pdf
"""

import sys
import os
import json
from typing import Dict, Any
from PyPDF2 import PdfReader


SUSPICIOUS_SOFTWARE_KEYWORDS = [
    "microsoft word",
    "wps",
    "libreoffice",
    "openoffice",
    "canva",
    "ilovepdf",
    "smallpdf",
    "sejda",
    "pdfescape",
    "pdfsam",
    "foxit",
    "nitro pdf",
    "pdf editor",
    "pdf xchange",
    "pdf24"
]

TRUSTED_GENERATORS = [
    "adobe",
    "skia",
    "ghostscript",
    "fpdf",
    "weasyprint",
    "tcpdf",
    "wkhtmltopdf",
    "nptel",
    "coursera"
]


def read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def analyze_raw_structure(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Analyze raw PDF bytes for structural tampering hints:
    - multiple xref sections
    - incremental updates (/Prev)
    - suspicious object count
    """
    text = pdf_bytes.decode("latin-1", errors="ignore")

    startxref_count = text.count("startxref")
    xref_count = text.count("xref")
    obj_count = text.count(" obj")
    trailer_count = text.count("trailer")
    prev_count = text.count("/Prev")

    incremental_updates = prev_count > 0 or startxref_count > 1 or xref_count > 1

    flags = []

    if incremental_updates:
        flags.append("PDF shows signs of incremental updates (/Prev or multiple xref/startxref).")

    if obj_count < 5:
        flags.append("PDF has unusually low object count (very small/simple file).")
    elif obj_count > 5000:
        flags.append("PDF has unusually high object count (possibly assembled or heavily edited).")

    return {
        "startxref_count": startxref_count,
        "xref_count": xref_count,
        "obj_count": obj_count,
        "trailer_count": trailer_count,
        "prev_count": prev_count,
        "incremental_updates": incremental_updates,
        "structural_flags": flags
    }


def extract_metadata_info(reader: PdfReader) -> Dict[str, Any]:
    """
    Extract producer/creator from the PDF metadata.
    """
    try:
        meta = reader.metadata or {}
    except Exception:
        meta = {}

    producer = str(meta.get("/Producer", "") or meta.get("Producer", "")).strip()
    creator = str(meta.get("/Creator", "") or meta.get("Creator", "")).strip()

    return {
        "raw_metadata": {k: str(v) for k, v in meta.items()} if isinstance(meta, dict) else {},
        "producer": producer,
        "creator": creator,
    }


def detect_signature_markers(reader: PdfReader) -> Dict[str, Any]:
    """
    Detect if there are any signature-related markers in the trailer.
    """
    raw = str(reader.trailer)

    markers = ["/Sig", "/ByteRange", "/Contents"]
    markers_found = {}
    total_hits = 0

    for m in markers:
        count = raw.count(m)
        markers_found[m] = count
        total_hits += count

    has_signature = total_hits > 0

    return {
        "has_signature": has_signature,
        "markers_found": markers_found,
        "raw_trailer_length": len(raw)
    }


def detect_suspicious_software(producer: str, creator: str) -> Dict[str, Any]:
    """
    Check if producer/creator match known suspicious or trusted software.
    """
    p = producer.lower()
    c = creator.lower()

    suspicious_hits = []
    trusted_hits = []

    for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
        if kw in p or kw in c:
            suspicious_hits.append(kw)

    for kw in TRUSTED_GENERATORS:
        if kw in p or kw in c:
            trusted_hits.append(kw)

    suspicious = len(suspicious_hits) > 0
    trusted = len(trusted_hits) > 0

    return {
        "suspicious": suspicious,
        "suspicious_keywords": suspicious_hits,
        "trusted": trusted,
        "trusted_keywords": trusted_hits
    }


def compute_ultra_forensic_score(
    signature_info: Dict[str, Any],
    struct_info: Dict[str, Any],
    meta_info: Dict[str, Any],
    soft_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine all signals into a single score 0..100 plus verdict & risk level.
    """

    score = 50  # neutral baseline
    reasons = []

    # 1) Digital signature presence
    if signature_info["has_signature"]:
        score += 30
        reasons.append("Digital signature markers found → strong sign of official issuance.")
    else:
        reasons.append("No digital signature markers found (normal for many real certificates).")

    # 2) Incremental updates / structural anomalies
    if struct_info["incremental_updates"]:
        score -= 15
        reasons.append("Incremental update markers found (PDF modified after initial creation).")

    if struct_info["obj_count"] < 5:
        score -= 5
        reasons.append("Very low object count – overly simple PDF (could be regenerated).")

    if struct_info["obj_count"] > 5000:
        score -= 10
        reasons.append("Very high object count – possibly merged or heavily edited PDF.")

    # 3) Suspicious vs trusted software
    if soft_info["trusted"]:
        score += 10
        reasons.append(
            f"Trusted PDF generator detected in producer/creator: {soft_info['trusted_keywords']}"
        )

    if soft_info["suspicious"]:
        score -= 20
        reasons.append(
            f"Suspicious editing software detected in producer/creator: {soft_info['suspicious_keywords']}"
        )

    # 4) Clamp the score
    if score > 100:
        score = 100
    if score < 0:
        score = 0

    # 5) Risk level + verdict
    if score >= 75:
        risk_level = "LOW"
        verdict = "LIKELY_ORIGINAL"
    elif score >= 45:
        risk_level = "MEDIUM"
        verdict = "UNCERTAIN"
    else:
        risk_level = "HIGH"
        verdict = "LIKELY_TAMPERED"

    return {
        "score": score,
        "verdict": verdict,
        "risk_level": risk_level,
        "reasons": reasons
    }


def ultra_forensic_signature_check(path: str) -> Dict[str, Any]:
    """
    Top-level function: runs ultra forensic analysis on a PDF.
    """
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}

    try:
        pdf_bytes = read_file_bytes(path)
    except Exception as e:
        return {"error": f"Unable to read file bytes: {e}"}

    try:
        reader = PdfReader(path)
    except Exception as e:
        return {"error": f"Failed to parse PDF with PyPDF2: {e}"}

    struct_info = analyze_raw_structure(pdf_bytes)
    meta_info = extract_metadata_info(reader)
    signature_info = detect_signature_markers(reader)
    soft_info = detect_suspicious_software(meta_info["producer"], meta_info["creator"])
    score_block = compute_ultra_forensic_score(signature_info, struct_info, meta_info, soft_info)

    result = {
        "verdict": score_block["verdict"],
        "final_score": score_block["score"],
        "risk_level": score_block["risk_level"],
        "signature_info": signature_info,
        "structure_info": struct_info,
        "metadata_info": {
            "producer": meta_info["producer"],
            "creator": meta_info["creator"],
            "raw_metadata": meta_info["raw_metadata"]
        },
        "software_classification": soft_info,
        "reasons": score_block["reasons"]
    }
    return result


def main():
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("Enter path to PDF: ").strip()

    out = ultra_forensic_signature_check(pdf_path)

    print("\n==== ULTRA FORENSIC SIGNATURE CHECK RESULT (JSON) ====\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
