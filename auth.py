"""
Basic auth and article log storage for Random Technical Wiki.
Uses JSON files for users, sessions, and per-user article logs.
"""

import hashlib
import json
import os
import secrets
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
LOGS_DIR = DATA_DIR / "logs"
SESSION_COOKIE = "wiki_session"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def _save_json(path: Path, data: dict | list):
    _ensure_data_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def register(username: str, password: str) -> str | None:
    """Register a new user. Returns error message or None on success."""
    if not username or not password:
        return "Username and password required"
    username = username.strip()
    if not username:
        return "Username required"
    if len(username) < 2:
        return "Username too short"
    if len(password) < 4:
        return "Password must be at least 4 characters"
    users = _load_json(USERS_FILE, {})
    if username in users:
        return "Username already taken"
    users[username] = _hash_password(password)
    _save_json(USERS_FILE, users)
    return None


def login(username: str, password: str) -> str | None:
    """Login. Returns session_id on success, error message on failure."""
    if not username or not password:
        return None
    users = _load_json(USERS_FILE, {})
    pw_hash = _hash_password(password)
    if users.get(username) != pw_hash:
        return None
    session_id = secrets.token_urlsafe(32)
    sessions = _load_json(SESSIONS_FILE, {})
    sessions[session_id] = username
    _save_json(SESSIONS_FILE, sessions)
    return session_id


def verify_session(session_id: str | None) -> str | None:
    """Verify session. Returns username if valid, else None."""
    if not session_id:
        return None
    sessions = _load_json(SESSIONS_FILE, {})
    return sessions.get(session_id)


def logout(session_id: str | None):
    """Remove session."""
    if not session_id:
        return
    sessions = _load_json(SESSIONS_FILE, {})
    sessions.pop(session_id, None)
    _save_json(SESSIONS_FILE, sessions)


def get_log(username: str) -> list:
    """Get article log for user."""
    log_path = LOGS_DIR / f"{username}.json"
    data = _load_json(log_path, [])
    return data if isinstance(data, list) else []


def save_log(username: str, log: list):
    """Save article log for user."""
    if not isinstance(log, list):
        return
    log_path = LOGS_DIR / f"{username}.json"
    _save_json(log_path, log)
