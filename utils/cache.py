"""In-memory + file-based caching for analysis results."""
import json
import os
import hashlib
from typing import Optional

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory cache for current session (avoids disk I/O on repeated runs)
_memory_cache: dict = {}


def get_file_hash(file_path: str) -> Optional[str]:
    """Get SHA256 hash of file content."""
    try:
        stat = os.stat(file_path)
        # Use mtime + size as fast hash key (avoids reading file content)
        return f"{stat.st_mtime}:{stat.st_size}"
    except:
        return None


def get_cache_key(repo_url: str, branch: str, file_path: str, file_hash: str) -> str:
    """Generate cache key for a file analysis."""
    key_str = f"{repo_url}:{branch}:{file_path}:{file_hash}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[dict]:
    """Retrieve cached analysis result (memory first, then disk)."""
    # Check memory cache first (fastest)
    if cache_key in _memory_cache:
        return _memory_cache[cache_key]
    
    # Check disk cache
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                result = json.load(f)
            # Promote to memory cache
            _memory_cache[cache_key] = result
            return result
        except:
            pass
    return None


def save_cached_result(cache_key: str, result: dict):
    """Save analysis result to memory cache only (batch flush to disk later)."""
    _memory_cache[cache_key] = result


def flush_cache_to_disk():
    """Flush all in-memory cache entries to disk in one batch."""
    for cache_key, result in _memory_cache.items():
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if not os.path.exists(cache_file):
            try:
                with open(cache_file, 'w') as f:
                    json.dump(result, f)
            except:
                pass


def clear_cache():
    """Clear all cached results."""
    import shutil
    _memory_cache.clear()
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR)
