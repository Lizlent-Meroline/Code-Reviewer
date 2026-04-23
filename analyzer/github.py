import os
import git
import threading

def clone_repo(repo_url: str, dest: str = "repos"):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(dest, repo_name)

    if not os.path.exists(dest):
        os.makedirs(dest)

    if os.path.exists(repo_path):
        return repo_path

    print("Cloning repo (fast mode)...")

    git.Repo.clone_from(
        repo_url,
        repo_path,
        depth=1,
    )

    return repo_path

def clone_with_timeout(repo_url, repo_path):
    result = [None]

    def task():
        result[0] = git.Repo.clone_from(repo_url, repo_path, depth=1)

    thread = threading.Thread(target=task)
    thread.start()
    thread.join(timeout=30)

    if thread.is_alive():
        raise TimeoutError("Clone took too long")

    return result[0]