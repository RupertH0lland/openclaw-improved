"""LLM-backed sub-agent - uses OpenAI/Anthropic based on routing."""
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from src.agents.base import BaseAgent
from src.config import load_config, get_env
from src.message_bus import MessageBus


class LLMAgent(BaseAgent):
    """Sub-agent that uses an LLM. Task type determines model via routing."""

    def __init__(self, agent_id: str, message_bus: MessageBus, project_root):
        super().__init__(agent_id, message_bus)
        self.root = project_root
        self._settings, self._models = load_config(project_root)
        self._env = get_env(self.project_root)
        self._client: AsyncOpenAI | None = None
        self._task_type = "default"

    def override_task_type(self, task_type: str) -> None:
        self._task_type = task_type

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._env.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self._client = AsyncOpenAI(api_key=self._env.openai_api_key)
        return self._client

    def _get_model(self) -> str:
        return self._models.routing.get(self._task_type, self._models.routing.get("default", "gpt-4o-mini"))

    async def run(self, task: str, context: dict[str, Any] | None = None) -> AsyncGenerator[str, None]:
        self._status = "running"
        try:
            model = self._get_model()
            self._log("orchestrator", "system", f"Running task (model={model})", {"task_type": self._task_type})
            full = ""
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful sub-agent. Complete the task concisely."},
                    {"role": "user", "content": task},
                ],
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    tok = chunk.choices[0].delta.content
                    full += tok
                    yield tok
            self._log("orchestrator", "assistant", full)
        finally:
            self._status = "idle"
