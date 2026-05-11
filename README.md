## Repo Analyzer

A fast, self-contained code analysis tool that scans GitHub repositories and provides instant feedback on code quality, structure, and potential issues.

## Features

- **Fast Analysis** — Analyze 1000 files in ~30 seconds, 5000 files in ~2 minutes
- **Multi-Language Support** — Python, Go, JavaScript, TypeScript, Java, C++, Rust, and more
- **Shallow Cloning** — 10-50x faster repo cloning using git shallow clones
- **Optional Authentication** — Sign up to save analysis history (email + password)
- **Branch Switching** — Quickly switch between branches without re-cloning
- **Dark/Light Mode** — Toggle between themes
- **Real-time Progress** — See analysis progress as files are scanned

## Tech Stack

**Backend:**
- FastAPI (REST API)
- SQLite (user auth + history)
- GitPython (repo cloning)
- bcrypt + JWT (authentication)

**Frontend:**
- Vanilla JavaScript
- Tailwind CSS (via CDN)
- No build step required

**Analysis:**
- Python: AST-based analysis (docstrings, function length)
- Go: Pattern matching (error handling, panic usage, function length)
- Generic: File size checks, TODO detection

## Quick Start

### Prerequisites

- Python 3.10+
- Git

### Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd Reviewer

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn api:app --reload
```

The app will be available at `http://localhost:8000`

### Optional: Set JWT Secret

For persistent sessions across server restarts:

```bash
export JWT_SECRET="your-secret-key-here"
uvicorn api:app --reload
```

## Project Structure

```
Reviewer/
│
├── api.py                  # FastAPI server (REST endpoints)
├── main.py                 # Core analysis engine
├── auth.py                 # User authentication (SQLite + JWT)
│
├── analyzer/               # Language-specific analyzers
│   ├── __init__.py
│   ├── detector.py         # Language detection
│   ├── github.py           # Git operations (clone, fetch, checkout)
│   ├── python_analyzer.py  # Python AST analysis
│   ├── go_analyzer.py      # Go pattern analysis
│   └── generic.py          # Fallback analyzer
│
├── utils/
│   └── parser.py           # File classification and scanning
│
├── src/
│   └── index.html          # Single-page frontend
│
├── history/                # User analysis history (auto-created)
├── repos/                  # Cloned repositories (auto-created)
└── users.db                # SQLite user database (auto-created)
```

## API Endpoints

### Analysis
- `POST /analyze` — Analyze a GitHub repository
- `POST /switch-branch` — Switch branch and re-analyze
- `POST /branches` — Get list of branches

### Authentication
- `POST /register` — Create new account
- `POST /login` — Sign in and get JWT token

### History
- `GET /history` — Get user's analysis history (requires auth)
- `DELETE /history` — Clear user's history (requires auth)

### Health
- `GET /health` — Health check
- `GET /` — Serve frontend

## Performance

**File Analysis:**
- 1,000 files: ~20-40 seconds
- 5,000 files: ~1.5-2 minutes
- 10,000 files: ~3-4 minutes

**Clone Speed (shallow):**
- Small repo (10MB): 1-2 seconds
- Medium repo (100MB): 3-5 seconds
- Large repo (500MB+): 5-15 seconds

**File Size Limits:**
- Files up to 4MB analyzed
- Files > 500KB use sampling (first/last 50KB)
- Files > 4MB skipped

## Configuration

### Thread Pool
Adjust worker count in `main.py`:
```python
MAX_WORKERS = min(32, (os.cpu_count() or 4) * 4)
```

### File Limits
Adjust in `utils/parser.py`:
```python
MAX_FILES = 10000  # Maximum files to scan
```

### Analysis Limits
Adjust in analyzer files:
```python
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
SAMPLE_SIZE = 50 * 1024  # 50KB sampling
```

## Development

### Run in development mode
```bash
uvicorn api:app --reload --log-level debug
```

### Clear cached repos
```bash
rm -rf repos/
```

### Clear user data
```bash
rm users.db
rm -rf history/
```

## Security Notes

- Passwords hashed with bcrypt
- JWT tokens expire after 30 days
- History stored per-user in separate JSON files
- No external auth services required

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- All functions have docstrings
- Code follows existing style
- Tests pass (if applicable)
