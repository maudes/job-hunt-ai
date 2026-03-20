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
├── .env                          # API keys and config (never commit)
├── .env.example                  # Template — copy to .env and fill in
├── .gitignore
├── pyproject.toml                # Dependencies + pytest config
├── uv.lock
├── .python-version
│
├── app.py                        # Streamlit UI — main entry point
├── main.py                       # FastAPI routes (future API use)
│
├── services/
│   ├── read.py                   # Fetches job content from any URL
│   │                             # Supports: Greenhouse, Ashby, Lever,
│   │                             # SmartRecruiters, Workday, 104.com.tw
│   │                             # Falls back to Jina Reader for others
│   ├── aianalyzer.py             # Gemini-powered CV vs JD analysis
│   └── updatesheet.py            # Writes results to Google Sheets via gspread
│
├── prompts/
│   └── analyzer_prompt.md        # System prompt for Gemini — edit to tune AI behaviour
│                                 # Version header at top tracks iteration history
│
├── data/
│   ├── cv.md                     # Your CV in markdown (never commit)
│   └── credentials.json          # GCP service account key (never commit)
│
└── tests/
    ├── test_read.py              # Unit tests — mocked, fast, run always
    └── test_read_integration.py  # Integration tests — real network, run manually
```
