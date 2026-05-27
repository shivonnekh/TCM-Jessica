"""CRM data models — immutable Pydantic.

Schema rules:
- All field updates create a NEW User instance (see User.with_updates).
- `conversation_history` is a rolling window (last N messages); the FULL
  log is in the `messages` table and joined via repo, not held in memory.
- `notes` is freeform agent-written; `tags` is a structured label set.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserStatus(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"  # showed interest in something concrete
    CONSTITUTION_DONE = "constitution_done"
    BOUGHT = "bought"
    BOOKED = "booked"
    CHURNED = "churned"
    OPTED_OUT = "opted_out"


class Constitution(StrEnum):
    """TCM 九體質 — set by Constitution Agent."""

    PINGHE = "平和質"
    QIXU = "氣虛質"
    YANGXU = "陽虛質"
    YINXU = "陰虛質"
    TANSHI = "痰濕質"
    SHIRE = "濕熱質"
    XUEYU = "血瘀質"
    QIYU = "氣鬱質"
    TEBING = "特稟質"
    UNKNOWN = "unknown"


class ConversationMessage(BaseModel):
    """One message in the conversation, either direction."""

    model_config = ConfigDict(frozen=True)

    role: str  # "user" | "jessica"
    content: str
    at: datetime
    wa_message_id: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    turn_id: str | None = None


class AppointmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    clinic_id: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    mode: str  # "in_person" | "online_video"
    status: str  # "proposed" | "confirmed" | "cancelled" | "completed"
    booked_at: datetime


class TongueRecord(BaseModel):
    """A single tongue photo + its vision-analysed findings.

    Stored per-user, oldest→newest. The TongueProgress agent reads the
    last record to generate before/after narratives for the user.
    """

    model_config = ConfigDict(frozen=True)

    photo_url: str
    captured_at: datetime
    # Structured findings (parsed from vision LLM output)
    tongue_colour: str = ""          # 淡紅 / 紅 / 絳 / 淡白 / 紫
    coating_colour: str = ""         # 白 / 黃 / 灰 / 黑
    coating_thickness: str = ""      # 薄 / 厚 / 無苔
    coating_moisture: str = ""       # 潤 / 燥 / 膩
    body_shape: str = ""             # 正常 / 胖 / 瘦
    teeth_marks: bool = False
    cracks: bool = False
    # Free-form analysis from vision LLM (fallback for narrative)
    raw_analysis: str = ""
    # Snapshot of user.constitution at upload time (for context)
    constitution_at_time: str = "unknown"


class ObservedPattern(BaseModel):
    """A 證 (TCM pattern/syndrome) observed during a conversation.

    Append-only history — every Planner inference produces a new entry
    timestamped with the source. Clinic doctor can later confirm/reject
    via /admin which updates `source` (jessica_inferred → doctor_confirmed
    / doctor_rejected) but never deletes the historical row.

    Why this isn't on `constitution` (which is one static value):
        - constitution changes over months/years
        - 證 changes over weeks (acute pattern of the moment)
        - Doctor needs a temporal trail to track treatment progress
    """

    model_config = ConfigDict(frozen=True)

    name: str                       # "肝鬱氣滯", "心脾兩虛", etc.
    confidence: float               # 0.0-1.0
    observed_at: datetime
    source: str                     # "jessica_inferred" | "doctor_confirmed" | "doctor_rejected"
    evidence: list[str] = Field(default_factory=list)
    layman_zh: str = ""             # Plain-language explanation for Writer
    turn_id: str | None = None      # Link to the conversation turn


class Promotion(BaseModel):
    """Active offer surfaced by Sales/Appointment agents.

    Loaded from data/promotions/active_offers.json — read-only at runtime.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    title_zh: str
    description_zh: str
    applies_to: list[str]  # e.g. ["appointment", "online_consultation"]
    expires_at: datetime | None = None
    discount_pct: float | None = None
    free_item: str | None = None  # e.g. "consultation_fee" or "shipping"


class User(BaseModel):
    """User record — the canonical CRM snapshot.

    Mutations create new instances via `with_updates(...)`. Never mutate
    a User in place — that's a CLAUDE.md / coding-style.md violation.
    """

    model_config = ConfigDict(frozen=True)

    phone: str
    name: str | None = None
    status: UserStatus = UserStatus.NEW
    age: int | None = None
    location: str | None = None  # freeform user input
    district: str | None = None  # normalized HK district (e.g. "沙田")

    constitution: Constitution = Constitution.UNKNOWN
    pain_points: list[str] = Field(default_factory=list)

    products_pitched: list[str] = Field(default_factory=list)
    products_purchased: list[str] = Field(default_factory=list)
    appointments: list[AppointmentRecord] = Field(default_factory=list)
    tongue_photos: list[TongueRecord] = Field(default_factory=list)

    # 辨證 layer — append-only history of TCM patterns observed in
    # conversation. Different from `constitution` (static, set once)
    # because 證 changes over weeks. See ObservedPattern docstring.
    observed_patterns: list[ObservedPattern] = Field(default_factory=list)

    # Menstrual cycle tracking (optional — female users only)
    last_period_start: date | None = None
    cycle_length_days: int = 28  # default 28-day cycle

    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)

    # Cross-turn flow state — owned by specialists. Examples:
    #   {"constitution_q_index": 2, "constitution_mcq_answers": [...],
    #    "tongue_findings": {"colour": "pale", "coating": "thin_white"}}
    # NOT for final answers (use the typed fields above) — only for
    # transient multi-turn state. Each specialist namespaces its own keys.
    temp_state: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def with_updates(self, **changes: Any) -> "User":
        """Return a new User with the given fields replaced.

        Re-validates the merged dict so string values from specialist
        diffs (e.g. {"constitution": "陽虛質"}) get coerced back to
        the proper Enum type — otherwise downstream code that calls
        ``user.constitution.value`` crashes with AttributeError.
        """
        merged = self.model_dump()
        merged.update(changes)
        merged["updated_at"] = datetime.utcnow()
        return User.model_validate(merged)

    def append_message(self, msg: ConversationMessage, window: int = 20) -> "User":
        """Append a message to the rolling history window."""
        new_history = [*self.conversation_history, msg][-window:]
        return self.with_updates(conversation_history=new_history)
