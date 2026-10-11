"""Provider-agnostic LLM layer: structured calls and web research for OpenAI or Anthropic.

The rest of the app only uses `structured()`, `web_research()` and `LLMError`, so the
provider is a configuration choice (LLM_PROVIDER in .env), not a code change.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from .config import EFFORT, MODEL, PROVIDER

T = TypeVar("T", bound=BaseModel)

RESEARCH_SYSTEM = ("You are a market researcher for automotive product management. Use web search to find "
                   "recent, trustworthy evidence (competitor offers, reviews, market and technology trends). "
                   "Prefer primary and reputable sources, state publication dates when known, and say clearly "
                   "when evidence is thin or contradictory. Be concise: max ~200 words.")


class LLMError(RuntimeError):
    pass


def structured(system: str, user: str, schema: type[T], effort: str = EFFORT, max_tokens: int = 64000) -> tuple[T, dict]:
    """One call returning a validated pydantic object plus usage metadata."""
    if PROVIDER == "anthropic":
        return _anthropic_structured(system, user, schema, effort, max_tokens)
    return _openai_structured(system, user, schema, effort, max_tokens)


def web_research(question: str, max_searches: int = 5) -> dict:
    """Web search with citations. Returns {'summary': str, 'sources': [{url,title,cited_text}], 'model': str}."""
    if PROVIDER == "anthropic":
        return _anthropic_research(question, max_searches)
    return _openai_research(question)


# ---------------------------------------------------------------- OpenAI (Responses API)

_openai_client = None


def _openai():
    global _openai_client
    if _openai_client is None:
        import openai
        _openai_client = openai.OpenAI()  # reads OPENAI_API_KEY from env / .env
    return _openai_client


def _openai_errors(e: Exception) -> LLMError:
    import openai
    if isinstance(e, openai.AuthenticationError):
        return LLMError("Invalid or missing OPENAI_API_KEY - set it in .env")
    if isinstance(e, openai.RateLimitError):
        return LLMError("Rate limited or out of credits on the OpenAI account - wait or check billing.")
    if isinstance(e, openai.NotFoundError):
        return LLMError(f"Model '{MODEL}' not available for this key - set LLM_MODEL in .env.")
    if isinstance(e, openai.APIStatusError):
        return LLMError(f"OpenAI API error {e.status_code}: {e.message}")
    if isinstance(e, openai.APIConnectionError):
        return LLMError("Could not reach the OpenAI API - check your connection.")
    raise e


def _openai_check(resp) -> None:
    if getattr(resp, "status", None) == "incomplete":
        reason = getattr(resp.incomplete_details, "reason", "unknown")
        raise LLMError(f"Response incomplete ({reason}) - narrow the scope and retry.")


def _openai_structured(system, user, schema, effort, max_tokens):
    import openai
    try:
        resp = _openai().responses.parse(
            model=MODEL,
            instructions=system,
            input=user,
            text_format=schema,
            reasoning={"effort": effort},
            max_output_tokens=max_tokens,
        )
    except openai.OpenAIError as e:
        raise _openai_errors(e) from e
    _openai_check(resp)
    parsed = resp.output_parsed
    if parsed is None:
        raise LLMError("The model returned no parseable structured output (possibly a refusal).")
    u = resp.usage
    return parsed, {"provider": "openai", "model": resp.model,
                    "input_tokens": getattr(u, "input_tokens", None), "output_tokens": getattr(u, "output_tokens", None)}


def _openai_research(question):
    import openai
    try:
        resp = _openai().responses.create(
            model=MODEL,
            instructions=RESEARCH_SYSTEM,
            input=question,
            tools=[{"type": "web_search"}],
            reasoning={"effort": "medium"},
        )
    except openai.OpenAIError as e:
        raise _openai_errors(e) from e
    _openai_check(resp)
    sources, seen = [], set()
    for item in resp.output:
        if getattr(item, "type", None) != "message":
            continue
        for part in item.content:
            text = getattr(part, "text", "") or ""
            for a in getattr(part, "annotations", None) or []:
                if getattr(a, "type", None) == "url_citation" and a.url not in seen:
                    seen.add(a.url)
                    cited = text[a.start_index:a.end_index] if getattr(a, "end_index", None) else ""
                    sources.append({"url": a.url, "title": getattr(a, "title", "") or a.url, "cited_text": cited})
    return {"summary": (resp.output_text or "").strip(), "sources": sources, "model": resp.model}


# ---------------------------------------------------------------- Anthropic (Claude)

# Server-side refusal fallback: on a policy decline the API re-runs the request on a
# suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_anthropic_client = None


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env / .env
    return _anthropic_client


def _anthropic_errors(e: Exception) -> LLMError:
    import anthropic
    if isinstance(e, anthropic.AuthenticationError):
        return LLMError("Invalid or missing ANTHROPIC_API_KEY - set it in .env")
    if isinstance(e, anthropic.RateLimitError):
        return LLMError("Rate limited by the API - wait a moment and retry.")
    if isinstance(e, anthropic.APIStatusError):
        return LLMError(f"API error {e.status_code}: {e.message}")
    if isinstance(e, anthropic.APIConnectionError):
        return LLMError("Could not reach the Anthropic API - check your connection.")
    raise e


def _anthropic_check(msg) -> None:
    if msg.stop_reason == "refusal":
        cat = getattr(msg.stop_details, "category", None) if msg.stop_details else None
        raise LLMError(f"Claude declined the request (category: {cat}).")
    if msg.stop_reason == "max_tokens":
        raise LLMError("Response hit max_tokens before finishing - narrow the scope and retry.")


def _anthropic_structured(system, user, schema, effort, max_tokens):
    import anthropic
    try:
        with _anthropic().beta.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": effort},
            cache_control={"type": "ephemeral"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AnthropicError as e:
        raise _anthropic_errors(e) from e
    _anthropic_check(msg)
    parsed = msg.parsed_output
    if parsed is None:
        raise LLMError("Claude returned no parseable structured output.")
    return parsed, {"provider": "anthropic", "model": msg.model,
                    "input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens}


def _anthropic_research(question, max_searches, max_continuations: int = 4):
    import anthropic
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
    messages = [{"role": "user", "content": question}]
    try:
        msg = None
        for _ in range(max_continuations + 1):
            with _anthropic().beta.messages.stream(
                model=MODEL, max_tokens=32000, system=RESEARCH_SYSTEM, messages=messages, tools=tools,
                output_config={"effort": "medium"}, betas=[FALLBACK_BETA], fallbacks="default",
            ) as stream:
                msg = stream.get_final_message()
            if msg.stop_reason != "pause_turn":
                break
            # Server-side search loop paused; resend so it resumes where it left off.
            messages = [{"role": "user", "content": question}, {"role": "assistant", "content": msg.content}]
    except anthropic.AnthropicError as e:
        raise _anthropic_errors(e) from e
    _anthropic_check(msg)

    text, sources, seen = [], [], set()
    for block in msg.content:
        if block.type == "text":
            text.append(block.text)
            for c in (getattr(block, "citations", None) or []):
                url = getattr(c, "url", None)
                if url and url not in seen:
                    seen.add(url)
                    sources.append({"url": url, "title": getattr(c, "title", "") or url,
                                    "cited_text": getattr(c, "cited_text", "")})
    return {"summary": "".join(text).strip(), "sources": sources, "model": msg.model}
