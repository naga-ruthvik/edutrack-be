"""
ResumeAnalyzer - Config-driven, rule-based Resume analyzer
Analyzes a single resume JSON (no JD) and prints user-friendly results.
"""

import re
import json
from pathlib import Path
from collections import Counter
from typing import Dict, Any


class ResumeAnalyzer:
    def __init__(self, config_folder: str = "config"):
        self.config_folder = Path(config_folder)

        # Load config files
        self.action_verbs = self._load_json(self.config_folder / "action_verbs.json")
        self.skills_db = self._load_json(self.config_folder / "skills_database.json")

        # Ensure skills_db structure
        if not isinstance(self.skills_db, dict):
            self.skills_db = {}
        if "soft_skills" not in self.skills_db:
            self.skills_db["soft_skills"] = []

    # -------------------------
    # JSON loader
    # -------------------------
    def _load_json(self, path: Path) -> dict:
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: failed to load {path}: {e}")
        return {}

    # -------------------------
    # Extract all text from JSON
    # -------------------------
    def _extract_all_text(self, data: dict) -> str:
        text_parts = []

        def collect(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for v in obj:
                    collect(v)
            elif isinstance(obj, str):
                text_parts.append(obj)

        collect(data)
        return " ".join(text_parts).lower()

    # -------------------------
    # RUN FULL ANALYSIS (no JD)
    # -------------------------
    def run_analysis(self, resume_json: dict) -> dict:
        resume_text = self._extract_all_text(resume_json)

        result = {
            "document_synopsis": self._document_synopsis(resume_json, resume_text),
            "data_identification": self._data_identification(resume_json),
            "lexical_analysis": self._lexical_analysis(resume_text),
            "semantic_analysis": self._semantic_analysis(resume_json, resume_text),
        }
        return result

    # -------------------------
    # DOCUMENT SYNOPSIS
    # -------------------------
    def _document_synopsis(self, resume_json: dict, text: str) -> dict:
        word_count = len(text.split())
        contains_numbers = bool(re.search(r"\d+", text))
        text_lower = text.lower()

    # ------------------------------------------------------------
    # REAL ATS-FRIENDLINESS CHECKS
    # ------------------------------------------------------------

    # 1. Extractable text (not empty)
        extractable = word_count > 20

    # 2. Experience section text-based detection
        experience_present = any(
            kw in text_lower 
            for kw in ["experience", "work experience", "employment"]
    )

    # 3. Projects detection — text OR JSON structure
        projects_present = (
            "project" in text_lower or
            len(resume_json.get("projects", [])) > 0
    )

    # 4. Experience OR Projects (your requirement)
        education_present = len(resume_json.get("education", [])) > 0
        skills_present = len(resume_json.get("skills", [])) > 0
        experience_present = len(resume_json.get("workExperience", [])) > 0

        projects_present = len(resume_json.get("projects", [])) > 0

        experience_or_projects = experience_present or projects_present


    # 7. Contact details
        email_present = bool(re.search(r"[^@]+@[^@]+\.[^@]+", text))
        phone_present = bool(re.search(r"\d{8,}", text))

    # 8. Bullet points
        bullets_present = any(b in text for b in ["-", "•", "*"])

    # 9. Minimum length requirement
        adequate_length = word_count >= 100

    # FINAL DECISION
        ats_compliant = all([
            extractable,
            experience_or_projects,   # <-- Your requirement applied here
            education_present,
            skills_present,
            (email_present or phone_present),
            bullets_present,
            adequate_length,
    ])

    # ------------------------------------------------------------
    # RESULTS + MESSAGES
    # ------------------------------------------------------------
        results = {
            "file_type": "JSON",
            "word_count": word_count,
            "contains_numbers": contains_numbers,
            "ats_compliant": ats_compliant,
            "page_count": 1,
            "word_count_status": "PASS" if word_count >= 300 else "FAIL",
    }

        messages = {
            "word_count": (
                f"✔ Word count: {word_count} words."
                if word_count >= 300
                else f"✘ Word count: {word_count} words. Consider adding more content."
        ),
            "numbers": (
                "✔ Numeric data present."
                if contains_numbers
                else "✘ No numeric data detected. Add measurable achievements."
        ),
            "ats_compliance": (
                "✔ Resume appears ATS-friendly."
                if ats_compliant else
                "✘ Resume may not be ATS-friendly. Missing key sections or structure."
        ),
            "page_count": f"✔ Page count (logical): {results['page_count']}",
    }

        return {"results": results, "messages": messages}



    def print_document_synopsis(self, doc_synopsis: dict):
        print("\nDOCUMENT SYNOPSIS\n")
        for msg in doc_synopsis["messages"].values():
            print(msg)

    # -------------------------
    # DATA IDENTIFICATION
    # -------------------------
    def _data_identification(self, resume_json: dict) -> dict:
        email = resume_json.get("email", "")
        phone = resume_json.get("contactInformation", "") or resume_json.get("phone", "")

        linkedin = ""
        # Same socialMedia handling pattern as JD version
        if isinstance(resume_json.get("socialMedia"), list):
            for item in resume_json["socialMedia"]:
                if "linkedin" in item.get("link", "").lower():
                    linkedin = item["link"]

        skills = resume_json.get("skills", []) or []

        # Extra sections like in ResumeJDAnalyzer
        education = resume_json.get("education", [])
        work_exp = resume_json.get("workExperience", [])

        # Validations
        email_valid = bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))
        phone_valid = bool(re.match(r"^[\d\-\+\s]{8,20}$", str(phone)))
        linkedin_valid = "linkedin.com" in str(linkedin).lower()
        skills_valid = len(skills) > 0
        education_valid = len(education) > 0
        work_valid = len(work_exp) > 0

        results = {
            "phone": {
                "valid": phone_valid,
                "value": phone,
                "success": "✔ Phone number detected.",
                "fail": "✘ Phone number missing or invalid.",
            },
            "email": {
                "valid": email_valid,
                "value": email,
                "success": f"✔ Email detected: {email}" if email_valid else "",
                "fail": "✘ Email missing or invalid.",
            },
            "linkedin": {
                "valid": linkedin_valid,
                "value": linkedin,
                "success": f"✔ LinkedIn detected: {linkedin}" if linkedin_valid else "",
                "fail": "✘ LinkedIn profile missing or invalid.",
            },
            "skills": {
                "valid": skills_valid,
                "value": skills,
                "success": "✔ Skills section detected." if skills_valid else "",
                "fail": "✘ Skills section missing.",
            },
            "education": {
                "valid": education_valid,
                "value": education,
                "success": "✔ Education section detected." if education_valid else "",
                "fail": "✘ Education section missing.",
            },
            "work_experience": {
                "valid": work_valid,
                "value": work_exp,
                "success": "✔ Work experience detected." if work_valid else "",
                "fail": "✘ Work experience section missing.",
            },
        }

        return results

    def print_data_identification(self, results: dict):
        print("\nDATA IDENTIFICATION\n")
        for info in results.values():
            print(info["success"] if info["valid"] else info["fail"])

    # -------------------------
    # LEXICAL ANALYSIS
    # -------------------------
    def _lexical_analysis(self, text: str) -> dict:
        words = [w for w in re.findall(r"\w[\w\+\-\.#]*", text)]
        avg_len = sum(len(w) for w in words) / len(words) if words else 0
        pronouns = [" i ", " me ", " my ", " we ", " us "]
        pronouns_found = any(p in f" {text} " for p in pronouns)
        numbers_found = bool(re.search(r"\d+%?", text))
        common_words = [w for w, _ in Counter(words).most_common(6)]

        results = {
            "avg_word_length": round(avg_len, 2),
            "personal_pronouns_found": pronouns_found,
            "numbers_found": numbers_found,
            "common_words": common_words,
        }

        messages = {
            "personal_pronouns": (
                "✔ No personal pronouns detected."
                if not pronouns_found
                else "✘ Personal pronouns detected."
            ),
            "numbers": (
                "✔ Numbers detected."
                if numbers_found
                else "✘ No numeric data detected."
            ),
            "vocabulary": f"✔ Avg word length: {round(avg_len, 2)}",
            "common_words": f"✔ Most common words: {', '.join(common_words)}",
        }

        return {"results": results, "messages": messages}

    def print_lexical_analysis(self, lexical: dict):
        print("\nLEXICAL ANALYSIS\n")
        for msg in lexical["messages"].values():
            print(msg)

    # -------------------------
    # SEMANTIC ANALYSIS
    # -------------------------
    def _semantic_analysis(self, resume_json: dict, text: str) -> dict:
        text_lower = text.lower()

        # Measurable achievements (all verbs from action_verbs.json)
        verbs = []
        if isinstance(self.action_verbs, dict):
            for cat_verbs in self.action_verbs.values():
                if isinstance(cat_verbs, list):
                    verbs.extend([v.lower() for v in cat_verbs])
        elif isinstance(self.action_verbs, list):
            verbs = [v.lower() for v in self.action_verbs]

        measurable_found = [v for v in verbs if v and v in text_lower]

        # Soft skills
        soft_skills_list = self.skills_db.get("soft_skills", []) or []
        soft_skills_found = [s for s in soft_skills_list if s and s.lower() in text_lower]

        # Hard skills
        hard_skills_found = []
        for category, skills in self.skills_db.items():
            if category == "soft_skills":
                continue
            if not isinstance(skills, list):
                continue
            for skill in skills:
                if not skill:
                    continue
                if skill.lower() in text_lower:
                    hard_skills_found.append(skill)

        results = {
            "measurable_achievements": measurable_found,
            "soft_skills_detected": soft_skills_found,
            "soft_skill_count": len(soft_skills_found),
            "hard_skills_detected": hard_skills_found,
            "hard_skill_count": len(hard_skills_found),
        }

        messages = {
            "measurable_achievements": (
                f"✔ Measurable achievements: {', '.join(measurable_found)}"
                if measurable_found
                else "✘ No measurable achievements detected."
            ),
            "soft_skills": (
                f"✔ Soft skills: {', '.join(soft_skills_found)}"
                if soft_skills_found
                else "✘ No soft skills detected."
            ),
            "hard_skills": (
                f"✔ Hard skills: {', '.join(hard_skills_found)}"
                if hard_skills_found
                else "✘ No hard skills detected."
            ),
        }

        return {"results": results, "messages": messages}

    def print_semantic_analysis(self, semantic: dict):
        print("\nSEMANTIC ANALYSIS\n")
        for msg in semantic["messages"].values():
            print(msg)
