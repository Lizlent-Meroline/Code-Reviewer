# Code-Reviewer

A FastAPI-based code analysis and review tool that integrates with GitHub to detect issues in code repositories using AI-powered analysis.

## Features

- Multi-language code analysis (Python, Go, JavaScript, etc.)
- GitHub integration for repository cloning and PR analysis
- AI-powered issue detection using OpenAI
- RESTful API with WebSocket support
- Caching for performance
- PDF/JSON export of analysis results

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Lizlent-Meroline/Code-Reviewer.git
   cd Code-Reviewer
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the development server:
```bash
./run.sh
```

The API will be available at `http://localhost:8000`.

## API Documentation

See [ENDPOINTS.md](ENDPOINTS.md) for detailed API endpoint documentation.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for AI analysis
- `GITHUB_TOKEN`: GitHub personal access token for repository access