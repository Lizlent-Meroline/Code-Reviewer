import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.github import (
    clone_repo, get_branches, checkout_branch,
    get_local_tags, get_local_commits,
    get_pull_requests, get_issues, get_gh_tags, get_repo_meta,
)
from utils.parser import get_all_files
from utils.cache import get_file_hash, get_cache_key, get_cached_result, save_cached_result, flush_cache_to_disk
from analyzer.detector import detect_language
from analyzer import get_analyzer

# Use all available cores for I/O-bound analysis
MAX_WORKERS = min(64, (os.cpu_count() or 4) * 8)
MAX_FILE_SIZE_KB = 4096  # 4MB limit per file


def analyze_file(file_meta: dict, repo_url: str = "", branch: str = "") -> dict:
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

    # Skip non-code files immediately — no analysis needed
    if file_meta["type"] != "code":
        return result

    # Check cache using fast mtime+size hash (no file read needed)
    file_hash = get_file_hash(path)
    if file_hash and repo_url and branch:
        cache_key = get_cache_key(repo_url, branch, path, file_hash)
        cached = get_cached_result(cache_key)
        if cached:
            return cached

    # Skip oversized files
    try:
        if os.path.getsize(path) / 1024 > MAX_FILE_SIZE_KB:
            result["issues"] = ["File too large, skipped"]
            return result
    except OSError:
        return result

    try:
        # Use pre-computed ext from parser if available, else detect from path
        lang = detect_language(path, file_meta.get("ext", ""))
        result["language"] = lang
        result["issues"] = get_analyzer(lang).analyze(path)

        # Save to memory cache (flushed to disk in batch after all files done)
        if file_hash and repo_url and branch:
            save_cached_result(cache_key, result)

    except Exception as e:
        result["issues"] = [f"Error: {e}"]

    return result


def run(repo_url: str, branch: str = None, client_id: str = None, manager=None, loop=None) -> dict:
    """Clone repo, checkout branch, and generate full analysis report."""
    repo_path = clone_repo(repo_url)
    all_branches = get_branches(repo_path)
    branch_names = [b["name"] for b in all_branches]

    target_branch = branch if branch in branch_names else all_branches[0]["name"]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches,
                         client_id=client_id, manager=manager, loop=loop)


def run_tag_switch(repo_url: str, tag: str) -> dict:
    """Fast path: checkout a tag and re-scan files, skip GitHub API calls."""
    from analyzer.github import checkout_tag
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join("repos", repo_name)

    all_branches = get_branches(repo_path)
    checkout_tag(repo_path, tag)

    result = _build_report(repo_url, repo_path, tag, all_branches, skip_gh_api=True)
    result["active_tag"] = tag
    return result


def run_branch_switch(repo_url: str, branch: str) -> dict:
    """Fast path: checkout + re-scan files, skip GitHub API calls."""
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join("repos", repo_name)

    all_branches = get_branches(repo_path)
    branch_names = [b["name"] for b in all_branches]

    target_branch = branch if branch in branch_names else all_branches[0]["name"]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches, skip_gh_api=True)


def _build_report(repo_url, repo_path, target_branch, all_branches,
                  skip_gh_api=False, client_id=None, manager=None, loop=None) -> dict:
    """Build analysis report with parallel file scans and GitHub API calls."""
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
    print(f"[main] {total_files} files on '{target_branch}' | workers={MAX_WORKERS}")

    send_progress({
        "stage": "scanning",
        "message": f"Found {total_files} files, starting analysis...",
        "progress": 5,
        "total": total_files,
        "completed": 0
    })

    # Run file analysis and GitHub API calls in parallel
    results = [None] * total_files
    completed = 0

    # Fire off GitHub API calls concurrently while files are being analyzed
    gh_executor = ThreadPoolExecutor(max_workers=4)
    if not skip_gh_api:
        future_meta    = gh_executor.submit(get_repo_meta, repo_url)
        future_prs     = gh_executor.submit(get_pull_requests, repo_url)
        future_issues  = gh_executor.submit(get_issues, repo_url)
        future_tags    = gh_executor.submit(get_gh_tags, repo_url)
        future_commits = gh_executor.submit(get_local_commits, repo_path, target_branch)
    else:
        future_commits = gh_executor.submit(get_local_commits, repo_path, target_branch)

    # Analyze files with large thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as file_executor:
        future_to_idx = {
            file_executor.submit(analyze_file, f, repo_url, target_branch): i
            for i, f in enumerate(files_meta)
        }

        # Progress update interval — scale with file count to avoid overhead
        update_interval = max(50, total_files // 20)

        for future in as_completed(future_to_idx):
            results[future_to_idx[future]] = future.result()
            completed += 1

            if completed % update_interval == 0 or completed == total_files:
                progress = 5 + int((completed / total_files) * 80)
                send_progress({
                    "stage": "analyzing",
                    "message": f"Analyzing... {completed}/{total_files}",
                    "progress": progress,
                    "total": total_files,
                    "completed": completed
                })
                print(f"[main] {completed}/{total_files} ({completed*100//total_files}%)")

    # Batch flush cache to disk after all files done (much faster than per-file writes)
    flush_cache_to_disk()

    # Strip repo path prefix from all results
    prefix = repo_path + "/"
    for r in results:
        r["path"] = r["path"].replace(prefix, "")

    code_files  = [r for r in results if r["type"] == "code"]
    docs_files  = [r for r in results if r["type"] == "docs"]
    other_files = [r for r in results if r["type"] == "other"]

    send_progress({
        "stage": "fetching",
        "message": "Fetching repository metadata...",
        "progress": 90
    })

    # Collect GitHub API results (they've been running in parallel)
    if skip_gh_api:
        meta, tags, prs, issues = {}, [], [], []
        commits = future_commits.result()
    else:
        meta    = future_meta.result()
        prs     = future_prs.result()
        issues  = future_issues.result()
        tags    = future_tags.result() or get_local_tags(repo_path)
        commits = future_commits.result()

    gh_executor.shutdown(wait=False)

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
