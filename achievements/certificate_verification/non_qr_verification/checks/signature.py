import cv2
import numpy as np
import fitz  # PyMuPDF
import json
import os
from skimage.metrics import structural_similarity as ssim

# ---------------------------------------------------------
# LOAD OFFICIAL SIGNATURE TEMPLATE
# ---------------------------------------------------------
OFFICIAL_SIGNATURE = "official_signature.png"

if not os.path.exists(OFFICIAL_SIGNATURE):
    print("ERROR: official_signature.png NOT FOUND!")
    print("Please place the authorized signature inside the folder.")
    exit()

official_sig = cv2.imread(OFFICIAL_SIGNATURE)
official_sig_gray = cv2.cvtColor(official_sig, cv2.COLOR_BGR2GRAY)

# ---------------------------------------------------------
# UTILITY: Extract signature area from PDF
# ---------------------------------------------------------
def extract_signature_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    output = None

    for page in doc:
        blocks = page.get_text("blocks")
        # Try to capture images near "Signature", "Signed", "Authorized" region
        for block in blocks:
            text = block[4].lower()
            if "sign" in text or "signature" in text or "authorized" in text:
                # Extract the bounding box area
                x1, y1, x2, y2 = block[:4]
                zoom = 3
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, clip=(x1, y1, x2, y2))
                img_bytes = pix.tobytes("png")
                output = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                break

    doc.close()
    return output

# ---------------------------------------------------------
# SIGNATURE MATCHING FUNCTIONS
# ---------------------------------------------------------
def orb_similarity(img1, img2):
    orb = cv2.ORB_create(1000)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        return 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    if len(matches) == 0:
        return 0

    good = [m for m in matches if m.distance < 70]
    return len(good) / len(matches)

def edge_density(img):
    edges = cv2.Canny(img, 50, 150)
    return np.sum(edges > 0) / edges.size

def ssim_score(img1, img2):
    img1 = cv2.resize(img1, (300, 100))
    img2 = cv2.resize(img2, (300, 100))
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return score

# ---------------------------------------------------------
# MAIN CHECK
# ---------------------------------------------------------
def analyze_signature(pdf_path):
    sig = extract_signature_from_pdf(pdf_path)
    if sig is None:
        return {
            "verdict": "NOT_FOUND",
            "reason": "Signature region not detected in certificate."
        }

    # Resize both
    sig_r = cv2.resize(sig, (300, 100))
    official_r = cv2.resize(official_sig, (300, 100))

    # Compute metrics
    orb_sim = orb_similarity(sig_r, official_r)
    ssim_sim = ssim_score(sig_r, official_r)
    edge_diff = abs(edge_density(sig_r) - edge_density(official_r))

    # Scoring
    final_score = (orb_sim * 40) + (ssim_sim * 50) + ((1 - edge_diff) * 10)

    verdict = "ORIGINAL" if final_score >= 65 else "FAKE"

    return {
        "verdict": verdict,
        "score": round(final_score, 2),
        "metrics": {
            "orb_similarity": round(orb_sim, 3),
            "ssim_similarity": round(ssim_sim, 3),
            "edge_difference": round(edge_diff, 3)
        }
    }


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    path = input("Enter certificate PDF path: ").strip()

    result = analyze_signature(path)

    print("\n==== SIGNATURE VERIFICATION RESULT ====\n")
    print(json.dumps(result, indent=4))
