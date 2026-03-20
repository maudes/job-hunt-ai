"""
aianalyzer.py — Gemini-powered job description analysis
---------------------------------------------------------
Reads cv.md once at startup, then for each job URL:
  1. Takes the raw JD text from read.py
  2. Sends CV + JD to Gemini with a structured prompt
  3. Returns a dict ready for updatesheet.py

Install:
    uv add google-genai python-dotenv

.env:
    GEMINI_API_KEY=your_key_here
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

CV_PATH     = Path(__file__).parent.parent / "data" / "cv.md"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyzer_prompt.md"
GEMINI_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Load CV and prompt once at module import
# ---------------------------------------------------------------------------

def _load_cv() -> str:
    if not CV_PATH.exists():
        raise FileNotFoundError(f"CV not found at {CV_PATH}")
    return CV_PATH.read_text(encoding="utf-8")


def _load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt not found at {PROMPT_PATH}")
    text = PROMPT_PATH.read_text(encoding="utf-8")
    # Strip version comment header if present
    lines = [l for l in text.splitlines() if not l.startswith("<!--")]
    return "\n".join(lines).strip()


_CV_CONTENT   = _load_cv()
_SYSTEM_PROMPT = _load_prompt()


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
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not set in .env")

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