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
Clear all history for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{ "status": "cleared" }
```

---

## Export

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
