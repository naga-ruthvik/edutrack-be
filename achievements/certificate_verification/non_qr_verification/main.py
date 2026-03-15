# main.py — Universal Certificate Verifier (integrator)
# Place this in the project root (same level as checks/).

import os
import sys
import json
import traceback
import importlib.util
from types import ModuleType
from contextlib import contextmanager
from typing import Any, Dict, Tuple

# ---------- CONFIG ----------
CHECKS_DIR = os.path.join(os.path.dirname(__file__), "checks")
CHECK_MODULES = [
    "color_check",
    "ela_check",
    "logo_check",
    "metadata_check",
    "name_check",
    "phash_check",
    "signature",
    "signature_check",
    "signature_image_check",
    "ssim_check",
    "text_check",
    "visual_fingerprint_check"
]

TOTAL = 100.0
META_WEIGHT = 50.0
OTHER_TOTAL = TOTAL - META_WEIGHT
NUM_OTHER = len(CHECK_MODULES) - 1
OTHER_WEIGHT_EACH = OTHER_TOTAL / NUM_OTHER if NUM_OTHER > 0 else 0.0

WEIGHTS = {m: (META_WEIGHT if m == "metadata_check" else OTHER_WEIGHT_EACH) for m in CHECK_MODULES}

REPORT_PATH = os.path.join(os.path.dirname(__file__), "report.json")


# ---------- UTILITIES ----------
@contextmanager
def chdir(path: str):
    old = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)


def load_module_from_path(module_name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"__checks__{module_name}", path)
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    loader.exec_module(module)
    return module


def extract_numeric_score(output: Any) -> Tuple[float, str]:
    if output is None:
        return 50.0, "UNKNOWN"

    if isinstance(output, dict):
        if "error" in output:
            return 0.0, "ERROR"

        for k in ("final_score", "finalScore", "finalscore"):
            if k in output and isinstance(output[k], (int, float)):
                return float(output[k]), str(output.get("final_verdict") or output.get("verdict") or "")

        if "score" in output:
            return float(output["score"]), str(output.get("verdict") or "")

        if "confidence" in output:
            c = float(output["confidence"])
            return (c * 100 if c <= 1 else c), str(output.get("verdict") or "")

        # Map verdict keywords
        v = str(output.get("verdict", "")).upper()
        if v in ("EXACT_MATCH", "ORIGINAL", "LIKELY_ORIGINAL"):
            return 100.0, v
        if v in ("POSSIBLE_MATCH", "LIKELY_SAME_TEMPLATE", "POSSIBLE"):
            return 70.0, v
        if v in ("NO_MATCH", "LIKELY_TAMPERED", "FAKE"):
            return 0.0, v
        if v in ("NO_DB", "UNKNOWN", ""):
            return 50.0, v

        # Deep search
        for val in output.values():
            if isinstance(val, dict):
                s, vv = extract_numeric_score(val)
                return s, vv

    if isinstance(output, (int, float)):
        return float(output), "NUMERIC"

    return 50.0, "UNKNOWN"


# ---------- MODULE RUNNER ----------
def run_check_module(module_name: str, pdf_path: str):
    module_file = os.path.join(CHECKS_DIR, f"{module_name}.py")
    if not os.path.isfile(module_file):
        return {"error": f"module file not found: {module_file}"}

    try:
        with chdir(CHECKS_DIR):
            module = load_module_from_path(module_name, module_file)
    except Exception as e:
        return {"error": f"import_failed: {e}", "trace": traceback.format_exc()}

    try:
        # Individual module handlers
        if module_name == "color_check":
            if hasattr(module, "extract_image_from_pdf") and hasattr(module, "analyze_color_palette"):
                try:
                    img = module.extract_image_from_pdf(pdf_path)
                except:
                    img = None
                if img is None:
                    try:
                        import cv2
                        img = cv2.imread(pdf_path)
                    except:
                        img = None
                return module.analyze_color_palette(img)

        if module_name == "ela_check":
            return module.ela_check(pdf_path)

        if module_name == "logo_check":
            results = {"candidates": []}
            try:
                imgs = module.extract_images_from_pdf(pdf_path)
                for im in imgs:
                    crop = module.crop_logo_region(im) if hasattr(module, "crop_logo_region") else im
                    if hasattr(module, "analyze_logo_with_gemini"):
                        res = module.analyze_logo_with_gemini(crop)
                        results["candidates"].append({"image": crop, "result": res})
            except Exception as e:
                return {"error": str(e)}
            return results

        if module_name == "metadata_check":
            return module.run_metadata_check(pdf_path)

        if module_name == "name_check":
            return module.analyze(pdf_path)

        if module_name == "phash_check":
            return module.analyze(pdf_path)

        if module_name == "signature":
            return module.analyze_signature(pdf_path)

        if module_name == "signature_check":
            return module.ultra_forensic_signature_check(pdf_path)

        if module_name == "signature_image_check":
            return module.verify_signature(pdf_path)

        if module_name == "ssim_check":
            return module.analyze_certificate(pdf_path)

        if module_name == "text_check":
            return module.combined_text_check(pdf_path)

        if module_name == "visual_fingerprint_check":
            return module.fingerprint_pdf(pdf_path)

        # fallback
        if hasattr(module, "run_check"):
            return module.run_check(pdf_path)

    except Exception as e:
        return {"error": f"handler crash: {e}", "trace": traceback.format_exc()}

    return {"error": "No valid function"}


# ---------- MAIN ----------
# ---------- MAIN ----------
def run_non_qr_checks(cert_path):
    if not os.path.exists(cert_path):
        return {"error": f"File not found: {cert_path}"}

    print("\n======== UNIVERSAL CERTIFICATE VERIFIER (NON-QR) ========\n")
    print("Certificate:", cert_path, "\n")

    results = {}
    weighted_total = 0
    total_possible = sum(WEIGHTS.values())

    for mod in CHECK_MODULES:
        weight = WEIGHTS[mod]
        # print(f"▶ Running: {mod}")

        raw = run_check_module(mod, cert_path)

        score, verdict = extract_numeric_score(raw)
        score = max(0, min(100, score))
        weighted = (score / 100) * weight
        weighted_total += weighted

        # print(f"   → Score: {score:.2f} → Weighted: {weighted:.2f}/{weight:.2f}")
        # print(f"   → Verdict: {verdict}")

        results[mod] = {
            "raw": raw,
            "score": score,
            "verdict": verdict,
            "weight": weight,
            "weighted_contribution": round(weighted, 3)
        }

    # Final classification
    final_score = round((weighted_total / total_possible) * 100, 2)

    if final_score >= 75:
        final_verdict = "ORIGINAL"
    elif final_score >= 45:
        final_verdict = "SUSPICIOUS"
    else:
        final_verdict = "FAKE"

    # ---------- OVERALL REASON ----------
    overall_reasons = []
    critical_issues = []
    strong_signals = []

    for mod, data in results.items():
        scr = data["score"]
        verdict = data["verdict"]

        if scr >= 85:
            strong_signals.append(mod)

        if scr <= 30 or verdict in ("FAKE", "TAMPERED", "NO_MATCH", "LIKELY_TAMPERED"):
            critical_issues.append(mod)

    if "metadata_check" in strong_signals:
        overall_reasons.append("Metadata strongly supports authenticity.")
    if "signature_check" in strong_signals:
        overall_reasons.append("Digital signature structure is valid.")

    if not overall_reasons:
        overall_reasons.append("No strong authenticity markers detected.")

    if critical_issues:
        overall_reasons.append("Potential tampering found in: " + ", ".join(critical_issues))
    else:
        overall_reasons.append("No strong tampering indicators found.")

    susp_count = sum(1 for d in results.values() if d["verdict"] in ("SUSPICIOUS", "UNCERTAIN"))
    if susp_count >= 5:
        overall_reasons.append("Multiple modules reported suspicious behaviour.")

    final_reason_text = " ".join(overall_reasons)

    # Save report (optional, maybe keep it or remove it based on backend needs, keeping it for now but also returning)
    report = {
        "certificate": cert_path,
        "final_score": final_score,
        "final_verdict": final_verdict,
        "overall_reason": final_reason_text,
        "weights": WEIGHTS,
        "modules": results
    }

    # with open(REPORT_PATH, "w", encoding="utf-8") as f:
    #     json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    cert_path = input("Enter certificate path: ").strip()
    res = run_non_qr_checks(cert_path)
    print(json.dumps(res, indent=2))
