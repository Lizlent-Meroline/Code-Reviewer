import ast
import os

MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
SAMPLE_SIZE = 50 * 1024  # Sample first/last 50KB for huge files


class PythonAnalyzer:
    def analyze(self, file_path):
        """Analyze Python source file for common issues."""
        issues = []
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Skip files larger than 4MB
            if file_size > MAX_FILE_SIZE:
                return ["File exceeds 4MB limit"]
            
            # For files > 500KB, use sampling strategy
            if file_size > 500 * 1024:
                return self._analyze_large_file(file_path, file_size)
            
            # Normal analysis for smaller files
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                return ["Empty file"]
            
            # Parse AST
            tree = ast.parse(content)
            
            # Only check top-level and class-level functions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    self._check_function(node, issues)
                elif isinstance(node, ast.ClassDef):
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, ast.FunctionDef):
                            self._check_function(child, issues)
        
        except SyntaxError:
            issues.append("Syntax error in file")
        except Exception:
            pass  # Silently skip unparseable files
        
        return issues
    
    def _analyze_large_file(self, file_path, file_size):
        """Fast sampling-based analysis for large files."""
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Read first 50KB
                head = f.read(SAMPLE_SIZE)
                
                # Seek to end and read last 50KB
                f.seek(max(0, file_size - SAMPLE_SIZE))
                tail = f.read(SAMPLE_SIZE)
            
            sample = head + "\n" + tail
            
            # Quick pattern checks (no AST parsing for speed)
            if "def " in sample:
                # Count function definitions
                func_count = sample.count("\ndef ")
                if func_count > 50:
                    issues.append(f"Large file with {func_count}+ functions")
            
            if "TODO" in sample or "FIXME" in sample:
                issues.append("Contains TODO/FIXME comments")
            
            if not sample.strip():
                issues.append("Empty or whitespace-only file")
        
        except Exception:
            pass
        
        return issues or ["Large file analyzed (sampled)"]
    
    def _check_function(self, node, issues):
        """Check a single function node."""
        if len(node.body) > 50:
            issues.append(f"Line {node.lineno}: {node.name}() is too long ({len(node.body)} lines)")

        if not ast.get_docstring(node):
            issues.append(f"Line {node.lineno}: {node.name}() missing docstring")

        # Check for bare except
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler) and child.type is None:
                issues.append(f"Line {getattr(child, 'lineno', '?')}: bare except clause in {node.name}()")
                break

        # Check for mutable default arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(f"Line {node.lineno}: {node.name}() uses mutable default argument")
