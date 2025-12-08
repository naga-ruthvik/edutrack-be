import fitz  # PyMuPDF
import cv2
import numpy as np
import requests
import base64
import os
import json

# ---------------- Gemini Configuration ----------------
API_KEY = "AIzaSyApVVAscT2-5jucxd_draFZSIRPqcoQa7o"
API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key="

# -------------------------------------------------------


def extract_images_from_pdf(pdf_path, out_dir="auto_logos"):
    """
    Extracts reasonable-sized images from PDF.
    Removes tiny icons & full page images.
    """
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    saved = []

    for i, page in enumerate(doc):
        images = page.get_images(full=True)
        for idx, info in enumerate(images):
            xref = info[0]
            pix = fitz.Pixmap(doc, xref)

            # Convert to RGB or PNG
            if pix.n < 5:
                img_bytes = pix.tobytes("png")
            else:
                pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("png")

            # Read with OpenCV to filter sizes
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                continue

            h, w = img.shape[:2]

            # ---- Skip useless images ----
            if w < 80 or h < 80:
                continue  # too small
            if w > 1000 and h > 1000:
                continue  # full page image

            # Save filtered image
            save_path = os.path.join(out_dir, f"logo_{i+1}_{idx+1}.png")
            cv2.imwrite(save_path, img)
            saved.append(save_path)

    doc.close()
    return saved


def crop_logo_region(img_path):
    """
    Detects possible logo region using contour + thresholding.
    Returns cropped image path.
    """
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, 180, 255, cv2.THRESH_BINARY_INV)

    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not cnts:
        return img_path  # No crop → return original image

    # Get largest contour (likely logo/seal)
    cnt = max(cnts, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt)

    crop = img[y:y+h, x:x+w]
    cropped_path = img_path.replace(".png", "_crop.png")
    cv2.imwrite(cropped_path, crop)

    return cropped_path


def analyze_logo_with_gemini(img_path):
    """
    Sends cropped logo image to Gemini Vision AI for authenticity scoring.
    """

    prompt = """
You are an expert in detecting forged certificate logos.
Analyze the provided logo image and classify as:

- OFFICIAL → Matches real institutional branding
- FAKE → Edited, AI-generated, wrong colors, incorrect symmetry
- SUSPICIOUS → Low-quality, blurred, inconsistent edges
- UNKNOWN → Cannot determine

Return ONLY JSON:

{
  "verdict": "OFFICIAL or FAKE or SUSPICIOUS or UNKNOWN",
  "confidence": 0-100,
  "reason": "short explanation"
}
"""

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": img_b64
                        }
                    }
                ]
            }
        ]
    }

    try:
        res = requests.post(
            API_URL + API_KEY,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60
        )
        res.raise_for_status()
    except Exception as e:
        return {"error": f"Request failed: {e}"}

    try:
        data = res.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        # Extract JSON from text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])

        return {"raw_output": text}

    except Exception as e:
        return {"error": f"Parsing error: {e}", "raw": res.text}


# ------------------------- MAIN ------------------------

if __name__ == "__main__":
    pdf = input("Enter certificate path (PDF/PNG/JPG): ").strip()

    if not os.path.exists(pdf):
        print("❌ File not found.")
        exit()

    print("\n📌 Extracting possible logo images...")
    extracted = extract_images_from_pdf(pdf)

    print(f"Found {len(extracted)} logo candidates.\n")

    if len(extracted) == 0:
        print("⚠️ No images or logos detected in PDF.")
        exit()

    final_results = []

    print("\n🔎 Running Gemini Logo Authenticity Check...\n")

    for img in extracted:
        cropped = crop_logo_region(img)
        print(f"Analyzing: {cropped}")

        result = analyze_logo_with_gemini(cropped)
        final_results.append({"image": cropped, "result": result})

        print(json.dumps(result, indent=4))
        print("-" * 60)

    print("\n✅ COMPLETED LOGO VERIFICATION\n")
