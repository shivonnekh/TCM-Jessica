"""backfill_comments.py — reply to comments that arrived before a keyword rule existed.

Meta webhooks never replay history: if a comment landed while a keyword had no
rule in ``data/channels/comment_responses.json``, the webhook saw it, found no
match, and silently skipped it forever. There is no "resend" on Meta's side.

This script closes that gap by pulling a post's comments directly via the
Graph API (read-only ``GET /{media_id}/comments``) and feeding each one through
the EXACT SAME ``handle_comment()`` used by the live webhook — same dedup,
same rule matching, same send calls. Safe to re-run: idempotency claims
(when a real CRM/pipeline is wired) or Meta's own dedup on repeated identical
private replies prevent double-sends. Here we run with ``pipeline=None``
(fine for ``use_agent: false`` canned rules — the only kind currently
configured), so no CRM persistence happens, just the actual Graph API sends.

Usage:
    python scripts/backfill_comments.py <media_id> [<media_id> ...]
    python scripts/backfill_comments.py --account 17841417304649448 --list   # discover recent media ids

Env: reads server credentials from .env (same as the live webhook).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from src.channels import meta_client  # noqa: E402
from src.channels.meta_events import IncomingComment  # noqa: E402
from src.channels.meta_webhook import handle_comment  # noqa: E402

DEFAULT_ACCOUNT_ID = "17841417304649448"  # jackiechan.tcm


async def _backfill_media(media_id: str, account_id: str) -> None:
    comments = await meta_client.list_comments(
        media_id, platform="instagram", account_id=account_id
    )
    print(f"\n=== media {media_id}: {len(comments)} comment(s) ===")
    if not comments:
        return

    for raw in comments:
        comment_id = str(raw.get("id") or "")
        from_id = str((raw.get("from") or {}).get("id") or "")
        username = str((raw.get("from") or {}).get("username") or raw.get("username") or "")
        text = str(raw.get("text") or "")
        if not comment_id or not from_id:
            print(f"  skip (missing id/from): {raw}")
            continue

        comment = IncomingComment(
            platform="instagram",
            comment_id=comment_id,
            text=text,
            from_id=from_id,
            from_username=username,
            media_id=media_id,
            recipient_id=account_id,
        )
        print(f"  -> [{username or from_id}] {text!r}")
        await handle_comment(comment, pipeline=None)  # type: ignore[arg-type]


async def _list_media(account_id: str) -> None:
    media = await meta_client.list_recent_media(platform="instagram", account_id=account_id)
    print(f"Recent media for account {account_id}:")
    for m in media:
        print(f"  {m.get('id')}  {m.get('timestamp')}  {m.get('caption', '')[:60]!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media_ids", nargs="*", help="Instagram media/post ids to backfill")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT_ID, help="business IG account id")
    parser.add_argument("--list", action="store_true", help="list recent media ids and exit")
    args = parser.parse_args()

    if args.list:
        asyncio.run(_list_media(args.account))
        return 0

    if not args.media_ids:
        parser.error("provide at least one media_id, or use --list to discover one")

    async def _run() -> None:
        for media_id in args.media_ids:
            await _backfill_media(media_id, args.account)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
