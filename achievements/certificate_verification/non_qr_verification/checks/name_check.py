import fitz
import cv2
import numpy as np
import easyocr
import json
import re
from difflib import SequenceMatcher
from PIL import Image, ImageChops, ImageEnhance


reader = easyocr.Reader(['en'], gpu=False)

# ----------------------------------------------------
# LOAD IMAGE FROM PDF OR PNG/JPG
# ----------------------------------------------------
def load_image(path):
    if path.lower().endswith(".pdf"):
        try:
            doc = fitz.open(path)
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
            return img
        except:
            return None

    return cv2.imread(path)


# ----------------------------------------------------
# OCR EXTRACTION
# ----------------------------------------------------
def extract_text(img):
    try:
        results = reader.readtext(img, detail=0)
        text = " ".join(results).lower()
        return text
    except:
        return ""


# ----------------------------------------------------
# FONT CONSISTENCY CHECK
# ----------------------------------------------------
def font_variance_score(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 180)

    var = np.var(edges)
    if var < 300:  # too clean (fake edits usually smoother)
        return 20, "Font edges too smooth — possible editing"
    elif var > 3000:  # too noisy
        return 20, "Font edges too uneven — inconsistent font usage"

    return 90, "Font consistency normal"


# ----------------------------------------------------
# SPELLING ERROR CHECK
# ----------------------------------------------------
def spelling_score(text):
    dictionary = [
        "certificate", "awarded", "successfully", "completed",
        "course", "instructor", "engineering", "technology",
        "institute", "verify", "score", "credits"
    ]

    words = re.findall(r"[a-zA-Z]+", text)
    errors = [w for w in words if len(w) > 5 and w not in dictionary]

    if len(errors) > 20:
        return 20, errors[:20]

    return 100 - len(errors) * 2, errors[:10]


# ----------------------------------------------------
# KEYWORD REASONABLENESS CHECK
# (NO PLATFORM NEEDED)
# ----------------------------------------------------
def keyword_score(text):
    required = ["certificate", "course", "awarded", "completed"]
    hits = sum(k in text for k in required)

    if hits == 0:
        return 10, hits

    return hits * 25, hits


# ----------------------------------------------------
# NUMBER / MARKS CONSISTENCY CHECK
# ----------------------------------------------------
def marks_score(text):
    marks = re.findall(r"\d+\.\d+\/\d+", text)  # like 17.71/25
    totals = re.findall(r"\b\d{2,3}\b", text)

    if len(marks) > 3:
        return 20, marks

    return 90, marks


# ----------------------------------------------------
# TEXT ALIGNMENT CHECK
# ----------------------------------------------------
def alignment_score(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    proj = np.sum(gray, axis=1)

    variance = np.var(proj)

    if variance < 1e7:
        return 25, "Text alignment inconsistent"

    return 95, "Text alignment normal"


# ----------------------------------------------------
# FINAL ANALYSIS ENGINE
# ----------------------------------------------------
def analyze(path):

    img = load_image(path)
    if img is None:
        return {"verdict": "ERROR", "reason": "Unable to open image"}

    text = extract_text(img)

    scores = {}

    scores["font_score"], font_reason = font_variance_score(img)
    scores["spell_score"], spelling_errors = spelling_score(text)
    scores["keyword_score"], key_hits = keyword_score(text)
    scores["marks_score"], marks = marks_score(text)
    scores["alignment_score"], align_reason = alignment_score(img)

    total = (
        scores["font_score"] * 0.25 +
        scores["spell_score"] * 0.25 +
        scores["keyword_score"] * 0.25 +
        scores["alignment_score"] * 0.15 +
        scores["marks_score"] * 0.10
    )

    if total >= 80:
        verdict = "ORIGINAL"
    elif total >= 55:
        verdict = "SUSPICIOUS"
    else:
        verdict = "FAKE"

    return {
        "verdict": verdict,
        "final_score": round(total, 2),
        "components": scores,
        "reasons": [
            font_reason,
            align_reason,
            f"{len(spelling_errors)} suspected spelling anomalies",
            f"{key_hits} required keywords found"
        ],
        "marks_detected": marks,
        "text_preview": text[:200]
    }



# ----------------------------------------------------
if __name__ == "__main__":
    path = input("Enter certificate path: ").strip()
    out = analyze(path)
    print("\n==== FIELD CONSISTENCY CHECK RESULT ====\n")
    print(json.dumps(out, indent=4))
