#!/usr/bin/env python3
"""
visual_fingerprint_check.py

Canonical visual fingerprint check for certificates.

Features:
- Computes binary SHA-256 of PDF
- Renders first page to canonical PNG and hashes it
- Computes perceptual hash (pHash)
- If a second PDF is provided, compares:
    * binary hash equality
    * canonical image hash equality
    * pHash distance & similarity
    * verdict: EXACT_MATCH / LIKELY_SAME_TEMPLATE / LIKELY_TAMPERED

Run with:
    python visual_fingerprint_check.py
or:
    python visual_fingerprint_check.py path/to/file.pdf
or:
    python visual_fingerprint_check.py original.pdf uploaded.pdf
"""

import sys
import os
import io
import json
import hashlib
from typing import Dict, Any, Optional

import fitz  # PyMuPDF
from PIL import Image, ImageOps
import imagehash


# -----------------------------
# Helper: compute SHA-256
# -----------------------------
def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


# -----------------------------
# Helper: render first page canonically
# -----------------------------
def render_canonical_png(pdf_bytes: bytes, dpi: int = 300, width_px: int = 2480) -> bytes:
    """
    Render the first page of the PDF to a PNG in a deterministic way.
    - fixed DPI (default 300)
    - resized to fixed width
    - no EXIF rotation issues
    Returns PNG bytes.
    """
    # Open in memory
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        doc.close()
        raise ValueError("PDF has no pages")

    page = doc.load_page(0)
    # matrix for given DPI
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()

    # Normalize with Pillow
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    img = ImageOps.exif_transpose(img)  # fix orientation if any
    w, h = img.size
    if w == 0 or h == 0:
        raise ValueError("Rendered image has invalid size")

    scale = width_px / float(w)
    new_size = (width_px, int(h * scale))
    img = img.resize(new_size, Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


# -----------------------------
# Helper: compute pHash from PNG bytes
# -----------------------------
def compute_phash_from_png(png_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    ph = imagehash.phash(img)
    return str(ph)


# -----------------------------
# Core: fingerprint a single PDF
# -----------------------------
def fingerprint_pdf(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}

    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        return {"error": f"Unable to read file: {e}"}

    try:
        binary_hash = sha256_bytes(pdf_bytes)
    except Exception as e:
        return {"error": f"Unable to compute binary hash: {e}"}

    try:
        canonical_png = render_canonical_png(pdf_bytes)
        canonical_hash = sha256_bytes(canonical_png)
        phash = compute_phash_from_png(canonical_png)
    except Exception as e:
        return {
            "error": f"Failed to render or hash canonical image: {e}",
            "binary_hash": binary_hash
        }

    return {
        "binary_hash": binary_hash,
        "canonical_hash": canonical_hash,
        "phash": phash
    }


# -----------------------------
# Compare two fingerprints
# -----------------------------
def compare_fingerprints(fp1: Dict[str, Any], fp2: Dict[str, Any]) -> Dict[str, Any]:
    # Handle error cases first
    if "error" in fp1 or "error" in fp2:
        return {
            "error": "Cannot compare because one or both fingerprints have errors.",
            "fp1": fp1,
            "fp2": fp2
        }

    b1 = fp1["binary_hash"]
    b2 = fp2["binary_hash"]
    c1 = fp1["canonical_hash"]
    c2 = fp2["canonical_hash"]
    p1 = imagehash.ImageHash.from_hex(fp1["phash"])
    p2 = imagehash.ImageHash.from_hex(fp2["phash"])

    same_binary = (b1 == b2)
    same_canonical = (c1 == c2)
    phash_distance = int(p1 - p2)  # Hamming distance between phashes
    max_bits = 64  # phash is 64 bits by default
    phash_similarity = round(100.0 * (1.0 - phash_distance / max_bits), 2)

    # Verdict logic
    reasons = []
    if same_binary and same_canonical:
        verdict = "EXACT_MATCH"
        reasons.append("Binary and canonical hashes are identical (bit-perfect match).")
    else:
        if phash_similarity >= 90.0:
            verdict = "LIKELY_SAME_TEMPLATE"
            reasons.append(
                f"High visual similarity (pHash similarity ≈ {phash_similarity}%). Layout likely same."
            )
            if not same_binary:
                reasons.append("Binary hashes differ → some minor change (metadata or compression).")
        elif phash_similarity >= 70.0:
            verdict = "POSSIBLY_SAME_TEMPLATE"
            reasons.append(
                f"Moderate visual similarity (pHash similarity ≈ {phash_similarity}%)."
            )
            reasons.append("Manual review recommended.")
        else:
            verdict = "LIKELY_TAMPERED"
            reasons.append(
                f"Low visual similarity (pHash similarity ≈ {phash_similarity}%). Layout/content changed."
            )

    return {
        "verdict": verdict,
        "same_binary": same_binary,
        "same_canonical": same_canonical,
        "phash_distance": phash_distance,
        "phash_similarity_percent": phash_similarity,
        "reasons": reasons,
        "fingerprint_1": fp1,
        "fingerprint_2": fp2
    }


# -----------------------------
# Main CLI
# -----------------------------
def main():
    args = sys.argv[1:]

    if len(args) == 0:
        # Single-file mode: compute fingerprint only
        pdf_path = input("Enter path to PDF: ").strip()
        fp = fingerprint_pdf(pdf_path)
        print("\n==== VISUAL FINGERPRINT (SINGLE PDF) ====\n")
        print(json.dumps(fp, indent=2))
    elif len(args) == 1:
        # Single-file mode from argument
        pdf_path = args[0]
        fp = fingerprint_pdf(pdf_path)
        print("\n==== VISUAL FINGERPRINT (SINGLE PDF) ====\n")
        print(json.dumps(fp, indent=2))
    else:
        # Two-file compare mode
        pdf_path_1 = args[0]
        pdf_path_2 = args[1]
        fp1 = fingerprint_pdf(pdf_path_1)
        fp2 = fingerprint_pdf(pdf_path_2)
        comp = compare_fingerprints(fp1, fp2)
        print("\n==== VISUAL FINGERPRINT COMPARISON (TWO PDFs) ====\n")
        print(json.dumps(comp, indent=2))


if __name__ == "__main__":
    main()
