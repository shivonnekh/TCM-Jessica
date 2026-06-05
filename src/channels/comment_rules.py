"""Keyword → canned-response rules for comment→DM CTAs.

WHY THIS EXISTS
---------------
For a fresh lead reacting to a "comment 'gut' and I'll DM you the guide"
CTA, you should NOT spin up the full Jessica pipeline. You already know
exactly what they asked for — just send the predefined content. That is:

    * cheaper (no LLM call),
    * faster,
    * predictable (no chance the agent goes off-script on a cold lead),
    * compliant (one clean DM per comment).

So comment handling is **canned-first**. Each keyword maps to a fixed DM
(text + optional image + optional public acknowledgement). Only if a rule
explicitly sets ``"use_agent": true`` do we run the pipeline for that
keyword (useful for open-ended prompts like "ask me anything").

CONFIG
------
``data/channels/comment_responses.json``::

    {
      "gut": {
        "dm_text": "多謝你留言 🌿 呢度係腸胃調理懶人包...",
        "image_url": "https://tcm-jessica.onrender.com/media/...png",
        "public_ack": "send咗私訊俾你喇！",
        "use_agent": false
      },
      "濕熱": { "dm_text": "...", "use_agent": false }
    }

Matching is case-insensitive substring on the comment text. The first
keyword (in file order) that appears in the comment wins.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

logger = logging.getLogger("channels.comment_rules")

_DEFAULT_PATH: Final[str] = str(
    Path(__file__).resolve().parent.parent.parent
    / "data" / "channels" / "comment_responses.json"
)


@dataclass(frozen=True)
class CommentReply:
    """One canned (or agent-routed) comment→DM rule."""

    keyword: str
    dm_text: str = ""
    image_url: str = ""
    public_ack: str = ""
    use_agent: bool = False


def _config_path() -> Path:
    return Path(os.environ.get("COMMENT_RESPONSES_PATH", _DEFAULT_PATH))


@lru_cache(maxsize=1)
def _load_raw(path_str: str, mtime: float) -> tuple[CommentReply, ...]:
    """Parse + validate the rules file. Cached on (path, mtime) so edits
    are picked up without a restart but we don't re-read on every comment."""
    path = Path(path_str)
    if not path.exists():
        return ()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[comment_rules] failed to load %s: %s", path, exc)
        return ()
    if not isinstance(data, dict):
        logger.warning("[comment_rules] root is not an object — ignoring")
        return ()

    rules: list[CommentReply] = []
    for keyword, spec in data.items():
        kw = str(keyword).strip().lower()
        if not kw or not isinstance(spec, dict):
            continue
        rules.append(
            CommentReply(
                keyword=kw,
                dm_text=str(spec.get("dm_text", "")).strip(),
                image_url=str(spec.get("image_url", "")).strip(),
                public_ack=str(spec.get("public_ack", "")).strip(),
                use_agent=bool(spec.get("use_agent", False)),
            )
        )
    return tuple(rules)


def load_rules() -> tuple[CommentReply, ...]:
    path = _config_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return _load_raw(str(path), mtime)


def match(text: str) -> CommentReply | None:
    """Return the first rule whose keyword appears in ``text`` (or None)."""
    haystack = (text or "").lower()
    for rule in load_rules():
        if rule.keyword and rule.keyword in haystack:
            return rule
    return None
