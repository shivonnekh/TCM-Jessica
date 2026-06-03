"""Tests for group_gate.decide_group() and effective_user_phone."""
from __future__ import annotations

import pytest

from src.whatsapp.group_gate import GroupAction, decide_group
from src.whatsapp.models import ChatDaddyMessage

BOT_JID = "85298765432"
BOT_NAMES = ["Jessica", "jessica"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_msg(
    text: str = "",
    mentioned_jids: tuple[str, ...] = (),
    quoted_from_me: bool = False,
    sender_contact_id: str = "67890123456789@lid",
    sender_name: str = "陳太",
) -> ChatDaddyMessage:
    return ChatDaddyMessage(
        event="message-insert",
        message_id="msg1",
        chat_id="120363123456789012@g.us",
        account_id="acc1",
        text=text,
        from_me=False,
        timestamp=1700000000,
        sender_name=sender_name,
        mentioned_jids=mentioned_jids,
        sender_contact_id=sender_contact_id,
        quoted_from_me=quoted_from_me,
    )


def _dm_msg(text: str = "hi") -> ChatDaddyMessage:
    return ChatDaddyMessage(
        event="message-insert",
        message_id="msg2",
        chat_id="85291234567@s.whatsapp.net",
        account_id="acc1",
        text=text,
        from_me=False,
        timestamp=1700000000,
    )


# ---------------------------------------------------------------------------
# effective_user_phone
# ---------------------------------------------------------------------------

class TestEffectiveUserPhone:
    def test_dm_returns_phone_digits(self):
        msg = _dm_msg()
        assert msg.effective_user_phone == "85291234567"

    def test_group_returns_g_prefix_plus_sender_id(self):
        msg = _group_msg(sender_contact_id="67890123456789@lid")
        assert msg.effective_user_phone == "g_67890123456789"

    def test_group_sender_id_strips_lid_suffix(self):
        msg = _group_msg(sender_contact_id="99999999999999@lid")
        assert msg.effective_user_phone == "g_99999999999999"

    def test_group_no_sender_contact_id_falls_back_to_chat_id(self):
        # When senderContactId is missing, sender_id falls back to chat_id split
        msg = _group_msg(sender_contact_id="")
        # chat_id = "120363123456789012@g.us" → sender_id = "120363123456789012"
        assert msg.effective_user_phone == "g_120363123456789012"


# ---------------------------------------------------------------------------
# decide_group — REPLY cases
# ---------------------------------------------------------------------------

class TestDecideGroupReply:
    def test_jid_in_mentioned_jids_triggers_reply(self):
        msg = _group_msg(
            text="大家食咩好？",
            mentioned_jids=(f"{BOT_JID}@s.whatsapp.net",),
        )
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_quote_reply_to_bot_triggers_reply(self):
        msg = _group_msg(text="好呀", quoted_from_me=True)
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_at_digits_in_text_triggers_reply(self):
        msg = _group_msg(text=f"@{BOT_JID} 我個頭好痛")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_at_jessica_in_text_triggers_reply(self):
        msg = _group_msg(text="@Jessica 幫我推薦湯水啦")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_at_jessica_lowercase_triggers_reply(self):
        msg = _group_msg(text="@jessica 你好")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_at_jessica_case_insensitive(self):
        msg = _group_msg(text="@JESSICA 幫我")
        # Our check is case-insensitive — both text and names lowercased
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_custom_bot_name_triggers_reply(self):
        msg = _group_msg(text="@Jessica姐 可唔可以介紹下湯水？")
        assert decide_group(msg, BOT_JID, ["Jessica姐"]) == GroupAction.REPLY

    def test_bare_name_no_at_triggers_reply(self):
        # The exact prod case (2026-06-03): user addressed her by name with
        # no @ symbol. ChatDaddy sends no mentionedJids on non-WABA, so this
        # must be caught by bare-name matching.
        msg = _group_msg(text="hi jessica, whats the weather today")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_bare_name_followed_by_cjk_triggers_reply(self):
        msg = _group_msg(text="jessica你好，想問下湯水")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_bare_name_start_of_message_triggers_reply(self):
        msg = _group_msg(text="Jessica 我個頭好痛")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.REPLY

    def test_jid_match_ignores_missing_jid_config(self):
        # If BOT_JID is blank, JID-based detection is skipped — still LISTEN
        msg = _group_msg(mentioned_jids=(f"{BOT_JID}@s.whatsapp.net",))
        assert decide_group(msg, "", BOT_NAMES) == GroupAction.LISTEN


# ---------------------------------------------------------------------------
# decide_group — LISTEN cases
# ---------------------------------------------------------------------------

class TestDecideGroupListen:
    def test_untagged_message_is_listen(self):
        msg = _group_msg(text="今日天氣好好")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.LISTEN

    def test_at_digits_mismatch_is_listen(self):
        # Someone else is @-tagged, not the bot
        msg = _group_msg(text="@85299999999 你好")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.LISTEN

    def test_name_embedded_in_larger_word_is_listen(self):
        # "jessicaa" — the name is a substring of a longer ASCII token, not
        # an address. Word-boundary matching must NOT fire here.
        msg = _group_msg(text="jessicaa is my username")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.LISTEN

    def test_empty_text_is_listen(self):
        msg = _group_msg(text="")
        assert decide_group(msg, BOT_JID, BOT_NAMES) == GroupAction.LISTEN

    def test_no_bot_jid_no_bot_names_is_always_listen(self):
        msg = _group_msg(text="@Jessica 你好")
        assert decide_group(msg, "", []) == GroupAction.LISTEN
