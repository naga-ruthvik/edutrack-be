#!/usr/bin/env python3
"""
phash_check.py

Perceptual-hash (pHash) similarity check for certificate files.

Usage:
    python phash_check.py /path/to/uploaded_certificate.pdf
    python phash_check.py /path/to/uploaded_image.png --db phash_db/

Place reference originals (PDFs or images) inside the folder `phash_db/` (or override with --db).
The script compares uploaded file's pHash to every file in the DB and reports best match.

Requires:
    pip install pillow imagehash PyMuPDF numpy

"""
import os
import sys
import io
import json
import argparse
from typing import Tuple, Dict, Any, List

try:
    import fitz  # PyMuPDF
except Exception as e:
    fitz = None
from PIL import Image, ImageOps
import imagehash
import numpy as np

HASH_SIZE = 8  # default phash size -> 8 => 64-bit hash
MAX_DIST = HASH_SIZE * HASH_SIZE  # maximum Hamming distance for phash

# thresholds (tune these)
EXACT_THRESHOLD = 5        # <= => very likely original (small visual differences)
LIKELY_THRESHOLD = 12      # <= => possible match (compressed / small edits)
# > LIKELY_THRESHOLD => probably no match


def pdf_first_page_image_bytes(path: str, dpi: int = 300) -> bytes:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required to read PDFs. Install with: pip install PyMuPDF")
    doc = fitz.open(path)
    if doc.page_count < 1:
        doc.close()
        raise RuntimeError("PDF has no pages")
    page = doc.load_page(0)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes


def load_image_from_path(path: str) -> Image.Image:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".pdf"]:
        img_bytes = pdf_first_page_image_bytes(path)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    else:
        img = Image.open(path).convert("RGB")
    # deterministic orientation
    img = ImageOps.exif_transpose(img)
    return img


def canonicalize_image(img: Image.Image, width_px: int = 1200) -> Image.Image:
    # Resize keeping aspect ratio to a deterministic width
    w, h = img.size
    scale = width_px / w
    new_size = (width_px, max(1, int(h * scale)))
    img = img.resize(new_size, Image.LANCZOS)
    return img


def compute_phash_for_image(img: Image.Image, hash_size: int = HASH_SIZE) -> imagehash.ImageHash:
    return imagehash.phash(img, hash_size=hash_size)


def compute_phash_for_file(path: str) -> Tuple[str, imagehash.ImageHash]:
    img = load_image_from_path(path)
    img = canonicalize_image(img)
    ph = compute_phash_for_image(img)
    return str(ph), ph


def hamming_distance(hash_a: imagehash.ImageHash, hash_b: imagehash.ImageHash) -> int:
    # imagehash ImageHash supports '-' operator to compute distance
    return int(hash_a - hash_b)


def compare_against_db(upload_hash: imagehash.ImageHash, db_folder: str) -> List[Dict[str, Any]]:
    results = []
    if not os.path.isdir(db_folder):
        return results
    for fname in sorted(os.listdir(db_folder)):
        fpath = os.path.join(db_folder, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            _, db_hash = compute_phash_for_file(fpath)
            dist = hamming_distance(upload_hash, db_hash)
            score_pct = round((1.0 - (dist / MAX_DIST)) * 100.0, 2)  # similarity percent
            results.append({
                "db_file": fname,
                "db_path": fpath,
                "phash": str(db_hash),
                "distance": dist,
                "similarity_pct": score_pct
            })
        except Exception as e:
            # skip files that can't be read
            results.append({
                "db_file": fname,
                "error": f"failed to process db file: {e}"
            })
    # sort by ascending distance (best match first)
    results.sort(key=lambda x: x.get("distance", 9999))
    return results


def verdict_from_best_distance(dist: int) -> Tuple[str, str]:
    if dist <= EXACT_THRESHOLD:
        return "ORIGINAL", "Distance <= exact threshold (very close visual match)."
    if dist <= LIKELY_THRESHOLD:
        return "POSSIBLE_MATCH", "Distance within likely threshold (resized/compressed or minor edit)."
    return "NO_MATCH", "No close match in database (distance too large)."


def analyze(upload_path: str, db_folder: str = "phash_db") -> Dict[str, Any]:
    if not os.path.isfile(upload_path):
        return {"error": f"File not found: {upload_path}"}

    try:
        phash_str, phash_obj = compute_phash_for_file(upload_path)
    except Exception as e:
        return {"error": f"Failed to compute pHash for upload: {e}"}

    db_results = compare_against_db(phash_obj, db_folder)

    best = db_results[0] if db_results else None
    if best and "distance" in best:
        verdict, reason = verdict_from_best_distance(best["distance"])
        best_match = {
            "db_file": best.get("db_file"),
            "distance": best.get("distance"),
            "similarity_pct": best.get("similarity_pct"),
            "phash": best.get("phash")
        }
    else:
        verdict = "NO_DB"
        reason = "No reference files found in database folder."
        best_match = None

    result = {
        "verdict": verdict,
        "reason": reason,
        "uploaded_file": os.path.basename(upload_path),
        "uploaded_phash": phash_str,
        "best_match": best_match,
        "all_matches": db_results,
        "thresholds": {
            "exact_threshold": EXACT_THRESHOLD,
            "likely_threshold": LIKELY_THRESHOLD,
            "hash_size": HASH_SIZE,
            "max_distance": MAX_DIST
        }
    }
    return result


def main():
    p = argparse.ArgumentParser(description="Perceptual hash (pHash) certificate similarity check")
    p.add_argument("path", help="Path to uploaded certificate (PDF/PNG/JPG)")
    p.add_argument("--db", default="phash_db", help="Folder containing reference originals (default: phash_db)")
    p.add_argument("--width", type=int, default=1200, help="Canonical width for rasterizing (default 1200 px)")
    args = p.parse_args()

    # allow override width by global canonicalize_image if provided
    global canonicalize_image
    def canonicalize_image_override(img, width_px=args.width):
        w, h = img.size
        scale = width_px / w
        new_size = (width_px, max(1, int(h * scale)))
        return img.resize(new_size, Image.LANCZOS)
    canonicalize_image = canonicalize_image_override

    res = analyze(args.path, args.db)
    print("\n==== PHASH SIMILARITY RESULT ====\n")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
