#!/usr/bin/env python3
"""
Clean ATS Resume Scorer + Resume Analyzer (JD-Aware)
NO LLM, NO report generator, NO exports
"""

import argparse
import json
import sys
import logging
from pathlib import Path

from .parsers.resume_parser import ResumeParser
from .parsers.jd_parser import JobDescriptionParser
from .scoring.scoring_engine import ATSScoringEngine, ScoringWeights
from .analyzers.resume_analyzer import ResumeJDAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def analyze_resume_with_jd(resume_data: dict, jd_text: str, weights_path: str = None) -> dict:
    """
    Analyzes a resume dictionary against a JD text and returns the results.
    Can be imported and used directly by the backend.
    """
    # Resolve paths relative to this file
    base_dir = Path(__file__).resolve().parent
    skills_db_path = base_dir / "config" / "skills_database.json"

    # Load custom weights (optional)
    weights = None
    if weights_path and Path(weights_path).exists():
        with open(weights_path, "r", encoding="utf-8") as f:
            weights = ScoringWeights(**json.load(f))

    # Parsers and engines
    resume_parser = ResumeParser(skills_db_path=str(skills_db_path))
    jd_parser = JobDescriptionParser()
    scoring_engine = ATSScoringEngine(weights)
    analyzer = ResumeJDAnalyzer(config_folder=str(base_dir / "config"))

    # Parse resume (supports dict input now)
    parsed_resume = resume_parser.parse_resume(resume_data)

    # Parse JD
    jd_data = jd_parser.parse_job_description(jd_text)

    # Compute ATS score
    scores = scoring_engine.calculate_overall_score(parsed_resume, jd_data)

    # Run analyzer
    analysis = analyzer.run_analysis(resume_data, jd_data)

    # ---------- BUILD JSON STRUCTURE ----------

    # ATS RESULTS section
    ats_results = {
        "header": "ATS RESULTS",
        "total_score_line": f"Total ATS Score: {scores['total_score']}/100",
        "breakdown_header": "Breakdown:",
        "breakdown_lines": [
            f"Keyword Match           : {scores['detailed_scores'].get('keyword_match', 0)}",
            f"Title Match             : {scores['detailed_scores'].get('title_match', 0)}",
            f"Education Match         : {scores['detailed_scores'].get('education_match', 0)}",
            f"Experience Match        : {scores['detailed_scores'].get('experience_match', 0)}",
            f"Projects Match          : {scores['detailed_scores'].get('projects_match', 0)}",
            f"Format Compliance       : {scores['detailed_scores'].get('format_compliance', 0)}",
            f"Action Verbs Grammar    : {scores['detailed_scores'].get('action_verbs_grammar', 0)}",
            f"Readability             : {scores['detailed_scores'].get('readability', 0)}",
        ]
    }

    # RESUME ANALYZER sections
    document_synopsis_lines = list(analysis["document_synopsis"]["messages"].values())
    data_identification_lines = [
        item["success"] if item["valid"] else item["fail"]
        for item in analysis["data_identification"].values()
    ]
    lexical_analysis_lines = list(analysis["lexical_analysis"]["messages"].values())
    semantic_analysis_lines = list(analysis["semantic_analysis"]["messages"].values())
    jd_matching_lines = list(analysis["jd_matching"]["messages"].values())

    resume_analyzer = {
        "header": "RESUME ANALYZER",
        "sections": {
            "DOCUMENT SYNOPSIS": document_synopsis_lines,
            "DATA IDENTIFICATION": data_identification_lines,
            "LEXICAL ANALYSIS": lexical_analysis_lines,
            "SEMANTIC ANALYSIS": semantic_analysis_lines,
            "JD MATCHING": jd_matching_lines,
        },
    }

    # Final JSON structure
    return {
        "ats_results": ats_results,
        "resume_analyzer": resume_analyzer
    }


def main():
    parser = argparse.ArgumentParser(description="ATS Resume Scorer + Resume Analyzer")

    parser.add_argument("--resume", "-r", required=True, help="Resume JSON file")
    parser.add_argument("--jd", "-j", required=True, help="Job description TXT file")
    parser.add_argument("--weights", "-w", help="Custom weights JSON")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    resume_path = Path(args.resume)
    jd_path = Path(args.jd)

    if not resume_path.exists():
        print(json.dumps({"error": f"Resume not found: {str(resume_path)}"}))
        sys.exit(1)
    if not jd_path.exists():
        print(json.dumps({"error": f"JD not found: {str(jd_path)}"}))
        sys.exit(1)

    # Load Resume JSON
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)

    # Load JD Text
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    # Run Analysis
    try:
        output = analyze_resume_with_jd(resume_data, jd_text, args.weights)
        print(json.dumps(output, indent=2))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
