"""PersonaProfile abstraction (Phase 0 scaffolding).

See src/personas/profile.py for the dataclass + loaders. Not wired into
any live dispatch path yet — see that module's docstring.
"""

from __future__ import annotations

from src.personas.profile import (
    PersonaProfile,
    default_jessica_profile,
    load_chloe_profile,
    load_jackie_profile,
)

__all__ = [
    "PersonaProfile",
    "default_jessica_profile",
    "load_chloe_profile",
    "load_jackie_profile",
]
