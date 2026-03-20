"""
test_read_integration.py — real network integration tests
----------------------------------------------------------
These tests make actual HTTP calls — no mocks.
Run with:  uv run pytest tests/test_read_integration.py -v -s

-s flag shows print output (useful for seeing fetched content length).
These are intentionally separate from unit tests in test_read.py
so CI can skip them with:  uv run pytest tests/test_read.py (unit only)
"""

import pytest
from services.read import fetch_job_content, NOT_A_JOB


# ---------------------------------------------------------------------------
# Test cases: (url, expected_platform, should_be_job)
# ---------------------------------------------------------------------------

CASES = [
    (
        "https://jobs.lever.co/magnetforensics/209745fb-3524-413a-9881-b491298f13c7",
        "Lever",
        True,
    ),
    (
        "https://job-boards.greenhouse.io/greenhouse/jobs/7483085?gh_jid=7483085",
        "Greenhouse",
        True,
    ),
    (
        "https://jobs.ashbyhq.com/wemolo/a707846e-da49-4a1e-a3cf-88dc08dd334e",
        "Ashby",
        True,
    ),
    (
        "https://advantech.wd3.myworkdayjobs.com/zh-TW/External/job/Solution-Product-Manager---Smart-Healthcare--iWard---iService---_JR202603039",
        "Workday",
        True,
    ),
    (
        "https://www.104.com.tw/job/8wywf",
        "Jina (104)",
        True,
    ),
    (
        "https://jobs.smartrecruiters.com/InterIKEAGroup/744000113104547-people-culture-generalist",
        "SmartRecruiters",
        True,
    ),
    (
        "https://www.google.com",
        "Jina (non-job)",
        False,  # should return NOT_A_JOB
    ),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,platform,should_be_job", CASES)
def test_fetch(url, platform, should_be_job):
    print(f"\n[{platform}] {url}")
    result = fetch_job_content(url)

    if should_be_job:
        assert result is not None, \
            f"[{platform}] Expected job content but got None"
        assert result != NOT_A_JOB, \
            f"[{platform}] Expected job content but got NOT_A_JOB"
        assert len(result) > 200, \
            f"[{platform}] Content too short ({len(result)} chars) — likely a failed fetch"
        print(f"  ✓ {len(result)} chars returned")
        print(f"  Preview: {result[:120].strip()}...")
    else:
        assert result == NOT_A_JOB, \
            f"[{platform}] Expected NOT_A_JOB for non-job URL but got: {str(result)[:100]}"
        print(f"  ✓ Correctly identified as non-job page")