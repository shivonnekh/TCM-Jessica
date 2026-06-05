"""Instagram webhook router — thin wrapper over ``meta_webhook``.

Endpoints:
    GET  /webhook/instagram   — Meta subscription handshake (hub.challenge)
    POST /webhook/instagram   — inbound DMs + comments → pipeline / canned

All processing logic (signature verify, parse, dedup, dispatch, media
interleaving, comment rules) lives in ``meta_webhook`` so Instagram and
Facebook share one battle-tested core. This module only:
    * owns the URL path,
    * owns the enable-flag (``IG_ENABLED``),
    * holds the pipeline reference for this surface.

Env: IG_ENABLED ("true" to process). Send-side + security vars are
documented in ``meta_webhook`` / ``meta_client``.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from src.channels import meta_webhook
from src.orchestrator.pipeline import JessicaPipeline

router = APIRouter(tags=["instagram"])

_pipeline_ref: JessicaPipeline | None = None


def set_pipeline(pipeline: JessicaPipeline) -> None:
    """Register the active pipeline. Called from ``web.lifespan`` at startup."""
    global _pipeline_ref
    _pipeline_ref = pipeline


def _enabled() -> bool:
    return os.environ.get("IG_ENABLED", "false").lower() == "true"


@router.get("/webhook/instagram", response_model=None)
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


@router.post("/webhook/instagram")
async def receive(request: Request) -> JSONResponse:
    raw = await request.body()
    body, status = await meta_webhook.process_post(
        raw=raw,
        signature_header=request.headers.get("X-Hub-Signature-256", ""),
        pipeline=_pipeline_ref,
        enabled=_enabled(),
    )
    return JSONResponse(body, status_code=status)
