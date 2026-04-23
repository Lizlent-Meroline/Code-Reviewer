import os
import shutil
import requests
import git


# ── Git local helpers ──────────────────────────────────────────────────────────

def clone_repo(repo_url: str, dest: str = "repos") -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(dest, repo_name)
    os.makedirs(dest, exist_ok=True)

    if os.path.exists(repo_path):
        try:
            print(f"[github] Fetching {repo_path}...")
            git.Repo(repo_path).remotes.origin.fetch()
            return repo_path
        except Exception as e:
            print(f"[github] Fetch failed ({e}), re-cloning...")
            shutil.rmtree(repo_path)

    print(f"[github] Cloning {repo_url}...")
    git.Repo.clone_from(repo_url, repo_path)
    print(f"[github] Done.")
    return repo_path


def get_branches(repo_path: str) -> list[str]:
    repo = git.Repo(repo_path)
    return [
        ref.name.replace("origin/", "")
        for ref in repo.remotes.origin.refs
        if not ref.name.endswith("/HEAD")
    ]


def checkout_branch(repo_path: str, branch: str):
    repo = git.Repo(repo_path)
    try:
        repo.git.checkout(branch)
    except git.GitCommandError:
        repo.git.checkout("-b", branch, f"origin/{branch}")
    print(f"[github] Checked out: {branch}")


def get_local_tags(repo_path: str) -> list[dict]:
    repo = git.Repo(repo_path)
    return [
        {
            "name": tag.name,
            "commit": str(tag.commit),
            "message": str(tag.tag.message).strip() if hasattr(tag, "tag") and tag.tag else "",
        }
        for tag in repo.tags
    ]


def get_local_commits(repo_path: str, branch: str, limit: int = 30) -> list[dict]:
    repo = git.Repo(repo_path)
    commits = []
    for c in repo.iter_commits(branch, max_count=limit):
        commits.append({
            "sha": c.hexsha[:7],
            "message": c.message.strip().splitlines()[0],
            "author": c.author.name,
            "date": c.committed_datetime.isoformat(),
        })
    return commits


# ── GitHub REST API helpers ────────────────────────────────────────────────────

def _gh_owner_repo(repo_url: str):
    """Extract owner/repo from a github.com URL."""
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    return parts[-2], parts[-1]


def _gh_get(path: str, token: str = None) -> list | dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    results = []
    url = f"https://api.github.com{path}?per_page=50&page=1"
    while url:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        if isinstance(data, list):
            results.extend(data)
            # follow pagination
            url = r.links.get("next", {}).get("url")
        else:
            return data
    return results


def get_pull_requests(repo_url: str, token: str = None) -> list[dict]:
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/pulls?state=all", token)
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


def get_issues(repo_url: str, token: str = None) -> list[dict]:
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/issues?state=all", token)
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
        if "pull_request" not in item   # issues endpoint returns PRs too
    ]


def get_gh_tags(repo_url: str, token: str = None) -> list[dict]:
    owner, repo = _gh_owner_repo(repo_url)
    raw = _gh_get(f"/repos/{owner}/{repo}/tags", token)
    return [{"name": t["name"], "sha": t["commit"]["sha"][:7]} for t in raw]


def get_repo_meta(repo_url: str, token: str = None) -> dict:
    owner, repo = _gh_owner_repo(repo_url)
    data = _gh_get(f"/repos/{owner}/{repo}", token)
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
