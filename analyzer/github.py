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
            git.Repo(repo_path)
            print(f"[github] Reusing cached repo: {repo_path}")
            return repo_path
        except Exception as e:
            print(f"[github] Cached repo invalid ({e}), re-cloning...")
            shutil.rmtree(repo_path)

    print(f"[github] Shallow cloning {repo_url} (single branch)...")
    try:
        git.Git(dest).clone(
            repo_url, repo_name,
            "--depth=1", "--no-tags", "--single-branch", "--filter=blob:none",
        )
    except git.GitCommandError:
        print(f"[github] Retrying without partial clone filter...")
        git.Git(dest).clone(
            repo_url, repo_name,
            "--depth=1", "--no-tags", "--single-branch",
        )

    print(f"[github] Clone done.")
    return repo_path


def get_branches(repo_path: str) -> list[dict]:
    """Return all remote branches by querying the remote (no full fetch needed)."""
    repo = git.Repo(repo_path)

    try:
        default = repo.remotes.origin.refs["HEAD"].reference.name.replace("origin/", "")
    except Exception:
        default = "main"

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

    try:
        if repo.active_branch.name == branch:
            print(f"[github] Already on: {branch}")
            return
    except TypeError:
        pass  # detached HEAD

    try:
        repo.git.checkout(branch)
        print(f"[github] Checked out local: {branch}")
        return
    except git.GitCommandError:
        pass

    print(f"[github] Fetching branch '{branch}' shallow...")
    try:
        repo.git.fetch("origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}", "--depth=1", "--no-tags")
        repo.git.checkout("-B", branch, f"origin/{branch}")
        print(f"[github] Checked out: {branch}")
    except git.GitCommandError as e:
        print(f"[github] Checkout error: {e}")
        raise RuntimeError(f"Could not checkout branch '{branch}': {e}")


def checkout_tag(repo_path: str, tag: str):
    """Checkout a specific tag (detached HEAD), fetching it if not present locally."""
    repo = git.Repo(repo_path)

    if tag not in [t.name for t in repo.tags]:
        print(f"[github] Fetching tag '{tag}'...")
        try:
            repo.git.fetch("origin", f"refs/tags/{tag}:refs/tags/{tag}", "--depth=1")
        except git.GitCommandError as e:
            raise RuntimeError(f"Could not fetch tag '{tag}': {e}")

    try:
        repo.git.checkout(f"tags/{tag}")
        print(f"[github] Checked out tag: {tag}")
    except git.GitCommandError as e:
        raise RuntimeError(f"Could not checkout tag '{tag}': {e}")


def get_local_tags(repo_path: str) -> list[dict]:
    """Get all tags from the local repository."""
    repo = git.Repo(repo_path)
    if not repo.tags:
        return []
    return [
        {
            "name": t.name,
            "commit": str(t.commit),
            "message": str(t.tag.message).strip() if hasattr(t, "tag") and t.tag else "",
        }
        for t in repo.tags
    ]


def get_local_commits(repo_path: str, branch: str, limit: int = 500) -> list[dict]:
    """Get commits from a branch, fetching full history if needed."""
    repo = git.Repo(repo_path)
    commits = []

    # If shallow clone, fetch more history
    shallow_file = os.path.join(repo_path, ".git", "shallow")
    if os.path.exists(shallow_file):
        try:
            print(f"[github] Fetching commit history for {branch}...")
            repo.git.fetch("--unshallow", "--no-tags", "origin", branch)
        except git.GitCommandError:
            # Already unshallow or fetch failed — continue with what we have
            pass

    try:
        for c in repo.iter_commits(branch, max_count=limit):
            commits.append({
                "sha": c.hexsha[:7],
                "message": c.message.strip().splitlines()[0],
                "author": c.author.name,
                "date": c.committed_datetime.isoformat(),
            })
    except Exception:
        pass

    return commits


#  GitHub REST API helpers

def _gh_owner_repo(repo_url: str):
    """Extract owner/repo from a github.com URL."""
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    return parts[-2], parts[-1]


def _gh_get(path: str, max_pages: int = 5) -> list | dict:
    """Make paginated GET request to GitHub API with page limit."""
    headers = {"Accept": "application/vnd.github+json"}
    results = []
    url = f"https://api.github.com{path}?per_page=100&page=1"
    pages = 0
    while url and pages < max_pages:
        try:
            r = requests.get(url, headers=headers, timeout=8)
        except requests.Timeout:
            break
        if r.status_code == 403:
            print("[github] API rate limit hit, returning partial results")
            break
        if r.status_code != 200:
            return []
        data = r.json()
        if isinstance(data, list):
            results.extend(data)
            url = r.links.get("next", {}).get("url")
            pages += 1
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
