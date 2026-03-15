"""
ATS Scoring Engine - Resume Only (No JD Required)
Core scoring logic that evaluates a resume on its own quality,
without comparing it to a specific job description.
"""

import re
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..parsers.resume_parser import ResumeData

from ..config.constants import DEFAULT_RESUME_ONLY_WEIGHTS, ACTION_VERBS

logger = logging.getLogger(__name__)


# ===========================
#  WEIGHTS
# ===========================

@dataclass
class ScoringWeights:
    """Configurable scoring weights for resume‑only evaluation."""
    keyword_match: float = 0.30
    title_match: float = 0.10
    education_match: float = 0.10
    experience_match: float = 0.15
    projects_match: float = 0.10
    format_compliance: float = 0.10
    action_verbs_grammar: float = 0.10
    readability: float = 0.05

    def __post_init__(self):
        """Optionally ensure weights are in a sane range (sum ~= 1.0)."""
        total = (
            self.keyword_match + self.title_match + self.education_match +
            self.experience_match + self.projects_match + self.format_compliance +
            self.action_verbs_grammar + self.readability
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")


# ===========================
#  SCORING ENGINE
# ===========================

class ATSScoringEngine:
    """
    Resume‑only ATS scoring engine.
    It does not accept or require a Job Description object.
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        # Load weights from JSON if not provided, otherwise use defaults
        if weights:
            self.weights = weights
        else:
            self.weights = ScoringWeights(**DEFAULT_RESUME_ONLY_WEIGHTS)

        # Load action verbs from config constants
        # Flatten all lists in the dict
        self.action_verbs = [
            verb for verbs in ACTION_VERBS.values() 
            if isinstance(verbs, list) for verb in verbs
        ]

    # ----------------------------------------------------
    # PUBLIC API — Resume‑Only
    # ----------------------------------------------------
    def calculate_resume_only_score(self, resume_data: ResumeData) -> Dict[str, Any]:
        """
        Main public method: computes a score using ONLY the resume content.
        """
        return self.calculate_overall_score(resume_data)

    # ----------------------------------------------------
    # INTERNAL MASTER CALCULATION
    # ----------------------------------------------------
    def calculate_overall_score(self, resume_data: ResumeData) -> Dict[str, Any]:
        """Aggregate all component scores into a final weighted score."""

        keyword_score = self.calculate_keyword_match_score(resume_data)
        title_score = self.calculate_title_match_score(resume_data)
        education_score = self.calculate_education_match_score(resume_data)
        experience_score = self.calculate_experience_match_score(resume_data)
        projects_score = self.calculate_projects_match_score(resume_data)
        format_score = self.calculate_format_compliance_score(resume_data)
        action_verbs_score = self.calculate_action_verbs_grammar_score(resume_data)
        readability_score = self.calculate_readability_score(resume_data)

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
            "weights_used": self.weights.__dict__,
        }

    # ==============================
    #  SCORING COMPONENTS
    # ==============================

    # 1. SKILL RICHNESS / KEYWORD SCORE
    def calculate_keyword_match_score(self, resume_data: ResumeData) -> float:
        """
        Simple skill‑richness score, independent of a JD.
        More unique skills → higher score.
        """
        skills = {s.lower() for s in (resume_data.skills or [])}
        if not skills:
            return 0.0

        count = len(skills)
        if count >= 20:
            return 100.0
        elif count >= 15:
            return 90.0
        elif count >= 10:
            return 80.0
        elif count >= 5:
            return 60.0
        else:
            return 40.0

    # 2. TITLE QUALITY SCORE
    def calculate_title_match_score(self, resume_data: ResumeData) -> float:
        """
        Rates how strong the candidate's main title looks,
        without any JD to compare against.
        """
        title = getattr(resume_data, "title", "") or ""
        if not title and resume_data.experience:
            title = resume_data.experience[0].title or ""

        if not title:
            return 0.0

        title = title.lower()
        strong = ["engineer", "developer", "scientist", "analyst", "manager"]
        good = ["intern", "assistant", "trainee"]

        if any(w in title for w in strong):
            return 100.0
        elif any(w in title for w in good):
            return 70.0
        else:
            return 50.0

    # 3. EDUCATION SCORE
    def calculate_education_match_score(self, resume_data: ResumeData) -> float:
        """
        Scores the highest degree level in the resume.
        No JD requirement logic here.
        """
        if not resume_data.education:
            return 0.0

        highest = max(
            (edu.degree.lower() for edu in resume_data.education if edu.degree),
            default=""
        )

        if "phd" in highest or "doctor" in highest:
            return 100.0
        if "master" in highest or "ms" in highest or "ma" in highest or "mba" in highest:
            return 90.0
        if "bachelor" in highest or "b.tech" in highest or "bs" in highest or "be" in highest:
            return 80.0
        if "diploma" in highest:
            return 60.0
        return 40.0

    # 4. EXPERIENCE DURATION SCORE
    def calculate_experience_match_score(self, resume_data: ResumeData) -> float:
        """
        Approximates total years of experience from durations in work history.
        """
        if not resume_data.experience:
            return 0.0

        years = sum(self._extract_years_from_duration(exp.duration or "")
                    for exp in resume_data.experience)

        if years >= 8:
            return 100.0
        elif years >= 5:
            return 90.0
        elif years >= 3:
            return 75.0
        elif years >= 1:
            return 60.0
        else:
            return 40.0

    def _extract_years_from_duration(self, duration: str) -> float:
        """
        Simple heuristic: look for patterns like '2 years'.
        Fallback small credit if nothing is found.
        """
        numbers = re.findall(r"(\d+(?:\.\d+)?)\s*year", duration.lower())
        if numbers:
            return float(numbers[0])
        return 0.5  # fallback credit

    # 5. PROJECT QUALITY SCORE
    def calculate_projects_match_score(self, resume_data: ResumeData) -> float:
        """
        Rates number of projects only (no JD relevance).
        """
        projects = getattr(resume_data, "projects", []) or []
        count = len(projects)

        if count >= 5:
            return 100.0
        elif count == 4:
            return 85.0
        elif count == 3:
            return 70.0
        elif count == 2:
            return 55.0
        elif count == 1:
            return 40.0
        else:
            return 20.0

    # 6. FORMAT CHECK SCORE
    def calculate_format_compliance_score(self, resume_data: ResumeData) -> float:
        """
        Basic structure check: presence of key sections only.
        """
        score = 0.0
        if resume_data.skills:
            score += 25.0
        if resume_data.experience:
            score += 25.0
        if resume_data.education:
            score += 25.0
        if getattr(resume_data, "projects", []):
            score += 25.0
        return min(score, 100.0)

    # 7. ACTION VERBS / GRAMMAR SCORE
    def calculate_action_verbs_grammar_score(self, resume_data: ResumeData) -> float:
        """
        Uses loaded action verbs plus basic quantified‑achievement checks.
        No language‑model grammar check to keep it lightweight.
        """
        text = (resume_data.raw_text or "").lower()
        score = 0.0

        # Action verb density
        action_verb_count = sum(
            len(re.findall(rf"\b{re.escape(verb)}\b", text))
            for verb in self.action_verbs
        )
        word_count = len(text.split()) or 1
        verb_density = action_verb_count / word_count
        score += min(verb_density * 1000.0, 60.0)

        # Quantified results (numbers, percentages, etc.)
        numbers_pattern = r"\d+%|\d+\s*(?:percent|million|thousand|k\b)"
        quantified = len(re.findall(numbers_pattern, text))
        score += min(quantified * 5.0, 20.0)

        # Base grammar / structure credit
        score += 20.0

        return max(0.0, min(score, 100.0))

    # 8. READABILITY SCORE
    def calculate_readability_score(self, resume_data: ResumeData) -> float:
        """
        Simple readability / structure heuristic, independent of any JD.
        """
        score = 0.0
        text = resume_data.raw_text or ""

        # Sentence length heuristic
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 20:
                score += 25.0
            elif 8 <= avg_sentence_length <= 25:
                score += 15.0
            else:
                score += 5.0

        # Section presence
        if resume_data.summary:
            score += 10.0
        if resume_data.experience:
            score += 10.0
        if resume_data.education:
            score += 10.0
        if resume_data.skills:
            score += 10.0

        return min(score, 100.0)
