"""
WebSocket route definitions for Worker control channel.
"""

from fastapi import APIRouter, WebSocket

from coordinator.websocket.manager import get_connection_manager

router = APIRouter(tags=["Worker WebSocket Gateway"])
manager = get_connection_manager()


@router.websocket("/ws/workers")
async def worker_websocket_endpoint(websocket: WebSocket) -> None:
    """
    Persistent bidirectional WebSocket endpoint for third-party GPU compute workers.
    Authenticates via worker secret token, receives telemetry heartbeats, and dispatches tasks.
    """
    await manager.handle_worker_lifecycle(websocket)
