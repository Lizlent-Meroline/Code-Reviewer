import ast

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def visit_FunctionDef(self, node):
        # Rule: function too long
        if len(node.body) > 50:
            self.issues.append(f"Function '{node.name}' is too long")

        # Rule: missing docstring
        if not ast.get_docstring(node):
            self.issues.append(f"Function '{node.name}' has no docstring")

        self.generic_visit(node)

def analyze_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)

    return analyzer.issues