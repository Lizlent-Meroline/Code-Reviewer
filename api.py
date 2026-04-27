import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from main import run, run_branch_switch
from analyzer.github import clone_repo, get_branches
from auth import get_user_id, create_user, authenticate, make_token

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)


def history_file(user_id: str) -> str:
    return os.path.join(HISTORY_DIR, f"{user_id}.json")


def load_history(user_id: str) -> list:
    """Load analysis history for a specific user."""
    path = history_file(user_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_history(user_id: str, entry: dict):
    """Save analysis entry to user's history (max 50 entries)."""
    history = load_history(user_id)
    history.insert(0, entry)
    history = history[:50]
    with open(history_file(user_id), "w") as f:
        json.dump(history, f)


class RepoRequest(BaseModel):
    url: str
    branch: Optional[str] = None


class AuthRequest(BaseModel):
    email: str
    password: str


@app.post("/register")
def register(req: AuthRequest):
    try:
        user = create_user(req.email, req.password)
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered.")
    return {"token": make_token(user["id"], user["email"]), "email": user["email"]}


@app.post("/login")
def login(req: AuthRequest):
    user = authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"token": make_token(user["id"], user["email"]), "email": user["email"]}


@app.post("/analyze")
def analyze(req: RepoRequest, user_id: Optional[str] = Depends(get_user_id)):
    """Analyze a GitHub repository and save to history if authenticated."""
    result = run(req.url, req.branch)
    if user_id:
        save_history(user_id, {
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
    """Switch to a different branch and re-analyze without re-fetching GitHub metadata."""
    return run_branch_switch(req.url, req.branch)


@app.post("/branches")
def branches(req: RepoRequest):
    """Get list of branches for a repository."""
    repo_path = clone_repo(req.url)
    return {"branches": get_branches(repo_path)}


@app.get("/history")
def history(user_id: Optional[str] = Depends(get_user_id)):
    """Get analysis history for authenticated user."""
    if not user_id:
        return []
    return load_history(user_id)


@app.delete("/history")
def clear_history(user_id: Optional[str] = Depends(get_user_id)):
    """Clear all history for authenticated user."""
    if user_id:
        path = history_file(user_id)
        if os.path.exists(path):
            os.remove(path)
    return {"status": "cleared"}


@app.get("/")
def home():
    """Serve the main HTML page."""
    return FileResponse("src/index.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
