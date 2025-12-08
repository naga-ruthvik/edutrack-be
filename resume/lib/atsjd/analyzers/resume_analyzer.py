"""
ResumeJDAnalyzer - Config-driven, rule-based Resume + JD analyzer
Matches resume with JD and prints user-friendly results
"""

import re
import json
from pathlib import Path
from collections import Counter
from typing import Dict, Any


class ResumeJDAnalyzer:
    def __init__(self, config_folder: str = "config"):
        self.config_folder = Path(config_folder)

        # Load config files
        self.action_verbs = self._load_json(self.config_folder / "action_verbs.json")
        self.skills_db = self._load_json(self.config_folder / "skills_database.json")
        self.default_verbs = self._load_json(self.config_folder / "default_verbs.json")

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
    # RUN FULL ANALYSIS + JD MATCH
    # -------------------------
    def run_analysis(self, resume_json: dict, jd_data) -> dict:
        resume_text = self._extract_all_text(resume_json)

        # jd_data is JobDescription object
        jd_text = getattr(jd_data, "raw_text", "")  # safely get raw_text
        jd_text = (jd_text or "").lower()

        result = {
            "document_synopsis": self._document_synopsis(resume_json, resume_text),
            "data_identification": self._data_identification(resume_json),
            "lexical_analysis": self._lexical_analysis(resume_text),
            "semantic_analysis": self._semantic_analysis(resume_json, resume_text),
            "jd_matching": self._match_resume_with_jd(resume_text, jd_text)
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
            experience_or_projects,  
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
        if isinstance(resume_json.get("socialMedia"), list):
            for item in resume_json["socialMedia"]:
                if "linkedin" in item.get("link", "").lower():
                    linkedin = item["link"]

        skills = resume_json.get("skills", []) or []

    # NEW fields
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
                "fail": "✘ Phone number missing or invalid."
        },
            "email": {
                "valid": email_valid,
                "value": email,
                "success": f"✔ Email detected: {email}" if email_valid else "",
                "fail": "✘ Email missing or invalid."
        },
            "linkedin": {
                "valid": linkedin_valid,
                "value": linkedin,
                "success": f"✔ LinkedIn detected: {linkedin}" if linkedin_valid else "",
                "fail": "✘ LinkedIn profile missing or invalid."
        },
            "skills": {
                "valid": skills_valid,
                "value": skills,
                "success": "✔ Skills section detected." if skills_valid else "",
                "fail": "✘ Skills section missing."
        },

        # NEW
            "education": {
                "valid": education_valid,
                "value": education,
                "success": "✔ Education section detected." if education_valid else "",
                "fail": "✘ Education section missing."
        },
            "work_experience": {
                "valid": work_valid,
                "value": work_exp,
                "success": "✔ Work experience detected." if work_valid else "",
                "fail": "✘ Work experience section missing."
        }
    }

        return results



    def print_data_identification(self, results: dict):
        print("\nDATA IDENTIFICATION\n")
        for info in results.values():
            print(info["success"] if info["valid"] else info["fail"])

        return results
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
            "common_words": common_words
        }

        messages = {
            "personal_pronouns": "✔ No personal pronouns detected." if not pronouns_found else "✘ Personal pronouns detected.",
            "numbers": "✔ Numbers detected." if numbers_found else "✘ No numeric data detected.",
            "vocabulary": f"✔ Avg word length: {round(avg_len, 2)}",
            "common_words": f"✔ Most common words: {', '.join(common_words)}"
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

        # Measurable achievements
        verbs = []
        for cat_verbs in self.action_verbs.values():
            if isinstance(cat_verbs, list):
                verbs.extend([v.lower() for v in cat_verbs])
        measurable_found = [v for v in verbs if v in text_lower]

        # Soft skills
        soft_skills_list = self.skills_db.get("soft_skills", []) or []
        soft_skills_found = [s for s in soft_skills_list if s.lower() in text_lower]

        # Hard skills
        hard_skills_found = []
        for category, skills in self.skills_db.items():
            if category == "soft_skills":
                continue
            for skill in skills:
                if skill.lower() in text_lower:
                    hard_skills_found.append(skill)

        results = {
            "measurable_achievements": measurable_found,
            "soft_skills_detected": soft_skills_found,
            "soft_skill_count": len(soft_skills_found),
            "hard_skills_detected": hard_skills_found,
            "hard_skill_count": len(hard_skills_found)
        }

        messages = {
            "measurable_achievements": f"✔ Measurable achievements: {', '.join(measurable_found)}" if measurable_found else "✘ No measurable achievements detected.",
            "soft_skills": f"✔ Soft skills: {', '.join(soft_skills_found)}" if soft_skills_found else "✘ No soft skills detected.",
            "hard_skills": f"✔ Hard skills: {', '.join(hard_skills_found)}" if hard_skills_found else "✘ No hard skills detected."
        }

        return {"results": results, "messages": messages}

    def print_semantic_analysis(self, semantic: dict):
        print("\nSEMANTIC ANALYSIS\n")
        for msg in semantic["messages"].values():
            print(msg)

    # -------------------------
    # JD MATCHING
    # -------------------------
    def _match_resume_with_jd(self, resume_text: str, jd_text: str) -> dict:
        # Hard skills
        hard_skill_matches = [
            skill for cat, skills in self.skills_db.items() if cat != "soft_skills"
            for skill in skills if skill.lower() in resume_text and skill.lower() in jd_text
        ]
        # Soft skills
        soft_skill_matches = [
            s for s in self.skills_db.get("soft_skills", [])
            if s.lower() in resume_text and s.lower() in jd_text
        ]
        # Verbs / responsibilities
        jd_verbs = self.default_verbs.get("verbs", [])
        verb_matches = [v for v in jd_verbs if v.lower() in resume_text and v.lower() in jd_text]

        score = len(hard_skill_matches)*5 + len(soft_skill_matches)*2 + len(verb_matches)*1

        results = {
            "hard_skill_matches": hard_skill_matches,
            "soft_skill_matches": soft_skill_matches,
            "verb_matches": verb_matches,
            "match_score": score
        }

        messages = {
            "hard_skills": f"✔ Matched hard skills: {', '.join(hard_skill_matches)}" if hard_skill_matches else "✘ No hard skills matched with JD.",
            "soft_skills": f"✔ Matched soft skills: {', '.join(soft_skill_matches)}" if soft_skill_matches else "✘ No soft skills matched with JD.",
            "verbs": f"✔ Matched responsibilities/verbs: {', '.join(verb_matches)}" if verb_matches else "✘ No verbs/responsibilities matched with JD.",
            "score": f"✔ Resume-JD match score: {score}"
        }

        return {"results": results, "messages": messages}

    # -------------------------
    # FINAL UPDATED PRINTER
    # -------------------------
    def print_jd_matching(self, jd_match: dict):
        print("\nJD MATCHING\n")

        results = jd_match["results"]
        messages = jd_match["messages"]

        print("Results:")
        print(f" - Hard Skills Matched     : {', '.join(results['hard_skill_matches']) if results['hard_skill_matches'] else 'None'}")
        print(f" - Soft Skills Matched     : {', '.join(results['soft_skill_matches']) if results['soft_skill_matches'] else 'None'}")
        print(f" - Verb Matches            : {', '.join(results['verb_matches']) if results['verb_matches'] else 'None'}")
        print(f" - Match Score             : {results['match_score']}")

        print("\nMessages:")
        print(f" - Hard Skills             : {messages['hard_skills']}")
        print(f" - Soft Skills             : {messages['soft_skills']}")
        print(f" - Verbs                   : {messages['verbs']}")
        print(f" - Score                   : {messages['score']}")
