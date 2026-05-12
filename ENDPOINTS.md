# API Endpoints

Base URL: `http://localhost:8000`

---

## Authentication

### `POST /register`
Create a new user account.

**Request:**
```json
{ "email": "user@example.com", "password": "yourpassword" }
```
**Response:**
```json
{ "token": "<jwt>", "email": "user@example.com" }
```
**Errors:** `400` — Email already registered.

---

### `POST /login`
Sign in and receive a JWT token.

**Request:**
```json
{ "email": "user@example.com", "password": "yourpassword" }
```
**Response:**
```json
{ "token": "<jwt>", "email": "user@example.com" }
```
**Errors:** `401` — Invalid email or password.

---

## Analysis

### `POST /analyze`
Analyze a GitHub repository. Saves to history if authenticated.

**Headers (optional):** `Authorization: Bearer <token>`

**Request:**
```json
{
  "url": "https://github.com/user/repo",
  "branch": "main",
  "client_id": "client_abc123"
}
```
- `branch` — optional, defaults to repo default branch
- `client_id` — optional, used for WebSocket progress updates

**Response:**
```json
{
  "repo_url": "...",
  "branch": "main",
  "branches": [...],
  "meta": { "full_name": "...", "stars": 0, "forks": 0, ... },
  "tags": [...],
  "commits": [...],
  "pull_requests": [...],
  "issues": [...],
  "summary": { "total": 0, "code": 0, "docs": 0, "other": 0, "issues": 0 },
  "code": [...],
  "docs": [...],
  "other": [...]
}
```

---

### `POST /switch-branch`
Switch to a different branch and re-analyze files. Skips GitHub API calls.

**Request:**
```json
{ "url": "https://github.com/user/repo", "branch": "feature-x" }
```
**Response:** Same structure as `/analyze`

---

### `POST /branches`
Get all branches for a repository without full analysis.

**Request:**
```json
{ "url": "https://github.com/user/repo" }
```
**Response:**
```json
{
  "branches": [
    { "name": "main", "is_default": true, "merged": true, "sha": "abc1234" }
  ]
}
```

---

### `POST /analyze/pr-diff`
Analyze only the files changed in a pull request.

**Headers (optional):** `Authorization: Bearer <token>`

**Request:**
```json
{
  "url": "https://github.com/user/repo",
  "base_branch": "main",
  "compare_branch": "feature-x",
  "client_id": "client_abc123"
}
```
**Response:**
```json
{
  "repo_url": "...",
  "base_branch": "main",
  "compare_branch": "feature-x",
  "diff_stats": { "files_changed": 3, "insertions": 45, "deletions": 12 },
  "summary": { "files_changed": 3, "code_files": 2, "issues": 5 },
  "files": [...]
}
```

---

## History

### `GET /history`
Get analysis history for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": "2024-01-01T00:00:00",
    "repo_url": "https://github.com/user/repo",
    "branch": "main",
    "summary": { "total": 100, "code": 80, "docs": 10, "other": 10, "issues": 5 },
    "meta": { ... }
  }
]
```
Returns `[]` if not authenticated.

---

### `DELETE /history`
Clear all history for the authenticated user. Also cascade-deletes all associated shares, comments, and assignments.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{ "status": "cleared" }
```

---

## Analytics

### `GET /analytics/scores`
Get quality scores for all history entries of the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[{ "id": "2024-01-01T00:00:00", "repo_url": "...", "branch": "main", "quality_score": 87, "timestamp": "..." }]
```

---

### `GET /analytics/trends?repo_url=<url>`
Get quality score trend over time for a specific repository.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[{ "timestamp": "2024-01-01T00:00:00", "branch": "main", "quality_score": 87 }]
```

---

### `GET /analytics/leaderboard`
Get repository leaderboard ranked by latest quality score.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[{ "repo_url": "...", "repo_name": "user/repo", "latest_quality_score": 92, "analyses_count": 5, "last_analyzed": "2024-01-01T00:00:00" }]
```

---

## Team Collaboration

All collaboration endpoints require authentication (`Authorization: Bearer <token>`).  
`{report_id}` is the ISO timestamp `id` from a history entry (e.g. `2024-01-15T10:30:00`).

---

### `POST /reports/{report_id}/share`
Share a report with one or more team members by email.

**Request:**
```json
{ "emails": ["alice@example.com", "bob@example.com"] }
```
**Response:**
```json
[{ "report_id": "...", "recipient_email": "alice@example.com", "shared_at": "..." }]
```
**Errors:** `401` — not authenticated. `404` — report not found or email not registered (body identifies the email). Duplicate shares are silently ignored.

---

### `DELETE /reports/{report_id}/share/{recipient_email}`
Revoke a share. Only the report owner may call this.

**Response:**
```json
{ "status": "revoked" }
```
**Errors:** `401` — not authenticated. `403` — caller is not the report owner. `404` — share not found.

---

### `GET /shared-with-me`
List all reports shared with the authenticated user.

**Response:**
```json
[{
  "report_id": "...",
  "owner_email": "carol@example.com",
  "repo_url": "https://github.com/org/repo",
  "branch": "main",
  "quality_score": 87,
  "shared_at": "..."
}]
```
**Errors:** `401` — not authenticated.

---

### `POST /reports/{report_id}/comments`
Add a comment to a specific issue within a report.

**Request:**
```json
{ "file_path": "src/main.py", "issue_index": 2, "text": "This looks risky." }
```
**Response `201`:**
```json
{
  "comment_id": "<uuid>",
  "report_id": "...",
  "author_email": "alice@example.com",
  "file_path": "src/main.py",
  "issue_index": 2,
  "text": "This looks risky.",
  "created_at": "..."
}
```
**Errors:** `401` — not authenticated. `403` — no access to report. `422` — empty or whitespace-only text.

---

### `GET /reports/{report_id}/comments`
Retrieve all comments for a report, ordered by `created_at` ascending.

**Response:** Array of comment objects (same shape as POST response).

**Errors:** `401` — not authenticated. `403` — no access to report.

---

### `DELETE /reports/{report_id}/comments/{comment_id}`
Delete a comment. Only the comment author may delete their own comment.

**Response:**
```json
{ "status": "deleted" }
```
**Errors:** `401` — not authenticated. `403` — caller is not the comment author. `404` — comment not found.

---

### `POST /reports/{report_id}/assignments`
Assign a specific issue to a developer. Creates or replaces the assignment for the same `(file_path, issue_index)` pair.

**Request:**
```json
{ "file_path": "src/main.py", "issue_index": 2, "assignee_email": "bob@example.com" }
```
**Response:**
```json
{
  "report_id": "...",
  "file_path": "src/main.py",
  "issue_index": 2,
  "assignee_email": "bob@example.com",
  "assigner_email": "alice@example.com",
  "assigned_at": "..."
}
```
**Errors:** `401` — not authenticated. `403` — no access to report. `404` — assignee email not registered.

---

### `GET /reports/{report_id}/assignments`
Retrieve all assignments for a report.

**Response:** Array of assignment objects (same shape as POST response).

**Errors:** `401` — not authenticated. `403` — no access to report.

---

### `GET /my-assignments`
Retrieve all issues assigned to the authenticated user, ordered by `assigned_at` descending.

**Response:** Array of assignment objects (same shape as POST /assignments response).

**Errors:** `401` — not authenticated.

---

### `POST /export/json`
Export analysis report as a downloadable JSON file.

**Request:** Full analysis result object (from `/analyze` response)

**Response:** `application/json` file download — `analysis-report.json`

---

### `POST /export/pdf`
Export analysis report as a downloadable PDF file.

**Request:** Full analysis result object (from `/analyze` response)

**Response:** `application/pdf` file download — `analysis-report.pdf`

---

## Cache

### `DELETE /cache`
Clear all cached file analysis results.

**Response:**
```json
{ "status": "cache cleared" }
```

---

## WebSocket

### `WS /ws/{client_id}`
Real-time progress updates during analysis.

**Connect:** `ws://localhost:8000/ws/<client_id>`

**Messages received:**
```json
{ "stage": "cloning",   "message": "Cloning repository...",      "progress": 0  }
{ "stage": "scanning",  "message": "Found 1234 files...",         "progress": 5  }
{ "stage": "analyzing", "message": "Analyzing... 500/1234",       "progress": 45, "total": 1234, "completed": 500 }
{ "stage": "fetching",  "message": "Fetching repository metadata...", "progress": 90 }
{ "stage": "complete",  "message": "Analysis complete!",          "progress": 100 }
```

---

## Other

### `GET /`
Serve the frontend HTML page.

### `GET /health`
Health check.

**Response:**
```json
{ "status": "ok" }
```

---

## Authentication Notes

- JWT tokens expire after **30 days**
- Pass token as: `Authorization: Bearer <token>`
- All auth-required endpoints return empty/no-op if token is missing (guest mode)
- Set `JWT_SECRET` env var for persistent sessions across server restarts

## Rate Limiting

GitHub API is used without a token (60 requests/hour limit). For heavy usage, set:
```bash
export GITHUB_TOKEN="your_token"
```
