"""WebSocket pipeline events (§6.4)."""

import asyncio
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.api.deps import get_orchestrator
from app.api.state import create_pending_ticket, fail_ticket, save_ticket
from app.schemas import PipelineEvento

logger = logging.getLogger(__name__)

router = APIRouter()

_connections: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast_event(ticket_id: str, evento: PipelineEvento) -> None:
    dead = []
    for ws in _connections.get(ticket_id, []):
        try:
            await ws.send_json(evento.model_dump(mode="json"))
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _connections[ticket_id]:
            _connections[ticket_id].remove(ws)


async def broadcast_json(ticket_id: str, payload: dict) -> None:
    dead = []
    for ws in list(_connections.get(ticket_id, [])):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _connections[ticket_id]:
            _connections[ticket_id].remove(ws)


def _process_ticket_sync(texto: str, ticket_id: str, loop: asyncio.AbstractEventLoop):
    def on_event(evento: PipelineEvento):
        asyncio.run_coroutine_threadsafe(broadcast_event(ticket_id, evento), loop)

    return get_orchestrator().process_ticket(texto, ticket_id=ticket_id, on_event=on_event)


@router.websocket("/ws/pipeline/{ticket_id}")
async def pipeline_ws(websocket: WebSocket, ticket_id: str):
    await websocket.accept()
    _connections[ticket_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "process" and data.get("texto"):
                # Recorded before the pipeline runs so GET /tickets/{id} can tell
                # "still processing" apart from "never existed" while it's in flight.
                create_pending_ticket(ticket_id)
                loop = asyncio.get_running_loop()
                try:
                    response = await asyncio.to_thread(
                        _process_ticket_sync, data["texto"], ticket_id, loop
                    )
                except Exception as exc:
                    # Caught here so it doesn't propagate silently to the caught-all
                    # WebSocketDisconnect handler — log the full traceback server-side
                    # even though only the short message goes to the client.
                    logger.exception("Pipeline failed for ticket %s", ticket_id)
                    fail_ticket(ticket_id, str(exc))
                    await broadcast_json(ticket_id, {"type": "error", "message": str(exc)})
                    continue
                save_ticket(response)
                payload = {"type": "result", "data": response.model_dump()}
                # Fan-out so a client that left and re-subscribed still gets the result.
                await broadcast_json(ticket_id, payload)
                if websocket.application_state != WebSocketState.CONNECTED:
                    # This connection died while the pipeline was running — the
                    # broadcast above already discovered that (send raised, got
                    # dropped from _connections) and flipped application_state.
                    # Looping back to receive_json() would raise RuntimeError
                    # instead of the WebSocketDisconnect below, since it checks
                    # application_state before it ever touches the socket.
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _connections[ticket_id]:
            _connections[ticket_id].remove(websocket)
