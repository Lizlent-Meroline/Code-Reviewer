import os

MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
SAMPLE_SIZE = 20 * 1024  # Sample first 20KB for quick checks


class GenericAnalyzer:
    def analyze(self, file_path):
        """Analyze any file for generic issues."""
        issues = []
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Skip files larger than 4MB
            if file_size > MAX_FILE_SIZE:
                return ["File exceeds 4MB limit"]
            
            # For large files, only sample
            read_size = min(file_size, SAMPLE_SIZE)
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(read_size)
            
            if not content.strip():
                issues.append("Empty file")
            elif "TODO" in content:
                issues.append("Contains TODO comments")
            
            # Note if we only sampled
            if file_size > SAMPLE_SIZE:
                issues.append(f"Large file ({file_size // 1024}KB, sampled)")
        
        except Exception:
            pass
        
        return issues
