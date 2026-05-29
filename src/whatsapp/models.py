"""Immutable data models for ChatDaddy webhook payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChatDaddyMessage:
    """Parsed incoming message from a ChatDaddy webhook."""

    event: str              # "message-insert"
    message_id: str         # data[0].id
    chat_id: str            # "85291234567@s.whatsapp.net" or "{gid}@g.us"
    account_id: str         # ChatDaddy accountId
    text: str               # data[0].text (empty string if media-only)
    from_me: bool           # data[0].fromMe
    timestamp: int          # Unix seconds
    sender_name: str = ""   # data[0].pushName or ""
    attachments: tuple[dict, ...] = field(default_factory=tuple)
    # Group-chat support — in group chats, chat_id is the group JID and
    # the actual sender is in sender_contact_id. mentioned_jids lists the
    # JIDs explicitly @-tagged in this message — but in practice ChatDaddy
    # webhooks DO NOT include this field, so group_gate.py relies on text
    # pattern matching against the raw ``text`` and ``quoted`` instead.
    mentioned_jids: tuple[str, ...] = field(default_factory=tuple)
    sender_contact_id: str = ""  # data[0].senderContactId — distinct from
                                 # chat_id in groups (sender's own JID).
    quoted_from_me: bool = False  # data[0].quoted.fromMe — True when this
                                  # message is a reply to the bot's own
                                  # previous message (a tag-equivalent).

    @property
    def phone(self) -> str:
        """Extract digits from chatId (e.g. '85291234567').

        WARNING — historical misnomer: in a group chat this returns the
        GROUP id digits, not anyone's phone. Use this property only as a
        chat-counterpart key (merge buffer, log lines). For the human
        sender's identifier, use ``sender_id``. For per-patient routing,
        derive ``user_id`` via ``src.groups.keys.patient_user_id`` —
        which knows about group composite keys (Phase 1).
        """
        return self.chat_id.split("@")[0]

    @property
    def is_group(self) -> bool:
        """True iff this message is from a WhatsApp group chat.

        Two signals (either is sufficient):
          * chat_id ends with ``@g.us`` — the canonical group suffix.
          * chat_id starts with ``120363`` — the 18-digit WhatsApp group
            prefix. Necessary because ChatDaddy occasionally delivers the
            same group with the ``@s.whatsapp.net`` suffix instead of
            ``@g.us``. Phone numbers never start with ``120363`` (they
            are 10–13 digits with country code), so this prefix check is
            unambiguous in practice.
        """
        return self.chat_id.endswith("@g.us") or self.phone.startswith("120363")

    @property
    def sender_id(self) -> str:
        """Opaque digits of the sender's own JID/LID (group-safe).

        In DMs this equals ``phone`` (E.164 digits without ``+``).
        In groups, this is a WhatsApp Linked Identifier (LID) — a 15-digit
        opaque ID that uniquely identifies the participant within the
        group but is NOT a phone number. ChatDaddy delivers it as
        ``senderContactId="<lid>@lid"``; we strip the suffix.

        Empty string if neither chat_id nor sender_contact_id has a
        suffix. Callers must treat this as opaque — never assume it can
        be looked up as a phone number, never display it to users.

        See ``docs/plans/group-chat-v1-family.md`` §3.3 / §7.1 for the
        identity-split rationale.
        """
        src = self.sender_contact_id or self.chat_id
        return src.split("@")[0]

    @property
    def sender_phone(self) -> str:
        """DEPRECATED — use ``sender_id`` instead.

        Kept for one release window of backward compatibility. The name
        is a misnomer: in groups it returns a LID's digit prefix, not a
        phone number. New code MUST use ``sender_id``.

        See ``docs/plans/group-chat-v1-family.md`` §7.1 for the rename
        rationale (architect review, 2026-05-05).
        """
        return self.sender_id

    @property
    def user_id(self) -> str:
        """Patient user_id for the CRM store (DM-only — Jessica is 1-on-1)."""
        return f"wa_{self.phone}"


def _extract_poll_selection(msg: dict) -> str:
    """Extract the selected option text from a ChatDaddy poll vote message.

    ChatDaddy sends poll votes in several shapes depending on API version:
      1. msg.vote.selectedOptions = ["B. 正常，偶爾攰"]
      2. msg.pollUpdates[0].selectedOptions = ["B. 正常，偶爾攰"]
      3. msg.selectedOptions = ["B. 正常，偶爾攰"]
      4. msg.text already contains the option (some versions send it directly)

    Returns the first selected option string, or "" if unrecognised.
    """
    # Shape 1: msg.vote
    vote = msg.get("vote")
    if isinstance(vote, dict):
        opts = vote.get("selectedOptions") or vote.get("options") or []
        if opts and isinstance(opts, list):
            return str(opts[0]).strip()

    # Shape 2: msg.pollUpdates (array)
    poll_updates = msg.get("pollUpdates")
    if isinstance(poll_updates, list) and poll_updates:
        first = poll_updates[0]
        if isinstance(first, dict):
            opts = first.get("selectedOptions") or first.get("options") or []
            if opts and isinstance(opts, list):
                return str(opts[0]).strip()

    # Shape 3: msg.selectedOptions
    selected = msg.get("selectedOptions")
    if isinstance(selected, list) and selected:
        return str(selected[0]).strip()

    # Shape 4: text already populated
    text = (msg.get("text") or "").strip()
    if text:
        return text

    return ""


def _parse_timestamp(raw: str | int | float) -> int:
    """Parse a timestamp that may be Unix int/float or ISO 8601 string."""
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        # Try int parse first (Unix seconds as string)
        try:
            return int(raw)
        except ValueError:
            pass
        # Try ISO 8601: "2026-04-14T06:25:08.000Z"
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except (ValueError, TypeError):
            pass
    return 0


def parse_webhook(payload: dict) -> ChatDaddyMessage | None:
    """Parse a ChatDaddy webhook body into a ChatDaddyMessage.

    Returns None for non-message events or malformed payloads.
    """
    event = payload.get("event", "")
    data_list = payload.get("data")

    if event != "message-insert" or not isinstance(data_list, list) or len(data_list) == 0:
        return None

    msg = data_list[0]
    if not isinstance(msg, dict):
        return None

    # Poll vote handling — when a user votes on a WhatsApp poll, ChatDaddy
    # fires a message-insert with messageType="pollUpdateMessage" and an
    # empty text field. We extract the selected option so the MCQ state
    # machine can process it as a normal A/B/C/D answer.
    msg_type = (msg.get("messageType") or msg.get("type") or "").lower()
    is_poll_vote = (
        "poll" in msg_type
        or "vote" in msg_type
        or bool(msg.get("vote"))
        or bool(msg.get("pollUpdates"))
        or bool(msg.get("selectedOptions"))
    )
    if is_poll_vote:
        selected = _extract_poll_selection(msg)
        if not selected:
            # Unknown poll vote format — capture but don't process
            return None
        # Inject selected option as text so the rest of the pipeline
        # treats it as a regular user message (MCQ answer).
        msg = {**msg, "text": selected, "messageType": "text"}

    message_id = msg.get("id") or payload.get("id") or ""
    chat_id = msg.get("chatId") or msg.get("senderContactId") or ""
    account_id = msg.get("accountId") or payload.get("accountId") or ""
    text = msg.get("text") or ""
    from_me = bool(msg.get("fromMe", False))
    timestamp = _parse_timestamp(msg.get("timestamp", 0))
    sender_name = msg.get("pushName") or msg.get("senderName") or ""

    raw_attachments = msg.get("attachments") or []
    attachments = tuple(raw_attachments) if isinstance(raw_attachments, list) else ()

    # Mentions — ChatDaddy has shipped this field under several names over
    # time. Take the first non-empty list we find. Each entry is a JID
    # string like "85299999999@s.whatsapp.net".
    raw_mentions = (
        msg.get("mentionedJids")
        or msg.get("mentioned")
        or msg.get("mentions")
        or []
    )
    mentioned_jids = (
        tuple(str(m) for m in raw_mentions)
        if isinstance(raw_mentions, list)
        else ()
    )

    sender_contact_id = str(msg.get("senderContactId") or "")

    # Quote-reply: when the user replies-to a previous message, ChatDaddy
    # delivers the quoted message under ``quoted``. If that quoted message
    # was sent by the bot (``fromMe=true``), this inbound is a reply to
    # the bot — treat as tag-equivalent in the group gate.
    quoted = msg.get("quoted") or {}
    quoted_from_me = bool(
        isinstance(quoted, dict) and quoted.get("fromMe")
    )

    # Inject quoted text into the message so the agent has full context.
    # Without this, a reply of "好" to the bot's soup recipe looks like
    # a standalone "好" with no context — agent can't tell what they agreed to.
    if isinstance(quoted, dict):
        quoted_text = (quoted.get("text") or "").strip()
        if quoted_text:
            prefix = "[回覆你講嘅]" if quoted_from_me else "[引用]"
            # Truncate long quoted messages (e.g. soup recipes) to 200 chars
            quoted_snippet = quoted_text[:200] + ("…" if len(quoted_text) > 200 else "")
            quote_block = f"{prefix}: 「{quoted_snippet}」"
            text = f"{quote_block}\n{text}" if text else quote_block

    if not chat_id:
        return None

    return ChatDaddyMessage(
        event=event,
        message_id=message_id,
        chat_id=chat_id,
        account_id=account_id,
        text=text,
        from_me=from_me,
        timestamp=timestamp,
        sender_name=sender_name,
        attachments=attachments,
        mentioned_jids=mentioned_jids,
        sender_contact_id=sender_contact_id,
        quoted_from_me=quoted_from_me,
    )
