import cv2
import numpy as np
import fitz  # PyMuPDF
import json
import os

def load_image(path):
    """Load image or convert PDF to image."""
    if path.lower().endswith(".pdf"):
        doc = fitz.open(path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        return img
    else:
        return cv2.imread(path)

def laplacian_variance(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def noise_residual(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = gray.astype("float32") - blur.astype("float32")
    return float(np.std(residual))

def edge_inconsistency(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return float(np.sum(edges) / edges.size)

def analyze_certificate(path):

    if not os.path.exists(path):
        return {"error": "File not found"}

    img = load_image(path)
    if img is None:
        return {"error": "Cannot load image (invalid format)"}

    lap_var = laplacian_variance(img)
    noise = noise_residual(img)
    edge_score = edge_inconsistency(img)

    # REAL CERTIFICATE RANGES
    real_lap_min = 80
    real_noise_min = 3
    real_edge_min = 0.005

    fake_score = 0
    reasons = []

    if lap_var < real_lap_min:
        fake_score += 30
        reasons.append("Low sharpness variance → likely edited.")

    if noise < real_noise_min:
        fake_score += 30
        reasons.append("Uniform noise pattern → digital modification.")

    if edge_score > 0.02:
        fake_score += 40
        reasons.append("Strong edge inconsistencies → pasted objects/text.")

    # FINAL VERDICT
    if fake_score >= 60:
        verdict = "TAMPERED"
    elif fake_score >= 30:
        verdict = "SUSPICIOUS"
    else:
        verdict = "ORIGINAL"

    return {
        "verdict": verdict,
        "score": float(100 - fake_score),
        "laplacian_variance": float(lap_var),
        "noise_residual": float(noise),
        "edge_inconsistency": float(edge_score),
        "reasons": reasons
    }

def main():
    path = input("Enter certificate file path (PDF/JPG/PNG): ").strip()
    result = analyze_certificate(path)

    print("\n==== FINAL LAYOUT FORGERY CHECK RESULT ====\n")
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
