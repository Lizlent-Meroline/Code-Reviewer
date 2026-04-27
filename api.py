import json
import os
from datetime import datetime
from typing import Optional
import asyncio

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from main import run, run_branch_switch
from analyzer.github import clone_repo, get_branches
from analyzer.pr_diff import get_changed_files, get_pr_diff_stats, filter_files_by_diff
from auth import get_user_id, create_user, authenticate, make_token
from utils.export import export_json, export_pdf
from utils.cache import clear_cache

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_progress(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except:
                self.disconnect(client_id)

manager = ConnectionManager()


def history_file(user_id: str) -> str:
    """Get the history file path for a specific user."""
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
    client_id: Optional[str] = None  # For WebSocket progress


class AuthRequest(BaseModel):
    email: str
    password: str


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@app.post("/register")
def register(req: AuthRequest):
    """Register a new user account."""
    try:
        user = create_user(req.email, req.password)
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered.")
    return {"token": make_token(user["id"], user["email"]), "email": user["email"]}


@app.post("/login")
def login(req: AuthRequest):
    """Authenticate user and return JWT token."""
    user = authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"token": make_token(user["id"], user["email"]), "email": user["email"]}


@app.post("/analyze")
async def analyze(req: RepoRequest, user_id: Optional[str] = Depends(get_user_id)):
    """Analyze a GitHub repository and save to history if authenticated."""
    # Send initial progress
    if req.client_id:
        await manager.send_progress(req.client_id, {
            "stage": "cloning",
            "message": "Cloning repository...",
            "progress": 0
        })
    
    result = await asyncio.to_thread(run, req.url, req.branch, req.client_id, manager, asyncio.get_event_loop())
    
    if user_id:
        save_history(user_id, {
            "id": datetime.utcnow().isoformat(),
            "repo_url": req.url,
            "branch": result["branch"],
            "summary": result["summary"],
            "meta": result.get("meta", {}),
        })
    
    # Send completion
    if req.client_id:
        await manager.send_progress(req.client_id, {
            "stage": "complete",
            "message": "Analysis complete!",
            "progress": 100
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


@app.post("/export/json")
async def export_report_json(data: dict):
    """Export analysis report as JSON."""
    json_data = export_json(data)
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=analysis-report.json"}
    )


@app.post("/export/pdf")
async def export_report_pdf(data: dict):
    """Export analysis report as PDF."""
    pdf_data = export_pdf(data)
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=analysis-report.pdf"}
    )


class PRDiffRequest(BaseModel):
    url: str
    base_branch: str
    compare_branch: str
    client_id: Optional[str] = None


@app.post("/analyze/pr-diff")
async def analyze_pr_diff(req: PRDiffRequest, user_id: Optional[str] = Depends(get_user_id)):
    """Analyze only changed files in a PR (base...compare)."""
    if req.client_id:
        await manager.send_progress(req.client_id, {
            "stage": "cloning",
            "message": "Cloning repository...",
            "progress": 0
        })
    
    # Clone and get both branches
    repo_path = await asyncio.to_thread(clone_repo, req.url)
    
    # Get changed files
    changed_files = await asyncio.to_thread(
        get_changed_files, repo_path, req.base_branch, req.compare_branch
    )
    
    # Get diff stats
    diff_stats = await asyncio.to_thread(
        get_pr_diff_stats, repo_path, req.base_branch, req.compare_branch
    )
    
    if req.client_id:
        await manager.send_progress(req.client_id, {
            "stage": "analyzing",
            "message": f"Analyzing {len(changed_files)} changed files...",
            "progress": 10
        })
    
    # Analyze only changed files
    from utils.parser import get_all_files
    all_files = get_all_files(repo_path)
    files_to_analyze = filter_files_by_diff(all_files, changed_files)
    
    # Run analysis on filtered files
    from main import analyze_file
    results = []
    for i, file_meta in enumerate(files_to_analyze):
        result = await asyncio.to_thread(analyze_file, file_meta, req.url, req.compare_branch)
        results.append(result)
        
        if req.client_id and (i % 10 == 0 or i == len(files_to_analyze) - 1):
            progress = 10 + int((i / len(files_to_analyze)) * 80)
            await manager.send_progress(req.client_id, {
                "stage": "analyzing",
                "message": f"Analyzing... {i+1}/{len(files_to_analyze)}",
                "progress": progress
            })
    
    # Build response
    code_files = [r for r in results if r["type"] == "code"]
    
    response = {
        "repo_url": req.url,
        "base_branch": req.base_branch,
        "compare_branch": req.compare_branch,
        "diff_stats": diff_stats,
        "summary": {
            "files_changed": len(results),
            "code_files": len(code_files),
            "issues": sum(len(r["issues"]) for r in code_files),
        },
        "files": results,
    }
    
    if req.client_id:
        await manager.send_progress(req.client_id, {
            "stage": "complete",
            "message": "PR analysis complete!",
            "progress": 100
        })
    
    return response


@app.delete("/cache")
def clear_analysis_cache():
    """Clear all cached analysis results."""
    clear_cache()
    return {"status": "cache cleared"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
