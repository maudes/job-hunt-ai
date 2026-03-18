
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