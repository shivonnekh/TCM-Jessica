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
from src.trace.writer import TraceWriter
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
    specialists = build_specialist_registry(client)
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

    try:
        yield
    finally:
        logger.info("shutdown: closing CRM + background tasks")
        for task in background_tasks:
            task.cancel()
        await wa_client.close()
        await crm.close()


app = FastAPI(title="TCM-Jessica", version="0.1.0", lifespan=lifespan)
app.include_router(whatsapp_router)
app.include_router(admin_router)

# Public-readable static media — ChatDaddy fetches these via the URL
# Jessica writes into `WriterOutput.media_to_send`.
if MEDIA_DIR.is_dir():
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

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
