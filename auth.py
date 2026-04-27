"""
Self-contained auth: SQLite users, bcrypt passwords, JWT sessions.
"""
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Header

DB_PATH    = "users.db"
JWT_SECRET = os.getenv("JWT_SECRET", "code-reviewer-default-secret-change-in-production")
JWT_EXPIRY = 30  # days


def get_db():
    """Get SQLite database connection with row factory."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Initialize SQLite database with users table."""
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       TEXT PRIMARY KEY,
                email    TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created  TEXT NOT NULL
            )
        """)


init_db()


def hash_password(plain: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_user(email: str, password: str) -> dict:
    """Create new user account with hashed password."""
    user_id = str(uuid.uuid4())
    hashed  = hash_password(password)
    with get_db() as con:
        con.execute(
            "INSERT INTO users (id, email, password, created) VALUES (?, ?, ?, ?)",
            (user_id, email.lower(), hashed, datetime.now(timezone.utc).isoformat())
        )
    return {"id": user_id, "email": email}


def authenticate(email: str, password: str) -> Optional[dict]:
    """Authenticate user with email and password."""
    with get_db() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    if row and verify_password(password, row["password"]):
        return {"id": row["id"], "email": row["email"]}
    return None


def make_token(user_id: str, email: str) -> str:
    """Generate JWT token for authenticated user."""
    payload = {
        "sub":   user_id,
        "email": email,
        "exp":   datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_user_id(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Dependency: extracts user_id from Bearer token, or None for guests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
