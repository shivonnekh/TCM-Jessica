"""Tests for the Instagram + Facebook (Meta) channel.

Covers the boundary layers that must be bulletproof:
    * ``meta_events.parse_meta_webhook`` — total parser over untrusted input
    * ``meta_webhook.verify_signature``  — X-Hub-Signature-256 validation
    * ``comment_rules``                  — canned keyword → DM resolution
and the dispatch glue (DM text+image interleave, canned vs agent comment)
with a fake pipeline + a monkeypatched ``meta_client``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field

import pytest

from src.channels import comment_rules, meta_client, meta_webhook
from src.channels.meta_events import (
    IncomingComment,
    IncomingDM,
    parse_meta_webhook,
)
from src.crm.models import User

# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _dm_payload(text="我成日口氣好重", *, is_echo=False, mid="m1", obj="instagram") -> dict:
    return {
        "object": obj,
        "entry": [{
            "id": "BIZ",
            "messaging": [{
                "sender": {"id": "IGSID123"},
                "recipient": {"id": "BIZ"},
                "timestamp": 1700000000000,
                "message": {"mid": mid, "text": text, "is_echo": is_echo},
            }],
        }],
    }


def _comment_payload(text="gut", *, cid="c1") -> dict:
    return {
        "object": "instagram",
        "entry": [{
            "id": "BIZ",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": cid, "text": text,
                    "from": {"id": "U9", "username": "amy"},
                    "media": {"id": "media42"},
                },
            }],
        }],
    }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_dm():
    dm = parse_meta_webhook(_dm_payload())[0]
    assert isinstance(dm, IncomingDM)
    assert dm.crm_key == "ig_IGSID123"
    assert dm.text == "我成日口氣好重"
    assert dm.is_echo is False


@pytest.mark.unit
def test_parse_echo_flagged():
    assert parse_meta_webhook(_dm_payload(is_echo=True))[0].is_echo is True


@pytest.mark.unit
def test_parse_comment():
    ev = parse_meta_webhook(_comment_payload())[0]
    assert isinstance(ev, IncomingComment)
    assert ev.crm_key == "ig_U9"
    assert ev.media_id == "media42"


@pytest.mark.unit
def test_parse_facebook_page_object():
    payload = {
        "object": "page",
        "entry": [{
            "id": "PAGE",
            "messaging": [{
                "sender": {"id": "PSID1"},
                "recipient": {"id": "PAGE"},
                "message": {"mid": "fm1", "text": "hi"},
            }],
        }],
    }
    dm = parse_meta_webhook(payload)[0]
    assert dm.platform == "facebook"
    assert dm.crm_key == "fb_PSID1"


@pytest.mark.unit
@pytest.mark.parametrize("bad", [None, "str", 123, {}, {"object": "x", "entry": []}, {"object": "instagram"}])
def test_parse_garbage_returns_empty(bad):
    assert parse_meta_webhook(bad) == []


@pytest.mark.unit
def test_parse_skips_message_without_mid():
    payload = _dm_payload()
    del payload["entry"][0]["messaging"][0]["message"]["mid"]
    assert parse_meta_webhook(payload) == []


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_signature_dev_no_secret_passes(monkeypatch):
    monkeypatch.setattr(meta_webhook, "APP_ENV", "development")
    monkeypatch.setenv("META_APP_SECRET", "")
    assert meta_webhook.verify_signature(b"{}", "") is True


@pytest.mark.unit
def test_signature_prod_no_secret_fails(monkeypatch):
    monkeypatch.setattr(meta_webhook, "APP_ENV", "production")
    monkeypatch.setenv("META_APP_SECRET", "")
    assert meta_webhook.verify_signature(b"{}", "") is False


@pytest.mark.unit
def test_signature_correct_and_wrong(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "shh")
    raw = b'{"a":1}'
    good = "sha256=" + hmac.new(b"shh", raw, hashlib.sha256).hexdigest()
    assert meta_webhook.verify_signature(raw, good) is True
    assert meta_webhook.verify_signature(raw, "sha256=deadbeef") is False
    assert meta_webhook.verify_signature(raw, "") is False


# ---------------------------------------------------------------------------
# Dedup + handshake
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dedup(monkeypatch):
    monkeypatch.setattr(meta_webhook, "_seen_ids", type(meta_webhook._seen_ids)())
    assert meta_webhook.is_duplicate("a") is False
    assert meta_webhook.is_duplicate("a") is True
    assert meta_webhook.is_duplicate("") is False


@pytest.mark.unit
def test_verify_subscription(monkeypatch):
    monkeypatch.setenv("META_VERIFY_TOKEN", "tok")
    assert meta_webhook.verify_subscription("subscribe", "tok", "1234") == "1234"
    assert meta_webhook.verify_subscription("subscribe", "wrong", "1234") is None
    assert meta_webhook.verify_subscription("delete", "tok", "1234") is None


# ---------------------------------------------------------------------------
# comment_rules
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_comment_rules_match(tmp_path, monkeypatch):
    cfg = tmp_path / "rules.json"
    cfg.write_text(json.dumps({
        "gut": {"dm_text": "腸胃懶人包", "image_url": "https://x/y.png", "public_ack": "send咗喇"},
        "濕熱": {"dm_text": "濕熱調理", "use_agent": True},
    }), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()

    r = comment_rules.match("please send me GUT info")
    assert r is not None and r.keyword == "gut" and r.dm_text == "腸胃懶人包"
    assert r.use_agent is False

    r2 = comment_rules.match("我想知濕熱")
    assert r2 is not None and r2.use_agent is True

    assert comment_rules.match("random words") is None


@pytest.mark.unit
def test_comment_rules_missing_file(monkeypatch):
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", "/no/such/file.json")
    comment_rules._load_raw.cache_clear()
    assert comment_rules.load_rules() == ()
    assert comment_rules.match("gut") is None


# ---------------------------------------------------------------------------
# Dispatch — fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeWriterOutput:
    bubbles: list[str] = field(default_factory=list)
    media_to_send: list[dict] = field(default_factory=list)


@dataclass
class _FakeResult:
    writer_output: _FakeWriterOutput


class _FakePipeline:
    def __init__(self, bubbles, media=None):
        self._out = _FakeWriterOutput(list(bubbles), list(media or []))
        self.calls = []

    async def run_turn(self, *, phone, user_message, wa_message_id=None, **_):
        self.calls.append({"phone": phone, "msg": user_message})
        return _FakeResult(self._out)


@pytest.mark.asyncio
async def test_handle_dm_interleaves_text_and_image(monkeypatch):
    sent = []

    async def fake_send_dm(rid, text, *, platform="instagram", **_):
        sent.append(("text", rid, text, platform)); return meta_client.SendResult(True)

    async def fake_send_dm_image(rid, url, *, platform="instagram", **_):
        sent.append(("image", rid, url, platform)); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_dm", fake_send_dm)
    monkeypatch.setattr(meta_client, "send_dm_image", fake_send_dm_image)
    monkeypatch.setattr(meta_webhook, "_BUBBLE_PAUSE_S", 0.0)
    monkeypatch.setattr(meta_webhook, "_MEDIA_PAUSE_S", 0.0)

    dm = IncomingDM(platform="instagram", sender_id="IGSID123", recipient_id="BIZ",
                    text="有咩湯水", message_id="m1", timestamp=0)
    pipe = _FakePipeline(
        ["第一款湯水", "第二款"],
        media=[{"url": "https://x/soup.png", "after_bubble_idx": 0}],
    )
    await meta_webhook._dispatch_dm(dm, pipe)

    assert pipe.calls[0]["phone"] == "ig_IGSID123"
    # text(0) → image(after 0) → text(1)
    assert [s[0] for s in sent] == ["text", "image", "text"]
    assert sent[1] == ("image", "IGSID123", "https://x/soup.png", "instagram")


@pytest.mark.asyncio
async def test_handle_comment_canned_no_agent(monkeypatch, tmp_path):
    cfg = tmp_path / "rules.json"
    cfg.write_text(json.dumps({
        "gut": {"dm_text": "腸胃懶人包送俾你", "image_url": "https://x/g.png", "public_ack": "send咗喇"},
    }), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()
    monkeypatch.setattr(meta_webhook, "_MEDIA_PAUSE_S", 0.0)

    private, public, images = [], [], []

    async def fake_priv(cid, text, *, platform="instagram", **_):
        private.append((cid, text)); return meta_client.SendResult(True)

    async def fake_pub(cid, text, *, platform="instagram", **_):
        public.append((cid, text)); return meta_client.SendResult(True)

    async def fake_img(rid, url, *, platform="instagram", **_):
        images.append((rid, url)); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_private_reply", fake_priv)
    monkeypatch.setattr(meta_client, "reply_to_comment", fake_pub)
    monkeypatch.setattr(meta_client, "send_dm_image", fake_img)

    comment = IncomingComment(platform="instagram", comment_id="c1", text="gut pls",
                              from_id="U9", from_username="amy", media_id="m42")
    pipe = _FakePipeline(["AGENT SHOULD NOT RUN"])
    await meta_webhook.handle_comment(comment, pipe)

    assert pipe.calls == []                       # agent never ran
    assert private == [("c1", "腸胃懶人包送俾你")]   # canned DM sent
    assert public == [("c1", "send咗喇")]          # public ack sent
    assert images == []                             # images wait for DM reply


class _FakeCRM:
    def __init__(self):
        self.claimed = set()
        self.messages = []
        self.users = {}

    async def try_claim_webhook_event(self, event_id, kind):
        if event_id in self.claimed:
            return False
        self.claimed.add(event_id)
        return True

    async def get_user(self, phone):
        return self.users.get(phone)

    async def get_or_create_user(self, phone):
        if phone not in self.users:
            self.users[phone] = User(phone=phone)
        return self.users[phone]

    async def save_user(self, user):
        self.users[user.phone] = user

    async def append_message(self, phone, msg):
        self.messages.append((phone, msg))


@pytest.mark.asyncio
async def test_handle_comment_persistent_dedup_blocks_repeat(monkeypatch, tmp_path):
    cfg = tmp_path / "rules.json"
    cfg.write_text(json.dumps({
        "gut": {
            "dm_text": "腸胃懶人包送俾你",
            "image_url": "https://x/g.png",
            "public_ack": "send咗喇",
        },
    }), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()
    monkeypatch.setattr(meta_webhook, "_MEDIA_PAUSE_S", 0.0)

    private, public, images = [], [], []

    async def fake_priv(cid, text, *, platform="instagram", **_):
        private.append((cid, text)); return meta_client.SendResult(True)

    async def fake_pub(cid, text, *, platform="instagram", **_):
        public.append((cid, text)); return meta_client.SendResult(True)

    async def fake_img(rid, url, *, platform="instagram", **_):
        images.append((rid, url)); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_private_reply", fake_priv)
    monkeypatch.setattr(meta_client, "reply_to_comment", fake_pub)
    monkeypatch.setattr(meta_client, "send_dm_image", fake_img)

    comment = IncomingComment(platform="instagram", comment_id="c1", text="gut pls",
                              from_id="U9", from_username="amy", media_id="m42")
    pipe = _FakePipeline(["AGENT SHOULD NOT RUN"])
    crm = _FakeCRM()
    pipe._crm = crm

    await meta_webhook.handle_comment(comment, pipe)
    await meta_webhook.handle_comment(comment, pipe)

    assert private == [("c1", "腸胃懶人包送俾你")]
    assert public == [("c1", "send咗喇")]
    assert images == []
    assert crm.users["ig_U9"].temp_state["meta_pending_guide_images"] == ["https://x/g.png"]
    assert [m[0] for m in crm.messages] == ["ig_U9", "ig_U9"]
    assert crm.messages[0][1].role == "user"
    assert crm.messages[0][1].content == "gut pls"
    assert crm.messages[1][1].role == "chloe"
    assert crm.messages[1][1].media_urls == ["https://x/g.png"]


@pytest.mark.asyncio
async def test_dm_reply_sends_pending_comment_guide_images(monkeypatch):
    monkeypatch.setattr(meta_webhook, "_MEDIA_PAUSE_S", 0.0)
    images = []

    async def fake_img(rid, url, *, platform="instagram", **_):
        images.append((rid, url)); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_dm_image", fake_img)

    crm = _FakeCRM()
    await crm.save_user(User(phone="ig_U9", temp_state={
        "meta_pending_guide_images": ["https://x/g1.png", "https://x/g2.png"],
    }))
    pipe = _FakePipeline(["AGENT SHOULD NOT RUN"])
    pipe._crm = crm

    dm = IncomingDM(platform="instagram", sender_id="U9", recipient_id="BIZ",
                    text="yes please", message_id="m2", timestamp=0)
    await meta_webhook._dispatch_dm(dm, pipe)

    assert images == [("U9", "https://x/g1.png"), ("U9", "https://x/g2.png")]
    assert pipe.calls == []
    assert "meta_pending_guide_images" not in crm.users["ig_U9"].temp_state


@pytest.mark.asyncio
async def test_handle_comment_use_agent_runs_pipeline(monkeypatch, tmp_path):
    cfg = tmp_path / "rules.json"
    cfg.write_text(json.dumps({
        "ask": {"dm_text": "", "use_agent": True},
    }), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()

    private = []

    async def fake_priv(cid, text, *, platform="instagram", **_):
        private.append((cid, text)); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_private_reply", fake_priv)

    comment = IncomingComment(platform="instagram", comment_id="c2", text="ask me anything",
                              from_id="U9", from_username="amy", media_id="m42")
    pipe = _FakePipeline(["你好", "想問咩"])
    await meta_webhook.handle_comment(comment, pipe)

    assert pipe.calls and pipe.calls[0]["phone"] == "ig_U9"
    assert private == [("c2", "你好\n\n想問咩")]


@pytest.mark.asyncio
async def test_handle_comment_no_rule_skips(monkeypatch, tmp_path):
    cfg = tmp_path / "rules.json"
    cfg.write_text(json.dumps({"gut": {"dm_text": "x"}}), encoding="utf-8")
    monkeypatch.setenv("COMMENT_RESPONSES_PATH", str(cfg))
    comment_rules._load_raw.cache_clear()

    called = []

    async def fake_priv(cid, text, *, platform="instagram", **_):
        called.append(cid); return meta_client.SendResult(True)

    monkeypatch.setattr(meta_client, "send_private_reply", fake_priv)
    comment = IncomingComment(platform="instagram", comment_id="c3", text="thanks doctor",
                              from_id="U9", from_username="amy", media_id="m42")
    await meta_webhook.handle_comment(comment, _FakePipeline(["no"]))
    assert called == []


@pytest.mark.asyncio
async def test_process_post_disabled_short_circuits():
    body, status = await meta_webhook.process_post(
        raw=b"{}", signature_header="", pipeline=None, enabled=False,
    )
    assert status == 200 and body["status"] == "disabled"
