"""Response cache - hash-based cache for LLM responses to reduce cost."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path


class ResponseCache:
    """Cache LLM responses by prompt hash. Configurable TTL."""

    def __init__(self, db_path: Path, ttl_seconds: int = 3600):
        self.db_path = db_path
        self.ttl = ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

    def _hash(self, model: str, messages: list) -> str:
        data = json.dumps({"model": model, "messages": messages}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def get(self, model: str, messages: list) -> str | None:
        key = self._hash(model, messages)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value, created_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if not row:
            return None
        value, created = row
        if self.ttl > 0 and (time.time() - created) > self.ttl:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            return None
        return value

    def set(self, model: str, messages: list, response: str) -> None:
        key = self._hash(model, messages)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
                (key, response, time.time()),
            )
