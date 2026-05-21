"""Group-chat response gate — Jessica is 1-on-1 only.

In a WhatsApp group, ChatDaddy delivers EVERY message in the chat to the
webhook. Jessica is a single-customer wellness agent — she should never
reply in a group context regardless of @-tags or quote-replies.

Policy: any inbound from a group JID (``@g.us`` suffix or ``120363``
prefix) is dropped silently. The caller gets a ``Decision`` object with
``should_process=False`` and a human-readable ``reason`` string.

(Dr. Baba's version supported conditional group responses via
``WA_BOT_JIDS`` / ``WA_BOT_NAMES`` — see ``dr-baba-agent/src/whatsapp/
group_gate.py``. We deliberately do not port that complexity; Jessica's
deployment model is 1-on-1 sales conversations only.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.whatsapp.models import ChatDaddyMessage

logger = logging.getLogger("whatsapp.group_gate")

__all__ = ["Decision", "decide"]


@dataclass(frozen=True)
class Decision:
    """Outcome of consulting the group gate for one inbound message."""

    should_process: bool
    reason: str  # human-readable diagnostic — logged, never sent to user

    @property
    def dropped(self) -> bool:
        return not self.should_process


def decide(msg: ChatDaddyMessage) -> Decision:
    """Return whether ``msg`` should be processed by the pipeline.

    DMs always pass. Group messages are always dropped.
    """
    if msg.is_group:
        return Decision(
            should_process=False,
            reason="group_chat_not_supported",
        )
    return Decision(should_process=True, reason="dm")
