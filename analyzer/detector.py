import os

EXTENSION_MAP = {
    ".py": "python",
    ".ipynb": "python",
    ".go": "go",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".swift": "swift",
}

SPECIAL_FILES = {
    "Dockerfile": "docker",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
}

def detect_language(file_path):
    filename = os.path.basename(file_path)

    # Layer 1: special filenames
    if filename in SPECIAL_FILES:
        return SPECIAL_FILES[filename]

    # Layer 2: extension
    _, ext = os.path.splitext(file_path)
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    # Layer 3: content-based fallback
    return detect_by_content(file_path)


def detect_by_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(800)

        if "package main" in content:
            return "go"
        if "def " in content:
            return "python"
        if "public class" in content:
            return "java"
        if "console.log" in content:
            return "javascript"
        if "#include" in content:
            return "cpp"

    except:
        pass

    return "unknown"