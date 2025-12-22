from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.exceptions import HTTPException
from jose import JWTError
from typing import Optional

from core.websocket import manager
from core.security import decode_token
from core.logger import get_logger

logger = get_logger(__name__)

websocket_router = APIRouter(tags=["WebSocket"])


async def get_current_user_ws(websocket: WebSocket, token: str = Query(...)):

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketDisconnect()

        return user_id

    except JWTError as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect()


@websocket_router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str = Depends(get_current_user_ws)
):

    # Accept connection
    await manager.connect(websocket, user_id)

    try:
        # Listen for messages from client
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")

            logger.info(f"Received WebSocket message from {user_id}: {message_type}")

            # Handle different message types
            if message_type == "ping":
                # Heartbeat - respond with pong
                await manager.send_personal_message(
                    user_id,
                    {"type": "pong", "timestamp": data.get("timestamp")}
                )

            elif message_type == "join_task":
                # User started viewing a task
                task_id = data.get("task_id")
                if task_id:
                    manager.join_task_view(user_id, task_id)

                    # Notify other viewers
                    await manager.broadcast_to_task_viewers(
                        task_id,
                        {
                            "type": "task_viewer_joined",
                            "task_id": task_id,
                            "user_id": user_id,
                            "viewers": manager.get_task_viewers(task_id)
                        }
                    )

            elif message_type == "leave_task":
                # User stopped viewing a task
                task_id = data.get("task_id")
                if task_id:
                    manager.leave_task_view(user_id, task_id)

                    # Notify other viewers
                    await manager.broadcast_to_task_viewers(
                        task_id,
                        {
                            "type": "task_viewer_left",
                            "task_id": task_id,
                            "user_id": user_id,
                            "viewers": manager.get_task_viewers(task_id)
                        }
                    )

            elif message_type == "get_online_users":
                # Client requests list of online users
                await manager.send_personal_message(
                    user_id,
                    {
                        "type": "online_users",
                        "users": manager.get_online_users()
                    }
                )

            else:
                logger.warning(f"Unknown message type: {message_type}")
                await manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    }
                )

    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(websocket, user_id)

        # Notify others that user went offline
        await manager.broadcast_user_status(user_id, "offline")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
        manager.disconnect(websocket, user_id)