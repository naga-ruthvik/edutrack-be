from resume.lib.ats_nojd.main import analyze_resume as analyze_resume_no_jd
from resume.lib.atsjd.main import analyze_resume_with_jd as analyze_resume_with_jd

def analyze_resume(resume_text, jd_text):
    if jd_text:
        return analyze_resume_with_jd(resume_text, jd_text)
    else:
        return analyze_resume_no_jd(resume_text)