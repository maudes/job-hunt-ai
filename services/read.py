import requests
import re
from loguru import logger

def fetch_job_content(url: str):
    # --- 1. Workday ---
    workday_re = r'https://(.+)\.myworkdayjobs\.com/.+/job/.+/(JR\d+|[A-Z0-9-]+)'
    
    # --- 2. Greenhouse ---
    # 格式: https://boards.greenhouse.io/{board_token}/jobs/{job_id}
    greenhouse_re = r'https://boards\.greenhouse\.io/([^/]+)/jobs/(\d+)'
    
    # --- 3. Ashby ---
    # 格式: https://jobs.ashbyhq.com/{company}/{job_id}
    ashby_re = r'https://jobs\.ashbyhq\.com/[^/]+/([a-f0-9\-]+)'

    # Main logic
    # A. Try Greenhouse
    gh_match = re.search(greenhouse_re, url)
    if gh_match:
        token, job_id = gh_match.groups()
        api_url = f"https://api.greenhouse.io/v1/boards/{token}/embed/job?job_id={job_id}"
        return _get_json_content(api_url, ["content", "description"])

    # B. Try Ashby
    ash_match = re.search(ashby_re, url)
    if ash_match:
        job_id = ash_match.group(1)
        # Ashby 通常需要 POST 或是特定的 GET API
        api_url = f"https://api.ashbyhq.com/api/public/jobBoard/job/{job_id}"
        return _get_json_content(api_url, ["description", "jobDescription"])

    # C. Try Workday 
    wd_match = re.search(workday_re, url)
    if wd_match:
        # ... 原有的 Workday 邏輯 ...
        pass

    # D. Try Jina
    return fetch_via_jina(url)

def _get_json_content(api_url, keys):

    try:
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # 遍歷可能的 key 找出描述內容
            for key in keys:
                if key in data: return data[key]
        return None
    except:
        return None