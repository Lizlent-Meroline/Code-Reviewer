"""File-based caching for analysis results."""
import json
import os
import hashlib
from typing import Optional

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def get_file_hash(file_path: str) -> Optional[str]:
    """Get SHA256 hash of file content."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None


def get_cache_key(repo_url: str, branch: str, file_path: str, file_hash: str) -> str:
    """Generate cache key for a file analysis."""
    key_str = f"{repo_url}:{branch}:{file_path}:{file_hash}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[dict]:
    """Retrieve cached analysis result."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None


def save_cached_result(cache_key: str, result: dict):
    """Save analysis result to cache."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except:
        pass


def clear_cache():
    """Clear all cached results."""
    import shutil
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR)
