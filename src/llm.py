"""LLM client — drop-in Anthropic-shaped facade backed by OpenAI gpt-4o-mini.

Agents were originally written against the Anthropic ``AsyncAnthropic``
shape:

    response = await client.messages.create(
        model=..., max_tokens=..., system=..., messages=[...]
    )
    text = response.content[0].text
    response.usage.input_tokens
    response.usage.output_tokens

We swap to OpenAI without rewriting every agent by wrapping
``openai.AsyncOpenAI`` and exposing the same surface. Vision content
(``{"type":"image","source":...}``) is translated to OpenAI's
``image_url`` content blocks on the fly.

Why OpenAI: 2026-05-21 — Anthropic account ran out of credits during
go-live. Switching to gpt-4o-mini (cheap, vision-capable, low latency).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger("llm")

# Model selection (Phase 1 migration 2026-05-26):
#   - gpt-4o-mini deprecated Feb 2026 → migrated to gpt-5.4-mini
#   - gpt-4o legacy/grandfathered → migrated to gpt-5.4-mini (vision-capable)
#   - All roles now run on gpt-5.4-mini except cheap specialists which
#     can drop to gpt-5.4-nano via OPENAI_NANO_MODEL override.
#
# Why all-mini: HK Cantonese quality is determined more by prompts +
# few-shots than by the GPT-5.4 sub-tier. Mini is the proven sweet spot
# for our budget (500 users target → ~$50-100/mo total).
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
# Planner gets the same tier — routing decisions are reliable on mini
# with our structured JSON output schema.
PLANNER_MODEL = os.environ.get("OPENAI_PLANNER_MODEL", "gpt-5.4-mini")
# Vision: gpt-5.4-mini is vision-capable and ~60% cheaper than gpt-4o.
# Tongue 舌診 calls are low volume (~4 per user lifetime) so cost is
# negligible regardless; mini is fine for routine analysis.
VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", "gpt-5.4-mini")
# Cheaper tier for high-frequency, low-stakes specialist calls
# (greeting boilerplate, casual chit-chat). Off by default; opt in by
# setting OPENAI_NANO_MODEL=gpt-5.4-nano.
NANO_MODEL = os.environ.get("OPENAI_NANO_MODEL", DEFAULT_MODEL)


# ──────────────────────────────────────────────────────────────────
# Anthropic-shaped response objects (so agents don't need to change)
# ──────────────────────────────────────────────────────────────────


@dataclass
class _TextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Response:
    content: list[_TextBlock]
    usage: _Usage


# ──────────────────────────────────────────────────────────────────
# Adapter — drop-in for AsyncAnthropic
# ──────────────────────────────────────────────────────────────────


class _Messages:
    """Adapter for ``client.messages.create(...)``."""

    def __init__(self, openai_client: AsyncOpenAI) -> None:
        self._c = openai_client

    async def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        **_ignored: Any,
    ) -> _Response:
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for m in messages:
            content = m.get("content")
            role = m.get("role", "user")
            if isinstance(content, str):
                oai_messages.append({"role": role, "content": content})
                continue
            if isinstance(content, list):
                oai_messages.append(
                    {"role": role, "content": [_translate_block(b) for b in content]}
                )
                continue
            oai_messages.append({"role": role, "content": str(content)})

        # OpenAI's `model` field uses different names; agents pass things
        # like "claude-sonnet-4-5-...". Map any unknown model to the
        # default and log it.
        effective_model = _coerce_model(model)

        # Newer OpenAI families (gpt-5.x and o-series) reject `max_tokens`
        # and require `max_completion_tokens`. Older gpt-4* models accept
        # `max_tokens`. Pick the right kwarg per model family.
        if _uses_max_completion_tokens(effective_model):
            token_kwargs = {"max_completion_tokens": max_tokens}
        else:
            token_kwargs = {"max_tokens": max_tokens}

        resp = await self._c.chat.completions.create(
            model=effective_model,
            messages=oai_messages,
            **token_kwargs,
        )

        text = (resp.choices[0].message.content or "") if resp.choices else ""
        usage = resp.usage
        return _Response(
            content=[_TextBlock(text=text)],
            usage=_Usage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
        )


class LLMClient:
    """Drop-in replacement for ``AsyncAnthropic`` backed by OpenAI."""

    def __init__(self, openai_client: AsyncOpenAI | None = None) -> None:
        self._openai = openai_client or AsyncOpenAI()
        self.messages = _Messages(self._openai)


# ──────────────────────────────────────────────────────────────────
# Block translation: Anthropic → OpenAI content blocks
# ──────────────────────────────────────────────────────────────────


def _translate_block(block: dict[str, Any]) -> dict[str, Any]:
    """Anthropic content block → OpenAI content block.

    - text → {"type":"text","text":...}
    - image (base64 source) → {"type":"image_url","image_url":{"url":"data:..."}}
    - image (url source)    → {"type":"image_url","image_url":{"url":...}}
    """
    bt = block.get("type")
    if bt == "text":
        return {"type": "text", "text": block.get("text", "")}
    if bt == "image":
        src = block.get("source", {})
        if src.get("type") == "base64":
            mime = src.get("media_type", "image/jpeg")
            data = src.get("data", "")
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"},
            }
        if src.get("type") == "url":
            return {"type": "image_url", "image_url": {"url": src.get("url", "")}}
    # Unknown — best effort
    return {"type": "text", "text": str(block)}


# ──────────────────────────────────────────────────────────────────
# Model name coercion
# ──────────────────────────────────────────────────────────────────


def _coerce_model(name: str | None) -> str:
    """Map Anthropic-style names → OpenAI model. Default to DEFAULT_MODEL
    (currently gpt-5.4-mini, see top of file)."""
    if not name:
        return DEFAULT_MODEL
    if name.startswith(("gpt-", "o1", "o3", "o4")):
        return name
    if name.startswith("claude-"):
        return DEFAULT_MODEL
    return DEFAULT_MODEL


def _uses_max_completion_tokens(model: str) -> bool:
    """Return True if the model rejects `max_tokens` and requires the
    new `max_completion_tokens` parameter.

    Affected families:
      - gpt-5.x (gpt-5, gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, ...)
      - o-series (o1, o3, o4, including mini/preview variants)

    Older gpt-4* models still accept `max_tokens` (and currently still
    accept `max_completion_tokens` too — but we keep them on `max_tokens`
    for backward compatibility).
    """
    if not model:
        return False
    return model.startswith(("gpt-5", "o1", "o3", "o4"))
