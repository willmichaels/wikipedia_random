"""
Basic auth and article log storage for Random Technical Wiki.
Uses pluggable storage backend (JSON files or Redis).
"""

import hashlib
import secrets

from lib.storage import get_storage

SESSION_COOKIE = "wiki_session"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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
    storage = get_storage()
    if storage.user_exists(username):
        return "Username already taken"
    storage.set_user(username, _hash_password(password))
    return None


def login(username: str, password: str) -> str | None:
    """Login. Returns session_id on success, error message on failure."""
    if not username or not password:
        return None
    storage = get_storage()
    pw_hash = _hash_password(password)
    if storage.get_user(username) != pw_hash:
        return None
    session_id = secrets.token_urlsafe(32)
    storage.set_session(session_id, username)
    return session_id


def verify_session(session_id: str | None) -> str | None:
    """Verify session. Returns username if valid, else None."""
    if not session_id:
        return None
    return get_storage().get_session(session_id)


def logout(session_id: str | None):
    """Remove session."""
    if not session_id:
        return
    get_storage().delete_session(session_id)


def get_log(username: str) -> list:
    """Get article log for user."""
    return get_storage().get_log(username)


def save_log(username: str, log: list):
    """Save article log for user."""
    if not isinstance(log, list):
        return
    get_storage().save_log(username, log)
