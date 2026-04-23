import ast
from analyzer.base import BaseAnalyzer

class PythonAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        issues = []

        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 50:
                    issues.append(f"{node.name} too long")

                if not ast.get_docstring(node):
                    issues.append(f"{node.name} missing docstring")

        return issues