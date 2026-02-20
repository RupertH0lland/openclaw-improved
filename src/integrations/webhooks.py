"""Webhooks - HTTP endpoint for external triggers (CI, GitHub, Zapier). Opt-in."""
from pathlib import Path
from typing import Callable, Awaitable

# Webhook handlers registered at runtime
_handlers: list[Callable[[dict], Awaitable[None]]] = []


def register_handler(fn: Callable[[dict], Awaitable[None]]) -> None:
    _handlers.append(fn)


async def dispatch(payload: dict) -> None:
    for h in _handlers:
        await h(payload)
