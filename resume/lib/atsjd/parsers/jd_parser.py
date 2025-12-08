# ats_resume_scorer/parsers/jd_parser.py
"""
Job Description Parser Module - Parses .txt job description files
"""

import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class JobDescription:
    """Job description data structure"""
    title: str
    required_skills: List[str]
    preferred_skills: List[str]
    education_requirements: List[str]
    experience_requirements: str
    responsibilities: List[str]
    raw_text: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    is_title_fallback: bool = False 


class JobDescriptionParser:
    """Parser for job description .txt files"""

    def __init__(self):
        """Initialize parser with skill keywords and patterns"""
        self.skill_indicators = [
            "experience with", "knowledge of", "proficiency in", "familiarity with",
            "expertise in", "skilled in", "background in", "understanding of"
        ]
        self.education_keywords = [
            "bachelor", "master", "phd", "doctorate", "degree", "diploma",
            "certification", "associate", "bs", "ba", "ms", "ma", "mba"
        ]
        self.experience_keywords = [
            "years", "experience", "background", "track record", "history"
        ]

    # ⭐ REQUIRED BY main.py ⭐
    def parse_job_description(self, jd_text: str) -> JobDescription:
        """Compatibility wrapper so main.py calls continue working"""
        return self.parse_jd_text(jd_text)

    def parse_jd_file(self, txt_file_path: str) -> JobDescription:
        """
        Parse job description from a .txt file
        """
        file_path = Path(txt_file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Job description file not found: {file_path}")
        
        if file_path.suffix.lower() != '.txt':
            raise ValueError(f"Only .txt files supported. Got: {file_path.suffix}")

        logger.info(f"Parsing job description: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            jd_text = f.read().strip()
        
        return self._parse_text(jd_text)

    def parse_jd_text(self, jd_text: str) -> JobDescription:
        """Parse job description from raw text string"""
        return self._parse_text(jd_text)

    def _parse_text(self, jd_text: str) -> JobDescription:
        """Internal method to parse job description text"""
        title, is_fallback = self.extract_title(jd_text)
        company = self.extract_company_name(jd_text)
        location = self.extract_location(jd_text)
        salary_range = self.extract_salary_range(jd_text)
        required_skills = self.extract_required_skills(jd_text)
        preferred_skills = self.extract_preferred_skills(jd_text)
        education_requirements = self.extract_education_requirements(jd_text)
        experience_requirements = self.extract_experience_requirements(jd_text)
        responsibilities = self.extract_responsibilities(jd_text)

        return JobDescription(
            title=title,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            education_requirements=education_requirements,
            experience_requirements=experience_requirements,
            responsibilities=responsibilities,
            raw_text=jd_text,
            company=company,
            location=location,
            salary_range=salary_range,
            is_title_fallback=is_fallback,
        )

    # --------------------
    # FIELD EXTRACTION LOGIC
    def extract_title(self, text: str):
    

        lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1️⃣ Direct title patterns
        patterns = [
            r"(?i)^job\s*title[:\-]\s*(.+)",
            r"(?i)^position[:\-]\s*(.+)",
            r"(?i)^role[:\-]\s*(.+)",
            r"(?i)we\s+are\s+looking\s+for\s+(?:a|an)\s+([^\n,]+)",
            r"(?i)we\s+are\s+seeking\s+(?:a|an)?\s*([^\n,]+)",
            r"(?i)hiring\s+for\s+(?:a|an)?\s*([^\n,]+)",
            r"(?i)open\s+position[:\-]\s*([^\n,]+)",
            r"(?i)^title[:\-]\s*(.+)",
    ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip(), False

    # 2️⃣ If first non-empty line looks like a job title
        first_line = lines[0].lower()
        job_keywords = [
            "developer", "engineer", "manager", "designer", "analyst",
            "scientist", "consultant", "specialist", "architect",
            "lead", "intern", "director"
    ]

        if any(k in first_line for k in job_keywords) and 2 <= len(first_line.split()) <= 8:
            return lines[0], False

    # 3️⃣ Last fallback
        return "Software Engineer", True



    def extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name"""
        company_patterns = [
            r"(?i)company:\s*([^\n]+)",
            r"(?i)at\s+([A-Z][a-zA-Z\s&]+?)(?:\s+(?:we|is|are))",
            r"(?i)^([A-Z][a-zA-Z\s&]+?)\s+(?:is\s+(?:hiring|seeking))",
        ]

        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                company = match.group(1).strip()
                if 2 < len(company) < 50:
                    return company.strip()
        return None

    def extract_location(self, text: str) -> Optional[str]:
        """Extract job location"""
        location_patterns = [
            r"(?i)location:\s*([^\n]+)",
            r"(?i)(?:remote|hybrid|onsite|office)\s*,?\s*([^\n,.]+)",
            r"([A-Z][a-z]+,\s*[A-Z]{2}(?:\s*\d{5})?)",
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip() if match.groups() else match.group().strip()
        return None

    def extract_salary_range(self, text: str) -> Optional[str]:
        """Extract salary information"""
        salary_patterns = [
            r"(?i)\$[\d,]+\s*-\s*\$[\d,]+(?:\s*/\s*year)?",
            r"(?i)\$[\d,]+(?:k)?\s*(?:per\s+year|annually)?",
            r"(?i)salary:\s*([^\n]+)",
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        return None

    def extract_required_skills(self, text: str) -> List[str]:
        """Extract required skills"""
        required_skills = set()

        required_patterns = [
            r"(?i)(?:required|must\s+have|essential).*?(?=\b(?:preferred|nice|bonus)|\n\n|$)",
            r"(?i)requirements.*?(?=\b(?:preferred|responsibilities)|\n\n|$)",
        ]

        for pattern in required_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                skills = self._extract_skills_from_section(match.group())
                required_skills.update(skills)

        exp_skills = re.findall(
            r"(\d+)\+?\s*years?\s+(?:with|in)\s+(.+?)(?=\.|,|\n|$)",
            text, re.IGNORECASE
        )
        for years, skill in exp_skills:
            skill = skill.strip().lower()
            if len(skill) > 2:
                required_skills.add(skill)

        return sorted(list(required_skills))

    def extract_preferred_skills(self, text: str) -> List[str]:
        """Extract preferred skills"""
        preferred_skills = set()

        preferred_patterns = [
            r"(?i)(?:preferred|nice\s+to\s+have|bonus|plus).*?(?=\n\n|$)",
        ]

        for pattern in preferred_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                skills = self._extract_skills_from_section(match.group())
                preferred_skills.update(skills)

        return sorted(list(preferred_skills))

    def _extract_skills_from_section(self, section_text: str) -> List[str]:
        """Extract skills from text section"""
        skills = set()

        bullets = re.findall(r"[-•*]\s*([^\n]+)", section_text)
        for bullet in bullets:
            cleaned = re.sub(r"(?i)(?:experience\s+(?:with|in)|knowledge\s+of)", "", bullet)
            sub_skills = re.split(r"[,;&/]", cleaned.strip())
            for skill in sub_skills:
                skill = skill.strip()
                if 2 < len(skill) < 50:
                    skills.add(skill.lower())

        for indicator in self.skill_indicators:
            pattern = rf"{re.escape(indicator)}\s+([^,.;\n]+)"
            matches = re.findall(pattern, section_text, re.IGNORECASE)
            skills.update([m.strip().lower() for m in matches if 2 < len(m.strip()) < 50])

        return list(skills)

    def extract_education_requirements(self, text: str) -> List[str]:
        """Extract education requirements"""
        edu_reqs = set()
        patterns = [
            r"(?i)bachelor['s]?\s+(?:degree)?",
            r"(?i)master['s]?\s+(?:degree)?",
            r"(?i)(?:phd|doctorate)",
            r"(?i)degree\s+(?:in|from)?\s*([^.\n]+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            edu_reqs.update(matches)

        return sorted(list(edu_reqs))

    def extract_experience_requirements(self, text: str) -> str:
        """Extract experience requirements"""
        patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"minimum\s+(\d+)\s+years?",
            r"at\s+least\s+(\d+)\s+years?",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().strip()

        return "Not specified"

    def extract_responsibilities(self, text: str) -> List[str]:
        """Extract job responsibilities"""
        responsibilities = []

        resp_patterns = [
            r"(?i)(?:responsibilities|duties).*?(?=\b(?:requirements|qualifications)|\n\n|$)",
        ]

        for pattern in resp_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                bullets = re.findall(r"[-•*]\s*([^\n]+)", match.group())
                responsibilities.extend([b.strip() for b in bullets if b.strip()])

        return responsibilities[:10]
