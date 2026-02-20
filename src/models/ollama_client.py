"""Ollama client - optional local model backend."""
import httpx
from pathlib import Path

from src.config import load_config


class OllamaClient:
    """Optional Ollama API client. Disabled by default."""

    def __init__(self, project_root: Path):
        _, models_config = load_config(project_root)
        self.enabled = models_config.ollama.enabled
        self.base_url = models_config.ollama.base_url
        self.models = models_config.ollama.models or []

    async def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def complete(self, model: str, prompt: str, system: str = "") -> str:
        """Generate completion from Ollama."""
        if not self.enabled:
            raise ValueError("Ollama is disabled")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
        return data.get("message", {}).get("content", "")
