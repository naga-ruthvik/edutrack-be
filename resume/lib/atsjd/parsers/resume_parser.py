"""
Resume Parser Module - Converts JSON resume files to structured ResumeData objects
"""

import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ==============================
#       DATA CLASSES
# ==============================

@dataclass
class ContactInfo:
    emails: List[str]
    phones: List[str]
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Experience:
    title: str
    company: str
    duration: str
    description: List[str]
    location: Optional[str] = None


@dataclass
class Education:
    degree: str
    institution: str
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None
    location: Optional[str] = None


@dataclass
class Project:
    title: str
    description: Optional[str] = None


@dataclass
class ResumeData:
    title: Optional[str] 
    contact_info: ContactInfo
    summary: Optional[str]
    skills: List[str]
    education: List[Education]
    experience: List[Experience]
    projects: List[Project]
    certifications: List[str]
    raw_text: str


# ==============================
#       PARSER CLASS
# ==============================
class ResumeParser:
    def __init__(self, skills_db_path: Optional[str] = None):
        self.skills_db = self._load_skills_database(skills_db_path)

    def _load_skills_database(self, skills_db_path: Optional[str]) -> Dict:
        if skills_db_path and Path(skills_db_path).exists():
            try:
                with open(skills_db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load skills database from {skills_db_path}: {e}")
                return {}
        logger.warning("skills_database.json not found. Using empty skills database.")
        return {
            "programming_languages": [],
            "web_technologies": [],
            "databases": [],
            "cloud_platforms": [],
            "devops_tools": [],
            "data_science": []
        }

    # ---------------------------
    # Add all other methods here
    # parse_resume_json, parse_resume, _extract_link, _enhance_skills_with_database
    # ---------------------------

    # ==============================
    #      MAIN JSON PARSER
    # ==============================

    def parse_resume_dict(self, json_data: Dict) -> ResumeData:
        """Convert dictionary to ResumeData."""
        
        # -------------------------------------------------
        #  FLEXIBLE FIELD HANDLING
        # -------------------------------------------------

        # Use summary as raw_text fallback
        raw_text = (
            json_data.get("raw_text")
            or json_data.get("summary")
            or ""
        )

        # accept skills as list OR structured sections
        raw_skills = json_data.get("skills", [])

        extracted_skills = []
        if isinstance(raw_skills, list):
            for block in raw_skills:
                if isinstance(block, dict) and "skills" in block:
                    extracted_skills.extend(block["skills"])
                elif isinstance(block, str):
                    extracted_skills.append(block)

        # accept both 'experience' and 'workExperience'
        experience_json = json_data.get("experience") or json_data.get("workExperience") or []

        # normal education field
        education_json = json_data.get("education", [])

        # -------------------------------------------------
        #  CONTACT INFO
        # -------------------------------------------------

        contact_info_raw = json_data.get("contactInformation") or {}
        contact_info = ContactInfo(
            emails=[json_data.get("email")] if json_data.get("email") else [],
            phones=[contact_info_raw] if isinstance(contact_info_raw, str) else [],
            linkedin=self._extract_link(json_data, "LinkedIn"),
            github=self._extract_link(json_data, "GitHub"),
            website=None,
            address=json_data.get("address")
        )

        # -------------------------------------------------
        #  EXPERIENCE PARSING
        # -------------------------------------------------

        experience_list = []
        for exp in experience_json:
            desc = exp.get("keyAchievements", "")
            desc_lines = desc.split("\n") if isinstance(desc, str) else []

            experience_list.append(
                Experience(
                    title=str(exp.get("position", "")),
                    company=str(exp.get("company", "")),
                    duration=f"{exp.get('startYear', '')} - {exp.get('endYear', '')}",
                    description=desc_lines,
                    location=str(exp.get("description", "")),
                )
            )

        # -------------------------------------------------
        #  EDUCATION PARSING
        # -------------------------------------------------

        education_list = []
        for edu in education_json:
            education_list.append(
                Education(
                    degree=str(edu.get("degree", "")),
                    institution=str(edu.get("school", "")),
                    graduation_year=edu.get("endYear"),
                )
            )

        # -------------------------------------------------
        #  PROJECTS
        # -------------------------------------------------

        projects_list = []
        for proj in json_data.get("projects", []):
            projects_list.append(
                Project(
                    title=str(proj.get("name", "")),
                    description=proj.get("description"),
                )
            )
        resume_title = (
            json_data.get("position")
            or (experience_list[0].title if experience_list else "")
        )

        # -------------------------------------------------
        #  SKILLS + ENHANCEMENT
        # -------------------------------------------------

        clean_base_skills = [s.strip() for s in extracted_skills if len(s.strip()) > 2]
        enhanced_skills = self._enhance_skills_with_database(raw_text, clean_base_skills)

        # -------------------------------------------------
        #  RETURN STRUCTURED DATA
        # -------------------------------------------------

        return ResumeData(
            title=resume_title,  
            contact_info=contact_info,
            summary=json_data.get("summary"),
            skills=enhanced_skills,
            education=education_list,
            experience=experience_list,
            projects=projects_list,
            certifications=json_data.get("certifications", []),
            raw_text=raw_text
        )

    def parse_resume_json(self, json_file_path: str) -> ResumeData:
        """Read JSON and convert to ResumeData."""

        file_path = Path(json_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Resume JSON not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        
        return self.parse_resume_dict(json_data)



    # ==============================
    #     HELPERS
    # ==============================

    def _extract_link(self, json_data: dict, key: str) -> Optional[str]:
        """Extract LinkedIn/GitHub links from socialMedia list."""
        for item in json_data.get("socialMedia", []):
            if item.get("socialMedia", "").lower() == key.lower():
                return item.get("link")
        return None

    def _enhance_skills_with_database(self, raw_text: str, base_skills: List[str]) -> List[str]:
        text_lower = raw_text.lower()
        found = set(base_skills)

        for _, skills_list in self.skills_db.items():
            for skill in skills_list:
                if skill.lower() in text_lower:
                    found.add(skill)

        return sorted(list(found))

    def parse_resume(self, input_data) -> ResumeData:
        """Universal entry point for JSON resume (file path or dict)."""
        
        if isinstance(input_data, dict):
            return self.parse_resume_dict(input_data)
            
        file_path_obj = Path(input_data)

        if file_path_obj.suffix.lower() == ".json":
            return self.parse_resume_json(str(file_path_obj))

        raise ValueError(
            f"Only JSON resumes or dicts are supported. Got: {type(input_data)}"
        )
