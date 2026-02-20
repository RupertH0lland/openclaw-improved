"""Message bus - logs all user <-> orchestrator and inter-agent communications to SQLite."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class MessageBus:
    """Persistent log of messages for dashboard display."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)
            """)

    def log(self, source: str, target: str, role: str, content: str, metadata: dict | None = None) -> None:
        """Log a message."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO messages (timestamp, source, target, role, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    source,
                    target,
                    role,
                    content,
                    json.dumps(metadata) if metadata else None,
                ),
            )

    def get_recent(self, limit: int = 100, source: str | None = None) -> list[dict]:
        """Get recent messages for dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, timestamp, source, target, role, content, metadata
                FROM messages
                WHERE (? IS NULL OR source = ?)
                ORDER BY id DESC
                LIMIT ?
                """,
                (source, source, limit),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "source": r["source"],
                "target": r["target"],
                "role": r["role"],
                "content": r["content"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
            }
            for r in rows
        ]
