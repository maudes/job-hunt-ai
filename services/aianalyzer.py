"""
aianalyzer.py — Gemini-powered job description analysis
---------------------------------------------------------
Reads cv.md once at startup, then for each job URL:
  1. Takes the raw JD text from read.py
  2. Sends CV + JD to Gemini with a structured prompt
  3. Returns a dict ready for updatesheet.py

"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from loguru import logger

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CV_PATH = Path(__file__).parent.parent / "data" / "cv.md"
GEMINI_MODEL = "gemini-2.0-flash"  # free tier, fast


# ---------------------------------------------------------------------------
# Load CV once at module import
# ---------------------------------------------------------------------------

def _load_cv() -> str:
    if not CV_PATH.exists():
        raise FileNotFoundError(f"CV not found at {CV_PATH}")
    return CV_PATH.read_text(encoding="utf-8")


_CV_CONTENT = _load_cv()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a strategic career advisor helping a job seeker evaluate job postings against their CV, with a focus on long-term career alignment — not just surface-level matching.

The candidate has the following priorities:
- Prefers stable, reputable companies (ideally globally recognized)
- Interested in IoT, health tech, gov tech, or impactful products
- Wants roles with long-term growth (3–5+ years potential)
- Open to transitioning but values transferable skills
- Values international exposure (global teams, overseas opportunities, or cross-border collaboration)

Analyze the provided CV and job description, then return a JSON object with exactly these keys:

- job_title         (string) job title extracted from the JD
- company           (string) company name extracted from the JD
- location          (string) job location, e.g. "Taipei, Taiwan" or "Remote"
- job_type          (string) "Full-time" | "Part-time" | "Contract" | "Internship"

- description_summary (string) 2-3 sentence summary of what the role is about

- key_requirements  (list of strings) top 5-7 must-have requirements from the JD
- highlights        (list of strings) 3-5 things that make this role attractive or distinctive

- match_score       (integer) overall match percentage 0-100 based on:
                      - Keywords match (20%)
                      - Skills match (30%)
                      - Years of experience (20%)
                      - Industry/domain relevance (15%)
                      - Role trajectory fit (15%)

- career_alignment  (integer) 0-100 score indicating how well this role aligns with the
                      candidate's long-term goals (industry, stability, growth, impact,
                      international exposure)

- relocation_feasibility (string) one of:
                      "High" | "Medium" | "Low" | "Unknown"
                      (based on location, visa likelihood, remote options)

- risk_flags        (list of strings) potential concerns such as:
                      - unstable industry
                      - low growth role
                      - irrelevant to long-term goals
                      - overqualification / underqualification
                      - unclear company credibility
                      - limited international exposure
                      - visa or relocation difficulty

- should_apply      (boolean) true if ALL:
                      - match_score >= 60
                      - career_alignment >= 60
                      - no major dealbreakers

- apply_verdict     (string) one of:
                      "Strong Match"      — match_score >= 75 AND career_alignment >= 75
                      "Good Match"        — match_score >= 60 AND career_alignment >= 70
                      "Strategic Apply"   — match_score >= 60 AND career_alignment 60–69
                                            (worth applying for strategic reasons such as brand,
                                             domain shift, or skill acquisition)
                      "Borderline"        — one score just below 60, no hard dealbreakers
                      "Not Recommended"   — match_score < 60 OR career_alignment < 60
                                            OR clear dealbreakers present

- holistic_explanation (string) 3-4 sentences explaining the decision by combining:
                      - match strength
                      - career alignment
                      - long-term value (skills, industry exposure)
                      - risks vs benefits

- matching_points   (list of strings) specific skills/experiences from the CV that match the JD

- gaps              (list of strings) requirements in the JD that are missing or weak in the CV

- skills_to_highlight (list of strings) skills from the CV to emphasise in the cover letter/interview,
                       only if should_apply is true

- quick_cv_edits    (list of strings) fast, high-impact CV tweaks tailored for THIS role

- application_effort (string) one of:
                      "Low" | "Medium" | "High"
                      (estimate based on gaps, competition, and customization needed)

- strategic_value   (string) 1-2 sentences answering:
                      "Even if not a perfect match, is this role worth applying for strategically?"

Scoring rules:
- Be strict and realistic — do not inflate scores
- Distinguish clearly between:
    - "Can get the job" (match_score)
    - "Should pursue the job" (career_alignment)
- should_apply is false if:
    - match_score < 60
    - OR career_alignment < 60
    - OR clear dealbreakers (e.g. required license, visa infeasibility)

- apply_verdict MUST strictly follow the definitions above and be consistent with both scores

- Favor long-term career strategy over short-term ease:
    - A slightly lower match but high alignment role can still be "Strategic Apply"
    - A high match but low alignment role should NOT be recommended

Respond with ONLY the JSON object. No markdown fences, no explanation, no preamble."""


def _build_prompt(jd_text: str, url: str) -> str:
    return f"""CV:
\"\"\"
{_CV_CONTENT}
\"\"\"

Job Description (source: {url}):
\"\"\"
{jd_text[:6000]}
\"\"\"
"""


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def analyze(jd_text: str, url: str) -> dict:
    """
    Analyze a job description against the loaded CV.

    Parameters
    ----------
    jd_text : str
        Raw plain-text job description from read.py
    url : str
        Original job posting URL (included in prompt for context)

    Returns
    -------
    dict with all analysis fields, plus 'original_url' injected.
    Raises ValueError if Gemini returns unparseable JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(jd_text, url)

    logger.info(f"[Gemini] analyzing JD for {url}")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={"system_instruction": _SYSTEM_PROMPT},
    )

    raw = response.text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"[Gemini] JSON parse failed: {e}\nRaw response:\n{raw[:500]}")
        raise ValueError(f"Gemini returned invalid JSON: {e}") from e

    # Inject the source URL so updatesheet.py doesn't need to pass it separately
    result["original_url"] = url

    verdict = result.get("apply_verdict", "?")
    score = result.get("match_score", "?")
    logger.success(f"[Gemini] done — {verdict} ({score}%) for {url}")

    return result


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from services.read import fetch_job_content

    test_url = "https://www.104.com.tw/job/8wywf"
    raw = fetch_job_content(test_url)

    if not raw:
        print("Could not fetch job content")
    else:
        result = analyze(raw, test_url)
        print(json.dumps(result, indent=2, ensure_ascii=False))