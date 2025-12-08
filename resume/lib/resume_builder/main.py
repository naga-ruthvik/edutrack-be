import json
import google.generativeai as genai
import os
import traceback

# ======================================================
# 1. SAFE JSON PARSER
# ======================================================

RESUME_GEMINI_API_KEY=os.getenv("RESUME_GEMINI_API_KEY")

def safe_parse_json(raw_json: str) -> dict:
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        last = raw_json.rfind("}")
        if last != -1:
            try:
                return json5.loads(raw_json[:last+1])
            except Exception:
                pass
    # fallback: try to locate first "{" ... "}" slice
    try:
        start = raw_json.find("{")
        end = raw_json.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json5.loads(raw_json[start:end+1])
    except Exception:
        pass
    return {}

# ======================================================
# 2. GEMINI CALL FUNCTION (defensive)
# ======================================================
def call_llm_extract(prompt: str) -> dict:
    try:
        genai.configure(api_key=RESUME_GEMINI_API_KEY)  # <-- replace with your Gemini API key

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction="Return only valid JSON. No explanations."
        )

        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0,
            "max_output_tokens": 2000,
            "candidate_count": 1
        }

        response = model.generate_content(prompt, generation_config=generation_config)
        # Response object shape can vary by SDK version — try common attributes
        raw_text = ""
        if hasattr(response, "text"):
            raw_text = response.text
        elif hasattr(response, "content"):
            # some SDKs return response.content
            raw_text = response.content
        else:
            raw_text = str(response)

        parsed = safe_parse_json(raw_text)
        if not isinstance(parsed, dict):
            print("[WARN] LLM returned JSON that is not an object; parsed type:", type(parsed))
            # wrap into a dict if it's a list or something else
            return {"_raw_parsed": parsed}
        return parsed
    except Exception as e:
        print("[ERROR] call_llm_extract failed:", e)
        traceback.print_exc()
        return {}

# ======================================================
# 3. BUILD PROMPT
# ======================================================
def build_extraction_prompt(resume_text: str, job_description: str) -> str:
    prompt = f"""
You are ATS Resume Generator — an expert system for parsing, structuring, and formatting resumes.  
Your primary objective is: PRESERVE 100% OF THE ORIGINAL CONTENT WITHOUT ALTERING ANY MEANING.  
You must output STRICT VALID JSON following the exact schema provided.

CRITICAL CONTENT PRESERVATION RULES

1. You MUST preserve every bullet point, sentence, description, detail, responsibility, and technical term.
2. You MUST NOT delete, shorten, paraphrase, simplify, summarize, or alter ANY content.
3. You MUST NOT invent companies, roles, skills, dates, education, achievements, tools, or certifications.
4. You MUST NOT change numerical values, dates, metrics, or terminology.
5. If the user provides incomplete information, output empty strings ("") or empty arrays/lists, NEVER null.

PERMITTED FORMAT IMPROVEMENTS

You may ONLY:
- Fix minor punctuation inconsistencies
- Correct capitalization of proper nouns or section titles
- Standardize spacing & indentation
- Standardize bullet formatting
- Organize content into the correct JSON fields without altering wording

You may NOT change wording, meaning, or order of facts.

Position and job_description are the SAME.
If 'position' is missing:
- If job_description exists → use job_description as the position.
- If job_description is empty → generate the position from skills.


SUMMARY RULES
- You MUST generate a 2-4 line professional summary.
- The summary must ONLY use information explicitly provided by the user.

MISSING DATA RULE
For ANY missing field:
- Use "" for text
- Use [] for lists
- Never output null.
INPUT RESUME TEXT:
\"\"\"{resume_text}\"\"\"

JOB DESCRIPTION:
\"\"\"{job_description}\"\"\"

STRICT OUTPUT SCHEMA

{{
  "name": "",
  "position": "",
  "contactInformation": "",
  "email": "",
  "address": "",
  "profilePicture": "",
  "socialMedia": [],
  "summary": "",
  "education": [],
  "workExperience": [],
  "projects": [],
  "skills": [],
  "languages": [],
  "certifications": []
}}

PROCESSING STEPS  
1. ANALYZE → Understand structure & content.  
2. EXTRACT → Move ALL user-provided details into correct JSON fields.  
3. FORMAT → Apply allowed formatting improvements.  
4. VALIDATE → Ensure NO content is missing, changed, shortened, or invented.  
5. OUTPUT → Produce ONLY the strict JSON.
6.You must convert every skill listed in the resume into **JSON objects** with this format:
   {{
       "title": "<Category Name>",  // e.g., "Technical Skills", "Soft Skills", "Additional Skills"
       "skills": ["Skill 1", "Skill 2", ...]  // each skill as a separate string
   }}
"""
    return prompt


# ======================================================
# helpers: normalize utilities
# ======================================================
def ensure_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]

def safe_get_list_of_dicts(value):
    """
    Accept many shapes: list of dicts, dict, list of strings, string.
    Return list of dict-like objects where possible.
    """
    if value is None:
        return []
    if isinstance(value, list):
        # if items are strings, convert to list of dicts with a single key 'value'
        out = []
        for it in value:
            if isinstance(it, dict):
                out.append(it)
            else:
                out.append({"value": it})
        return out
    if isinstance(value, dict):
        return [value]
    # fallback: single string
    return [{"value": value}]

# ======================================================
# 4. CONVERSION TO TARGET FORMAT (comprehensive)
# ======================================================
def convert_to_target_format(raw: dict) -> dict:
    """
    Map LLM output (raw) to exact target schema and order.
    Defensive handling of different key names/shapes.
    """
    if not isinstance(raw, dict):
        return {
            "name": "",
            "position": "",
            "contactInformation": "",
            "email": "",
            "address": "",
            "profilePicture": "",
            "socialMedia": [],
            "summary": "",
            "education": [],
            "workExperience": [],
            "projects": [],
            "skills": [],
            "languages": [],
            "certifications": []
        }

    def read_str(*keys):
        for k in keys:
            val = raw.get(k)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def read_list(*keys):
        for k in keys:
            val = raw.get(k)
            if val is None:
                continue
            if isinstance(val, list):
                return val
            if isinstance(val, str) and "," in val:
                return [s.strip() for s in val.split(",") if s.strip()]
            return [val]
        return []

    output = {
        "name": read_str("name", "fullName", "fullname"),
        "position": read_str("position", "role", "job_title", "title"),
        "contactInformation": read_str("contactInformation", "contact", "phone", "phoneNumber"),
        "email": read_str("email", "Email", "emailAddress"),
        "address": read_str("address", "location", "addr"),
        "profilePicture": read_str("profilePicture", "photo", "avatar"),
        "socialMedia": [],
        "summary": read_str("summary", "objective", "profile"),
        "education": [],
        "workExperience": [],
        "projects": [],
        "skills": [],
        "languages": read_list("languages", "language"),
        "certifications": []
    }

    # ---- Social Media ----
    raw_sm = raw.get("socialMedia") or raw.get("socialMedias") or raw.get("socials") or []
    for item in ensure_list(raw_sm):
        if isinstance(item, dict):
            name = item.get("platform") or item.get("socialMedia") or item.get("name") or ""
            link = item.get("url") or item.get("link") or item.get("value") or ""
            output["socialMedia"].append({"socialMedia": name, "link": link})
        elif isinstance(item, str) and ":" in item:
            name, link = item.split(":", 1)
            output["socialMedia"].append({"socialMedia": name.strip(), "link": link.strip()})
        else:
            output["socialMedia"].append({"socialMedia": str(item), "link": ""})

    # ---- Education ----
    raw_edu = raw.get("education") or raw.get("educations") or []
    for edu in ensure_list(raw_edu):
        if isinstance(edu, dict):
            school = edu.get("school") or edu.get("degree") or edu.get("institution") or edu.get("college") or ""
            degree = edu.get("degree") or edu.get("major") or edu.get("program") or ""
            duration = edu.get("duration") or edu.get("years") or ""
            startYear = endYear = ""
            if isinstance(duration, str) and " - " in duration:
                startYear, endYear = [p.strip() for p in duration.split(" - ", 1)]
            else:
                startYear = str(edu.get("startYear") or edu.get("from") or "")
                endYear = str(edu.get("endYear") or edu.get("to") or "")
            output["education"].append({
                "school": school,
                "degree": degree,
                "startYear": startYear,
                "endYear": endYear
            })
        else:
            output["education"].append({"school": str(edu), "degree": "", "startYear": "", "endYear": ""})

    # ---- Work Experience ----
    raw_work = raw.get("workExperience") or raw.get("experience") or raw.get("work_experience") or []
    for w in ensure_list(raw_work):
        if isinstance(w, dict):
            company = w.get("company") or w.get("employer") or w.get("organization") or ""
            position = w.get("position") or w.get("role") or w.get("title") or ""
            description = w.get("description") or w.get("location") or w.get("summary") or ""
            resp = w.get("responsibilities") or w.get("achievements") or w.get("keyAchievements") or w.get("tasks") or []
            if isinstance(resp, str):
                resp_list = [r.strip() for r in resp.replace(";", "\n").split("\n") if r.strip()]
            else:
                resp_list = ensure_list(resp)
            duration = w.get("duration") or w.get("period") or ""
            startYear = endYear = ""
            if isinstance(duration, str) and " - " in duration:
                startYear, endYear = [p.strip() for p in duration.split(" - ", 1)]
            else:
                startYear = str(w.get("startYear") or w.get("from") or "")
                endYear = str(w.get("endYear") or w.get("to") or "")
            output["workExperience"].append({
                "company": company,
                "position": position,
                "description": description,
                "keyAchievements": "\n".join(resp_list),
                "startYear": startYear,
                "endYear": endYear
            })
        else:
            s = str(w)
            output["workExperience"].append({
                "company": s, "position": "", "description": "", "keyAchievements": "", "startYear": "", "endYear": ""
            })

    # ---- Projects (FIXED INDENTATION + CORRECT FORMAT) ----
    raw_projects = raw.get("projects") or []
    for p in ensure_list(raw_projects):
        if isinstance(p, dict):
            ka = p.get("keyAchievements") or p.get("achievements") or p.get("Key Achievements") or ""
            if isinstance(ka, list):
                ka = "\n".join([str(k).strip() for k in ka if k])
            output["projects"].append({
                "name": p.get("name") or p.get("title") or p.get("Project Name") or "",
                "link": p.get("link") or p.get("url") or "",
                "description": p.get("description") or "",
                "keyAchievements": ka,
                "startYear": p.get("startYear") or p.get("start") or "",
                "endYear": p.get("endYear") or p.get("end") or ""
            })
        else:
            output["projects"].append({
                "name": str(p),
                "link": "",
                "description": "",
                "keyAchievements": "",
                "startYear": "",
                "endYear": ""
            })
    
    

    # ---- Skills (ATS-ready, flat strings) ----
    output["skills"] = []
    raw_skills = raw.get("skills") or []

    for group in ensure_list(raw_skills):
        if isinstance(group, dict):
            title = (group.get("title") or "Skills").strip()
            skills_list = []
            for s in ensure_list(group.get("skills", [])):
                if isinstance(s, str) and s.strip():
                    skills_list.append(s.strip())
                elif isinstance(s, dict):
                # Flatten objects like {"name": "Python"} or {"skillName": "React"} to strings
                    for key in ["name", "skillName", "skill"]:
                        if key in s and isinstance(s[key], str) and s[key].strip():
                            skills_list.append(s[key].strip())
            if skills_list:
                output["skills"].append({"title": title, "skills": skills_list})

        elif isinstance(group, list):
            skills_list = [s.strip() for s in group if isinstance(s, str) and s.strip()]
            if skills_list:
                output["skills"].append({"title": "Skills", "skills": skills_list})

        elif isinstance(group, str) and group.strip():
        # Single string → default to Technical Skills
            output["skills"].append({
                "title": "Technical Skills",
                "skills": [group.strip()]
            })

    # ---- Languages (flat array of strings for ATS) ----
    # ---- Languages (flat array of strings for ATS input box) ----
    raw_langs = raw.get("languages") or raw.get("language") or []
    flat_langs = []
    for l in ensure_list(raw_langs):
        if isinstance(l, str) and l.strip():
            flat_langs.append(l.strip())
        elif isinstance(l, dict):
            val = l.get("language") or l.get("name") or ""
            if val.strip():
                flat_langs.append(val.strip())
        output["languages"] = flat_langs




    # ---- Certifications ----
    raw_certs = raw.get("certifications") or raw.get("certs") or []
    for c in ensure_list(raw_certs):
        if isinstance(c, dict):
            output["certifications"].append(c.get("name") or c.get("title") or "")
        else:
            output["certifications"].append(str(c))

    # ---- Ensure all arrays are lists ----
    for key in ["socialMedia", "education", "workExperience", "projects", "skills", "languages", "certifications"]:
        output[key] = ensure_list(output.get(key))

    return output



# ======================================================
# 5. CREATE RESUME
# ======================================================
def create_resume_from_string(resume_text: str, job_description: str = "") -> str:
    try:
        raw_result = call_llm_extract(build_extraction_prompt(resume_text, job_description))
        if not raw_result:
            print("[WARN] LLM returned empty result; proceeding with defaults.")
        final_result = convert_to_target_format(raw_result or {})
        return json.dumps(final_result, separators=(",", ":"))
    except Exception as e:
        print("[ERROR] create_resume_from_string failed:", e)
        traceback.print_exc()
        # return an empty-but-valid schema if something went wrong
        empty = {
            "name": "",
            "position": "",
            "contactInformation": "",
            "email": "",
            "address": "",
            "profilePicture": "",
            "socialMedia": [],
            "summary": "",
            "education": [],
            "workExperience": [],
            "projects": [],
            "skills": [],
            "languages": [],
            "certifications": []
        }
        return json.dumps(empty, separators=(",", ":"))

# ======================================================
# 6. MAIN — PROCESS MULTIPLE RESUMES
# ======================================================
# if __name__ == "__main__":
#     # Replace this list with your input array (you posted earlier)
#     input_list = [
#         {
#             "text": """
#             Name: Olivia Bennett
# Email: olivia.bennett@example.com
# Contact Information: +1-555-0200
# Address: 789 Innovation Avenue, New York, NY
# Profile Picture: https://example.com/profiles/olivia.jpg

# Social Media:
# LinkedIn: https://linkedin.com/in/oliviabennett
# GitHub: https://github.com/oliviabennett

# Education:

# Bachelor of Science in Computer Engineering
# College: New York University, NY
# Start Year: 2014
# End Year: 2018
# CGPA: 8.9/10
# Courses: Computer Networks, Operating Systems, Machine Learning, Cloud Computing, Database Systems

# Intermediate (Science)
# School: Manhattan College, NY
# Start Year: 2012
# End Year: 2014
# Percentage: 92%

# Secondary School
# School: Riverdale High School, NY
# Start Year: 2000
# End Year: 2012
# GPA: 9.4/10

# Work Experience:

# NextGen Solutions
# Role: Full Stack Developer
# Location: New York, NY
# Duration: Jul 2018 - Present
# Responsibilities:
# Developed full-stack web applications using Django and React
# Optimized SQL queries and database performance
# Implemented CI/CD pipelines with Docker and GitHub Actions
# Collaborated with product team for feature development

# TechBridge Inc
# Role: Software Development Intern
# Location: New York, NY
# Duration: Jan 2018 - Jun 2018
# Responsibilities:
# Assisted in building internal tools and APIs
# Performed unit testing and debugging
# Documented code and workflows for team use

# Projects:

# Online Learning Platform
# Link: https://github.com/oliviabennett/online-learning
# Description: Built an online learning platform with course management and real-time quizzes.
# Key Achievements:
# Increased student engagement by 30%
# Integrated real-time chat and notifications
# StartYear: Feb 2018
# EndYear: Jun 2018

# API Analytics Dashboard
# Link: https://github.com/oliviabennett/api-analytics
# Description: Dashboard to monitor API usage, performance, and errors.
# Key Achievements:
# Reduced API response time by 20%
# Automated alert notifications for failures
# StartYear: Sep 2017
# EndYear: Jan 2018

# Skills:

# Technical Skills:
# Python, JavaScript, HTML, CSS,Frameworks: Django, React, Flask,PostgreSQL, MongoDB,Docker, Git, GitHub Actions

# Soft Skills:
# Teamwork, Problem Solving, Communication, Time Management

# Languages:
# English, French

# Certifications:
# AWS Certified Developer -Associate, 2019
# Python for Data Analysis (Coursera), 2018
# Certified Scrum Master (CSM), 2020

# """,
#             "jd": " "
#         }
#     ]

#     os.makedirs("extracted_resumes", exist_ok=True)

#     for idx, item in enumerate(input_list, start=1):
#         minified_json = create_resume_from_string(item["text"], item.get("jd", ""))
#         filename = f"extracted_resumes/resume_{idx}.json"
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(minified_json)
#         print(f"[INFO] Saved minified JSON for resume {idx}: {filename}")
#         print(minified_json)  # one-line JSON
