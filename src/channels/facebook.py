"""Facebook Messenger webhook router — thin wrapper over ``meta_webhook``.

Endpoints:
    GET  /webhook/facebook   — Meta subscription handshake (hub.challenge)
    POST /webhook/facebook   — inbound Page DMs + comments → pipeline / canned

Facebook Pages emit the SAME Messenger + comment webhook shapes as
Instagram (``object == "page"``), so the entire processing core is
reused from ``meta_webhook``. Differences are only:
    * URL path (/webhook/facebook),
    * enable-flag (``FB_ENABLED``),
    * send credentials (FB_PAGE_ACCESS_TOKEN / FB_PAGE_ID, resolved inside
      ``meta_client`` via the event's ``platform`` field).

The Meta App secret + verify token (``META_APP_SECRET`` /
``META_VERIFY_TOKEN``) are shared across products of the same App, so no
new security vars are needed.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from src.channels import meta_webhook
from src.orchestrator.pipeline import JessicaPipeline

router = APIRouter(tags=["facebook"])

_pipeline_ref: JessicaPipeline | None = None


def set_pipeline(pipeline: JessicaPipeline) -> None:
    """Register the active pipeline. Called from ``web.lifespan`` at startup."""
    global _pipeline_ref
    _pipeline_ref = pipeline


def _enabled() -> bool:
    return os.environ.get("FB_ENABLED", "false").lower() == "true"


@router.get("/webhook/facebook", response_model=None)
async def verify(request: Request) -> PlainTextResponse | JSONResponse:
    params = request.query_params
    challenge = meta_webhook.verify_subscription(
        mode=params.get("hub.mode", ""),
        token=params.get("hub.verify_token", ""),
        challenge=params.get("hub.challenge", ""),
    )
    if challenge is not None:
        return PlainTextResponse(challenge)
    return JSONResponse({"error": "verification failed"}, status_code=403)


@router.post("/webhook/facebook")
async def receive(request: Request) -> JSONResponse:
    raw = await request.body()
    body, status = await meta_webhook.process_post(
        raw=raw,
        signature_header=request.headers.get("X-Hub-Signature-256", ""),
        pipeline=_pipeline_ref,
        enabled=_enabled(),
    )
    return JSONResponse(body, status_code=status)
