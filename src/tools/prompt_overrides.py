"""Live prompt override store.

Agents call ``resolve(key, default)`` on every turn. If the key has an
override saved in ``data/prompt_overrides.json``, that string is used
instead of the code-baked prompt. Edit-and-go: no redeploy needed.

Edit surface lives in src/admin_views.py — POST /admin/api/prompts.

Atomicity: writes go through a tmp-then-rename so a half-written file
never corrupts a live read.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("tools.prompt_overrides")

DEFAULT_PATH = Path(
    os.environ.get(
        "PROMPT_OVERRIDES_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "prompt_overrides.json"),
    )
)

# Known keys — informational; resolver works with any key.
KNOWN_KEYS = (
    "planner_system",
    "writer_system",
    "greeting_system",
    "faq_system",
    "sales_system",
    "constitution_vision_system",
)


_LOCK = threading.Lock()
_CACHE: dict[str, str] | None = None
_CACHE_MTIME: float = 0.0


def _read_file() -> dict[str, str]:
    if not DEFAULT_PATH.is_file():
        return {}
    try:
        data = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if isinstance(k, str)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("prompt_overrides parse failed: %s", exc)
    return {}


def _load_cache() -> dict[str, str]:
    """Hot reload on every call (cheap stat + occasional read)."""
    global _CACHE, _CACHE_MTIME
    try:
        mtime = DEFAULT_PATH.stat().st_mtime if DEFAULT_PATH.is_file() else 0.0
    except OSError:
        mtime = 0.0
    if _CACHE is None or mtime != _CACHE_MTIME:
        with _LOCK:
            _CACHE = _read_file()
            _CACHE_MTIME = mtime
    return _CACHE or {}


def resolve(key: str, default: str) -> str:
    """Return override for `key` if set + non-empty, else `default`."""
    val = _load_cache().get(key)
    return val if val and val.strip() else default


def get_all() -> dict[str, str]:
    return dict(_load_cache())


def set_override(key: str, value: str) -> None:
    """Write `key` → `value`. Empty value deletes the override."""
    with _LOCK:
        data = _read_file()
        if not value or not value.strip():
            data.pop(key, None)
        else:
            data[key] = value
        DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = DEFAULT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, DEFAULT_PATH)
        # invalidate cache
        global _CACHE, _CACHE_MTIME
        _CACHE = None
        _CACHE_MTIME = 0.0
    logger.info("prompt_overrides: set %s (len=%d)", key, len(value or ""))
