import cv2
import numpy as np
import os
import fitz
import json
import math

# ---------------- OFFICIAL BRAND COLORS ----------------
OFFICIAL_BRANDS = {
    "NPTEL": ["#F58220"],
    "Coursera": ["#0056D2"],
    "IIT": ["#A52A2A"],
    "GUVI": ["#00C853"],
    "Cisco": ["#1BA0E2"],
    "Microsoft": ["#F25022", "#7FBA00", "#00A4EF", "#FFB900"]
}

# ---------------- COLOR UTILITIES ----------------
def hex_to_rgb(hex_color):
    hex_color = hex_color.replace("#", "")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_lab(rgb):
    """Convert RGB tuple to LAB color space."""
    rgb = np.array([[rgb]], dtype=np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[0][0]
    return lab.astype(float)


# ---------------- CIEDE2000 ΔE formula ----------------
def delta_e_ciede2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_L = (L1 + L2) / 2.0
    C1 = math.sqrt(a1**2 + b1**2)
    C2 = math.sqrt(a2**2 + b2**2)
    avg_C = (C1 + C2) / 2.0

    G = 0.5 * (1 - math.sqrt((avg_C**7) / (avg_C**7 + 25**7)))
    a1p = (1 + G) * a1
    a2p = (1 + G) * a2

    C1p = math.sqrt(a1p**2 + b1**2)
    C2p = math.sqrt(a2p**2 + b2**2)

    deltahp = math.degrees(math.atan2(b2, a2p) - math.atan2(b1, a1p))

    if deltahp > 180:
        deltahp -= 360
    elif deltahp < -180:
        deltahp += 360

    delta_Hp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(deltahp / 2.0))

    delta_Lp = L2 - L1
    delta_Cp = C2p - C1p

    avg_hp = (math.degrees(math.atan2(b1, a1p)) + math.degrees(math.atan2(b2, a2p))) / 2.0

    T = (
        1
        - 0.17 * math.cos(math.radians(avg_hp - 30))
        + 0.24 * math.cos(math.radians(2 * avg_hp))
        + 0.32 * math.cos(math.radians(3 * avg_hp + 6))
        - 0.20 * math.cos(math.radians(4 * avg_hp - 63))
    )

    SL = 1 + (0.015 * (avg_L - 50)**2) / math.sqrt(20 + (avg_L - 50)**2)
    SC = 1 + 0.045 * avg_C
    SH = 1 + 0.015 * avg_C * T

    delta_ro = 30 * math.exp(-((avg_hp - 275) / 25)**2)
    RC = 2 * math.sqrt((avg_C**7) / (avg_C**7 + 25**7))

    RT = -RC * math.sin(math.radians(2 * delta_ro))

    delta_E = math.sqrt(
        (delta_Lp / SL)**2 +
        (delta_Cp / SC)**2 +
        (delta_Hp / SH)**2 +
        RT * (delta_Cp / SC) * (delta_Hp / SH)
    )

    return delta_E


# ---------------- PDF IMAGE EXTRACTION ----------------
def extract_image_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)

    for page in doc:
        images = page.get_images(full=True)
        if not images:
            continue

        xref = images[0][0]
        pix = fitz.Pixmap(doc, xref)

        if pix.n < 5:
            img_bytes = pix.tobytes("png")
        else:
            pix = fitz.Pixmap(fitz.csRGB, pix)
            img_bytes = pix.tobytes("png")

        doc.close()
        return cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    return None


# ---------------- Dominant Color Extraction ----------------
def get_dominant_colors(img, k=5):
    img_small = cv2.resize(img, (300, 300))
    Z = img_small.reshape((-1, 3))
    Z = np.float32(Z)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, _, centers = cv2.kmeans(Z, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    centers = np.uint8(centers)

    # convert numpy uint8 → Python int
    return [tuple(int(x) for x in center) for center in centers]


# ---------------- MAIN COLOR CHECK ----------------
def analyze_color_palette(img):
    dom_colors = get_dominant_colors(img)

    best_brand = None
    best_score = 9999

    for brand, colors in OFFICIAL_BRANDS.items():
        for hex_c in colors:
            rgb_ref = hex_to_rgb(hex_c)

            for c in dom_colors:
                lab1 = rgb_to_lab(c)
                lab2 = rgb_to_lab(rgb_ref)

                score = delta_e_ciede2000(lab1, lab2)

                if score < best_score:
                    best_score = score
                    best_brand = brand

    if best_score < 25:
        verdict = "ORIGINAL"
    elif best_score < 60:
        verdict = "SUSPICIOUS"
    else:
        verdict = "FAKE"

    return {
        "verdict": verdict,
        "delta_e": float(best_score),
        "brand_detected": best_brand,
        "dominant_colors": dom_colors     # already safe Python ints
    }


# ---------------- MAIN ENTRY ----------------
if __name__ == "__main__":
    path = input("Enter certificate (PDF/PNG) path: ").strip()

    if not os.path.exists(path):
        print("❌ File not found!")
        exit()

    if path.lower().endswith(".pdf"):
        img = extract_image_from_pdf(path)
    else:
        img = cv2.imread(path)

    if img is None:
        print("❌ Could not load image.")
        exit()

    result = analyze_color_palette(img)

    print("\n==== COLOR CHECK RESULT ====\n")
    print(json.dumps(result, indent=4))
