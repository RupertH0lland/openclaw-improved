"""Scheduled digest - daily summary of AI activity."""
from pathlib import Path
from datetime import datetime


async def generate_digest(project_root: Path) -> str:
    """Generate daily digest: what the AI did, files changed, pending tasks."""
    data_dir = project_root / "data"
    lines = [f"Digest for {datetime.utcnow().date()}"]
    try:
        import sqlite3
        db = data_dir / "agent_logs.db"
        if db.exists():
            with sqlite3.connect(db) as conn:
                cursor = conn.execute(
                    """SELECT COUNT(*) FROM messages WHERE date(timestamp) = date('now')"""
                )
                count = cursor.fetchone()[0]
                lines.append(f"- Messages today: {count}")
    except Exception:
        pass
    output_dir = project_root / "data" / "output"
    if output_dir.exists():
        files = list(output_dir.rglob("*"))
        files = [f for f in files if f.is_file()]
        lines.append(f"- Output files: {len(files)}")
    return "\n".join(lines)
