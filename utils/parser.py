import os

CODE_EXTENSIONS = {
    ".py", ".ipynb", ".go", ".js", ".ts", ".java", ".cpp", ".c",
    ".rs", ".php", ".rb", ".zig", ".html", ".css", ".sh", ".swift",
    ".kt", ".scala", ".cs", ".r", ".m", ".lua", ".ex", ".exs",
}

DOCS_EXTENSIONS = {
    ".md", ".txt", ".rst", ".pdf", ".docx", ".csv", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".xml",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor", "target",
    "site-packages", "lib64", "bin", "include",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "eggs", ".eggs", "htmlcov", ".coverage", ".cache",
    "coverage", "tmp", "temp", ".idea", ".vscode",
}

# Skip files that are never useful to analyze
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp4", ".mp3", ".wav", ".ogg", ".woff", ".woff2", ".ttf",
    ".eot", ".otf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".lock", ".sum", ".mod",  # lock files — no analysis value
    ".min.js", ".min.css",    # minified files
}

MAX_FILES = 50000


def classify_file(file_path: str) -> str:
    """Returns 'code', 'docs', or 'other'."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in DOCS_EXTENSIONS:
        return "docs"
    return "other"


def get_all_files(repo_path: str) -> list[dict]:
    """Walk the repo and return all files with their classification."""
    results = []

    if not os.path.exists(repo_path):
        print(f"[parser] ERROR: path does not exist: {repo_path}")
        return results

    print(f"[parser] Scanning: {repo_path}")

    for root, dirs, files in os.walk(repo_path, topdown=True):
        # Prune skip dirs in-place (prevents os.walk from descending)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

        for filename in files:
            _, ext = os.path.splitext(filename)
            ext_lower = ext.lower()

            # Skip binary/useless extensions immediately
            if ext_lower in SKIP_EXTENSIONS:
                continue

            # Skip minified files by name pattern
            if filename.endswith('.min.js') or filename.endswith('.min.css'):
                continue

            full_path = os.path.join(root, filename)
            results.append({
                "path": full_path,
                "name": filename,
                "ext": ext_lower,
                "type": classify_file(filename),
            })

            if len(results) >= MAX_FILES:
                print(f"[parser] Hit cap of {MAX_FILES} files")
                return results

    print(f"[parser] Found {len(results)} files")
    return results
