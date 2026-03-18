## Job Hunting AI Assistant
### Purpose
A automation tool built with FastAPI and LLM logic designed to streamline the job search process. This assistant eliminates tedious manual work by automatically extracting, analyzing, and prioritizing job opportunities.

### Core Features
- Extract job descriptions directly from a URL or via manual copy-paste fallback
- Deep comparison between job requirements and your `cv.md` using LLM
- Generate matching points, potential gaps, and improvement suggestions
- Syncs all analysis, job details, and application status directly to your designated spreadsheet
- Automated follow-up reminders for items based on specific status

### Project Structure
```
.
├── .env                 # API Keys
├── pyproject.toml      
├── main.py              # FastAPI Route
├── services/
│   ├── read.py          # User input url
│   ├── aianalyzer.py    # LLM logic
│   └── updatesheet.py   # Update content into the target spreadsheet
├── data/
│   ├── cv.md            # CV content
│   └── credentials.json # Google Service Account key
└── tests/               # General tests
```