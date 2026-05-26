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

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# Higher-quality model used for components where reasoning + tone quality
# matter most. As of 2026-05-26: Planner (routing logic), vision tasks
# (Constitution + TongueProgress).
PLANNER_MODEL = os.environ.get("OPENAI_PLANNER_MODEL", "gpt-4o")
VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o")


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
        # default (gpt-4o-mini) and log it.
        effective_model = _coerce_model(model)

        resp = await self._c.chat.completions.create(
            model=effective_model,
            max_tokens=max_tokens,
            messages=oai_messages,
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
    """Map Anthropic-style names → OpenAI model. Default to gpt-4o-mini."""
    if not name:
        return DEFAULT_MODEL
    if name.startswith(("gpt-", "o1", "o3", "o4")):
        return name
    if name.startswith("claude-"):
        return DEFAULT_MODEL
    return DEFAULT_MODEL
