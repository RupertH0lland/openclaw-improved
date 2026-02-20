"""Dashboard API - shared backend for chat and message log."""
from pathlib import Path

from src.config import load_config
from src.orchestrator.core import Orchestrator
from src.message_bus import MessageBus


def get_orchestrator(project_root: Path) -> Orchestrator:
    """Get orchestrator instance for dashboard."""
    return Orchestrator(project_root)


def get_message_bus(project_root: Path) -> MessageBus:
    """Get message bus for dashboard."""
    settings, _ = load_config(project_root)
    data_dir = project_root / settings.data_dir
    return MessageBus(data_dir / "agent_logs.db")
