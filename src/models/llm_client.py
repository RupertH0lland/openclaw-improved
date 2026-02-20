"""Unified LLM client - routes to OpenAI, Anthropic (Claude), or Ollama based on model name.
Claude Code / Anthropic models use the same API. Use at your own risk."""
from src.config import get_env


def _is_claude(model: str) -> bool:
    return model.lower().startswith("claude")


async def complete(
    project_root,
    model: str,
    messages: list[dict[str, str]],
    stream: bool = True,
) -> AsyncGenerator[str, None] | str:
    """Complete with OpenAI, Anthropic (Claude), or raise. Yields tokens if stream=True."""
    env = get_env(project_root)
    if _is_claude(model):
        if not env.anthropic_api_key:
            raise ValueError("Anthropic/Claude API key not set. Run: python main.py setup")
        return await _anthropic_complete(env.anthropic_api_key, model, messages, stream)
    # Default: OpenAI
    if not env.openai_api_key:
        raise ValueError("OpenAI API key not set. Run: python main.py setup")
    return await _openai_complete(env.openai_api_key, model, messages, stream)


async def _openai_complete(api_key: str, model: str, messages: list[dict], stream: bool):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    if stream:
        stream_resp = await client.chat.completions.create(model=model, messages=messages, stream=True)
        async for chunk in stream_resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        resp = await client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content or ""


async def _anthropic_complete(api_key: str, model: str, messages: list[dict], stream: bool):
    import anthropic
    system = ""
    msgs = []
    for m in messages:
        if m.get("role") == "system":
            system = m.get("content", "")
        else:
            msgs.append({"role": m["role"], "content": m.get("content", "")})
    client = anthropic.AsyncAnthropic(api_key=api_key)
    if stream:
        async with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system or "You are helpful.",
            messages=msgs,
        ) as s:
            async for t in s.text_stream:
                yield t
    else:
        r = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system or "You are helpful.",
            messages=msgs,
        )
        return (r.content[0].text if r.content else "") or ""
