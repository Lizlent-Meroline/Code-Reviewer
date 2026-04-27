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
    "eggs", ".eggs", "htmlcov", ".coverage",
}

MAX_FILES = 10000  


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
    """
    Walk the repo and return all files with their classification.
    Each entry: { path, name, ext, type: 'code'|'docs'|'other' }
    """
    results = []

    if not os.path.exists(repo_path):
        print(f"[parser] ERROR: path does not exist: {repo_path}")
        return results

    print(f"[parser] Scanning: {repo_path}")

    for root, dirs, files in os.walk(repo_path):
        # Prune dirs in-place so os.walk won't descend into them
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        # Belt-and-suspenders: skip this root if any path segment is a skip dir
        rel_root = os.path.relpath(root, repo_path)
        if rel_root != "." and any(part in SKIP_DIRS for part in rel_root.split(os.sep)):
            dirs.clear()  # also stop descending further
            continue

        for filename in files:
            full_path = os.path.join(root, filename)
            _, ext = os.path.splitext(filename)
            results.append({
                "path": full_path,
                "name": filename,
                "ext": ext.lower(),
                "type": classify_file(filename),
            })

            if len(results) >= MAX_FILES:
                print(f"[parser] Hit cap of {MAX_FILES} files")
                return results

    print(f"[parser] Found {len(results)} files")
    return results
