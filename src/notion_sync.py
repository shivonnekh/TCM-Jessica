"""notion_sync.py — auto-wire new Notion content into comment_responses.json.

WHY THIS EXISTS
---------------
ai-tcm-ip (the Notion-driven content factory) authors CTA keywords + First DM
copy for every post before it ships. Historically, getting that keyword live
on this bot required a human to notice a post went out and manually add a
rule to ``data/channels/comment_responses.json`` — which is exactly how the
"eye" and "migraine" posts sat silent for a day (see 2026-07-01 incident).

This module closes that gap without merging the two repos: it reads
Production Tracker directly (stdlib ``urllib``, no ai-tcm-ip import needed —
these are separate Render deployments) and, the moment a row's ``Stage``
flips to ``✅ Published``, mechanically drafts + wires a keyword rule here.

WHAT IT DOES NOT DO
--------------------
- Does not generate infographic images (that still requires ai-tcm-ip's
  GPT-image pipeline). New keywords land as text-only DMs; images are added
  by hand afterward (copy into ``data/media/guides/`` + add ``image_urls``).
- Does not touch anything outside ``comment_responses.json`` +
  ``notion_sync_state.json``.

STATE
-----
``data/channels/notion_sync_state.json`` — list of Production Tracker row
ids already processed, so re-running (the webhook can fire more than once
per edit) never double-adds a rule.

Entry point: ``sync_once()``, called from ``POST /admin/notion-sync``
in ``src/web.py``.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
_IDS_PATH = REPO_ROOT / "scripts" / "notion_ids.json"
_RULES_PATH = REPO_ROOT / "data" / "channels" / "comment_responses.json"
_STATE_PATH = REPO_ROOT / "data" / "channels" / "notion_sync_state.json"

NOTION_API = "https://api.notion.com/v1"
_STOP_WORDS = {"comment", "the", "word", "below", "type", "now"}

# IP Registry title → (account_id, language). Extend as new IPs go live.
# Matches the same accounts already wired in meta_client._ACCOUNT_CREDS_ENV
# and comment_rules._ACCOUNT_LANGUAGE.
_IP_ACCOUNT: dict[str, tuple[str, str]] = {
    "jackie": ("17841417304649448", "en"),
    "chloe": ("17841424706900394", "yue"),
    "jessica": ("17841424706900394", "yue"),  # legacy IP name, same account
}

_VOICE_TEMPLATE = {
    "en": (
        "Hey, I'm Jackie 🌿 Thanks for commenting.\n\n"
        "{tip}\n\n"
        "Want to tell me more about what you're experiencing? Reply here 👇"
    ),
    "yue": (
        "多謝你留言！🌿 我係芷晴～\n\n"
        "{tip}\n\n"
        "有任何症狀想傾？回覆我 👇"
    ),
}
_ACK_TEMPLATE = {
    "en": "I've sent you the TCM {title} guide — check your DM! 🌿",
    "yue": "Send咗中醫{title}資料俾你喇 — 入嚟睇下 DM！🌿",
}


class NotionSyncError(RuntimeError):
    pass


def _notion_key() -> str:
    key = os.environ.get("NOTION_KEY", "").strip()
    if not key:
        raise NotionSyncError("NOTION_KEY not set")
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_notion_key()}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _ncall(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{NOTION_API}{path}", data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise NotionSyncError(f"Notion API {method} {path} failed: {exc.code} {detail}") from exc


def _query_all(db_id: str) -> list[dict]:
    rows: list[dict] = []
    cursor: str | None = None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        d = _ncall("POST", f"/databases/{db_id}/query", body)
        rows.extend(d["results"])
        if not d.get("has_more"):
            return rows
        cursor = d["next_cursor"]


def _title(page: dict) -> str:
    for prop in page["properties"].values():
        if prop.get("type") == "title":
            return "".join(t["plain_text"] for t in prop["title"])
    return ""


def _children(block_id: str) -> list[dict]:
    out: list[dict] = []
    cursor: str | None = None
    while True:
        suffix = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        d = _ncall("GET", f"/blocks/{block_id}/children{suffix}")
        out.extend(d["results"])
        if not d.get("has_more"):
            return out
        cursor = d["next_cursor"]


def _block_text(block: dict) -> str:
    t = block["type"]
    return "".join(x.get("plain_text", "") for x in block.get(t, {}).get("rich_text", []))


def normalize_keyword(cta: str) -> str:
    if not cta:
        return ""
    quoted = re.search(r"[\"'“”‘’]([^\"'“”‘’]+)[\"'“”‘’]", cta)
    if quoted:
        return quoted.group(1).strip().lower().split()[0]
    tokens = re.findall(r"[a-zA-Z]+", cta.lower())
    for tok in tokens:
        if tok not in _STOP_WORDS:
            return tok
    return tokens[0] if tokens else ""


def _extract_first_dm(content_page_id: str) -> str:
    """Walk a Content Library page body → the 'First DM' code block text."""
    label = None
    for block in _children(content_page_id):
        t = block["type"]
        text = _block_text(block)
        if t == "heading_3":
            label = "first_dm" if "First DM" in text else None
        elif t == "code" and label == "first_dm":
            return text
    return ""


def _ip_account(ip_full_name: str) -> tuple[str, str] | None:
    name = ip_full_name.split("(")[0].strip().lower()
    for key, val in _IP_ACCOUNT.items():
        if key in name:
            return val
    return None


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _draft_rule(keyword: str, title: str, first_dm: str, language: str, account_id: str) -> dict:
    """Mechanically template the raw Notion first_dm into this bot's established
    per-brand DM voice (matches the pattern used by every hand-authored rule:
    opening line + tip body + closing CTA). No LLM call — deterministic,
    free, instant. A human (or a follow-up LLM pass) can refine wording later;
    this guarantees a live, on-voice DM the moment content goes public."""
    tip = first_dm.strip()
    dm_text = _VOICE_TEMPLATE[language].format(tip=tip)
    ack = _ACK_TEMPLATE[language].format(title=keyword)
    return {
        "keyword": keyword,
        "language": language,
        "accounts": [account_id],
        "dm_text": dm_text,
        "public_ack": ack,
        "use_agent": False,
        "_source": "notion_sync",
        "_notion_title": title,
    }


def sync_once() -> dict[str, Any]:
    """Find newly-Published Production rows, draft + wire keyword rules.

    Idempotent: rows already recorded in notion_sync_state.json are skipped.
    Returns a summary dict — never raises for expected "nothing to do" paths,
    but does raise NotionSyncError for auth/config problems (caller maps that
    to a 5xx so the Notion Automation retries later).
    """
    ids = json.loads(_IDS_PATH.read_text(encoding="utf-8"))
    state: list[str] = _load_json(_STATE_PATH, [])
    state_set = set(state)

    rows = _query_all(ids["prod_db"])
    added: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    rules: list[dict] = _load_json(_RULES_PATH, [])
    existing_keys = {(r.get("keyword"), tuple(r.get("accounts") or [])) for r in rules}

    for row in rows:
        row_id = row["id"]
        if row_id in state_set:
            continue

        props = row["properties"]
        stage = (props.get("Stage", {}).get("select") or {}).get("name", "")
        if stage != "✅ Published":
            continue  # not published yet — leave unmarked, check again next sync

        content_rel = props.get("Content", {}).get("relation") or []
        ip_rel = props.get("IP", {}).get("relation") or []
        if not content_rel or not ip_rel:
            state_set.add(row_id)
            skipped.append(f"{row_id}: missing Content/IP relation")
            continue

        try:
            content_page = _ncall("GET", f"/pages/{content_rel[0]['id']}")
            ip_page = _ncall("GET", f"/pages/{ip_rel[0]['id']}")
        except NotionSyncError as exc:
            errors.append(str(exc))
            continue  # transient — retry next sync, do NOT mark as processed

        ip_full = _title(ip_page)
        account = _ip_account(ip_full)
        if account is None:
            state_set.add(row_id)
            skipped.append(f"{row_id}: no known account for IP '{ip_full}'")
            continue
        account_id, language = account

        title = _title(content_page)
        cta = "".join(
            t["plain_text"] for t in content_page["properties"].get("CTA", {}).get("rich_text", [])
        )
        keyword = normalize_keyword(cta)
        if not keyword:
            state_set.add(row_id)
            skipped.append(f"{row_id}: no CTA keyword ('{title}')")
            continue

        first_dm = _extract_first_dm(content_rel[0]["id"])
        if not first_dm:
            skipped.append(f"{row_id}: Material not authored yet ('{title}') — will retry")
            continue  # do NOT mark processed — Material may land later

        key = (keyword, (account_id,))
        if key in existing_keys:
            state_set.add(row_id)
            skipped.append(f"{row_id}: '{keyword}' rule already exists for this account")
            continue

        rule = _draft_rule(keyword, title, first_dm, language, account_id)
        rules.append(rule)
        existing_keys.add(key)
        state_set.add(row_id)
        added.append(f"{row_id}: added '{keyword}' ({language}, {title})")

    if added:
        _save_json(_RULES_PATH, rules)
    _save_json(_STATE_PATH, sorted(state_set))

    return {
        "checked": len(rows),
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "rules_changed": bool(added),
    }
