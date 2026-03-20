"""
updatesheet.py — Google Sheets integration for job-hunt-ai
-----------------------------------------------------------
Uses gspread (already in your stack) instead of google-api-python-client.

Setup:
  1. Enable Google Sheets API in Google Cloud Console
  2. Create a Service Account and download credentials JSON
  3. Share your target spreadsheet with the service account email
  4. Set in .env:
       GOOGLE_SHEET_ID=your_spreadsheet_id
       GOOGLE_APPLICATION_CREDENTIALS=data/credentials.json
"""

import os
from datetime import datetime, timezone

import gspread
from google.oauth2 import service_account
from loguru import logger

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> gspread.Client:
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "data/credentials.json")
    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet(sheet_name: str = "Sheet1") -> gspread.Worksheet:
    client = _get_client()
    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_SHEET_ID not set in .env")
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(sheet_name)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

COLUMNS = [
    "URL",                  # A — unique key
    "Company",              # B
    "Title",                # C
    "Location",             # D
    "Job Type",             # E
    "Status",               # F
    "Verdict",              # G
    "Match Score",          # H
    "Alignment",            # I
    "Relocation",           # J
    "Effort",               # K
    "Description Summary",  # L
    "Key Requirements",     # M
    "Matching Points",      # N
    "Gaps",                 # O
    "Risk Flags",           # P
    "Skills to Highlight",  # Q
    "Quick CV Edits",       # R
    "Strategic Value",      # S
    "Holistic Explanation", # T
    "Notes",                # U
    "Date Added",           # V
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_header(sheet: gspread.Worksheet):
    """Write header row if sheet is empty."""
    first_row = sheet.row_values(1)
    if not first_row:
        sheet.append_row(COLUMNS)
        logger.info("Header written to sheet")


def _find_row_by_url(sheet: gspread.Worksheet, url: str) -> int | None:
    """Return 1-based row number matching url in column A, or None."""
    col_a = sheet.col_values(1)
    for i, cell in enumerate(col_a):
        if cell == url:
            return i + 1
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _join(items: list) -> str:
    """Convert a list to a newline-separated string for sheet storage."""
    if not items:
        return ""
    return "\n".join(f"• {i}" for i in items)


def upsert_job(
    spreadsheet_id: str,  # kept for API compatibility
    url: str,
    raw_content: str = "",
    *,
    company: str = "",
    title: str = "",
    location: str = "",
    job_type: str = "",
    status: str = "Interested",
    verdict: str = "",
    match_score: int | str = "",
    alignment: int | str = "",
    relocation: str = "",
    effort: str = "",
    description_summary: str = "",
    key_requirements: list = None,
    matching_points: list = None,
    gaps: list = None,
    risk_flags: list = None,
    skills_to_highlight: list = None,
    quick_cv_edits: list = None,
    strategic_value: str = "",
    holistic_explanation: str = "",
    notes: str = "",
    sheet_name: str = "Sheet1",
):
    """
    Insert a new job row or update an existing one matched by URL.
    Preserves manually-set Status and Notes on update.
    """
    sheet = _get_sheet(sheet_name)
    _ensure_header(sheet)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    row_data = {
        "URL":                  url,
        "Company":              company,
        "Title":                title,
        "Location":             location,
        "Job Type":             job_type,
        "Status":               status,
        "Verdict":              verdict,
        "Match Score":          match_score,
        "Alignment":            alignment,
        "Relocation":           relocation,
        "Effort":               effort,
        "Description Summary":  description_summary,
        "Key Requirements":     _join(key_requirements or []),
        "Matching Points":      _join(matching_points or []),
        "Gaps":                 _join(gaps or []),
        "Risk Flags":           _join(risk_flags or []),
        "Skills to Highlight":  _join(skills_to_highlight or []),
        "Quick CV Edits":       _join(quick_cv_edits or []),
        "Strategic Value":      strategic_value,
        "Holistic Explanation": holistic_explanation,
        "Notes":                notes,
        "Date Added":           now,
    }
    row_values = [row_data.get(col, "") for col in COLUMNS]

    existing_row = _find_row_by_url(sheet, url)

    if existing_row:
        current = sheet.row_values(existing_row)
        current += [""] * (len(COLUMNS) - len(current))
        col_map = {col: i for i, col in enumerate(COLUMNS)}

        # Overwrite all AI-derived fields
        overwrite_fields = (
            "Company", "Title", "Location", "Job Type", "Verdict",
            "Match Score", "Alignment", "Relocation", "Effort",
            "Description Summary", "Key Requirements", "Matching Points",
            "Gaps", "Risk Flags", "Skills to Highlight", "Quick CV Edits",
            "Strategic Value", "Holistic Explanation",
        )
        for field in overwrite_fields:
            current[col_map[field]] = str(row_data[field])

        # Preserve manually-set fields if already filled
        for field in ("Status", "Notes"):
            if not current[col_map[field]]:
                current[col_map[field]] = row_data[field]

        sheet.update(f"A{existing_row}", [current])
        logger.success(f"Updated row {existing_row} for {url}")
    else:
        sheet.append_row(row_values)
        logger.success(f"Appended new row for {url}")


def update_llm_summary(
    spreadsheet_id: str,  # kept for API compatibility
    url: str,
    summary: str,
    sheet_name: str = "Sheet1",
):
    """Write the LLM summary to the LLM Summary column for a given URL."""
    sheet = _get_sheet(sheet_name)
    row = _find_row_by_url(sheet, url)
    if not row:
        logger.warning(f"URL not found in sheet, cannot update summary: {url}")
        return
    col_index = COLUMNS.index("LLM Summary") + 1  # gspread is 1-based
    sheet.update_cell(row, col_index, summary)
    logger.success(f"LLM summary written to row {row}")