"""PersonaProfile — persona/brand abstraction for the shared pipeline.

Phase 0 scaffolding (migration plan, phase 0 of N). This module is
introduced as pure, additive data modelling — it is NOT wired into any
live dispatch path yet:

  - src/orchestrator/pipeline.py::JessicaPipeline.run_turn accepts an
    OPTIONAL ``profile`` kwarg that defaults to ``None`` everywhere it is
    called today (WhatsApp webhook, tests, etc). ``profile=None`` behaves
    identically to before this module existed.
  - src/channels/meta_webhook.py, src/channels/chloe_agent.py, src/web.py
    are UNCHANGED — they keep serving live Instagram DM traffic exactly
    as today via ``ChloeAgent`` (an entirely separate, ungrounded code
    path). This module does not replace or touch that agent.

A ``PersonaProfile`` describes everything that varies between "IPs"
sharing the Planner -> Specialists -> Writer pipeline: language, identity,
which specialists are in scope (commerce-free personas exclude Sales /
Appointment), brand-naming rules, greeting content, and reply-shape
limits. A later phase (NOT this one) will thread real profiles into the
pipeline for Jackie / Chloe behind a feature flag.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

logger = logging.getLogger("personas.profile")

_DATA_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent / "data" / "personas"

_VALID_LANGUAGES: Final[frozenset[str]] = frozenset({"yue", "en"})


@dataclass(frozen=True)
class PersonaProfile:
    """Immutable description of one IP/persona sharing the pipeline.

    Fields:
      key: stable identifier, e.g. "jessica" / "jackie" / "chloe".
      language: "yue" (Cantonese) | "en" (English).
      identity_name: the name the persona uses to refer to itself.
      allowed_specialists: specialist name strings (see
        src.agents.base.SpecialistName values) this persona may route to.
        The Planner clamps any disallowed routing decision back into
        scope — see src.agents.planner._clamp_to_profile. Only enforced
        when a profile is explicitly supplied to PlannerAgent.decide().
      brand_policy: prose block describing what may / may not be named
        (clinic, products, WhatsApp, other practitioners).
      greeting_bubbles: first-touch intro bubbles (rendered verbatim, no
        LLM ad-libbing — brand consistency, mirrors GreetingAgent's
        official-intro fast path).
      greeting_media_url: absolute URL of the first-touch portrait/media
        (empty string = no media).
      max_bubbles: hard cap on reply bubble count.
      tongue_read_only: when True, the Constitution specialist should
        stop after tongue-vision analysis and NOT advance into the MCQ /
        full-declaration phases. Defined now for the data model only —
        enforcement inside constitution_agent.py is explicitly OUT of
        scope for Phase 0 and is not wired into any call site.
    """

    key: str
    language: str
    identity_name: str
    allowed_specialists: frozenset[str]
    brand_policy: str
    greeting_bubbles: tuple[str, ...] = ()
    greeting_media_url: str = ""
    max_bubbles: int = 5
    tongue_read_only: bool = False

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("PersonaProfile.key must be non-empty")
        if self.language not in _VALID_LANGUAGES:
            raise ValueError(
                f"PersonaProfile({self.key!r}).language must be one of "
                f"{sorted(_VALID_LANGUAGES)}, got {self.language!r}"
            )
        if not self.identity_name:
            raise ValueError(f"PersonaProfile({self.key!r}).identity_name must be non-empty")
        if not self.allowed_specialists:
            raise ValueError(
                f"PersonaProfile({self.key!r}).allowed_specialists must be non-empty"
            )
        if self.max_bubbles < 1:
            raise ValueError(f"PersonaProfile({self.key!r}).max_bubbles must be >= 1")


# -----------------------------------------------------------------------
# Jessica — default profile. MUST mirror TODAY'S hardcoded WhatsApp
# pipeline behaviour exactly, since profile=None (the only value used by
# every existing call site today) is equivalent to this profile.
# -----------------------------------------------------------------------

# Mirrors src.agents.base.SpecialistName — every specialist is in scope
# for Jessica today (full commerce pipeline).
_JESSICA_ALL_SPECIALISTS: Final[frozenset[str]] = frozenset(
    {
        "greeting",
        "casual",
        "faq",
        "sales",
        "constitution",
        "appointment",
        "tongue_progress",
    }
)

# Mirrors the "公司事實" / WhatsApp-link-ban / order-flow rules baked into
# src.agents.writer._SYSTEM today. Kept as an independent prose paraphrase
# here (not a byte-for-byte copy) — Writer's default (profile=None) output
# path does NOT consume this field; it still renders the original
# hardcoded block verbatim. See tests/test_writer_default_profile_unchanged.py
# for the byte-identity proof.
_JESSICA_BRAND_POLICY: Final[str] = (
    "心宜中醫 Care Plus 自己出 10 款預製湯水 (HK$48-120) + 3 款藥膏，全部自家配方 / "
    "自家製作，唔係市售。可以主動提呢個 general fact，但具體邊一款產品 + 價錢必須嚟自 "
    "Sales specialist 嘅 payload，唔可以自己作。絕對唔可以畀 WhatsApp 號碼 / 連結俾用"
    "戶 — 對話本身已經喺 WhatsApp 度，叫用戶去另一個號碼冇意義；你就係客服，落單資料應"
    "該直接喺呢個對話收集。"
)


def default_jessica_profile() -> PersonaProfile:
    """Build the Jessica profile — captures TODAY'S hardcoded pipeline
    behaviour (language, full specialist scope, commerce rules, greeting
    content, bubble cap). This is the profile every existing call site
    is equivalent to when it passes ``profile=None``.
    """
    bubbles, media_url = _jessica_greeting_content()
    return PersonaProfile(
        key="jessica",
        language="yue",
        identity_name="Jessica",
        allowed_specialists=_JESSICA_ALL_SPECIALISTS,
        brand_policy=_JESSICA_BRAND_POLICY,
        greeting_bubbles=bubbles,
        greeting_media_url=media_url,
        max_bubbles=5,  # mirrors src.agents.writer.MAX_BUBBLES
        tongue_read_only=False,
    )


def _jessica_greeting_content() -> tuple[tuple[str, ...], str]:
    """Pull Jessica's real first-touch greeting from data/greetings.json
    using the SAME loader + URL-resolution logic as GreetingAgent, so this
    profile reflects actual current behaviour instead of a re-typed copy
    that could drift out of sync.
    """
    try:
        from src.agents.greeting_agent import _load_greetings, _public_base_url  # noqa: PLC0415

        greetings = _load_greetings()
        first_touch = greetings.get("first_touch_clean", {})
        bubbles = tuple(str(b) for b in first_touch.get("bubbles", []))
        media = first_touch.get("media", [])
        media_url = ""
        if media:
            url_path = str(media[0].get("url_path", ""))
            base = _public_base_url()
            media_url = f"{base}{url_path}" if url_path.startswith("/") else url_path
        return bubbles, media_url
    except Exception:  # noqa: BLE001
        logger.warning(
            "could not derive Jessica greeting content from data/greetings.json",
            exc_info=True,
        )
        return (), ""


# -----------------------------------------------------------------------
# Jackie / Chloe — loaders reading data/personas/{jackie,chloe}.json.
# These personas exclude commerce specialists (Sales, Appointment) and
# are tongue-read-only. NOT wired into any live dispatch path in Phase 0.
#
# Note: ``ChloeAgent`` (src/channels/chloe_agent.py) reads these SAME JSON
# files directly for its own (unrelated, ungrounded, currently-live)
# persona model and is unaffected — the 3 new fields these loaders read
# (language / allowed_specialists / brand_policy) are purely additive; no
# existing field was removed or renamed.
# -----------------------------------------------------------------------


def load_jackie_profile(path: Path | None = None) -> PersonaProfile:
    """Load Jackie's profile from data/personas/jackie.json (or ``path``)."""
    return _load_json_persona(path or (_DATA_DIR / "jackie.json"), key="jackie")


def load_chloe_profile(path: Path | None = None) -> PersonaProfile:
    """Load Chloe's profile from data/personas/chloe.json (or ``path``)."""
    return _load_json_persona(path or (_DATA_DIR / "chloe.json"), key="chloe")


def _load_json_persona(path: Path, *, key: str) -> PersonaProfile:
    data = json.loads(path.read_text(encoding="utf-8"))

    language = str(data.get("language", "")).strip()
    if not language:
        raise ValueError(f"{path}: missing required 'language' field")

    raw_allowed = data.get("allowed_specialists")
    if not raw_allowed:
        raise ValueError(f"{path}: missing required 'allowed_specialists' field")
    allowed_specialists = frozenset(str(s) for s in raw_allowed)

    brand_policy = str(data.get("brand_policy", "")).strip()
    if not brand_policy:
        raise ValueError(f"{path}: missing required 'brand_policy' field")

    return PersonaProfile(
        key=key,
        language=language,
        identity_name=str(data.get("display_name", key.title())),
        allowed_specialists=allowed_specialists,
        brand_policy=brand_policy,
        greeting_bubbles=tuple(
            str(b) for b in data.get("greeting_bubbles", []) if str(b).strip()
        ),
        greeting_media_url=str(data.get("greeting_media_url", "")).strip(),
        max_bubbles=int(data.get("max_bubbles", 3)),
        tongue_read_only=True,
    )
