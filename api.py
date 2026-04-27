import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from main import run, run_branch_switch
from analyzer.github import clone_repo, get_branches

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_FILE = "history.json"


def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_history(entry: dict):
    history = load_history()
    # keep latest 50 reports
    history.insert(0, entry)
    history = history[:50]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


class RepoRequest(BaseModel):
    url: str
    branch: Optional[str] = None


@app.post("/analyze")
def analyze(req: RepoRequest):
    result = run(req.url, req.branch)
    save_history({
        "id": datetime.utcnow().isoformat(),
        "repo_url": req.url,
        "branch": result["branch"],
        "summary": result["summary"],
        "meta": result.get("meta", {}),
    })
    return result


class SwitchRequest(BaseModel):
    url: str
    branch: str


@app.post("/switch-branch")
def switch_branch(req: SwitchRequest):
    return run_branch_switch(req.url, req.branch)


@app.post("/branches")
def branches(req: RepoRequest):
    repo_path = clone_repo(req.url)
    return {"branches": get_branches(repo_path)}


@app.get("/history")
def history():
    return load_history()


@app.delete("/history")
def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    return {"status": "cleared"}


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
