"""
Extract and Transfrom the job description text from the provided url.
"""
import re
import requests
from bs4 import BeautifulSoup
from loguru import logger


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Workday: captures (subdomain_with_version, tenant, board_type, job_slug)
# e.g. https://advantech.wd3.myworkdayjobs.com/zh-TW/External/job/Solution-PM_JR202603039
WORKDAY_RE = re.compile(
    r'https://([^.]+\.\w+)\.myworkdayjobs\.com/([^/]+)/([^/]+)/job/([^/?#]+)'
)

# Greenhouse: https://job-boards.greenhouse.io/company/jobs/12345
GREENHOUSE_RE = re.compile(
    r'https://job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)'
)

# Ashby: https://jobs.ashbyhq.com/wemolo/72f4f134-930f-488b-806e-81c15c8e31a1
ASHBY_RE = re.compile(
    r'https://jobs\.ashbyhq\.com/([^/]+)/([a-f0-9-]{36})'
)

# Lever: https://jobs.lever.co/company/uuid
LEVER_RE = re.compile(
    r'https://jobs\.lever\.co/([^/]+)/([a-f0-9-]{36})'
)

# SmartRecruiters: https://careers.smartrecruiters.com/Company/job-id
SMARTRECRUITERS_RE = re.compile(
    r'https://jobs\.smartrecruiters\.com/([^/]+)/([^/?#]+)'
)


# ---------------------------------------------------------------------------
# HTML → plain text helper
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Strip HTML tags and normalise whitespace for LLM consumption."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["p", "li", "br", "h1", "h2", "h3", "h4"]):
        tag.insert_before("\n")
    text = soup.get_text(separator=" ")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


# ---------------------------------------------------------------------------
# Per-platform fetchers
# ---------------------------------------------------------------------------

def _fetch_greenhouse(url: str) -> str | None:
    match = GREENHOUSE_RE.search(url)
    if not match:
        return None
    token, job_id = match.groups()
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}?questions=false"
    logger.info(f"[Greenhouse] fetching {api_url}")
    try:
        res = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        data = res.json()
        # 'content' is the full HTML blob; fall back to 'description'
        html = data.get("content") or data.get("description", "")
        return _html_to_text(html) or None
    except Exception as e:
        logger.error(f"[Greenhouse] error: {e}")
        return None


def _fetch_ashby(url: str) -> str | None:
    match = ASHBY_RE.search(url)
    if not match:
        return None
    board_name, target_id = match.groups()
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    logger.info(f"[Ashby] fetching board {api_url}")
    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        jobs = res.json().get("jobs", [])
        for job in jobs:
            if target_id in job.get("jobUrl", ""):
                html = job.get("descriptionHtml") or ""
                plain = job.get("descriptionPlain") or ""
                return _html_to_text(html) or plain or None
        logger.warning(f"[Ashby] job {target_id} not found in board listing")
        return None
    except Exception as e:
        logger.error(f"[Ashby] error: {e}")
        return None


def _fetch_workday(url: str) -> str | None:
    match = WORKDAY_RE.search(url)
    if not match:
        return None
    subdomain_full, locale_or_board, board_type, job_slug = match.groups()
    # subdomain_full is e.g. "advantech.wd3" → tenant is "advantech"
    tenant = subdomain_full.split(".")[0]

    # Workday CXS endpoint expects just the JR ID, not the full readable slug
    # e.g. "Solution-PM---Smart-Healthcare_JR202603039" → "JR202603039"
    job_id_match = re.search(r'(JR\d+)', job_slug)
    job_id = job_id_match.group(1) if job_id_match else job_slug

    api_url = (
        f"https://{subdomain_full}.myworkdayjobs.com"
        f"/wday/cxs/{tenant}/{board_type}/job/{job_id}"
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    logger.info(f"[Workday] POST {api_url}")
    try:
        res = requests.post(api_url, json={}, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        info = data.get("jobPostingInfo", {})
        html = info.get("jobDescription", "")
        return _html_to_text(html) or None
    except Exception as e:
        logger.error(f"[Workday] error: {e}")
        return None


def _fetch_lever(url: str) -> str | None:
    """
    Lever has a clean public JSON API.
    e.g. https://api.lever.co/v0/postings/company/uuid
    """
    match = LEVER_RE.search(url)
    if not match:
        return None
    company, job_id = match.groups()
    api_url = f"https://api.lever.co/v0/postings/{company}/{job_id}"
    logger.info(f"[Lever] fetching {api_url}")
    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        data = res.json()
        # Lever returns lists of {header, body} content blocks
        sections = data.get("lists", [])
        text_parts = [data.get("descriptionPlain", "")]
        for section in sections:
            header = section.get("text", "")
            body_html = section.get("content", "")
            text_parts.append(f"\n{header}\n{_html_to_text(body_html)}")
        additional = data.get("additional", "")
        if additional:
            text_parts.append(_html_to_text(additional))
        return "\n".join(filter(None, text_parts)) or None
    except Exception as e:
        logger.error(f"[Lever] error: {e}")
        return None


def _fetch_smartrecruiters(url: str) -> str | None:
    """
    SmartRecruiters public API:
    https://api.smartrecruiters.com/v1/companies/{company}/postings/{job_id}
    """
    match = SMARTRECRUITERS_RE.search(url)
    if not match:
        return None
    company, job_id_slug = match.groups()
    # Slug is "744000113104547-people-culture-generalist" — API needs only the numeric prefix
    job_id_match = re.match(r'(\d+)', job_id_slug)
    job_id = job_id_match.group(1) if job_id_match else job_id_slug
    api_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{job_id}"
    logger.info(f"[SmartRecruiters] fetching {api_url}")
    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        data = res.json()
        sections = data.get("jobAd", {}).get("sections", {})
        parts = []
        for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
            html = sections.get(key, {}).get("text", "")
            if html:
                parts.append(_html_to_text(html))
        return "\n\n".join(parts) or None
    except Exception as e:
        logger.error(f"[SmartRecruiters] error: {e}")
        return None


# Trim everything AFTER these markers (boilerplate / footer)
_JINA_TAIL_CUTOFFS = [
    "### 類似職缺",        # Workday TW: similar jobs
    "### Similar Jobs",    # Workday EN: similar jobs
    "### About ",          # company boilerplate
    "## 聯絡方式",          # 104.com.tw: contact section
    "這些工作也很適合你",    # 104.com.tw: recommended jobs footer
]

# Trim everything BEFORE these markers (navbar / banner noise)
_JINA_HEAD_CUTOFFS = [
    "## 工作內容",   # 104.com.tw: job content starts here
    "## ",           # generic: first h2 is usually the job title
]


def _fetch_via_jina(url: str) -> str | None:
    """Fallback: Jina Reader fetches the page and returns clean markdown.
    Trims navbar/banner noise from the top and boilerplate from the bottom.
    """
    jina_url = f"https://r.jina.ai/{url}"
    logger.info(f"[Jina] fallback fetch {jina_url}")
    try:
        res = requests.get(jina_url, timeout=20)
        res.raise_for_status()
        text = res.text

        # 1. Trim boilerplate from the bottom
        for cutoff in _JINA_TAIL_CUTOFFS:
            if cutoff in text:
                text = text[:text.index(cutoff)].strip()
                logger.debug(f"[Jina] tail trimmed at '{cutoff}'")
                break

        # 2. Trim navbar/banner noise from the top
        for marker in _JINA_HEAD_CUTOFFS:
            if marker in text:
                text = text[text.index(marker):].strip()
                logger.debug(f"[Jina] head trimmed at '{marker}'")
                break

        # 3. Sanity check: if page says "Loading" and is short, JS didn't render
        if "Loading" in text and len(text) < 1500:
            logger.warning("[Jina] page appears unrendered (Loading state) — returning None")
            return None

        return text or None
    except Exception as e:
        logger.error(f"[Jina] error: {e}")
        return None


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

# Each entry: (detector_fn, fetcher_fn)
# Ordered from most-specific to least-specific
_FETCHERS = [
    (_fetch_greenhouse, GREENHOUSE_RE),
    (_fetch_ashby, ASHBY_RE),
    (_fetch_lever, LEVER_RE),
    (_fetch_smartrecruiters, SMARTRECRUITERS_RE),
    (_fetch_workday, WORKDAY_RE),
]


def fetch_job_content(url: str) -> str | None:
    """
    Detect the job board from `url` and return cleaned plain-text job content
    suitable for LLM consumption.

    Strategy per URL:
      1. Platform-specific API  (structured JSON, cleanest output)
      2. Jina Reader            (if API fails/empty — handles HTML stripping itself)
      3. None                   (both failed, caller should handle)
    """
    for fetcher, pattern in _FETCHERS:
        if pattern.search(url):
            result = fetcher(url)
            if result:
                logger.success(f"[OK] {fetcher.__name__} returned {len(result)} chars")
                return result
            # API matched but came back empty — try Jina before giving up
            logger.warning(f"{fetcher.__name__} matched but returned no content — trying Jina")
            jina_result = _fetch_via_jina(url)
            if jina_result:
                logger.success(f"[OK] Jina fallback returned {len(jina_result)} chars")
            else:
                logger.error(f"Both {fetcher.__name__} and Jina failed for {url}")
            return jina_result

    # No platform regex matched — send straight to Jina
    logger.info(f"No platform matched for {url} — using Jina")
    return _fetch_via_jina(url)

if __name__ == "__main__":
    test_url = "https://jobs.smartrecruiters.com/InterIKEAGroup/744000113104547-people-culture-generalist"
    result = fetch_job_content(test_url)
    print(result)

# Test Results/ pass: 104, Ashby, greenhouse, workday, 
#https://jobs.lever.co/magnetforensics/209745fb-3524-413a-9881-b491298f13c7
#https://job-boards.greenhouse.io/greenhouse/jobs/7483085?gh_jid=7483085
#https://jobs.ashbyhq.com/wemolo/a707846e-da49-4a1e-a3cf-88dc08dd334e
#https://advantech.wd3.myworkdayjobs.com/zh-TW/External/job/Solution-Product-Manager---Smart-Healthcare--iWard---iService---_JR202603039?q=Product%20Manager
#https://www.104.com.tw/job/8wywf
#https://jobs.smartrecruiters.com/InterIKEAGroup/744000113104547-people-culture-generalist