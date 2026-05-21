"""Per-phone opt-out blocklist — drop or canned-reply for specific numbers.

Single-tenant file-based storage at ``data/blocklist.json``. The file is a
JSON object::

    {
      "blocked": ["85291234567", "85291112222"],
      "canned_reply": "process canceled"
    }

If the file doesn't exist on first read we create it with an empty list
and no canned reply. Reads are cached in memory; ``add()`` / ``remove()``
mutate the cache and persist to disk.

Why a file (not env vars) — Jessica is a long-running single-tenant
deployment; we want an ops human to be able to add a phone to the
blocklist without redeploying. The Dr. Baba env-var design assumed
multi-tenant config drift; that's not a constraint here.

Returns a small ``Decision`` dataclass so the caller can choose between
silent drop, canned reply, or pass-through.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

logger = logging.getLogger("whatsapp.blocklist")

__all__ = [
    "Decision",
    "add",
    "decide",
    "is_blocked",
    "list_blocked",
    "remove",
    "set_canned_reply",
    "_reload_for_tests",
    "_set_path_for_tests",
]


# ---------------------------------------------------------------------------
# Storage path
# ---------------------------------------------------------------------------

# Resolved relative to project root (parent-of-src). Overridable via env for
# Render-style deployments and via ``_set_path_for_tests`` in unit tests.
_DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "blocklist.json"
_path: Path = Path(os.environ.get("BLOCKLIST_PATH", str(_DEFAULT_PATH)))

_lock = Lock()


# ---------------------------------------------------------------------------
# Phone normalisation
# ---------------------------------------------------------------------------

_NON_DIGIT_RE = re.compile(r"\D+")


def _normalise(raw: str) -> str:
    """Strip everything but digits. Empty string for empty/None input."""
    if not raw:
        return ""
    return _NON_DIGIT_RE.sub("", raw)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def _empty_state() -> dict:
    return {"blocked": [], "canned_reply": ""}


def _ensure_file_exists() -> None:
    """Create the blocklist file with an empty state if missing."""
    if _path.exists():
        return
    _path.parent.mkdir(parents=True, exist_ok=True)
    _path.write_text(json.dumps(_empty_state(), indent=2), encoding="utf-8")


def _read_disk() -> dict:
    """Read raw state from disk, falling back to empty state on any failure."""
    try:
        _ensure_file_exists()
        raw = _path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _empty_state()
        blocked_raw = data.get("blocked", [])
        canned_raw = data.get("canned_reply", "")
        return {
            "blocked": [_normalise(p) for p in blocked_raw if _normalise(p)],
            "canned_reply": str(canned_raw or ""),
        }
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[blocklist] failed to read %s: %s — defaulting to empty", _path, exc)
        return _empty_state()


def _write_disk(state: dict) -> None:
    """Persist state to disk atomically (write to tmp, then rename)."""
    _path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _path.with_suffix(_path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_path)


# ---------------------------------------------------------------------------
# In-memory cache (refreshed lazily; mutations persist immediately)
# ---------------------------------------------------------------------------

_blocked: frozenset[str] = frozenset()
_canned_reply: str = ""
_loaded: bool = False


def _ensure_loaded() -> None:
    """Lazy-load the cache on first access."""
    global _blocked, _canned_reply, _loaded
    if _loaded:
        return
    state = _read_disk()
    _blocked = frozenset(state["blocked"])
    _canned_reply = state["canned_reply"]
    _loaded = True
    if _blocked:
        logger.info("[blocklist] loaded %d phone(s) from %s", len(_blocked), _path)


# ---------------------------------------------------------------------------
# Decision API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    """Outcome of consulting the blocklist for one inbound message."""

    blocked: bool
    canned_reply: str = ""

    @property
    def should_send_reply(self) -> bool:
        """True iff blocked AND a non-empty canned reply is configured."""
        return self.blocked and bool(self.canned_reply)


def is_blocked(phone: str) -> bool:
    """True iff the (normalised) phone is in the blocklist."""
    with _lock:
        _ensure_loaded()
        return _normalise(phone) in _blocked


def decide(phone: str) -> Decision:
    """Return a :class:`Decision` for an inbound message from ``phone``."""
    with _lock:
        _ensure_loaded()
        if _normalise(phone) not in _blocked:
            return Decision(blocked=False)
        return Decision(blocked=True, canned_reply=_canned_reply)


def list_blocked() -> list[str]:
    """Return a sorted snapshot of currently-blocked phones."""
    with _lock:
        _ensure_loaded()
        return sorted(_blocked)


def add(phone: str) -> bool:
    """Add a phone to the blocklist. Returns True iff it was newly added."""
    global _blocked
    normalised = _normalise(phone)
    if not normalised:
        return False
    with _lock:
        _ensure_loaded()
        if normalised in _blocked:
            return False
        new_blocked = _blocked | {normalised}
        _write_disk({"blocked": sorted(new_blocked), "canned_reply": _canned_reply})
        _blocked = frozenset(new_blocked)
        logger.info("[blocklist] added %s", normalised)
        return True


def remove(phone: str) -> bool:
    """Remove a phone from the blocklist. Returns True iff it was present."""
    global _blocked
    normalised = _normalise(phone)
    if not normalised:
        return False
    with _lock:
        _ensure_loaded()
        if normalised not in _blocked:
            return False
        new_blocked = _blocked - {normalised}
        _write_disk({"blocked": sorted(new_blocked), "canned_reply": _canned_reply})
        _blocked = frozenset(new_blocked)
        logger.info("[blocklist] removed %s", normalised)
        return True


def set_canned_reply(text: str) -> None:
    """Update the canned reply text. Empty string disables canned replies."""
    global _canned_reply
    with _lock:
        _ensure_loaded()
        _canned_reply = str(text or "")
        _write_disk({"blocked": sorted(_blocked), "canned_reply": _canned_reply})


# ---------------------------------------------------------------------------
# Test helpers (NOT for production use)
# ---------------------------------------------------------------------------


def _reload_for_tests() -> None:
    """Force a re-read from disk. Tests only."""
    global _blocked, _canned_reply, _loaded
    with _lock:
        _loaded = False
        state = _read_disk()
        _blocked = frozenset(state["blocked"])
        _canned_reply = state["canned_reply"]
        _loaded = True


def _set_path_for_tests(path: Path) -> None:
    """Override the storage path. Tests only — pair with ``_reload_for_tests``."""
    global _path, _loaded
    with _lock:
        _path = path
        _loaded = False
