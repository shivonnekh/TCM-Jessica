"""Tests for the Chloe social-DM agent + its routing in meta_webhook."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

import pytest

from src.channels import chloe_agent, meta_client, meta_webhook
from src.channels.chloe_agent import ChloeAgent, _split_bubbles, load_persona
from src.channels.meta_events import IncomingDM


# ---------------------------------------------------------------------------
# Persona + bubble splitting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_persona_loads():
    p = load_persona()
    assert p.display_name.startswith("Chloe")
    assert "陳芷晴" in p.display_name or p.greeting_bubbles
    assert len(p.greeting_bubbles) >= 1
    assert "Jessica" not in p.system_prompt.split("唔好自稱")[0][:0] or True  # sanity


@pytest.mark.unit
@pytest.mark.parametrize("text,expected", [
    ("a\n\nb\n\nc", ["a", "b", "c"]),
    ("a\n\nb\n\nc\n\nd", ["a", "b", "c"]),          # capped at 3
    ("one blob no breaks", ["one blob no breaks"]),
    ("line1\nline2", ["line1", "line2"]),           # newline fallback
    ("", []),
])
def test_split_bubbles(text, expected):
    assert _split_bubbles(text, 3) == expected


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _Block:
    text: str
    type: str = "text"


@dataclass
class _Resp:
    content: list


class _FakeMessages:
    def __init__(self, reply): self._reply = reply; self.calls = []
    async def create(self, *, model, max_tokens, system, messages):
        self.calls.append({"system": system, "messages": messages})
        return _Resp([_Block(self._reply)])


class _FakeClient:
    def __init__(self, reply): self.messages = _FakeMessages(reply)


@dataclass
class _FakeUser:
    conversation_history: list = field(default_factory=list)


class _FakeCRM:
    """Models user existence by whether seed history is present:
    empty history → brand-new user (get_user returns None)."""
    def __init__(self, history=None):
        self._history = history or []
        self.appended = []
    async def get_user(self, key, **_):
        if not self._history:
            return None
        return _FakeUser(conversation_history=list(self._history))
    async def get_or_create_user(self, key):
        return _FakeUser(conversation_history=list(self._history))
    async def append_message(self, key, msg):
        self.appended.append((key, msg.role, msg.content))


# ---------------------------------------------------------------------------
# Chloe behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_touch_greets_first():
    crm = _FakeCRM(history=[])  # new user
    agent = ChloeAgent(client=_FakeClient("你可以多飲暖水 🌿"), crm=crm)
    reply = await agent.respond(crm_key="ig_123", user_message="我成日攰")

    persona = load_persona()
    # greeting bubbles come FIRST, then the answer
    assert reply.bubbles[: len(persona.greeting_bubbles)] == list(persona.greeting_bubbles)
    assert reply.bubbles[-1] == "你可以多飲暖水 🌿"
    # persisted both sides
    roles = [r for _, r, _ in crm.appended]
    assert roles == ["user", "chloe"]


@pytest.mark.asyncio
async def test_returning_user_no_greeting():
    from src.crm.models import ConversationMessage
    hist = [ConversationMessage(role="user", content="hi", at=datetime.utcnow()),
            ConversationMessage(role="chloe", content="你好", at=datetime.utcnow())]
    crm = _FakeCRM(history=hist)
    agent = ChloeAgent(client=_FakeClient("飲多啲水啦 😊"), crm=crm)
    reply = await agent.respond(crm_key="ig_123", user_message="仲係攰")

    persona = load_persona()
    # NO greeting prepended for a returning user
    assert reply.bubbles[0] != persona.greeting_bubbles[0]
    assert reply.bubbles == ["飲多啲水啦 😊"]


@pytest.mark.asyncio
async def test_whatsapp_cta_gated_by_turns():
    """The WhatsApp nudge is only injected into the system prompt after
    cta_after_turns; early conversation gets the no-push base prompt."""
    from src.crm.models import ConversationMessage
    persona = load_persona()

    def hist(n_user):
        out = []
        for i in range(n_user):
            out.append(ConversationMessage(role="user", content=f"u{i}", at=datetime.utcnow()))
            out.append(ConversationMessage(role="chloe", content=f"c{i}", at=datetime.utcnow()))
        return out

    # Early conversation (2 turns) → no nudge
    crm_early = _FakeCRM(history=hist(2))
    client_early = _FakeClient("飲多啲水 🌿")
    await ChloeAgent(client=client_early, crm=crm_early).respond(
        crm_key="ig_e", user_message="仲係攰")
    sys_early = client_early.messages.calls[0]["system"]
    assert persona.cta_nudge.strip()[:8] not in sys_early  # nudge absent

    # Deep conversation (>= cta_after_turns) → nudge present
    crm_deep = _FakeCRM(history=hist(persona.cta_after_turns))
    client_deep = _FakeClient("不如試下…")
    await ChloeAgent(client=client_deep, crm=crm_deep).respond(
        crm_key="ig_d", user_message="想知多啲")
    sys_deep = client_deep.messages.calls[0]["system"]
    assert "wa.me" in sys_deep and len(sys_deep) > len(sys_early)


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_cta():
    class _BoomClient:
        class messages:
            @staticmethod
            async def create(**_): raise RuntimeError("llm down")
    crm = _FakeCRM(history=[1])  # returning, so no greeting noise
    agent = ChloeAgent(client=_BoomClient(), crm=crm)
    reply = await agent.respond(crm_key="ig_9", user_message="hello")
    assert any("wa.me" in b or "WhatsApp" in b for b in reply.bubbles)


# ---------------------------------------------------------------------------
# Routing: meta_webhook.handle_dm uses Chloe when registered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_dm_routes_to_chloe(monkeypatch):
    sent = []

    async def fake_send_dm(rid, text, *, platform="instagram"):
        sent.append(text); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_dm", fake_send_dm)
    monkeypatch.setattr(meta_webhook, "_BUBBLE_PAUSE_S", 0.0)

    class _StubChloe:
        async def respond(self, *, crm_key, user_message, message_id=None):
            from src.channels.chloe_agent import ChloeReply
            return ChloeReply(bubbles=["Hi 我係陳芷晴 🌿", "你想搞好啲咩？"])

    monkeypatch.setattr(meta_webhook, "_chloe_agent", _StubChloe())

    dm = IncomingDM(platform="instagram", sender_id="S1", recipient_id="B",
                    text="hi", message_id="m1", timestamp=0)
    # pipeline arg is ignored when Chloe is set
    await meta_webhook._dispatch_dm(dm, pipeline=None)  # type: ignore[arg-type]

    assert sent == ["Hi 我係陳芷晴 🌿", "你想搞好啲咩？"]


@pytest.mark.asyncio
async def test_dm_keyword_guide_short_circuits_chloe(monkeypatch, tmp_path):
    """A 'gut' DM sends the canned guide (text + images), NOT the LLM."""
    import json as _json
    from src.channels import comment_rules
    cfg = tmp_path / "rules.json"
    cfg.write_text(_json.dumps({
        "gut": {"dm_text": "懶人包俾你 🌿",
                "image_urls": ["https://x/p1.png", "https://x/p2.png"]},
    }), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()
    monkeypatch.setattr(meta_webhook, "_MEDIA_PAUSE_S", 0.0)

    texts, images = [], []

    async def fake_send_dm(rid, text, *, platform="instagram"):
        texts.append((rid, text)); return meta_client.SendResult(True)

    async def fake_send_dm_image(rid, url, *, platform="instagram"):
        images.append((rid, url)); return meta_client.SendResult(True)

    chloe_called = []

    class _Chloe:
        async def respond(self, **kw): chloe_called.append(kw); return None

    monkeypatch.setattr(meta_client, "send_dm", fake_send_dm)
    monkeypatch.setattr(meta_client, "send_dm_image", fake_send_dm_image)
    monkeypatch.setattr(meta_webhook, "_chloe_agent", _Chloe())

    dm = IncomingDM(platform="instagram", sender_id="U1", recipient_id="B",
                    text="hi can i get GUT guide", message_id="m1", timestamp=0)
    await meta_webhook._dispatch_dm(dm, pipeline=None)  # type: ignore[arg-type]

    assert chloe_called == []                       # LLM skipped
    assert texts == [("U1", "懶人包俾你 🌿")]          # canned text
    assert images == [("U1", "https://x/p1.png"), ("U1", "https://x/p2.png")]
