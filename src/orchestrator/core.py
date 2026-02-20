"""Core orchestrator - routes tasks, calls LLM (OpenAI, Claude, Ollama), has file/API access."""
from pathlib import Path
from typing import AsyncGenerator

from src.config import get_env, load_config
from src.message_bus import MessageBus
from src.agents.router import AgentRouter
from src.orchestrator.config_engine import ConfigEngine, load_skills
from src.models.cache import ResponseCache
from src.models.cost_tracker import CostTracker


class Orchestrator:
    """Main orchestrator agent - handles user messages and delegates to tools."""

    def __init__(self, project_root: Path | None = None):
        self.root = project_root or Path(__file__).parent.parent.parent
        self.settings, self.models_config = load_config(self.root)
        self.env = get_env(self.root)
        data_dir = self.root / self.settings.data_dir
        self.message_bus = MessageBus(data_dir / "agent_logs.db")
        self.output_dir = Path(self.settings.output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = self.root / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._model = self.models_config.routing.get("default", "gpt-4o-mini")
        self._router: AgentRouter | None = None
        self._cache = ResponseCache(data_dir / "response_cache.db", ttl_seconds=3600)
        self._cost_tracker = CostTracker(data_dir / "cost_log.db")
        from src.memory.store import MemoryStore
        self._memory = MemoryStore(data_dir)
        self._config_engine = ConfigEngine(self.root)

    @property
    def router(self) -> AgentRouter:
        if self._router is None:
            self._router = AgentRouter(self.root, self.message_bus)
        return self._router

    def _system_prompt(self) -> str:
        return """You are an AI orchestrator with access to the user's device. You can:
- Read and write files (you will receive tool outputs)
- Use external APIs when the user provides keys
- Execute tasks and respond helpfully

Rules:
- Do not send messages or make external API calls without user permission unless explicitly asked
- Be concise but helpful
- When writing files, use the output directory provided
- If you need to do something you cannot do, explain what's needed

The user will send you messages. Respond appropriately."""
    
    async def process(
        self, 
        user_message: str, 
        source: str = "user",
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Process a user message and yield response tokens (streaming)."""
        if self.settings.use_subagents:
            async for token in self.router.route(user_message, source=source):
                yield token
            return

        self.message_bus.log(source, "orchestrator", "user", user_message)
        context = ""
        try:
            facts = self._memory.search(user_message, n_results=3)
            if facts:
                context = "\nRelevant context:\n" + "\n".join(f["content"] for f in facts)
        except Exception:
            pass
        sys_prompt = self._system_prompt() + context
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_message},
        ]
        if self.settings.budget.enabled:
            daily = self._cost_tracker.get_daily_total()
            if daily >= self.settings.budget.daily_usd:
                full_response = f"Budget cap reached (daily ${daily:.2f}). Set budget.enabled: false or increase daily_usd."
                self.message_bus.log("orchestrator", source, "assistant", full_response)
                yield full_response
                return
        full_response = ""
        if not stream:
            cached = self._cache.get(self._model, messages)
            if cached:
                self.message_bus.log("orchestrator", source, "assistant", cached)
                yield cached
                return
        try:
            from src.models.llm_client import complete
            gen_or_resp = await complete(self.root, self._model, messages, stream=stream)
            if stream:
                async for token in gen_or_resp:
                    full_response += token
                    yield token
                inp_est = sum(len(m.get("content", "")) for m in messages) // 4
                out_est = len(full_response) // 4
                self._cost_tracker.log("orchestrator", self._model, max(1, inp_est), max(1, out_est))
            else:
                full_response = gen_or_resp or ""
                self._cost_tracker.log(
                    "orchestrator",
                    self._model,
                    sum(len(m.get("content", "")) for m in messages) // 4,
                    len(full_response) // 4,
                )
                self._cache.set(self._model, messages, full_response)
                yield full_response
        except Exception as e:
            from src.models.ollama_client import OllamaClient
            ollama = OllamaClient(self.root)
            if ollama.enabled:
                try:
                    full_response = await ollama.complete(
                        ollama.models[0] if ollama.models else "llama3.2",
                        user_message,
                        system=self._system_prompt(),
                    )
                    yield full_response
                except Exception as e2:
                    full_response = f"Cloud API error: {e}. Ollama fallback failed: {e2}"
                    yield full_response
            else:
                full_response = f"Error: {e}"
                yield full_response

        self.message_bus.log("orchestrator", source, "assistant", full_response)

    async def process_sync(self, user_message: str, source: str = "user") -> str:
        """Process without streaming; returns full response."""
        result = ""
        async for token in self.process(user_message, source, stream=False):
            result = token
        return result
