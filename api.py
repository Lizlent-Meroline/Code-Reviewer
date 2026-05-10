import json
import os
import uuid
from datetime import datetime, timezone
from functools import cmp_to_key
from typing import Optional
import asyncio

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from main import run, run_branch_switch, run_tag_switch
from analyzer.github import clone_repo, get_branches
from analyzer.pr_diff import get_changed_files, get_pr_diff_stats, filter_files_by_diff
from auth import get_user_id, create_user, authenticate, make_token
from utils.export import export_json, export_pdf
from utils.cache import clear_cache

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)


# Analytics models

class ScoreItem(BaseModel):
    id: str
    repo_url: str
    branch: str
    quality_score: int
    timestamp: str


class TrendPoint(BaseModel):
    timestamp: str
    branch: str
    quality_score: int


class LeaderboardEntry(BaseModel):
    repo_url: str
    repo_name: str
    latest_quality_score: int
    analyses_count: int
    last_analyzed: str


# Team Collaboration models 

class ShareRequest(BaseModel):
    emails: list[str]


class ShareRecord(BaseModel):
    report_id: str
    recipient_email: str
    shared_at: str


class SharedReportItem(BaseModel):
    report_id: str
    owner_email: str
    repo_url: str
    branch: str
    quality_score: int
    shared_at: str


class CommentRequest(BaseModel):
    file_path: str
    issue_index: int
    text: str


class CommentResponse(BaseModel):
    comment_id: str
    report_id: str
    author_email: str
    file_path: str
    issue_index: int
    text: str
    created_at: str


class AssignmentRequest(BaseModel):
    file_path: str
    issue_index: int
    assignee_email: str


class AssignmentResponse(BaseModel):
    report_id: str
    file_path: str
    issue_index: int
    assignee_email: str
    assigner_email: str
    assigned_at: str


def compute_quality_score(summary: dict) -> int:
    """Compute quality score [0-100] from a summary dict."""
    issues = summary.get("issues", 0)
    code   = summary.get("code", 0)
    return max(0, 100 - round((issues / max(code, 1)) * 100))


def compute_trends(history: list, repo_url: str) -> list:
    """Return time-ordered trend points for a given repo_url (case-insensitive)."""
    target = repo_url.lower()
    points = []
    for entry in history:
        if entry.get("repo_url", "").lower() != target:
            continue
        summary = entry.get("summary")
        if not summary:
            continue
        points.append({
            "timestamp":     entry.get("id", ""),
            "branch":        entry.get("branch", ""),
            "quality_score": compute_quality_score(summary),
        })
    points.sort(key=lambda p: p["timestamp"])
    return points


def compute_leaderboard(history: list) -> list:
    """Return repos ranked by latest quality score descending."""
    groups: dict[str, list] = {}
    for entry in history:
        url = entry.get("repo_url", "")
        if url:
            groups.setdefault(url, []).append(entry)

    rows = []
    for url, entries in groups.items():
        latest = max(entries, key=lambda e: e.get("id", ""))
        summary = latest.get("summary") or {}
        meta    = latest.get("meta") or {}
        repo_name = meta.get("full_name") or url.rstrip("/").split("/")[-1]
        rows.append({
            "repo_url":             url,
            "repo_name":            repo_name,
            "latest_quality_score": compute_quality_score(summary),
            "analyses_count":       len(entries),
            "last_analyzed":        latest.get("id", ""),
        })

    rows.sort(key=lambda r: (-r["latest_quality_score"], r["last_analyzed"]))
    return rows

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
    username: Optional[str] = None  # required on signup, ignored on login


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
    if not req.username or not req.username.strip():
        raise HTTPException(status_code=400, detail="Username is required.")
    try:
        user = create_user(req.email, req.password, req.username)
    except Exception:
        raise HTTPException(status_code=400, detail="Email or username already registered.")
    return {"token": make_token(user["id"], user["email"], user["username"]), "email": user["email"], "username": user["username"]}


@app.post("/login")
def login(req: AuthRequest):
    """Authenticate user and return JWT token."""
    user = authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"token": make_token(user["id"], user["email"], user["username"]), "email": user["email"], "username": user["username"]}


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


class TagRequest(BaseModel):
    url: str
    tag: str


@app.post("/switch-branch")
def switch_branch(req: SwitchRequest):
    """Switch to a different branch and re-analyze without re-fetching GitHub metadata."""
    return run_branch_switch(req.url, req.branch)


@app.post("/switch-tag")
def switch_tag(req: TagRequest):
    """Checkout a tag and re-analyze files without re-fetching GitHub metadata."""
    return run_tag_switch(req.url, req.tag)


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
            # Cascade-delete all collaboration data for each report entry
            with open(path) as f:
                history = json.load(f)
            from auth import get_db
            db = get_db()
            for entry in history:
                rid = entry.get("id")
                if rid:
                    db.execute(
                        "DELETE FROM report_shares WHERE report_owner_id = ? AND report_id = ?",
                        (user_id, rid)
                    )
                    db.execute(
                        "DELETE FROM issue_comments WHERE report_owner_id = ? AND report_id = ?",
                        (user_id, rid)
                    )
                    db.execute(
                        "DELETE FROM issue_assignments WHERE report_owner_id = ? AND report_id = ?",
                        (user_id, rid)
                    )
            db.commit()
            os.remove(path)
    return {"status": "cleared"}


@app.get("/")
def home():
    """Serve the main HTML page."""
    return FileResponse("src/index.html")


@app.get("/src/{path:path}")
def serve_src(path: str):
    """Serve static files from src directory."""
    file_path = os.path.join("src", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


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


def compute_quality_score(summary: dict) -> int:
    """Compute a quality score (0–100) from an analysis summary.

    Formula: max(0, 100 - round((issues / max(code, 1)) * 100))

    Where:
      - issues: number of detected issues (defaults to 0 if absent)
      - code:   number of code files analysed (defaults to 0 if absent)

    The max(code, 1) guard prevents zero-division when no code files were
    analysed, returning a perfect score of 100 in that case.
    """
    issues = summary.get("issues", 0)
    code = summary.get("code", 0)
    return max(0, 100 - round((issues / max(code, 1)) * 100))


class ScoreItem(BaseModel):
    id: str
    repo_url: str
    branch: str
    quality_score: int
    timestamp: str


class TrendPoint(BaseModel):
    timestamp: str
    branch: str
    quality_score: int


class LeaderboardEntry(BaseModel):
    repo_url: str
    repo_name: str
    latest_quality_score: int
    analyses_count: int
    last_analyzed: str


@app.get("/analytics/scores", response_model=list[ScoreItem])
def analytics_scores(user_id: Optional[str] = Depends(get_user_id)):
    """Return a quality score for every history entry of the authenticated user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    history = load_history(user_id)
    result = []
    for entry in history:
        summary = entry.get("summary")
        if not summary:
            continue
        result.append(ScoreItem(
            id=entry["id"],
            repo_url=entry["repo_url"],
            branch=entry.get("branch", ""),
            quality_score=compute_quality_score(summary),
            timestamp=entry["id"],
        ))
    return result


def compute_trends(history: list, repo_url: str) -> list[dict]:
    """Filter history by repo_url (case-insensitive) and return time-ordered quality scores."""
    matched = [
        e for e in history
        if e.get("repo_url", "").lower() == repo_url.lower() and e.get("summary")
    ]
    matched.sort(key=lambda e: e["id"])
    return [
        {
            "timestamp": e["id"],
            "branch": e.get("branch", ""),
            "quality_score": compute_quality_score(e["summary"]),
        }
        for e in matched
    ]


@app.get("/analytics/trends", response_model=list[TrendPoint])
def analytics_trends(repo_url: str, user_id: Optional[str] = Depends(get_user_id)):
    """Return time-ordered quality scores for a specific repository."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    history = load_history(user_id)
    return compute_trends(history, repo_url)


def compute_leaderboard(history: list) -> list[dict]:
    """Aggregate history into one entry per repo, ranked by latest quality score."""
    repos: dict[str, list] = {}
    for entry in history:
        url = entry.get("repo_url", "")
        if url:
            repos.setdefault(url, []).append(entry)

    result = []
    for url, entries in repos.items():
        latest = max(entries, key=lambda e: e["id"])
        summary = latest.get("summary") or {}
        meta = latest.get("meta") or {}
        repo_name = meta.get("full_name") or url.rstrip("/").split("/")[-1]
        result.append({
            "repo_url": url,
            "repo_name": repo_name,
            "latest_quality_score": compute_quality_score(summary),
            "analyses_count": len(entries),
            "last_analyzed": latest["id"],
        })

    def cmp(a, b):
        if a["latest_quality_score"] != b["latest_quality_score"]:
            return b["latest_quality_score"] - a["latest_quality_score"]
        return (b["last_analyzed"] > a["last_analyzed"]) - (b["last_analyzed"] < a["last_analyzed"])

    result.sort(key=cmp_to_key(cmp))
    return result


@app.get("/analytics/leaderboard", response_model=list[LeaderboardEntry])
def analytics_leaderboard(user_id: Optional[str] = Depends(get_user_id)):
    """Return repositories ranked by latest quality score."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    history = load_history(user_id)
    return compute_leaderboard(history)


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


# ── Team Collaboration helpers ────────────────────────────────────────────────

def _assert_report_access(user_id: str, report_owner_id: str, report_id: str, db) -> bool:
    """
    Verify that user_id has access to the specified report.
    
    Returns True if:
    - user_id equals report_owner_id (owner always has access), OR
    - a matching row exists in report_shares table
    
    Raises HTTPException(403) if access is denied.
    """
    # Owner always has access
    if user_id == report_owner_id:
        return True
    
    # Check if user is a recipient of the report
    row = db.execute(
        """
        SELECT 1 FROM report_shares
        WHERE report_owner_id = ? AND report_id = ? AND recipient_id = ?
        """,
        (report_owner_id, report_id, user_id)
    ).fetchone()
    
    if row:
        return True
    
    # No access
    raise HTTPException(status_code=403, detail="Access denied")


def _resolve_report_owner(user_id: str, report_id: str, db) -> str:
    """
    Resolve the report_owner_id for a given report_id and requesting user.
    Returns user_id if they own the report, or the owner_id from report_shares.
    Raises HTTPException(403) if no access found.
    """
    # Check if user owns the report
    history_path = f"history/{user_id}.json"
    if os.path.exists(history_path):
        with open(history_path) as f:
            history = json.load(f)
        if any(r["id"] == report_id for r in history):
            return user_id

    # Check if user is a recipient
    row = db.execute(
        "SELECT report_owner_id FROM report_shares WHERE report_id = ? AND recipient_id = ?",
        (report_id, user_id)
    ).fetchone()
    if row:
        return row["report_owner_id"]

    raise HTTPException(status_code=403, detail="Access denied")


# Analytics endpoints 

@app.get("/analytics/scores")
def analytics_scores(user_id: Optional[str] = Depends(get_user_id)):
    """Return quality scores for all history entries of the authenticated user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    history = load_history(user_id)
    result = []
    for entry in history:
        summary = entry.get("summary")
        if not summary:
            continue
        result.append(ScoreItem(
            id=entry.get("id", ""),
            repo_url=entry.get("repo_url", ""),
            branch=entry.get("branch", ""),
            quality_score=compute_quality_score(summary),
            timestamp=entry.get("id", ""),
        ))
    return result


@app.get("/analytics/trends")
def analytics_trends(repo_url: str, user_id: Optional[str] = Depends(get_user_id)):
    """Return time-ordered quality score trend for a specific repository."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    history = load_history(user_id)
    return compute_trends(history, repo_url)


@app.get("/analytics/leaderboard")
def analytics_leaderboard(user_id: Optional[str] = Depends(get_user_id)):
    """Return repositories ranked by latest quality score."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    history = load_history(user_id)
    return compute_leaderboard(history)


# Team Collaboration endpoints

@app.post("/reports/{report_id}/share", response_model=list[ShareRecord])
async def share_report(report_id: str, req: ShareRequest, user_id: str = Depends(get_user_id)):
    """Share a report with one or more recipients by email."""
    # Require auth
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate report exists in caller's history
    history_path = f"history/{user_id}.json"
    if not os.path.exists(history_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(history_path) as f:
        history = json.load(f)
    
    report = next((r for r in history if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Look up each email and create shares
    from auth import get_db
    db = get_db()
    results = []
    
    for email in req.emails:
        # Look up recipient
        row = db.execute("SELECT id FROM users WHERE email = ?", (email.lower(),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"User not found: {email}")
        
        recipient_id = row["id"]
        
        # Check if share already exists
        existing = db.execute(
            """
            SELECT shared_at FROM report_shares
            WHERE report_owner_id = ? AND report_id = ? AND recipient_id = ?
            """,
            (user_id, report_id, recipient_id)
        ).fetchone()
        
        if existing:
            # Return existing share record
            shared_at = existing["shared_at"]
        else:
            # Create new share record
            share_id = str(uuid.uuid4())
            shared_at = datetime.now(timezone.utc).isoformat()
            
            db.execute(
                """
                INSERT INTO report_shares 
                (id, report_owner_id, report_id, recipient_id, shared_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (share_id, user_id, report_id, recipient_id, shared_at)
            )
            db.commit()
        
        results.append(ShareRecord(
            report_id=report_id,
            recipient_email=email,
            shared_at=shared_at
        ))
    
    return results


@app.delete("/reports/{report_id}/share/{recipient_email}")
async def revoke_share(report_id: str, recipient_email: str, user_id: str = Depends(get_user_id)):
    """Revoke a share. Only the report owner may call this."""
    # Require auth
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify caller is report owner by checking history
    history_path = f"history/{user_id}.json"
    if not os.path.exists(history_path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    with open(history_path) as f:
        history = json.load(f)
    
    report = next((r for r in history if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Look up recipient
    from auth import get_db
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (recipient_email.lower(),)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Share not found")
    
    recipient_id = row["id"]
    
    # Delete share
    cursor = db.execute(
        """
        DELETE FROM report_shares
        WHERE report_owner_id = ? AND report_id = ? AND recipient_id = ?
        """,
        (user_id, report_id, recipient_id)
    )
    db.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Share not found")
    
    return {"status": "revoked"}


@app.get("/shared-with-me", response_model=list[SharedReportItem])
async def get_shared_reports(user_id: str = Depends(get_user_id)):
    """List all reports shared with the authenticated user."""
    # Require auth
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from auth import get_db
    db = get_db()
    
    # Get all shares for this user
    rows = db.execute(
        """
        SELECT rs.report_owner_id, rs.report_id, rs.shared_at, u.email as owner_email
        FROM report_shares rs
        JOIN users u ON rs.report_owner_id = u.id
        WHERE rs.recipient_id = ?
        ORDER BY rs.shared_at DESC
        """,
        (user_id,)
    ).fetchall()
    
    results = []
    for row in rows:
        owner_id = row["report_owner_id"]
        report_id = row["report_id"]
        owner_email = row["owner_email"]
        shared_at = row["shared_at"]
        
        # Load owner's history to get report details
        history_path = f"history/{owner_id}.json"
        if not os.path.exists(history_path):
            continue  # Skip if history file doesn't exist
        
        with open(history_path) as f:
            history = json.load(f)
        
        report = next((r for r in history if r["id"] == report_id), None)
        if not report:
            continue  # Skip if report not found in history
        
        # Compute quality score using existing helper
        quality_score = compute_quality_score(report.get("summary", {}))
        
        results.append(SharedReportItem(
            report_id=report_id,
            owner_email=owner_email,
            repo_url=report.get("repo_url", ""),
            branch=report.get("branch", ""),
            quality_score=quality_score,
            shared_at=shared_at
        ))
    
    return results


@app.post("/reports/{report_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(report_id: str, req: CommentRequest, user_id: str = Depends(get_user_id)):
    """Add a comment to a specific issue within a report."""
    # Require auth
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate text is non-empty after stripping
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Comment text cannot be empty")
    
    # Determine report owner (either current user or from share)
    from auth import get_db
    db = get_db()
    
    # Check if user owns the report
    history_path = f"history/{user_id}.json"
    is_owner = False
    report_owner_id = None
    
    if os.path.exists(history_path):
        with open(history_path) as f:
            history = json.load(f)
        report = next((r for r in history if r["id"] == report_id), None)
        if report:
            is_owner = True
            report_owner_id = user_id
    
    # If not owner, find owner via share
    if not is_owner:
        row = db.execute(
            """
            SELECT report_owner_id FROM report_shares
            WHERE report_id = ? AND recipient_id = ?
            """,
            (report_id, user_id)
        ).fetchone()
        if row:
            report_owner_id = row["report_owner_id"]
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify access using helper
    _assert_report_access(user_id, report_owner_id, report_id, db)
    
    # Insert comment
    comment_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    db.execute(
        """
        INSERT INTO issue_comments
        (comment_id, report_owner_id, report_id, author_id, file_path, issue_index, text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (comment_id, report_owner_id, report_id, user_id, req.file_path, req.issue_index, text, created_at)
    )
    db.commit()
    
    # Get author email
    author_row = db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    author_email = author_row["email"]
    
    return CommentResponse(
        comment_id=comment_id,
        report_id=report_id,
        author_email=author_email,
        file_path=req.file_path,
        issue_index=req.issue_index,
        text=text,
        created_at=created_at
    )


@app.get("/reports/{report_id}/comments", response_model=list[CommentResponse])
async def get_comments(report_id: str, user_id: str = Depends(get_user_id)):
    """Retrieve all comments for a report, ordered by created_at ascending."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from auth import get_db
    db = get_db()

    # Resolve report_owner_id
    report_owner_id = _resolve_report_owner(user_id, report_id, db)

    _assert_report_access(user_id, report_owner_id, report_id, db)

    rows = db.execute(
        """
        SELECT ic.comment_id, ic.report_id, ic.file_path, ic.issue_index,
               ic.text, ic.created_at, u.email as author_email
        FROM issue_comments ic
        JOIN users u ON ic.author_id = u.id
        WHERE ic.report_owner_id = ? AND ic.report_id = ?
        ORDER BY ic.created_at ASC
        """,
        (report_owner_id, report_id)
    ).fetchall()

    return [
        CommentResponse(
            comment_id=r["comment_id"],
            report_id=r["report_id"],
            author_email=r["author_email"],
            file_path=r["file_path"],
            issue_index=r["issue_index"],
            text=r["text"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@app.delete("/reports/{report_id}/comments/{comment_id}")
async def delete_comment(report_id: str, comment_id: str, user_id: str = Depends(get_user_id)):
    """Delete a comment. Only the comment author may delete their own comment."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from auth import get_db
    db = get_db()

    row = db.execute(
        "SELECT author_id FROM issue_comments WHERE comment_id = ? AND report_id = ?",
        (comment_id, report_id)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")

    if row["author_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.execute("DELETE FROM issue_comments WHERE comment_id = ?", (comment_id,))
    db.commit()

    return {"status": "deleted"}


# ── Assignment endpoints ───────────────────────────────────────────────────────

@app.post("/reports/{report_id}/assignments", response_model=AssignmentResponse)
async def create_assignment(report_id: str, req: AssignmentRequest, user_id: str = Depends(get_user_id)):
    """Assign an issue to a developer. Creates or replaces the assignment."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from auth import get_db
    db = get_db()

    report_owner_id = _resolve_report_owner(user_id, report_id, db)
    _assert_report_access(user_id, report_owner_id, report_id, db)

    # Look up assignee
    assignee_row = db.execute(
        "SELECT id FROM users WHERE email = ?", (req.assignee_email.lower(),)
    ).fetchone()
    if not assignee_row:
        raise HTTPException(status_code=404, detail=f"User not found: {req.assignee_email}")

    assignee_id = assignee_row["id"]
    assignment_id = str(uuid.uuid4())
    assigned_at = datetime.now(timezone.utc).isoformat()

    db.execute(
        """
        INSERT OR REPLACE INTO issue_assignments
        (id, report_owner_id, report_id, file_path, issue_index, assignee_id, assigner_id, assigned_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (assignment_id, report_owner_id, report_id, req.file_path, req.issue_index,
         assignee_id, user_id, assigned_at)
    )
    db.commit()

    assigner_row = db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()

    return AssignmentResponse(
        report_id=report_id,
        file_path=req.file_path,
        issue_index=req.issue_index,
        assignee_email=req.assignee_email,
        assigner_email=assigner_row["email"],
        assigned_at=assigned_at,
    )


@app.get("/reports/{report_id}/assignments", response_model=list[AssignmentResponse])
async def get_assignments(report_id: str, user_id: str = Depends(get_user_id)):
    """Retrieve all assignments for a report."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from auth import get_db
    db = get_db()

    report_owner_id = _resolve_report_owner(user_id, report_id, db)
    _assert_report_access(user_id, report_owner_id, report_id, db)

    rows = db.execute(
        """
        SELECT ia.report_id, ia.file_path, ia.issue_index, ia.assigned_at,
               a.email as assignee_email, r.email as assigner_email
        FROM issue_assignments ia
        JOIN users a ON ia.assignee_id = a.id
        JOIN users r ON ia.assigner_id = r.id
        WHERE ia.report_owner_id = ? AND ia.report_id = ?
        """,
        (report_owner_id, report_id)
    ).fetchall()

    return [
        AssignmentResponse(
            report_id=r["report_id"],
            file_path=r["file_path"],
            issue_index=r["issue_index"],
            assignee_email=r["assignee_email"],
            assigner_email=r["assigner_email"],
            assigned_at=r["assigned_at"],
        )
        for r in rows
    ]


@app.get("/my-assignments", response_model=list[AssignmentResponse])
async def get_my_assignments(user_id: str = Depends(get_user_id)):
    """Retrieve all issues assigned to the authenticated user, ordered by assigned_at descending."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from auth import get_db
    db = get_db()

    rows = db.execute(
        """
        SELECT ia.report_id, ia.file_path, ia.issue_index, ia.assigned_at,
               a.email as assignee_email, r.email as assigner_email
        FROM issue_assignments ia
        JOIN users a ON ia.assignee_id = a.id
        JOIN users r ON ia.assigner_id = r.id
        WHERE ia.assignee_id = ?
        ORDER BY ia.assigned_at DESC
        """,
        (user_id,)
    ).fetchall()

    return [
        AssignmentResponse(
            report_id=r["report_id"],
            file_path=r["file_path"],
            issue_index=r["issue_index"],
            assignee_email=r["assignee_email"],
            assigner_email=r["assigner_email"],
            assigned_at=r["assigned_at"],
        )
        for r in rows
    ]
