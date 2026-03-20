## Job Hunting AI Assistant
### Purpose
An automation tool built with FastAPI and LLM logic designed to streamline the job search process. This assistant eliminates tedious manual work by automatically extracting, analyzing, and prioritizing job opportunities.

### Core Features
- Extract job descriptions directly from a URL or via manual copy-paste fallback
- Deep comparison between job requirements and your `cv.md` using LLM
- Generate matching points, potential gaps, and improvement suggestions
- Syncs all analysis, job details, and application status directly to your designated spreadsheet
- Automated follow-up reminders for items based on specific status

### Project Structure
```
.
├── .env                          # GOOGLE_SHEET_ID, GOOGLE_APPLICATION_CREDENTIALS,
│                                 # GOOGLE_API_KEY, JINA_API_KEY
├── .env.example                  # template (commit this, not .env)
├── .gitignore                    # .env, data/credentials.json, __pycache__, .venv
├── pyproject.toml                # uv deps + pytest config
├── uv.lock
├── .python-version
│
├── app.py                        # Streamlit UI
├── main.py                       # FastAPI routes (future)
│
├── services/
│   ├── read.py                   # fetch_job_content + NOT_A_JOB sentinel
│   ├── aianalyzer.py             # Gemini analysis against CV
│   └── updatesheet.py            # gspread writer
│
├── data/
│   ├── cv.md                     # your CV (never commit)
│   └── credentials.json          # GCP service account (never commit)
│
└── tests/
    ├── test_read.py              # unit tests (mocked, fast)
    └── test_read_integration.py  # integration tests (real network, run manually)
```
