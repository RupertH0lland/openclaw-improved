"""Cost tracker - token usage and spend per request/agent."""
import sqlite3
from datetime import datetime
from pathlib import Path

# Approximate costs per 1K tokens (as of 2024)
MODEL_COSTS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


class CostTracker:
    """Track token usage and cost per request."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def log(
        self,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        costs = MODEL_COSTS.get(model, {"input": 0.001, "output": 0.002})
        cost = (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO cost_log (timestamp, agent_id, model, input_tokens, output_tokens, cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), agent_id, model, input_tokens, output_tokens, cost),
            )
        return cost

    def get_daily_total(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(cost_usd), 0) FROM cost_log
                   WHERE date(timestamp) = date('now')"""
            ).fetchone()
        return row[0] if row else 0.0

    def get_monthly_total(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(cost_usd), 0) FROM cost_log
                   WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')"""
            ).fetchone()
        return row[0] if row else 0.0
