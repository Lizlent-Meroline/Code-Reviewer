import re
from analyzer.base import BaseAnalyzer


class GoAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()

            # long functions
            in_func = False
            func_name = ""
            func_start = 0
            brace_depth = 0

            for i, line in enumerate(lines):
                if re.match(r'^\s*func\s+', line):
                    in_func = True
                    func_name = re.search(r'func\s+(\w+)', line)
                    func_name = func_name.group(1) if func_name else "unknown"
                    func_start = i
                    brace_depth = line.count('{') - line.count('}')
                elif in_func:
                    brace_depth += line.count('{') - line.count('}')
                    if brace_depth <= 0:
                        length = i - func_start
                        if length > 50:
                            issues.append(f"{func_name}() is too long ({length} lines)")
                        in_func = False

            # missing error checks: err != nil pattern absent after err returns
            if "err :=" in content and "err != nil" not in content:
                issues.append("Possible unhandled errors (err != nil never checked)")

            # TODO comments
            if "TODO" in content or "FIXME" in content:
                issues.append("Contains TODO/FIXME comments")

            # use of panic
            if re.search(r'\bpanic\(', content):
                issues.append("Uses panic() — consider returning errors instead")

        except Exception as e:
            issues.append(f"Error analyzing file: {e}")

        return issues
