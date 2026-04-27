"""Analyze only changed files in a PR."""
import git
import os
from typing import List, Dict


def get_changed_files(repo_path: str, base_branch: str, compare_branch: str) -> List[str]:
    """Get list of files changed between two branches."""
    repo = git.Repo(repo_path)
    
    try:
        # Get diff between branches
        diff = repo.git.diff(f"origin/{base_branch}...origin/{compare_branch}", name_only=True)
        changed_files = [os.path.join(repo_path, f) for f in diff.split('\n') if f.strip()]
        return changed_files
    except Exception as e:
        print(f"[pr_diff] Error getting diff: {e}")
        return []


def get_pr_diff_stats(repo_path: str, base_branch: str, compare_branch: str) -> Dict:
    """Get statistics about changes in PR."""
    repo = git.Repo(repo_path)
    
    try:
        # Get detailed diff stats
        diff_stats = repo.git.diff(
            f"origin/{base_branch}...origin/{compare_branch}",
            shortstat=True
        )
        
        # Parse stats (e.g., "3 files changed, 45 insertions(+), 12 deletions(-)")
        stats = {
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "diff_text": diff_stats
        }
        
        parts = diff_stats.split(',')
        for part in parts:
            part = part.strip()
            if 'file' in part:
                stats["files_changed"] = int(part.split()[0])
            elif 'insertion' in part:
                stats["insertions"] = int(part.split()[0])
            elif 'deletion' in part:
                stats["deletions"] = int(part.split()[0])
        
        return stats
    except Exception as e:
        print(f"[pr_diff] Error getting stats: {e}")
        return {"files_changed": 0, "insertions": 0, "deletions": 0, "diff_text": ""}


def filter_files_by_diff(all_files: List[Dict], changed_files: List[str]) -> List[Dict]:
    """Filter file list to only include changed files."""
    changed_set = set(changed_files)
    return [f for f in all_files if f["path"] in changed_set]
