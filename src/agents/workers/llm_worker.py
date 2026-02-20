"""LLM-backed sub-agent - uses OpenAI or Claude based on routing."""
from typing import Any, AsyncGenerator

from src.agents.base import BaseAgent
from src.config import load_config
from src.message_bus import MessageBus
from src.models.llm_client import complete


class LLMAgent(BaseAgent):
    """Sub-agent that uses an LLM. Task type determines model via routing."""

    def __init__(self, agent_id: str, message_bus: MessageBus, project_root):
        super().__init__(agent_id, message_bus)
        self.root = project_root
        self._settings, self._models = load_config(project_root)
        self._task_type = "default"

    def override_task_type(self, task_type: str) -> None:
        self._task_type = task_type

    def _get_model(self) -> str:
        return self._models.routing.get(self._task_type, self._models.routing.get("default", "gpt-4o-mini"))

    async def run(self, task: str, context: dict[str, Any] | None = None) -> AsyncGenerator[str, None]:
        self._status = "running"
        try:
            model = self._get_model()
            self._log("orchestrator", "system", f"Running task (model={model})", {"task_type": self._task_type})
            full = ""
            messages = [
                {"role": "system", "content": "You are a helpful sub-agent. Complete the task concisely."},
                {"role": "user", "content": task},
            ]
            gen = await complete(self.root, model, messages, stream=True)
            async for tok in gen:
                full += tok
                yield tok
            self._log("orchestrator", "assistant", full)
        finally:
            self._status = "idle"
