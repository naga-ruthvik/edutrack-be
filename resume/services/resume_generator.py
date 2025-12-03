import json
from resume.lib.resume_builder.main import create_resume_from_string

def generate_resume_service(resume_text: str, jd_text: str = "") -> dict:
    """
    Service to handle resume generation.
    Can add extra logic here (logging, caching, etc.)
    """
    json_str = create_resume_from_string(resume_text, jd_text)
    return json.loads(json_str)