import os
from analyzer.base import BaseAnalyzer

def too_big(file_path, limit_kb=500):
    try:
        return os.path.getsize(file_path) / 1024 > limit_kb
    except:
        return False


class GenericAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        issues = []

        if too_big(file_path):
            issues.append("File is too large, consider splitting it")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "TODO" in content:
            issues.append("Contains TODO comments")

        if len(content.strip()) == 0:
            issues.append("Empty file")

        return issues