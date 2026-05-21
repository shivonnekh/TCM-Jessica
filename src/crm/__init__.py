"""CRM — single source of truth for user state.

Specialists never maintain their own memory. They read a snapshot from
CRM at turn start (via Orchestrator) and the Writer / Orchestrator
writes back at turn end.
"""

from src.crm.models import (
    AppointmentRecord,
    Constitution,
    ConversationMessage,
    Promotion,
    User,
    UserStatus,
)
from src.crm.repo import CRMRepo
from src.crm.repo_factory import open_crm_repo

__all__ = [
    "AppointmentRecord",
    "Constitution",
    "ConversationMessage",
    "CRMRepo",
    "Promotion",
    "User",
    "UserStatus",
]
