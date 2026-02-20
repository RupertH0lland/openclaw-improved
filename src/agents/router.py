"""Agent router - classifies tasks and routes to appropriate sub-agents or orchestrator."""
from pathlib import Path
from typing import Any, AsyncGenerator

from src.message_bus import MessageBus
from src.agents.workers.llm_worker import LLMAgent


class AgentRouter:
    """Routes tasks to sub-agents. Logs all communications for dashboard."""

    def __init__(self, project_root: Path, message_bus: MessageBus):
        self.root = project_root
        self.message_bus = message_bus
        self._agents: dict[str, LLMAgent] = {}
        self._ensure_default_agent()

    def _ensure_default_agent(self) -> None:
        if "default" not in self._agents:
            self._agents["default"] = LLMAgent("default", self.message_bus, self.root)

    def _classify_task(self, task: str) -> str:
        """Simple rule-based classification. Can be replaced with LLM classifier."""
        t = task.lower()
        if "classify" in t or "category" in t:
            return "classify"
        if "summar" in t or "summary" in t:
            return "summarize"
        if "code" in t or "program" in t or "implement" in t:
            return "code_gen"
        if "reason" in t or "analyze" in t or "explain why" in t:
            return "reasoning"
        return "default"

    async def route(self, task: str, source: str = "user", context: dict | None = None) -> AsyncGenerator[str, None]:
        """Route task to appropriate agent and stream response."""
        task_type = self._classify_task(task)
        self.message_bus.log(source, "router", "user", task, {"task_type": task_type})
        agent = self._agents["default"]
        agent.override_task_type(task_type)
        full = ""
        async for token in agent.run(task, context):
            full += token
            yield token
        self.message_bus.log("router", source, "assistant", full)
