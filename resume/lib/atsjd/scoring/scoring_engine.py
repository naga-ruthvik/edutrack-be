# ats_resume_scorer/scoring/scoring_engine.py
"""
ATS Scoring Engine - Core scoring logic for resume evaluation
"""
import os                   # Needed for CONFIG_DIR path
import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


from ..parsers.resume_parser import ResumeData
from ..parsers.jd_parser import JobDescription


logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

def load_json_file(filename: str):
    path = os.path.join(CONFIG_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {filename} | Error: {e}")
        return {}


@dataclass
class ScoringWeights:
    """Configurable scoring weights for different categories"""
    keyword_match: float = 0.25
    title_match: float = 0.10
    education_match: float = 0.10
    experience_match: float = 0.15
    projects_match: float = 0.10
    format_compliance: float = 0.10
    action_verbs_grammar: float = 0.10
    readability: float = 0.10

    def __post_init__(self):
        """Validate that weights sum to 1.0"""
        total = (
            self.keyword_match + self.title_match + self.education_match +
            self.experience_match + self.projects_match + self.format_compliance +
            self.action_verbs_grammar + self.readability
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")


class ATSScoringEngine:
    """Main ATS scoring engine"""

    def __init__(self, weights: Optional['ScoringWeights'] = None):
        """Initialize scoring engine with weights"""
        # Load weights from JSON if not provided
        if weights:
            self.weights = weights
        else:
            weight_data = load_json_file("default_weights.json")
            if weight_data:
                self.weights = ScoringWeights(**weight_data)
            else:
                self.weights = ScoringWeights()

        # Load action verbs from JSON
        verbs_data = load_json_file("action_verbs.json")
        if isinstance(verbs_data, list):
            self.action_verbs = verbs_data
        else:
            logger.warning("action_verbs.json missing or invalid, using empty list")
            self.action_verbs = []

        # ✅ Load skills database JSON
        skills_data = load_json_file("skills_database.json")
        if isinstance(skills_data, dict):
            self.skills_db = skills_data
        else:
            logger.warning("skills_database.json missing or invalid, using empty dict")
            self.skills_db = {}
    def calculate_overall_score(self, resume_data: ResumeData, job_description: JobDescription) -> Dict[str, Any]:
        """Calculate comprehensive ATS score"""
        # Calculate individual scores
        keyword_score = self.calculate_keyword_match_score(resume_data, job_description)
        title_score = self.calculate_title_match_score(resume_data, job_description)
        education_score = self.calculate_education_match_score(resume_data, job_description)
        experience_score = self.calculate_experience_match_score(resume_data, job_description)
        projects_score = self.calculate_projects_match_score(resume_data, job_description)
        format_score = self.calculate_format_compliance_score(resume_data)
        action_verbs_score = self.calculate_action_verbs_grammar_score(resume_data)
        readability_score = self.calculate_readability_score(resume_data)

        # Calculate weighted total
        total_score = (
            keyword_score * self.weights.keyword_match +
            title_score * self.weights.title_match +
            education_score * self.weights.education_match +
            experience_score * self.weights.experience_match +
            projects_score * self.weights.projects_match +
            format_score * self.weights.format_compliance +
            action_verbs_score * self.weights.action_verbs_grammar +
            readability_score * self.weights.readability
        )

        return {
            "total_score": round(total_score, 2),
            "detailed_scores": {
                "keyword_match": round(keyword_score, 2),
                "title_match": round(title_score, 2),
                "education_match": round(education_score, 2),
                "experience_match": round(experience_score, 2),
                "projects_match": round(projects_score, 2),
                "format_compliance": round(format_score, 2),
                "action_verbs_grammar": round(action_verbs_score, 2),
                "readability": round(readability_score, 2),
            },
           
        }
    def calculate_title_match_score(self, resume_data: ResumeData, job_description: JobDescription) -> float:
        
        # 1. Get resume title
        resume_title = getattr(resume_data, "title", "") or ""

        # Fallback: use first work experience title
        if not resume_title and resume_data.experience:
            resume_title = resume_data.experience[0].title or ""

        # 2. Get JD title
        jd_title = getattr(job_description, "title", "") or ""

        # If either title missing → 0
        if not resume_title or not jd_title:
            return 0.0

        # 3. Clean both titles (normalize separators, remove noise, sort words)
        def clean_title(text: str) -> str:
            text = text.lower()
            for ch in ["|", "-", "/", "&"]:
                text = text.replace(ch, " ")
            words = text.split()
            stop_words = {"senior", "jr", "junior", "sr", "lead", "intern", "trainee"}
            words = [w for w in words if w not in stop_words]
            return " ".join(sorted(words))

        resume_clean = clean_title(resume_title)
        jd_clean = clean_title(jd_title)

        if not resume_clean or not jd_clean:
            return 0.0

        # 4. Direct full substring match (strong match)
        if resume_clean in jd_clean or jd_clean in resume_clean:
            return 100.0

        # 5. Partial word overlap (relaxed)
        resume_words = set(resume_clean.split())
        jd_words = set(jd_clean.split())
        common = resume_words.intersection(jd_words)

        if not common:
            return 0.0

        # Score by overlap ratio (at least 40 if there is some overlap)
        overlap_ratio = len(common) / max(len(jd_words), 1)
        score = 40.0 + overlap_ratio * 60.0  # 40–100

        return min(score, 100.0)


    def calculate_keyword_match_score(self, resume_data: ResumeData, job_description: JobDescription) -> float:
        """Calculate keyword/skills matching score using skills_database.json and JD action verbs"""
        
        # Flatten database skills (excluding soft_skills)
        db_hard_skills = set()
        for category, skills in self.skills_db.items():
            if category != "soft_skills":
                db_hard_skills.update(s.lower() for s in skills)
        
        # Resume hard skills
        resume_skills = {s.lower() for s in resume_data.skills if s.lower() in db_hard_skills}
        
        # Job Description hard skills
        jd_required = {s.lower() for s in job_description.required_skills if s.lower() in db_hard_skills}
        jd_preferred = {s.lower() for s in job_description.preferred_skills if s.lower() in db_hard_skills}
        
        # Hard skill matches
        required_matches = len(resume_skills.intersection(jd_required))
        preferred_matches = len(resume_skills.intersection(jd_preferred))
        required_score = 100 if not jd_required else (required_matches / len(jd_required)) * 100
        preferred_score = (preferred_matches / len(jd_preferred)) * 100 * 0.3 if jd_preferred else 0
        
        # Soft skill matches
        soft_skills_db = {s.lower() for s in self.skills_db.get("soft_skills", [])}
        resume_soft_skills = {s.lower() for s in resume_data.skills if s.lower() in soft_skills_db}
        jd_soft_skills = {s.lower() for s in getattr(job_description, "soft_skills", []) if s.lower() in soft_skills_db}
        soft_skill_score = (len(resume_soft_skills.intersection(jd_soft_skills)) / (len(jd_soft_skills) or 1)) * 100 * 0.1

        # JD Action verbs
        resume_text = resume_data.raw_text.lower()
        jd_text = getattr(job_description, "raw_text", "").lower()
        jd_verbs_used = [verb for verb in self.action_verbs if verb in jd_text]
        resume_verbs_matched = sum(1 for verb in jd_verbs_used if verb in resume_text)
        action_verbs_score = (resume_verbs_matched / (len(jd_verbs_used) or 1)) * 100 * 0.1

        # TF-IDF text similarity
        try:
            documents = [resume_text, jd_text]
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(documents)
            text_similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
        except:
            text_similarity_score = 0

        # Combine final score
        final_score = (
            required_score * 0.6 +
            preferred_score * 0.1 +
            soft_skill_score +
            action_verbs_score +
            text_similarity_score * 0.2
        )
        return min(final_score, 100)


    def calculate_education_match_score(self, resume_data: ResumeData, job_description: JobDescription) -> float:
        """Calculate education matching score"""
        education_reqs = getattr(job_description, "education_requirements", [])
        if not education_reqs:
            return 100

        if not resume_data.education:
            return 0
        
        score = 0
        total_requirements = len(job_description.education_requirements)
        
        for requirement in job_description.education_requirements:
            requirement_lower = requirement.lower()
            for education in resume_data.education:
                degree_lower = education.degree.lower()
                
                # Degree level matches
                if any(kw in requirement_lower for kw in ["bachelor", "bs", "ba"]):
                    if any(kw in degree_lower for kw in ["bachelor", "bs", "ba"]):
                        score += 100 / total_requirements
                        break
                elif any(kw in requirement_lower for kw in ["master", "ms", "ma", "mba"]):
                    if any(kw in degree_lower for kw in ["master", "ms", "ma", "mba"]):
                        score += 100 / total_requirements
                        break
                elif any(kw in requirement_lower for kw in ["phd", "doctorate"]):
                    if any(kw in degree_lower for kw in ["phd", "doctorate"]):
                        score += 100 / total_requirements
                        break
                elif "degree" in requirement_lower and "degree" in degree_lower:
                    score += 50 / total_requirements
                    break
        
        return min(score, 100)

    def calculate_experience_match_score(self, resume_data: ResumeData, job_description: JobDescription) -> float:
        """Calculate experience matching score"""
        if not resume_data.experience:
            return 0
        
        experience_req_text = getattr(job_description, "experience_requirements", "")
        required_years = self._extract_years_from_text(experience_req_text)

        total_years = sum(self._extract_years_from_duration(exp.duration) for exp in resume_data.experience)
        
        if required_years == 0:
            return 100
        
        ratio = total_years / required_years
        if ratio >= 1.0:
            score = 100
        elif ratio >= 0.8:
            score = 80 + (ratio - 0.8) * 100
        elif ratio >= 0.5:
            score = 50 + (ratio - 0.5) * 100
        else:
            score = ratio * 100
        
        return min(score, 100)

    def calculate_projects_match_score(self, resume_data: ResumeData, job_description: JobDescription) -> float:
    
        if not hasattr(resume_data, 'projects') or not resume_data.projects:
            return 0

        jd_text = getattr(job_description, "raw_text", "").lower()
        jd_skills = {s.lower() for s in job_description.required_skills + job_description.preferred_skills}
        project_texts = []

    # Combine project title + description
        for project in resume_data.projects:
            parts = []
            if hasattr(project, 'title') and project.title:
                parts.append(project.title.lower())
            if hasattr(project, 'description') and project.description:
                parts.append(project.description.lower())
            if parts:
                project_texts.append(" ".join(parts))

        if not project_texts:
            return 0

        all_project_text = " ".join(project_texts)

    # --- TF-IDF similarity ---
        try:
            documents = [all_project_text, jd_text]
            vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
            tfidf_matrix = vectorizer.fit_transform(documents)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            tfidf_score = similarity * 100  # raw TF-IDF percent
        except:
            tfidf_score = 0

    # --- JD-relevant skills in projects ---
        project_words = set(all_project_text.split())
        matched_skills = len(project_words.intersection(jd_skills))
        skills_score = (matched_skills / (len(jd_skills) or 1)) * 100

    # --- Number of projects bonus ---
        num_projects = len(resume_data.projects)
        if num_projects >= 3:
            projects_bonus = 20
        elif num_projects >= 1:
            projects_bonus = 10
        else:
            projects_bonus = 0

    # --- Weighted combination ---
        final_score = tfidf_score * 0.4 + skills_score * 0.4 + projects_bonus * 0.2

        return min(final_score, 100)


    def calculate_format_compliance_score(self, resume_data: ResumeData) -> float:
        """Calculate ATS format compliance score"""
        score = 0
        text = resume_data.raw_text
        
        # Contact info
        if resume_data.contact_info.emails:
            score += 15
        if resume_data.contact_info.phones:
            score += 10
        
        # Required sections
        if resume_data.experience:
            score += 20
        if resume_data.education:
            score += 10
        if resume_data.skills:
            score += 10
        
        # Formatting checks
        if re.search(r"[•\-\*]\s+", text):
            score += 10
        
        word_count = len(text.split())
        if 300 <= word_count <= 1000:
            score += 10
        elif 200 <= word_count <= 1500:
            score += 5
        
        return min(score, 100)

    def calculate_action_verbs_grammar_score(self, resume_data: ResumeData) -> float:
        """Calculate action verbs and grammar score"""
        text = resume_data.raw_text.lower()
        score = 0
        
        # Action verbs
        action_verb_count = sum(len(re.findall(rf"\b{verb}\b", text)) for verb in self.action_verbs)
        word_count = len(text.split())
        verb_density = action_verb_count / word_count if word_count > 0 else 0
        score += min(verb_density * 1000, 60)
        
        # Quantified achievements bonus
        numbers_pattern = r"\d+%|\d+\s*(?:percent|million|thousand|k\b)"
        quantified = len(re.findall(numbers_pattern, text))
        score += min(quantified * 5, 20)
        
        # Grammar base score
        score += 20
        
        return max(0, min(score, 100))

    def calculate_readability_score(self, resume_data: ResumeData) -> float:
        """Calculate readability and structure score"""
        score = 0
        text = resume_data.raw_text
        
        # Sentence length
        sentences = re.split(r"[.!?]+", text)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 20:
                score += 25
            elif 8 <= avg_sentence_length <= 25:
                score += 15
            else:
                score += 5
        
        # Structure checks
        if resume_data.summary:
            score += 10
        if resume_data.experience:
            score += 10
        if resume_data.education:
            score += 10
        if resume_data.skills:
            score += 10
        
        return min(score, 100)
    

    def _extract_years_from_text(self, text: str) -> int:
        """Extract years from text like '3+ years'"""
        if not text:
            return 0
        patterns = [
            r"(\d+)\+?\s*years?",
            r"minimum\s+of\s+(\d+)",
            r"at\s+least\s+(\d+)",
            r"(\d+)-\d+\s*years?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        return 0

    def _extract_years_from_duration(self, duration: str) -> float:
        """Extract years from duration string"""
        if not duration:
            return 0
        
        year_match = re.search(r"(\d{4})\s*-\s*(\d{4})", duration)
        if year_match:
            return int(year_match.group(2)) - int(year_match.group(1))
        
        years_match = re.search(r"(\d+(?:\.\d+)?)\s*years?", duration.lower())
        if years_match:
            return float(years_match.group(1))
        
        months_match = re.search(r"(\d+)\s*months?", duration.lower())
        if months_match:
            return int(months_match.group(1)) / 12
        
        return 1.0
