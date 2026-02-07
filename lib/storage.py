"""
Storage abstraction for auth and article logs.
Supports JSON files (local dev) and Upstash Redis (Vercel deployment).
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class StorageBackend(ABC):
    """Abstract storage backend for users, sessions, and article logs."""

    @abstractmethod
    def get_user(self, username: str) -> str | None:
        """Get password hash for username, or None."""
        pass

    @abstractmethod
    def set_user(self, username: str, password_hash: str) -> None:
        """Store user with password hash."""
        pass

    @abstractmethod
    def user_exists(self, username: str) -> bool:
        """Check if username exists."""
        pass

    @abstractmethod
    def get_all_users(self) -> dict[str, str]:
        """Get all users as {username: password_hash}."""
        pass

    @abstractmethod
    def set_session(self, session_id: str, username: str) -> None:
        """Store session."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> str | None:
        """Get username for session, or None."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Remove session."""
        pass

    @abstractmethod
    def get_log(self, username: str) -> list:
        """Get article log for user."""
        pass

    @abstractmethod
    def save_log(self, username: str, log: list) -> None:
        """Save article log for user."""
        pass


class JsonStorage(StorageBackend):
    """File-based JSON storage for local development."""

    def __init__(self):
        base = Path(__file__).resolve().parent.parent
        self._data_dir = base / "data"
        self._users_file = self._data_dir / "users.json"
        self._sessions_file = self._data_dir / "sessions.json"
        self._logs_dir = self._data_dir / "logs"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path, default: dict | list) -> dict | list:
        if not path.exists():
            return default
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default

    def _save_json(self, path: Path, data: dict | list):
        self._ensure_dirs()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def get_user(self, username: str) -> str | None:
        users = self._load_json(self._users_file, {})
        return users.get(username)

    def set_user(self, username: str, password_hash: str) -> None:
        users = self._load_json(self._users_file, {})
        users[username] = password_hash
        self._save_json(self._users_file, users)

    def user_exists(self, username: str) -> bool:
        return self.get_user(username) is not None

    def get_all_users(self) -> dict[str, str]:
        return self._load_json(self._users_file, {})

    def set_session(self, session_id: str, username: str) -> None:
        sessions = self._load_json(self._sessions_file, {})
        sessions[session_id] = username
        self._save_json(self._sessions_file, sessions)

    def get_session(self, session_id: str) -> str | None:
        sessions = self._load_json(self._sessions_file, {})
        return sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        sessions = self._load_json(self._sessions_file, {})
        sessions.pop(session_id, None)
        self._save_json(self._sessions_file, sessions)

    def get_log(self, username: str) -> list:
        log_path = self._logs_dir / f"{username}.json"
        data = self._load_json(log_path, [])
        return data if isinstance(data, list) else []

    def save_log(self, username: str, log: list) -> None:
        if not isinstance(log, list):
            return
        log_path = self._logs_dir / f"{username}.json"
        self._save_json(log_path, log)


class RedisStorage(StorageBackend):
    """Upstash Redis storage for Vercel deployment."""

    USERS_KEY = "wiki:users"
    SESSIONS_KEY = "wiki:sessions"

    def __init__(self):
        # Support both Vercel KV and Upstash env var names
        url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not url or not token:
            raise ValueError("Redis requires KV_REST_API_URL/KV_REST_API_TOKEN or UPSTASH_REDIS_REST_URL/UPSTASH_REDIS_REST_TOKEN")
        from upstash_redis import Redis
        self._redis = Redis(url=url, token=token)

    def get_user(self, username: str) -> str | None:
        val = self._redis.hget(self.USERS_KEY, username)
        return val if val is not None else None

    def set_user(self, username: str, password_hash: str) -> None:
        self._redis.hset(self.USERS_KEY, username, password_hash)

    def user_exists(self, username: str) -> bool:
        return self.get_user(username) is not None

    def get_all_users(self) -> dict[str, str]:
        raw = self._redis.hgetall(self.USERS_KEY)
        if not raw:
            return {}
        return {k: v for k, v in raw.items()}

    def set_session(self, session_id: str, username: str) -> None:
        self._redis.hset(self.SESSIONS_KEY, session_id, username)

    def get_session(self, session_id: str) -> str | None:
        val = self._redis.hget(self.SESSIONS_KEY, session_id)
        return val if val is not None else None

    def delete_session(self, session_id: str) -> None:
        self._redis.hdel(self.SESSIONS_KEY, session_id)

    def get_log(self, username: str) -> list:
        key = f"wiki:log:{username}"
        val = self._redis.get(key)
        if not val:
            return []
        try:
            data = json.loads(val)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def save_log(self, username: str, log: list) -> None:
        if not isinstance(log, list):
            return
        key = f"wiki:log:{username}"
        self._redis.set(key, json.dumps(log))


def _get_storage() -> StorageBackend:
    """Return storage backend based on environment."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        return RedisStorage()
    return JsonStorage()


def get_storage() -> StorageBackend:
    """Return the configured storage backend."""
    return _get_storage()
