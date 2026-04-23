import os

VALID_EXTENSIONS = (
    ".py",
    ".ipynb",
    ".go",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".rs",
    ".php",
    ".rb",
    ".zig",
    ".html",
    ".css",
    ".sh",
)

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor", "target",
}

MAX_FILES = 100


def get_code_files(repo_path):
    code_files = []

    for root, dirs, files in os.walk(repo_path):
        # prune dirs in-place so os.walk skips them entirely
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file.endswith(VALID_EXTENSIONS):
                code_files.append(os.path.join(root, file))
                if len(code_files) >= MAX_FILES:
                    return code_files

    return code_files