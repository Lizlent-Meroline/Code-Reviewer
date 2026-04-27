import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.github import (
    clone_repo, get_branches, checkout_branch,
    get_local_tags, get_local_commits,
    get_pull_requests, get_issues, get_gh_tags, get_repo_meta,
)
from utils.parser import get_all_files
from utils.cache import get_file_hash, get_cache_key, get_cached_result, save_cached_result
from analyzer.detector import detect_language
from analyzer import get_analyzer

# Optimize for I/O-bound workload
MAX_WORKERS = min(32, (os.cpu_count() or 4) * 4)
MAX_FILE_SIZE_KB = 4096  # Analyze files up to 4MB


def analyze_file(file_meta: dict, repo_url: str = "", branch: str = "", use_cache: bool = True) -> dict:
    """Analyze a single file and detect issues based on language."""
    path = file_meta["path"]
    result = {
        "path": path,
        "name": file_meta["name"],
        "ext": file_meta["ext"],
        "type": file_meta["type"],
        "language": None,
        "issues": [],
    }
    
    # Skip non-code files immediately
    if file_meta["type"] != "code":
        return result
    
    # Check cache first
    if use_cache and repo_url and branch:
        file_hash = get_file_hash(path)
        if file_hash:
            cache_key = get_cache_key(repo_url, branch, path, file_hash)
            cached = get_cached_result(cache_key)
            if cached:
                return cached
    
    # Skip large files early
    try:
        if os.path.getsize(path) / 1024 > MAX_FILE_SIZE_KB:
            result["issues"] = ["File too large, skipped analysis"]
            return result
    except:
        return result
    
    try:
        lang = detect_language(path)
        result["language"] = lang
        result["issues"] = get_analyzer(lang).analyze(path)
        
        # Save to cache
        if use_cache and repo_url and branch:
            file_hash = get_file_hash(path)
            if file_hash:
                cache_key = get_cache_key(repo_url, branch, path, file_hash)
                save_cached_result(cache_key, result)
    except Exception as e:
        result["issues"] = [f"Error: {e}"]
    
    return result


def run(repo_url: str, branch: str = None, client_id: str = None, manager=None, loop=None) -> dict:
    """Clone repo, checkout branch, and generate full analysis report."""
    import asyncio
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except Exception:
            pass

    repo_path = clone_repo(repo_url)
    all_branches = get_branches(repo_path)
    branch_names = [b["name"] for b in all_branches]

    target_branch = branch if branch in branch_names else all_branches[0]["name"]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches, client_id=client_id, manager=manager, loop=loop)


def run_branch_switch(repo_url: str, branch: str) -> dict:
    """Fast path: just checkout + re-scan files, skip GitHub API calls."""
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join("repos", repo_name)

    all_branches = get_branches(repo_path)
    branch_names = [b["name"] for b in all_branches]

    target_branch = branch if branch in branch_names else all_branches[0]["name"]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches, skip_gh_api=True)


def _build_report(repo_url, repo_path, target_branch, all_branches, skip_gh_api=False, client_id=None, manager=None, loop=None) -> dict:
    """Build analysis report with file scans, commits, PRs, and issues."""
    import asyncio

    def send_progress(msg: dict):
        """Send WebSocket progress from a worker thread safely."""
        if not (client_id and manager and loop):
            return
        try:
            asyncio.run_coroutine_threadsafe(manager.send_progress(client_id, msg), loop)
        except Exception:
            pass

    files_meta = get_all_files(repo_path)
    total_files = len(files_meta)
    print(f"[main] Analyzing {total_files} files on '{target_branch}'...")

    send_progress({
        "stage": "scanning",
        "message": f"Scanning {total_files} files...",
        "progress": 5,
        "total": total_files,
        "completed": 0
    })

    results = [None] * total_files
    completed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(analyze_file, f, repo_url, target_branch): i for i, f in enumerate(files_meta)}
        
        for future in as_completed(future_to_idx):
            results[future_to_idx[future]] = future.result()
            completed += 1
            
            # Send progress update every 10 files (more frequent than 50)
            if completed % 10 == 0 or completed == total_files:
                progress = 5 + int((completed / total_files) * 85)
                send_progress({
                    "stage": "analyzing",
                    "message": f"Analyzing files... {completed}/{total_files}",
                    "progress": progress,
                    "total": total_files,
                    "completed": completed
                })
            
            # Progress indicator every 100 files
            if completed % 100 == 0 or completed == total_files:
                print(f"[main] Progress: {completed}/{total_files} files ({completed*100//total_files}%)")

    for r in results:
        r["path"] = r["path"].replace(repo_path + "/", "")

    code_files  = [r for r in results if r["type"] == "code"]
    docs_files  = [r for r in results if r["type"] == "docs"]
    other_files = [r for r in results if r["type"] == "other"]

    commits = get_local_commits(repo_path, target_branch)

    if skip_gh_api:
        meta, tags, prs, issues = {}, [], [], []
    else:
        meta   = get_repo_meta(repo_url)
        tags   = get_gh_tags(repo_url) or get_local_tags(repo_path)
        prs    = get_pull_requests(repo_url)
        issues = get_issues(repo_url)

    return {
        "repo_url": repo_url,
        "branch":   target_branch,
        "branches": all_branches,
        "meta":     meta,
        "tags":     tags,
        "commits":  commits,
        "pull_requests": prs,
        "issues":   issues,
        "summary": {
            "total":  len(results),
            "code":   len(code_files),
            "docs":   len(docs_files),
            "other":  len(other_files),
            "issues": sum(len(r["issues"]) for r in code_files),
        },
        "code":  code_files,
        "docs":  docs_files,
        "other": other_files,
    }
