import re
import os

MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
SAMPLE_SIZE = 50 * 1024  # Sample first/last 50KB

# Precompile regexes for performance
FUNC_PATTERN = re.compile(r'^\s*func\s+(\w+)')
PANIC_PATTERN = re.compile(r'\bpanic\(')


class GoAnalyzer:
    def analyze(self, file_path):
        """Analyze Go source file for common issues."""
        issues = []
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Skip files larger than 4MB
            if file_size > MAX_FILE_SIZE:
                return ["File exceeds 4MB limit"]
            
            # For files > 500KB, use sampling
            if file_size > 500 * 1024:
                return self._analyze_large_file(file_path, file_size)
            
            # Normal analysis
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            if not content.strip():
                return ["Empty file"]
            
            lines = content.splitlines()
            
            # Check for long functions
            self._check_long_functions(lines, issues)
            
            # Quick string checks
            if "err :=" in content and "err != nil" not in content:
                issues.append("Possible unhandled errors")
            
            if "TODO" in content or "FIXME" in content:
                issues.append("Contains TODO/FIXME comments")
            
            if PANIC_PATTERN.search(content):
                issues.append("Uses panic()")
        
        except Exception:
            pass
        
        return issues
    
    def _analyze_large_file(self, file_path, file_size):
        """Fast sampling-based analysis for large files."""
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read first 50KB
                head = f.read(SAMPLE_SIZE)
                
                # Seek to end and read last 50KB
                f.seek(max(0, file_size - SAMPLE_SIZE))
                tail = f.read(SAMPLE_SIZE)
            
            sample = head + "\n" + tail
            
            # Quick pattern checks
            func_count = sample.count("func ")
            if func_count > 30:
                issues.append(f"Large file with {func_count}+ functions")
            
            if "err :=" in sample and "err != nil" not in sample:
                issues.append("Possible unhandled errors")
            
            if "TODO" in sample or "FIXME" in sample:
                issues.append("Contains TODO/FIXME")
            
            if "panic(" in sample:
                issues.append("Uses panic()")
        
        except Exception:
            pass
        
        return issues or ["Large file analyzed (sampled)"]
    
    def _check_long_functions(self, lines, issues):
        """Check for functions longer than 50 lines."""
        in_func = False
        func_name = ""
        func_start = 0
        brace_depth = 0
        
        for i, line in enumerate(lines):
            match = FUNC_PATTERN.match(line)
            if match:
                in_func = True
                func_name = match.group(1)
                func_start = i
                brace_depth = line.count('{') - line.count('}')
            elif in_func:
                brace_depth += line.count('{') - line.count('}')
                if brace_depth <= 0:
                    length = i - func_start
                    if length > 50:
                        issues.append(f"{func_name}() too long ({length} lines)")
                    in_func = False
