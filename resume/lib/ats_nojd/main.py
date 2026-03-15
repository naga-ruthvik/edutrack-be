#!/usr/bin/env python3
"""
Clean ATS Resume Scorer + Resume Analyzer (Resume-Only)
NO LLM, NO JD, NO report generator, NO exports
"""

import argparse
import json
import sys
import logging
from pathlib import Path

from .parsers.resume_parser import ResumeParser
from .scoring.scoring_engine import ATSScoringEngine, ScoringWeights
from .analyzers.resume_analyzer import ResumeAnalyzer


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def analyze_resume(resume_data: dict, weights_path: str = None) -> dict:
    """
    Analyzes a resume dictionary and returns the results.
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
    scoring_engine = ATSScoringEngine(weights)
    analyzer = ResumeAnalyzer(config_folder=str(base_dir / "config"))

    # Parse resume (supports dict input now)
    # Note: parse_resume returns a ResumeData object
    parsed_resume = resume_parser.parse_resume(resume_data)

    # Compute ATS score (resume-only)
    scores = scoring_engine.calculate_resume_only_score(parsed_resume)

    # Run analyzer (expects dict)
    analysis = analyzer.run_analysis(resume_data)

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
        ],
        "weights_header": "Weights Used:",
        "weights_lines": [
            f"{k}: {v}" for k, v in scores.get("weights_used", {}).items()
        ],
    }

    # RESUME ANALYZER sections
    document_synopsis_lines = list(
        analysis["document_synopsis"]["messages"].values()
    )
    data_identification_lines = [
        item["success"] if item["valid"] else item["fail"]
        for item in analysis["data_identification"].values()
    ]
    lexical_analysis_lines = list(
        analysis["lexical_analysis"]["messages"].values()
    )
    semantic_analysis_lines = list(
        analysis["semantic_analysis"]["messages"].values()
    )

    resume_analyzer = {
        "header": "RESUME ANALYZER",
        "sections": {
            "DOCUMENT SYNOPSIS": document_synopsis_lines,
            "DATA IDENTIFICATION": data_identification_lines,
            "LEXICAL ANALYSIS": lexical_analysis_lines,
            "SEMANTIC ANALYSIS": semantic_analysis_lines,
        },
    }

    # Final JSON structure
    return {
        "ats_results": ats_results,
        "resume_analyzer": resume_analyzer,
    }


def main():
    parser = argparse.ArgumentParser(
        description="ATS Resume Scorer + Resume Analyzer (Resume-Only, No JD)"
    )

    parser.add_argument("--resume", "-r", required=True, help="Resume JSON file")
    parser.add_argument("--weights", "-w", help="Custom weights JSON")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    resume_path = Path(args.resume)

    if not resume_path.exists():
        print(json.dumps({"error": f"Resume not found: {str(resume_path)}"}))
        sys.exit(1)

    # Load Resume JSON
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)

    # Run Analysis
    try:
        output = analyze_resume(resume_data, args.weights)
        print(json.dumps(output, indent=2))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
