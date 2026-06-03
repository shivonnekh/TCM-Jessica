"""Group-chat response gate.

Jessica can participate in WhatsApp groups. Policy:

* **REPLY** — the bot was @-mentioned (by JID, by name in text, or via a
  quote-reply to the bot's own message). Run the full pipeline and send.
* **LISTEN** — bot was NOT mentioned. Silently absorb the message: update the
  sender's CRM record (name, pain-points) so Jessica already has context when
  the user eventually @-mentions her. No reply is sent.

DMs bypass this module entirely; the caller checks ``msg.is_group`` first.

Configuration (env vars):
    JESSICA_BOT_JID   — the bot's own WhatsApp JID digits, e.g. ``85212345678``.
                        Used to match against ``mentioned_jids`` and
                        ``@<digits>`` patterns in the message text. If unset,
                        JID-based detection is skipped (name-based + quote
                        detection still work).
    JESSICA_BOT_NAMES — comma-separated display names to recognise as @-tags,
                        e.g. ``Jessica,jessica,Jessica姐``.
                        Default: ``Jessica,jessica``.

(Dr. Baba's version used ``WA_BOT_JIDS`` / ``WA_BOT_NAMES`` for *conditional*
group responses across 50 tenants. We keep only what Jessica needs: one bot,
one reply policy, two actions.)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from src.whatsapp.models import ChatDaddyMessage

logger = logging.getLogger("whatsapp.group_gate")

__all__ = ["Decision", "GroupAction", "decide", "decide_group"]


# ---------------------------------------------------------------------------
# DM gate (backward compat — used by smoke-test path and legacy callers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    """Outcome of consulting the group gate for one inbound DM message."""

    should_process: bool
    reason: str  # human-readable diagnostic — logged, never sent to user

    @property
    def dropped(self) -> bool:
        return not self.should_process


def decide(msg: ChatDaddyMessage) -> Decision:
    """Return whether a **DM** message should be processed by the pipeline.

    DMs always pass. Group messages should go through ``decide_group``
    instead, but for safety we still drop them here.
    """
    if msg.is_group:
        return Decision(
            should_process=False,
            reason="group_chat_not_supported",
        )
    return Decision(should_process=True, reason="dm")


# ---------------------------------------------------------------------------
# Group gate
# ---------------------------------------------------------------------------

class GroupAction(Enum):
    """What Jessica should do with a group message."""
    REPLY = "reply"    # bot was mentioned → full pipeline + send
    LISTEN = "listen"  # bot was not mentioned → CRM update only, no send


# Pre-compiled patterns for @<digits> detection in message text.
# Matches any @ followed by 6+ consecutive digits (WhatsApp phone/JID length).
_AT_DIGITS_RE = re.compile(r"@(\d{6,})")


def _mentioned_by_jid(msg: ChatDaddyMessage, bot_jid_digits: str) -> bool:
    """True if the bot's JID appears in the message's explicit mention list."""
    if not bot_jid_digits:
        return False
    for jid in msg.mentioned_jids:
        if jid.split("@")[0] == bot_jid_digits:
            return True
    return False


def _mentioned_in_text(msg: ChatDaddyMessage, bot_jid_digits: str, bot_names: list[str]) -> bool:
    """True if the message text @-tags the bot by digits or by name."""
    text = msg.text
    if not text:
        return False

    # @<digits> — e.g. "@85212345678"
    if bot_jid_digits:
        for match in _AT_DIGITS_RE.finditer(text):
            if match.group(1) == bot_jid_digits:
                return True

    # @<name> — e.g. "@Jessica", "@jessica"
    text_lower = text.lower()
    for name in bot_names:
        if f"@{name.lower()}" in text_lower:
            return True

    return False


def decide_group(
    msg: ChatDaddyMessage,
    bot_jid_digits: str,
    bot_names: list[str],
) -> GroupAction:
    """Decide what Jessica should do with a group message.

    Returns ``GroupAction.REPLY`` when the bot is mentioned, else
    ``GroupAction.LISTEN``.

    Detection hierarchy (first match wins):
    1. ``mentioned_jids`` contains the bot's JID (ChatDaddy explicit mention).
    2. ``quoted_from_me=True`` — user quoted the bot's own previous message
       (semantically equivalent to an @-mention).
    3. Text contains ``@<bot_jid_digits>`` (plain-text JID tag).
    4. Text contains ``@<bot_name>`` for any name in ``bot_names``.
    """
    # 1. Explicit JID mention via ChatDaddy mentionedJids field
    if _mentioned_by_jid(msg, bot_jid_digits):
        logger.debug("[group_gate] REPLY — JID mention jid_digits=%s", bot_jid_digits)
        return GroupAction.REPLY

    # 2. Quote-reply to bot's own previous message
    if msg.quoted_from_me:
        logger.debug("[group_gate] REPLY — quote-reply to bot")
        return GroupAction.REPLY

    # 3. & 4. Text @-tag (digits or name)
    if _mentioned_in_text(msg, bot_jid_digits, bot_names):
        logger.debug("[group_gate] REPLY — text mention in message")
        return GroupAction.REPLY

    logger.debug("[group_gate] LISTEN — not mentioned (sender=%s)", msg.sender_id)
    return GroupAction.LISTEN
