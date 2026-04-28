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
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
}

SPECIAL_FILES = {
    "Dockerfile": "docker",
    "dockerfile": "docker",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
}


def detect_language(file_path, ext_hint: str = ""):
    """Detect programming language from file path and content."""
    filename = os.path.basename(file_path)

    # Layer 1: special filenames
    if filename in SPECIAL_FILES:
        return SPECIAL_FILES[filename]

    # Layer 2: use pre-computed ext hint if provided, else extract from path
    ext = (ext_hint or os.path.splitext(file_path)[1]).lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    # Layer 3: content-based fallback
    return detect_by_content(file_path)


def detect_by_content(file_path):
    """Fallback language detection by analyzing file content."""
    try:
        # Only read first 512 bytes for speed
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(512)

        # Quick substring checks (faster than regex)
        if "package main" in content or "func main()" in content:
            return "go"
        if content.startswith("#!/bin/bash") or content.startswith("#!/bin/sh") or content.startswith("#!/usr/bin/env bash"):
            return "bash"
        if "def " in content or "import " in content:
            return "python"
        if "public class" in content or "private class" in content:
            return "java"
        if "console.log" in content or "function(" in content:
            return "javascript"
        if "#include" in content:
            return "cpp"

    except:
        pass

    return "unknown"
