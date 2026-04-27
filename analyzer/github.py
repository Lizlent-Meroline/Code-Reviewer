import os
import shutil
import requests
import git


#  Git local helpers 

def clone_repo(repo_url: str, dest: str = "repos") -> str:
    """Clone or reuse a GitHub repository using a fast single-branch shallow clone."""
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(dest, repo_name)
    os.makedirs(dest, exist_ok=True)

    if os.path.exists(repo_path):
        try:
            # Validate it's a real repo — if so, reuse it as-is (already cloned)
            git.Repo(repo_path)
            print(f"[github] Reusing cached repo: {repo_path}")
            return repo_path
        except Exception as e:
            print(f"[github] Cached repo invalid ({e}), re-cloning...")
            shutil.rmtree(repo_path)

    print(f"[github] Shallow cloning {repo_url} (single branch)...")
    try:
        # depth=1 + single branch = fastest possible clone (no history, no other branches)
        git.Git(dest).clone(
            repo_url,
            repo_name,
            "--depth=1",
            "--no-tags",
            "--single-branch",
            "--filter=blob:none",  # skip large blobs until needed (partial clone)
        )
    except git.GitCommandError:
        # --filter may not be supported on older git, fall back without it
        print(f"[github] Retrying without partial clone filter...")
        git.Git(dest).clone(
            repo_url,
            repo_name,
            "--depth=1",
            "--no-tags",
            "--single-branch",
        )

    print(f"[github] Clone done.")
    return repo_path


def get_branches(repo_path: str) -> list[dict]:
    """Return all remote branches by querying the remote (no full fetch needed)."""
    repo = git.Repo(repo_path)

    # Get default branch
    try:
        default = repo.remotes.origin.refs["HEAD"].reference.name.replace("origin/", "")
    except Exception:
        default = "main"

    # Use ls-remote to list all remote branches without fetching them
    try:
        raw = repo.git.ls_remote("--heads", "origin")
        branches = []
        for line in raw.strip().splitlines():
            if not line:
                continue
            sha, ref = line.split("\t", 1)
            name = ref.replace("refs/heads/", "")
            branches.append({
                "name": name,
                "merged": name == default,
                "is_default": name == default,
                "sha": sha[:7],
            })
        branches.sort(key=lambda b: (not b["is_default"], b["name"]))
        return branches
    except Exception:
        pass

    # Fallback: use already-fetched remote refs
    branches = []
    for ref in repo.remotes.origin.refs:
        if ref.name.endswith("/HEAD"):
            continue
        name = ref.name.replace("origin/", "")
        branches.append({
            "name": name,
            "merged": name == default,
            "is_default": name == default,
            "sha": ref.commit.hexsha[:7] if ref.commit else "",
        })
    branches.sort(key=lambda b: (not b["is_default"], b["name"]))
    return branches


def checkout_branch(repo_path: str, branch: str):
    """Checkout a branch, fetching it shallow from origin if not already local."""
    repo = git.Repo(repo_path)

    # Already on this branch?
    try:
        if repo.active_branch.name == branch:
            print(f"[github] Already on: {branch}")
            return
    except TypeError:
        pass  # detached HEAD

    # Try local checkout first
    try:
        repo.git.checkout(branch)
        print(f"[github] Checked out local: {branch}")
        return
    except git.GitCommandError:
        pass

    # Fetch only this branch shallow, then checkout
    print(f"[github] Fetching branch '{branch}' shallow...")
    try:
        repo.git.fetch("origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}", "--depth=1", "--no-tags")
        repo.git.checkout("-B", branch, f"origin/{branch}")
        print(f"[github] Checked out: {branch}")
    except git.GitCommandError as e:
        print(f"[github] Checkout error: {e}")
        raise RuntimeError(f"Could not checkout branch '{branch}': {e}")


def get_local_tags(repo_path: str) -> list[dict]:
    """Get all tags from the local repository."""
    repo = git.Repo(repo_path)
    # Shallow clones don't have tags by default
    if not repo.tags:
        return []
    return [
        {
            "name": tag.name,
            "commit": str(tag.commit),
            "message": str(tag.tag.message).strip() if hasattr(tag, "tag") and tag.tag else "",
        }
        for tag in repo.tags
    ]


def get_local_commits(repo_path: str, branch: str, limit: int = 30) -> list[dict]:
    """Get recent commits from a specific branch."""
    repo = git.Repo(repo_path)
    commits = []
    
    # For shallow clones, we only have 1 commit per branch
    # Fetch more if needed
    try:
        for c in repo.iter_commits(branch, max_count=limit):
            commits.append({
                "sha": c.hexsha[:7],
                "message": c.message.strip().splitlines()[0],
                "author": c.author.name,
                "date": c.committed_datetime.isoformat(),
            })
    except Exception:
        # If we can't get commits, return empty
        pass
    
    return commits


#  GitHub REST API helpers

def _gh_owner_repo(repo_url: str):
    """Extract owner/repo from a github.com URL."""
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    return parts[-2], parts[-1]


def _gh_get(path: str) -> list | dict:
    """Make paginated GET request to GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    results = []
    url = f"https://api.github.com{path}?per_page=50&page=1"
    while url:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        if isinstance(data, list):
            results.extend(data)
            url = r.links.get("next", {}).get("url")
        else:
            return data
    return results


def get_pull_requests(repo_url: str) -> list[dict]:
    """Fetch all pull requests from GitHub API."""
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/pulls?state=all")
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "author": pr["user"]["login"],
            "branch": pr["head"]["ref"],
            "created_at": pr["created_at"],
            "url": pr["html_url"],
        }
        for pr in raw
    ]


def get_issues(repo_url: str) -> list[dict]:
    """Fetch all issues (excluding PRs) from GitHub API."""
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/issues?state=all")
    return [
        {
            "number": item["number"],
            "title": item["title"],
            "state": item["state"],
            "author": item["user"]["login"],
            "labels": [l["name"] for l in item.get("labels", [])],
            "created_at": item["created_at"],
            "url": item["html_url"],
        }
        for item in raw
        if "pull_request" not in item
    ]


def get_gh_tags(repo_url: str) -> list[dict]:
    """Fetch all tags from GitHub API."""
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/tags")
    return [{"name": t["name"], "sha": t["commit"]["sha"][:7]} for t in raw]


def get_repo_meta(repo_url: str) -> dict:
    """Fetch repository metadata from GitHub API."""
    owner, repo = _gh_owner_repo(repo_url)
    data = _gh_get(f"/repos/{owner}/{repo}")
    if not isinstance(data, dict):
        return {}
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "url": data.get("html_url"),
    }
