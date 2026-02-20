"""Proactive scheduler - heartbeat, task priority queues, CRON management."""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class ProactiveScheduler:
    """Heartbeat every 30 min, task priority queue (user > proactive > cron), CRON management."""

    def __init__(self, project_root: Path, on_heartbeat: Callable[[], Awaitable[None]]):
        self.root = project_root
        self.on_heartbeat = on_heartbeat
        self._scheduler = AsyncIOScheduler()
        self._task_queue: list[tuple[int, str, Callable]] = []  # (priority, id, coro)
        self._last_heartbeat: datetime | None = None

    def start(self) -> None:
        """Start heartbeat (every 30 min)."""
        self._scheduler.add_job(
            self._heartbeat,
            IntervalTrigger(minutes=30),
            id="heartbeat",
        )
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown()

    async def _heartbeat(self) -> None:
        self._last_heartbeat = datetime.utcnow()
        await self.on_heartbeat()

    def get_last_heartbeat(self) -> datetime | None:
        return self._last_heartbeat

    def add_cron(self, expr: str, cmd: str) -> bool:
        """Add cron job (Unix only). Returns True on success."""
        try:
            import sys
            if sys.platform == "win32":
                return False
            import subprocess
            current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            lines = current.stdout.splitlines() if current.returncode == 0 else []
            lines.append(f"{expr} {cmd}")
            subprocess.run(["crontab", "-"], input="\n".join(lines), text=True, check=True)
            return True
        except Exception:
            return False

    def list_cron(self) -> list[str]:
        """List current cron jobs (Unix only)."""
        try:
            import sys
            if sys.platform == "win32":
                return []
            import subprocess
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            return r.stdout.strip().splitlines() if r.returncode == 0 else []
        except Exception:
            return []
