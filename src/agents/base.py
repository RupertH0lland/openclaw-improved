"""Base agent - sub-agents that can communicate with each other."""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from src.message_bus import MessageBus


class BaseAgent(ABC):
    """Base class for sub-agents. Agents can send messages to each other via the message bus."""

    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self._status = "idle"

    @property
    def status(self) -> str:
        return self._status

    def _log(self, target: str, role: str, content: str, metadata: dict | None = None) -> None:
        """Log inter-agent communication."""
        self.message_bus.log(self.agent_id, target, role, content, metadata)

    @abstractmethod
    async def run(self, task: str, context: dict[str, Any] | None = None) -> AsyncGenerator[str, None]:
        """Execute a task and yield response tokens (streaming)."""
        pass
