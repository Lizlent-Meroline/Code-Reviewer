# Deployment Guide

## Render Deployment Issues & Solutions

### 1. WebSocket Connection Failures

**Error:** `WebSocket connection to 'wss://...' failed`

**Cause:** Render's free tier may not support WebSockets, or requires specific configuration.

**Solution:** WebSocket is optional for progress updates. The app works without it. To suppress the error:
- The frontend already handles WebSocket failures gracefully with `console.warn`
- Progress updates will be disabled but analysis still works

**Alternative:** Upgrade to Render's paid tier which supports WebSockets.

---

### 2. 500 Error on `/analyze`

**Error:** `Failed to load resource: the server responded with a status of 500 ()`

**Common Causes:**
1. **Missing Git** — Render needs Git installed to clone repos
2. **Disk space** — Ephemeral filesystem may run out of space
3. **Memory limits** — Free tier has 512MB RAM limit
4. **Missing dependencies** — Check all packages are in requirements.txt

**Solutions:**

#### Check Render Logs
1. Go to your Render dashboard
2. Click on your service
3. View "Logs" tab to see the actual error

#### Add Git to Render
Add to your `render.yaml` or use a build command:
```yaml
services:
  - type: web
    name: code-reviewer
    env: python
    buildCommand: "apt-get update && apt-get install -y git && pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

#### Increase Memory (Paid Tier)
Free tier: 512MB RAM  
Starter tier: 2GB RAM (handles larger repos)

#### Use Shallow Clones
The app already uses `--depth=1` for faster, smaller clones.

---

### 3. Slow Performance

**Causes:**
- **Cold starts** — Free tier spins down after 15 minutes of inactivity
- **Limited CPU** — Free tier has shared CPU
- **GitHub API rate limits** — 60 requests/hour without token

**Solutions:**

#### Add GitHub Token
Set environment variable in Render dashboard:
```
GITHUB_TOKEN=your_github_personal_access_token
```
This increases rate limit to 5000 requests/hour.

#### Keep Service Warm
Use a service like UptimeRobot to ping your health endpoint every 5 minutes:
```
https://your-app.onrender.com/health
```

#### Upgrade to Paid Tier
- Faster CPU
- No cold starts
- More memory

---

### 4. Missing Favicon (404)

**Error:** `Failed to load resource: the server responded with a status of 404 () /favicon.ico`

**Solution:** Add a favicon.ico file to your project root or serve it from the static directory.

---

## Environment Variables

Set these in Render dashboard → Environment:

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | Recommended | Secret key for JWT tokens (default: insecure) |
| `GITHUB_TOKEN` | Optional | GitHub personal access token for higher rate limits |
| `PORT` | Auto-set | Render sets this automatically |

---

## Recommended Render Configuration

### render.yaml
```yaml
services:
  - type: web
    name: github-code-reviewer
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: JWT_SECRET
        generateValue: true
      - key: GITHUB_TOKEN
        sync: false
```

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Troubleshooting Checklist

- [ ] Check Render logs for actual error messages
- [ ] Verify all dependencies in requirements.txt
- [ ] Set JWT_SECRET environment variable
- [ ] Add GITHUB_TOKEN for better rate limits
- [ ] Test `/health` endpoint works
- [ ] Try analyzing a small repo first
- [ ] Check disk space isn't full (Render logs will show)
- [ ] Verify Git is available in the container

---

## Performance Optimization

1. **Use caching** — The app caches file analysis results
2. **Analyze smaller repos first** — Test with repos < 100 files
3. **Use branch switching** — Faster than full re-analysis
4. **Clear cache periodically** — `DELETE /cache` endpoint
5. **Monitor memory usage** — Check Render metrics

---

## Production Recommendations

1. **Use paid tier** for production workloads
2. **Set up monitoring** with UptimeRobot or similar
3. **Add error tracking** like Sentry
4. **Use PostgreSQL** instead of SQLite for multi-instance deployments
5. **Add rate limiting** to prevent abuse
6. **Compile Tailwind CSS** instead of using CDN (see Tailwind docs)
7. **Add Redis** for distributed caching

---

## Getting Help

If issues persist:
1. Check Render logs first
2. Test locally with `uvicorn main:app --reload`
3. Verify the `/health` endpoint returns `{"status": "ok"}`
4. Try a minimal test repo: `https://github.com/octocat/Hello-World`
