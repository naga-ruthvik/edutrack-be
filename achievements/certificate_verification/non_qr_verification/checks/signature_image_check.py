import os, sys, json, io
import numpy as np
import cv2
from PIL import Image
import fitz
from pdf2image import convert_from_path

POPPLER_PATH = r"C:\poppler\Library\bin"   # CHANGE IF NEEDED


# -----------------------------------------
# PDF → Image Extraction (Robust)
# -----------------------------------------
def pdf_to_image(path):
    # Try pdf2image first
    try:
        pages = convert_from_path(path, dpi=300, poppler_path=POPPLER_PATH)
        return pages[0].convert("RGB")
    except:
        pass

    # Fallback to PyMuPDF
    try:
        doc = fitz.open(path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        doc.close()
        return img
    except:
        return None


def load_image(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return pdf_to_image(path)
    return Image.open(path).convert("RGB")


# -----------------------------------------
# Signature Region Detection
# -----------------------------------------
def find_signature_region(img):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # Basic threshold to find ink
    _, bw = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch

        # Signature expected in lower 40% of certificate
        if y > h * 0.5 and 800 < area < 30000:
            regions.append((x, y, cw, ch))

    if not regions:
        return None

    # Pick largest signature-looking region
    x, y, cw, ch = max(regions, key=lambda b: b[2] * b[3])
    return img.crop((x, y, x + cw, y + ch))


# -----------------------------------------
# Stroke width variation
# -----------------------------------------
def stroke_score(region):
    gray = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # Distance transform (approx stroke width)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    pts = dist[dist > 0]

    if len(pts) < 50:
        return 999  # too small to evaluate

    return float(np.std(pts))


# -----------------------------------------
# ELA (Error Level Analysis)
# -----------------------------------------
def ela_score(region):
    from PIL import ImageChops
    buf = io.BytesIO()
    region.save(buf, "JPEG", quality=85)
    rec = Image.open(buf).convert("RGB")
    diff = ImageChops.difference(region, rec)
    diff_gray = cv2.cvtColor(np.array(diff), cv2.COLOR_RGB2GRAY)
    return float(np.mean(diff_gray))


# -----------------------------------------
# Final signature evaluation
# -----------------------------------------
def verify_signature(path):
    img = load_image(path)

    if img is None:
        return {
            "verdict": "ERROR",
            "confidence": 0,
            "reason": "Failed to read PDF/image"
        }

    region = find_signature_region(img)

    # -----------------------------------------
    # CASE 1: No signature found → score = 0
    # -----------------------------------------
    if region is None:
        return {
            "verdict": "NO_SIGNATURE",
            "confidence": 0,
            "reason": "No signature detected in the certificate"
        }

    # -----------------------------------------
    # CASE 2: Signature exists → compute scores
    # -----------------------------------------
    sw = stroke_score(region)
    ela = ela_score(region)

    score = 50
    reasons = []

    # Stroke consistency
    if sw < 3:
        score += 30
        reasons.append("Natural handwritten signature")
    elif sw < 7:
        score += 10
        reasons.append("Moderate signature variation")
    else:
        score -= 20
        reasons.append("Digitally pasted signature suspected")

    # Tampering via ELA
    if ela > 18:
        score -= 25
        reasons.append("ELA indicates signature region editing")
    else:
        reasons.append("No major ELA tampering marks")

    score = max(0, min(100, score))

    if score >= 70:
        verdict = "ORIGINAL_SIGNATURE"
    elif score <= 40:
        verdict = "FAKE_SIGNATURE"
    else:
        verdict = "UNCERTAIN"

    return {
        "verdict": verdict,
        "confidence": round(score / 100, 2),
        "reason": reasons[0]  # only one reason needed
    }


# -----------------------------------------
# CLI
# -----------------------------------------
if __name__ == "__main__":
    path = input("Enter certificate path: ").strip()
    result = verify_signature(path)

    print("\n==== SIGNATURE VERIFICATION RESULT ====\n")
    print(json.dumps(result, indent=4))
