# ela_check.py  — FINAL SIH VERSION (COMPLETE)

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import io
import os
import json


# ---------------------------------------------------
# 1. Extract raster images
# ---------------------------------------------------
def extract_first_raster_image(pdf_path):
    """
    Extracts the first raster image from the PDF.
    If no raster images → returns None (meaning ELA cannot be applied).
    """
    doc = fitz.open(pdf_path)
    for page in doc:
        imgs = page.get_images(full=True)
        for im in imgs:
            xref = im[0]
            img = doc.extract_image(xref)
            if img and img.get("image"):
                return img["image"]  # return bytes
    return None


# ---------------------------------------------------
# 2. Run Error Level Analysis
# ---------------------------------------------------
def run_ela(image_bytes, quality=90):
    """Runs ELA and returns the ELA diff array."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Recompress
    buff = io.BytesIO()
    img.save(buff, format="JPEG", quality=quality)
    recompressed = Image.open(io.BytesIO(buff.getvalue())).convert("RGB")

    # Compute difference
    arr1 = np.asarray(img).astype(np.int16)
    arr2 = np.asarray(recompressed).astype(np.int16)

    diff = np.abs(arr1 - arr2).astype(np.uint8)
    return diff


# ---------------------------------------------------
# 3. ELA statistics → decide tampering
# ---------------------------------------------------
def analyze_ela(diff):
    gray = diff.mean(axis=2)

    mean_ela = float(np.mean(gray))
    std_ela = float(np.std(gray))

    # count high ELA areas (sensitive threshold)
    high_mask = gray > 40
    high_ratio = float(high_mask.sum() / gray.size)

    return {
        "mean_ela": mean_ela,
        "std_ela": std_ela,
        "high_ratio": high_ratio,
        "high_threshold": 40.0
    }


# ---------------------------------------------------
# 4. Main ELA check logic
# ---------------------------------------------------
def ela_check(pdf_path):
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}

    # Extract raster image
    img_bytes = extract_first_raster_image(pdf_path)

    if img_bytes is None:
        return {
            "verdict": "NOT_APPLICABLE",
            "score": 50,
            "reason": "PDF contains only vector graphics (no raster image). ELA cannot be applied safely."
        }

    # Run ELA
    diff = run_ela(img_bytes)
    stats = analyze_ela(diff)

    mean_e = stats["mean_ela"]
    high_r = stats["high_ratio"]

    reasons = []

    # Classification thresholds (tuned)
    if high_r > 0.03:
        verdict = "LIKELY_TAMPERED"
        score = 30
        reasons.append("Large high-ELA regions detected — strong sign of editing.")
    elif high_r > 0.01:
        verdict = "SUSPICIOUS"
        score = 55
        reasons.append("Moderate ELA spikes — possible local edits.")
    else:
        verdict = "LIKELY_ORIGINAL"
        score = 85
        reasons.append("Very low ELA variations — no visible tampering.")
    
    reasons.append(f"mean_ela={mean_e:.2f}")
    reasons.append(f"high_ratio={high_r:.4f}")

    return {
        "verdict": verdict,
        "score": score,
        "ela_stats": stats,
        "reasons": reasons
    }


# ---------------------------------------------------
# 5. CLI wrapper
# ---------------------------------------------------
def main():
    pdf_path = input("Enter path to PDF: ").strip()
    result = ela_check(pdf_path)

    print("\n==== ELA TAMPERING CHECK RESULT (JSON) ====\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
