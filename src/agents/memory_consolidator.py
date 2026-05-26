"""Memory consolidator — auto-summary of conversation history into user.notes.

Why this exists:
    Jessica's rolling conversation window is capped at 20 messages. Any
    history older than that is in the DB but invisible to agents. After
    every 15 new messages, this consolidator reads the un-summarised
    portion, extracts key insights, and appends them to user.notes — so
    next time the user returns, Jessica still "remembers" older context.

Trigger:
    pipeline.py fires this as an asyncio background task after save_user.
    It's fire-and-forget — latency impact on the main turn is zero.

Model:
    gpt-4o-mini (cheap, fast). Memory consolidation doesn't need
    high-reasoning capacity — just structured extraction.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.crm.models import ConversationMessage, User
from src.llm import DEFAULT_MODEL

logger = logging.getLogger("memory_consolidator")

# Minimum number of new messages since last consolidation before we bother.
MIN_NEW_MESSAGES = 15

# Maximum messages to read per consolidation run.
MSG_LIMIT = 60

_SYSTEM_PROMPT = """\
你係 Jessica，心宜中醫嘅 WhatsApp 健康顧問。
你嘅任務係根據最新嘅對話，更新用戶嘅記憶筆記。

記憶筆記嘅作用：幫你下次見到呢個用戶時，唔使佢重新介紹自己，
你已經知道佢嘅背景、健康狀況、同你哋之前講過咩。
"""

_USER_PROMPT_TMPL = """\
【現有筆記】
{existing_notes}

【最新對話（由舊到新）】
{conversation}

【任務】
根據以上對話，更新筆記。重點記錄：
• 健康問題或症狀（例：失眠、腰痛、皮膚差、消化唔好）
• 情緒或生活狀態（例：工作壓力大、最近心情低落、睡眠差）
• 對產品嘅反應（例：飲咗xxx湯，話有改善 / 唔鍾意味道）
• 重要個人資料（例：媽媽身體差、有兩個細路、係護士）
• 任何下次值得記住嘅事

規則：
- 保留舊有重要資訊，唔好刪除
- 只加入新嘢，唔好重複已有內容
- 用廣東話口語，簡潔清晰，每點一兩句
- 筆記總長唔超過 400 字
- 如果呢段對話完全冇新嘢值得記，只需返回原有筆記，唔好加任何說明文字
"""


def _format_messages(messages: list[ConversationMessage]) -> str:
    lines: list[str] = []
    for msg in messages:
        speaker = "用戶" if msg.role == "user" else "Jessica"
        lines.append(f"[{speaker}] {msg.content}")
    return "\n".join(lines)


async def consolidate_memory(
    crm: Any,
    llm: Any,
    user: User,
) -> User:
    """Read un-summarised messages and update user.notes.

    Returns the updated User (already saved to CRM).
    Does nothing and returns the original User if there's nothing to consolidate.
    """
    last_at_str: str | None = user.temp_state.get("last_consolidated_at")
    since: datetime | None = (
        datetime.fromisoformat(last_at_str) if last_at_str else None
    )

    messages = await crm.get_messages_since(user.phone, since=since, limit=MSG_LIMIT)

    if len(messages) < MIN_NEW_MESSAGES:
        logger.debug(
            "memory_consolidator: skip %s — only %d new messages (need %d)",
            user.phone[-4:],
            len(messages),
            MIN_NEW_MESSAGES,
        )
        return user

    logger.info(
        "memory_consolidator: consolidating %d messages for %s",
        len(messages),
        user.phone[-4:],
    )

    existing_notes = user.notes.strip() or "（未有筆記）"
    conversation_text = _format_messages(messages)

    prompt = _USER_PROMPT_TMPL.format(
        existing_notes=existing_notes,
        conversation=conversation_text,
    )

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=600,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        updated_notes = response.content[0].text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("memory_consolidator: LLM call failed for %s: %s", user.phone[-4:], exc)
        return user

    if not updated_notes or updated_notes == existing_notes:
        # Nothing new — still bump the timestamp so we don't re-read same messages
        updated_notes = user.notes

    new_temp = {
        **user.temp_state,
        "last_consolidated_at": datetime.utcnow().isoformat(),
    }
    updated_user = user.with_updates(notes=updated_notes, temp_state=new_temp)
    await crm.save_user(updated_user)

    logger.info(
        "memory_consolidator: done for %s — notes now %d chars",
        user.phone[-4:],
        len(updated_notes),
    )
    return updated_user


async def should_consolidate(crm: Any, user: User) -> bool:
    """Return True if this user has enough new messages to warrant consolidation."""
    last_at_str: str | None = user.temp_state.get("last_consolidated_at")

    if last_at_str is None:
        # First time: only bother if there's history beyond the rolling window.
        total = await crm.get_message_count(user.phone)
        return total > 20

    since = datetime.fromisoformat(last_at_str)
    # Peek at message count since last consolidation without loading full content.
    recent = await crm.get_messages_since(user.phone, since=since, limit=MIN_NEW_MESSAGES)
    return len(recent) >= MIN_NEW_MESSAGES
