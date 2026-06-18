"""Consultation FastAPI router.

Endpoints:
  POST /api/consultation/create        — create room, return patient + practitioner URLs
  GET  /api/consultation/list          — list recent consultations (dashboard)
  GET  /api/consultation/ice-config    — ICE servers config (STUN + optional TURN)
  WS   /ws/consultation/{room_id}/{role} — WebRTC signaling
  GET  /consult/{room_id}              — serve the video call page
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from src.consultation.signaling import get_hub
from src.consultation.voice_ws import handle_voice

logger = logging.getLogger("consultation.router")

router = APIRouter()

_CONSULT_HTML = Path(__file__).resolve().parent.parent / "static" / "consult.html"


# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------


@router.post("/api/consultation/create")
async def create_consultation(request: Request) -> JSONResponse:
    body = await request.json()
    crm_key = str(body.get("crm_key", "unknown"))
    preferred_time = str(body.get("preferred_time", ""))

    repo = request.app.state.consultation_repo
    consult = await repo.create(crm_key=crm_key, preferred_time=preferred_time)

    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "room_id": consult.id,
        "patient_url":       f"{base}{consult.patient_url}",
        "practitioner_url":  f"{base}{consult.practitioner_url}",
        "preferred_time":    consult.preferred_time,
        "status":            consult.status,
    })


@router.get("/api/consultation/list")
async def list_consultations(request: Request) -> JSONResponse:
    repo = request.app.state.consultation_repo
    items = await repo.list_recent(limit=30)
    base = str(request.base_url).rstrip("/")
    return JSONResponse([
        {
            "id": c.id,
            "crm_key": c.crm_key,
            "preferred_time": c.preferred_time,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "patient_joined_at": c.patient_joined_at.isoformat() if c.patient_joined_at else None,
            "practitioner_joined_at": c.practitioner_joined_at.isoformat() if c.practitioner_joined_at else None,
            "patient_url": f"{base}{c.patient_url}",
            "practitioner_url": f"{base}{c.practitioner_url}",
        }
        for c in items
    ])


@router.get("/api/consultation/ice-config")
async def ice_config() -> JSONResponse:
    """Return ICE server config to the client — keeps credentials off the HTML source."""
    servers: list[dict] = [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"},
    ]

    turn_url  = os.environ.get("TURN_URL", "").strip()
    turn_user = os.environ.get("TURN_USERNAME", "").strip()
    turn_cred = os.environ.get("TURN_CREDENTIAL", "").strip()
    if turn_url and turn_user and turn_cred:
        servers.append({
            "urls": turn_url,
            "username": turn_user,
            "credential": turn_cred,
        })

    return JSONResponse({"iceServers": servers})


# ---------------------------------------------------------------------------
# Video call page
# ---------------------------------------------------------------------------


@router.get("/consult/{room_id}", response_class=HTMLResponse)
async def consult_page(room_id: str, request: Request) -> HTMLResponse:
    if not _CONSULT_HTML.exists():
        return HTMLResponse("<h1>consult.html not found</h1>", status_code=500)
    return HTMLResponse(_CONSULT_HTML.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# WebSocket signaling
# ---------------------------------------------------------------------------


@router.websocket("/ws/voice/{room_id}")
async def voice_ws(websocket: WebSocket, room_id: str) -> None:
    """Voice AI WebSocket — patient speaks, Chloe responds with audio."""
    chloe = websocket.app.state.chloe_agent
    if chloe is None:
        await websocket.close(code=4000)
        return
    await handle_voice(websocket, room_id, chloe)


@router.websocket("/ws/consultation/{room_id}/{role}")
async def signaling_ws(websocket: WebSocket, room_id: str, role: str) -> None:
    if role not in ("patient", "practitioner"):
        await websocket.close(code=4000)
        return

    await websocket.accept()
    hub = get_hub()
    repo = websocket.app.state.consultation_repo

    await hub.join(room_id, role, websocket)
    await repo.mark_joined(room_id, role)

    # Mark room active once both peers have joined
    if hub.peer_count(room_id) >= 2:
        await repo.update_status(room_id, "active")

    try:
        while True:
            data = await websocket.receive_json()
            await hub.relay(room_id, role, data)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("[signaling] unexpected error room=%s role=%s", room_id, role)
    finally:
        await hub.leave(room_id, role)
        # Mark done when everyone has left
        if hub.peer_count(room_id) == 0:
            await repo.update_status(room_id, "done")
