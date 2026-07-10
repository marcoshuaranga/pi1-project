"""WebSocket pipeline events (§6.4)."""

import asyncio
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_orchestrator
from app.api.state import save_ticket
from app.schemas import PipelineEvento

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
                loop = asyncio.get_running_loop()
                response = await asyncio.to_thread(
                    _process_ticket_sync, data["texto"], ticket_id, loop
                )
                save_ticket(response)
                await websocket.send_json({"type": "result", "data": response.model_dump()})
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _connections[ticket_id]:
            _connections[ticket_id].remove(websocket)
