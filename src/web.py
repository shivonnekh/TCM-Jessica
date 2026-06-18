"""FastAPI app — webhook receiver + trace viewer.

Endpoints:
    POST /webhook/chatdaddy   — incoming WhatsApp messages (via router)
    GET  /trace/{turn_id}     — JSON dump of a turn trace
    GET  /trace               — list recent traces (HTML)
    GET  /health              — simple liveness probe

The ``/webhook/chatdaddy`` endpoint is owned by ``src.whatsapp.router``.
For real ChatDaddy webhook traffic it does signature verification, dedup,
group-gate, blocklist, buffer/merge, and dispatches to the pipeline in
the background while returning 200 immediately. For dev / curl smoke
tests it accepts a minimal ``{"phone","text"}`` body and runs the
pipeline inline, returning the bubbles in the response.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.admin_views import router as admin_router
from src.agents.registry import build_specialist_registry
from src.crm.repo_factory import open_crm_repo, resolve_database_url
from src.llm import LLMClient
from src.orchestrator.pipeline import JessicaPipeline
from src.tools.embedder import Embedder
from src.tools.kb_index import KBIndex
from src.tools.kb_indexer import index_kb
from src.tools.kb_search import KBSearch
from src.tools.vector_store import VectorStore
from src.trace.writer import TraceWriter
from src.channels.facebook import router as facebook_router
from src.channels.facebook import set_pipeline as set_fb_pipeline
from src.channels.instagram import router as instagram_router
from src.channels.instagram import set_pipeline as set_ig_pipeline
from src.consultation.repo import ConsultationRepo
from src.consultation.router import router as consultation_router
from src.whatsapp import client as wa_client
from src.whatsapp.router import router as whatsapp_router
from src.whatsapp.router import set_pipeline as set_wa_pipeline

logger = logging.getLogger("web")

ROOT = Path(__file__).resolve().parent.parent
DB_URL = resolve_database_url(str(ROOT / "data" / "jessica.db"))
TRACE_DIR = os.environ.get("TRACE_DIR", str(ROOT / "traces"))
MEDIA_DIR = ROOT / "data" / "media"


# -------------------------------------------------------------------
# App lifecycle
# -------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    masked = DB_URL[:20] + "…" if len(DB_URL) > 25 else DB_URL
    logger.info("startup: connecting CRM at %s", masked)
    # For SQLite paths, ensure parent dir exists. Postgres URLs skip this.
    if not DB_URL.startswith(("postgres://", "postgresql://")):
        Path(DB_URL).parent.mkdir(parents=True, exist_ok=True)
    crm = await open_crm_repo(DB_URL)
    trace_writer = TraceWriter(TRACE_DIR)

    client = LLMClient()  # OpenAI under the hood, picks up OPENAI_API_KEY

    # ---- Vector KB (hybrid search) ----
    # If DATABASE_URL is Postgres, mount pgvector + embedder + run
    # idempotent index on startup. Skip cleanly if anything fails.
    vector_store = None
    embedder = None
    kb_index = KBIndex.load()
    if DB_URL.startswith(("postgres://", "postgresql://")):
        try:
            vector_store = await VectorStore.connect(DB_URL)
            embedder = Embedder()
            stats = await index_kb(kb=kb_index, store=vector_store, embedder=embedder)
            logger.info("vector KB ready: %s", stats)
        except Exception as exc:  # noqa: BLE001
            logger.exception("vector KB init failed (%s) — falling back to keyword-only", exc)
            vector_store = None
            embedder = None
    else:
        logger.info("DB is SQLite — vector search disabled (keyword-only)")

    app.state.kb_search = KBSearch(
        kb_index, vector_store=vector_store, embedder=embedder
    )
    app.state.vector_store = vector_store
    app.state.embedder = embedder

    specialists = build_specialist_registry(
        client, kb_search=app.state.kb_search
    )
    pipeline = JessicaPipeline(
        crm=crm,
        trace_writer=trace_writer,
        client=client,
        specialists=specialists,
    )

    app.state.crm = crm
    app.state.trace_writer = trace_writer
    app.state.pipeline = pipeline

    # Register the pipeline with the WhatsApp router so the webhook +
    # poller can dispatch turns to it.
    set_wa_pipeline(pipeline)
    # Same pipeline backs the Instagram + Facebook webhooks (opt-in via
    # IG_ENABLED / FB_ENABLED). CRM keys are namespaced ("ig_<igsid>",
    # "fb_<psid>") so surfaces never collide.
    set_ig_pipeline(pipeline)
    set_fb_pipeline(pipeline)

    # ---- Video consultation repo ----
    consultation_repo = await ConsultationRepo.connect(DB_URL)
    app.state.consultation_repo = consultation_repo

    # Social DMs use the Chloe persona (陳芷晴) — a separate, lighter route
    # from Jessica: greeting-first, drives to WhatsApp. Comments still use
    # the canned comment_rules.
    from src.channels.chloe_agent import ChloeAgent
    from src.channels.meta_webhook import set_chloe_agent
    chloe_agent = ChloeAgent(client=client, crm=crm,
                             consultation_repo=consultation_repo)
    set_chloe_agent(chloe_agent)
    app.state.chloe_agent = chloe_agent

    # Start background tasks — token refresh + (optional) polling fallback.
    # Both are best-effort: if ChatDaddy credentials aren't configured we
    # log a warning and continue (dev / smoke-test mode still works via
    # the inline pipeline path).
    background_tasks: list[asyncio.Task] = []
    if os.environ.get("CHATDADDY_REFRESH_TOKEN"):
        background_tasks.append(
            asyncio.create_task(wa_client.start_token_refresh_loop())
        )
        if os.environ.get("WA_POLL_ENABLED", "true").lower() == "true":
            # Import lazily so tests that don't touch the gateway can
            # still import web.py without httpx round-trips at start.
            from src.whatsapp.poller import start_polling_loop
            background_tasks.append(asyncio.create_task(start_polling_loop()))
    else:
        logger.warning(
            "CHATDADDY_REFRESH_TOKEN unset — outbound sends will fail. "
            "Set it before exposing the webhook publicly."
        )

    # Proactive weather broadcast loop — opt-in via env var (default OFF).
    # Requires CHATDADDY_ACCOUNT_ID + OPENAI_API_KEY to be set.
    if os.environ.get("BROADCAST_ENABLED", "false").lower() == "true":
        from src.broadcaster.scheduler import start_broadcast_loop
        from src.whatsapp.router import DEFAULT_ACCOUNT_ID
        background_tasks.append(
            asyncio.create_task(
                start_broadcast_loop(crm, client, DEFAULT_ACCOUNT_ID)
            )
        )
        logger.info("Broadcast loop scheduled (interval=6h, cap=2/user/week)")

    try:
        yield
    finally:
        logger.info("shutdown: closing CRM + background tasks")
        for task in background_tasks:
            task.cancel()
        await wa_client.close()
        await crm.close()
        await consultation_repo.close()
        if vector_store is not None:
            try:
                await vector_store.close()
            except Exception:  # noqa: BLE001
                pass


app = FastAPI(title="TCM-Jessica", version="0.1.0", lifespan=lifespan)
app.include_router(whatsapp_router)
app.include_router(instagram_router)
app.include_router(facebook_router)
app.include_router(admin_router)
app.include_router(consultation_router)

# Public-readable static media — ChatDaddy fetches these via the URL
# Jessica writes into `WriterOutput.media_to_send`.
if MEDIA_DIR.is_dir():
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Static assets for the consultation video page (consult.html served by router,
# but any future CSS/JS assets live here).
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Dev sandbox UI — http://localhost:8000/dev/ to test pipeline without WhatsApp.
DEV_UI_DIR = ROOT / "static" / "dev"
if DEV_UI_DIR.is_dir():
    app.mount("/dev", StaticFiles(directory=str(DEV_UI_DIR), html=True), name="dev")


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tcm-jessica"}


# Privacy policy + data deletion — required to publish the Meta App to Live mode.
_LEGAL_PAGE = """<!DOCTYPE html>
<html lang="zh-HK"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — 心宜中醫 Jessica</title>
<style>
 body{{font-family:-apple-system,"PingFang HK",sans-serif;max-width:720px;
 margin:40px auto;padding:0 20px;line-height:1.7;color:#222}}
 h1{{font-size:1.6rem}} h2{{font-size:1.15rem;margin-top:1.6em}}
 a{{color:#0a7}} small{{color:#888}}
</style></head><body>
{body}
<hr><small>心宜中醫 (Care Plus) · Jessica AI · 聯絡 / Contact:
<a href="https://wa.me/85252417448">wa.me/85252417448</a></small>
</body></html>"""

_PRIVACY_BODY = """
<h1>私隱政策 Privacy Policy</h1>
<p><small>最後更新 Last updated: 2026-06-05</small></p>

<p>心宜中醫 (Care Plus) 旗下嘅 AI 助手「Jessica」透過 WhatsApp、Instagram
及 Facebook Messenger 同用戶溝通。本政策說明我哋點樣收集、使用同保護你嘅資料。</p>

<h2>1. 我哋收集嘅資料 Information We Collect</h2>
<ul>
<li>你發送嘅訊息內容（文字、語音、圖片）</li>
<li>你的平台帳戶識別碼（Instagram / Facebook / WhatsApp ID）同顯示名稱</li>
<li>你主動提供嘅健康相關資訊（用作中醫體質建議）</li>
</ul>

<h2>2. 用途 How We Use It</h2>
<ul>
<li>回覆你嘅查詢、提供中醫養生及產品資訊</li>
<li>安排診所預約</li>
<li>改善服務質素</li>
</ul>
<p>我哋<strong>唔會</strong>將你嘅個人資料出售俾第三方。</p>

<h2>3. 資料保存與保安 Data Retention & Security</h2>
<p>對話記錄只用於提供服務，並以加密方式儲存。你可隨時要求刪除你嘅資料。</p>

<h2>4. 第三方服務 Third-Party Services</h2>
<p>我哋使用 Meta（Instagram / Facebook / WhatsApp）平台 API 傳遞訊息，
並使用 AI 模型生成回覆。相關資料受各供應商之私隱政策約束。</p>

<h2>5. 刪除你的資料 Data Deletion</h2>
<p>如需刪除你嘅所有資料，請參閱
<a href="/data-deletion">資料刪除說明</a>，或 WhatsApp
<a href="https://wa.me/85252417448">wa.me/85252417448</a> 通知我哋。</p>

<h2>6. 聯絡我哋 Contact</h2>
<p>任何私隱相關查詢，請 WhatsApp
<a href="https://wa.me/85252417448">wa.me/85252417448</a>。</p>
"""

_DATA_DELETION_BODY = """
<h1>資料刪除 Data Deletion Instructions</h1>
<p>你有權要求刪除我哋持有嘅所有關於你嘅資料。</p>
<h2>點樣要求刪除 How to request deletion</h2>
<ol>
<li>WhatsApp 我哋：<a href="https://wa.me/85252417448">wa.me/85252417448</a></li>
<li>或喺 Instagram / Facebook 私訊我哋，發送訊息「<strong>DELETE MY DATA</strong>」</li>
</ol>
<p>我哋會喺 30 日內刪除你嘅對話記錄及個人識別資料，並向你確認。</p>
"""


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy() -> str:
    return _LEGAL_PAGE.format(title="私隱政策 Privacy Policy", body=_PRIVACY_BODY)


@app.get("/data-deletion", response_class=HTMLResponse)
async def data_deletion() -> str:
    return _LEGAL_PAGE.format(title="資料刪除 Data Deletion", body=_DATA_DELETION_BODY)


@app.post("/admin/crm/reset")
async def admin_crm_reset(request: Request) -> JSONResponse:
    """Wipe one CRM record by key — for testing (e.g. reset a Chloe IG flow).

    Body: ``{"key": "ig_2069881150591895"}``. Guarded by ADMIN_RESET_TOKEN
    when set (header ``X-Admin-Token``); open in dev if unset.
    """
    expected = os.environ.get("ADMIN_RESET_TOKEN", "")
    if expected and request.headers.get("X-Admin-Token", "") != expected:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    key = (body.get("key") or "").strip()
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    crm = request.app.state.crm
    try:
        counts = await crm.delete_all_for_phone(key)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[admin] crm reset failed for %s", key)
        return JSONResponse({"error": str(exc)}, status_code=500)
    logger.info("[admin] crm reset key=%s counts=%s", key, counts)
    return JSONResponse({"status": "reset", "key": key, "deleted": counts})


@app.get("/admin/webhooks/recent")
async def admin_recent_webhooks(limit: int = 20, group_only: bool = False) -> JSONResponse:
    """Return recent raw ChatDaddy webhook payloads captured in memory.

    Diagnostic only — lets us inspect the exact shape of group @-mention
    events (mentioned_jids, quoted, text) without grepping logs. The
    underlying buffer is bounded + ephemeral (lost on restart).
    Pass ?group_only=true to filter to group-chat events.
    """
    from src.whatsapp import diagnostic_capture
    return JSONResponse(diagnostic_capture.recent(limit=limit, group_only=group_only))


@app.post("/api/dev-chat")
async def dev_chat(request: Request) -> JSONResponse:
    """Dev-sandbox pipeline runner.

    Bypasses WhatsApp + buffer/merge entirely. Accepts:
        { phone: str, text: str?, image: {b64, mime, name}?, audio: {b64, mime}? }
    Saves any image to /tmp + transcribes any audio via Whisper, then
    runs the pipeline synchronously and returns the bubble list + media.
    """
    import base64
    import secrets
    from pathlib import Path as _Path

    from src.llm_transcribe import transcribe_audio
    from src.whatsapp.router import _MEDIA_TMP_DIR, _is_restart_command

    body = await request.json()
    phone = (body.get("phone") or "").strip()
    text = (body.get("text") or "").strip()
    image = body.get("image") or None
    audio = body.get("audio") or None

    if not phone:
        return JSONResponse({"error": "missing phone"}, status_code=400)

    pipeline: JessicaPipeline = request.app.state.pipeline

    # RESTART command — wipe CRM for this phone (mirrors WA router).
    if _is_restart_command(text):
        try:
            counts = await pipeline._crm.delete_all_for_phone(phone)  # noqa: SLF001
            logger.info("[dev] RESTART wiped phone=%s counts=%s", phone, counts)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[dev] RESTART failed: %s", exc)
            return JSONResponse(
                {
                    "turn_id": "restart_err",
                    "bubbles": [f"⚠️ wipe failed: {exc}"],
                    "media_to_send": [],
                }
            )
        return JSONResponse(
            {
                "turn_id": "restart_ok",
                "bubbles": [
                    "已清除你嘅資料 🌿 我哋重新開始啦，發 hi 我幫你 onboard 返。"
                ],
                "media_to_send": [],
                "wiped": counts,
            }
        )

    media_urls: list[str] = []
    transcript: str = ""

    # 1. Image → /tmp file → path in media_urls (Constitution Agent reads it)
    if image and isinstance(image, dict) and image.get("b64"):
        try:
            ext = {
                "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
                "image/webp": "webp", "image/gif": "gif",
            }.get(image.get("mime", "").lower(), "jpg")
            tag = secrets.token_hex(6)
            p = _Path(_MEDIA_TMP_DIR) / f"dev_{tag}.{ext}"
            p.write_bytes(base64.b64decode(image["b64"]))
            media_urls.append(str(p))
            logger.info("[dev] saved image %d bytes → %s", p.stat().st_size, p)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[dev] image decode failed: %s", exc)

    # 2. Audio → Whisper → append to text
    if audio and isinstance(audio, dict) and audio.get("b64"):
        try:
            raw = base64.b64decode(audio["b64"])
            transcript = await transcribe_audio(
                raw, filename_hint=f"dev_voice_{secrets.token_hex(4)}.webm"
            )
            if transcript:
                text = (text + " " + transcript).strip() if text else transcript
                logger.info("[dev] transcript: %r", transcript[:120])
        except Exception as exc:  # noqa: BLE001
            logger.exception("[dev] transcribe failed: %s", exc)

    # 3. Pipeline
    try:
        result = await pipeline.run_turn(
            phone=phone,
            user_message=text or "(media only)",
            media_urls=media_urls,
            wa_message_id=f"dev_{secrets.token_hex(6)}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[dev] pipeline error")
        return JSONResponse({"error": f"pipeline: {exc}"}, status_code=500)

    return JSONResponse(
        {
            "turn_id": result.turn_id,
            "bubbles": result.writer_output.bubbles,
            "media_to_send": [
                dict(m) for m in (result.writer_output.media_to_send or [])
            ],
            "transcript": transcript or None,
        }
    )


@app.get("/trace/{turn_id}")
async def get_trace(turn_id: str, request: Request) -> JSONResponse:
    writer: TraceWriter = request.app.state.trace_writer
    bundle = writer.read(turn_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"no trace for turn_id={turn_id}")
    return JSONResponse(bundle.model_dump(mode="json"))


@app.get("/trace", response_class=HTMLResponse)
async def list_traces(request: Request, phone: str | None = None) -> HTMLResponse:
    writer: TraceWriter = request.app.state.trace_writer
    paths = writer.list_recent(phone=phone, limit=50)

    rows = []
    for p in paths:
        turn_id = p.stem
        relative = p.relative_to(writer._root)  # noqa: SLF001
        rows.append(
            f"<tr><td><a href='/trace/{turn_id}'>{turn_id}</a></td>"
            f"<td>{relative}</td></tr>"
        )

    html = f"""<!doctype html>
<html><head><title>Jessica Traces</title>
<style>
body {{ font-family: -apple-system, sans-serif; padding: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f4f4f4; }}
a {{ color: #0366d6; text-decoration: none; }}
</style></head>
<body>
<h1>Jessica Traces — {len(paths)} recent</h1>
<table>
<thead><tr><th>turn_id</th><th>path</th></tr></thead>
<tbody>
{''.join(rows) or '<tr><td colspan=2>(no traces yet)</td></tr>'}
</tbody>
</table>
</body></html>"""
    return HTMLResponse(html)
