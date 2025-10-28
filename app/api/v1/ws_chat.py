from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set

from app.api.deps import get_current_user_ws
from app.models.user import User

router = APIRouter()
rooms: Dict[str, Set[WebSocket]] = {}

@router.websocket("/ws/chat/{appointment_id}")
async def ws_chat(ws: WebSocket, appointment_id: str, user: User = Depends(get_current_user_ws)):
    await ws.accept()

    if appointment_id not in rooms:
        rooms[appointment_id] = set()
    rooms[appointment_id].add(ws)

    try:
        # Mensaje de bienvenida opcional con el role y nombre
        await ws.send_json({"type": "system", "text": f"{user.full_name} conectado", "role": str(user.role)})

        while True:
            data = await ws.receive_json()
            # Ejemplo de payload esperado:
            # { "type":"msg", "text":"...", "client_ts": 1712345678 }
            for peer in list(rooms.get(appointment_id, [])):
                if peer is not ws:
                    await peer.send_json({
                        "type": data.get("type", "msg"),
                        "text": data.get("text", ""),
                        "sender": user.full_name,
                        "role": str(user.role),
                        "appointment_id": appointment_id
                    })
            # TODO (opcional): persistir en DB
    except WebSocketDisconnect:
        pass
    finally:
        rooms.get(appointment_id, set()).discard(ws)
