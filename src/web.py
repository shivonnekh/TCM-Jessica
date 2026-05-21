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

from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.agents.registry import build_specialist_registry
from src.crm.repo import CRMRepo
from src.orchestrator.pipeline import JessicaPipeline
from src.trace.writer import TraceWriter
from src.whatsapp import client as wa_client
from src.whatsapp.router import router as whatsapp_router
from src.whatsapp.router import set_pipeline as set_wa_pipeline

logger = logging.getLogger("web")

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "data" / "jessica.db"))
TRACE_DIR = os.environ.get("TRACE_DIR", str(ROOT / "traces"))


# -------------------------------------------------------------------
# App lifecycle
# -------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: connecting CRM at %s", DB_PATH)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    crm = await CRMRepo.connect(DB_PATH)
    trace_writer = TraceWriter(TRACE_DIR)

    client = AsyncAnthropic()  # picks up ANTHROPIC_API_KEY from env
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


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tcm-jessica"}


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
