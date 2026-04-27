import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.github import (
    clone_repo, get_branches, checkout_branch,
    get_local_tags, get_local_commits,
    get_pull_requests, get_issues, get_gh_tags, get_repo_meta,
)
from utils.parser import get_all_files
from analyzer.detector import detect_language
from analyzer import get_analyzer

MAX_WORKERS = 8


def analyze_file(file_meta: dict) -> dict:
    path = file_meta["path"]
    result = {
        "path": path,
        "name": file_meta["name"],
        "ext": file_meta["ext"],
        "type": file_meta["type"],
        "language": None,
        "issues": [],
    }
    if file_meta["type"] == "code":
        try:
            lang = detect_language(path)
            result["language"] = lang
            result["issues"] = get_analyzer(lang).analyze(path)
        except Exception as e:
            result["issues"] = [f"Error: {e}"]
    return result


def run(repo_url: str, branch: str = None) -> dict:
    repo_path = clone_repo(repo_url)
    all_branches = get_branches(repo_path)

    target_branch = branch if branch in all_branches else all_branches[0]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches)


def run_branch_switch(repo_url: str, branch: str) -> dict:
    """Fast path: just checkout + re-scan files, skip GitHub API calls."""
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join("repos", repo_name)

    all_branches = get_branches(repo_path)
    target_branch = branch if branch in all_branches else all_branches[0]
    checkout_branch(repo_path, target_branch)

    return _build_report(repo_url, repo_path, target_branch, all_branches, token=None, skip_gh_api=True)


def _build_report(repo_url, repo_path, target_branch, all_branches, skip_gh_api=False) -> dict:
    files_meta = get_all_files(repo_path)
    print(f"[main] {len(files_meta)} files on '{target_branch}'")

    results = [None] * len(files_meta)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(analyze_file, f): i for i, f in enumerate(files_meta)}
        for future in as_completed(future_to_idx):
            results[future_to_idx[future]] = future.result()

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
