from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime,timezone
from core.logger import get_logger
from uuid import UUID

logger = get_logger(__name__)

class ConnectionManager:
    #this manages websocket connections for real time updates


    def __init__(self):
        #stores active connections
        self.active_connections: Dict[str,List[WebSocket]] = {}

        self.task_viewers: Dict[str, Set[str]] = {}


    async def connect(self, websocket: WebSocket, user_id:str):
        #this accepts a new websocket connection
        #takes an argument of the websocket connection and the ID of the user connecting
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

        logger.info(f"websocket connected: user = {user_id}, total_connections = {len(self.active_connections[user_id])}")

        await self.send_personal_message(
            user_id,
            {
                "type": "connection",
                "status": "connected",
                "message": "Successfully connected to real-time updates",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        await self.broadcast_user_status(user_id, "online")

    def disconnect(self, websocket:WebSocket, user_id: str):
        #removes a websocket connection

        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            #remove user from dict if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"websocket disconnected: user= {user_id} (all connections closed)")

                #remove from task viewers
                for task_id in list(self.task_viewers.keys()):
                    if user_id in self.task_viewers[task_id]:
                        self.task_viewers[task_id].remove(user_id)
                        if not self.task_viewers[task_id]:
                            del self.task_viewers[task_id]
            else:
                logger.info(f"WebSocket disconnected: user={user_id} ({len(self.active_connections[user_id])} connections remaining)")

    async def send_personal_message(self, user_id: str, message: dict):
        if user_id not in self.active_connections:
            return
        disconnected = []

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"failed to send message to user{user_id}: {e}")
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket, user_id)

    async def broadcast(self, message: dict, exclude_user: str = None):
        #broadcast a message to all connected users.
        logger.info(f"broadcasting message to {len(self.active_connections)} users")
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(user_id, message)


    async def broadcast_to_task_viewers(self, task_id: str, message: dict):
        #send message to all users currently viewing a task

        if task_id not in self.task_viewers:
            return
        viewers = list(self.task_viewers[task_id])
        logger.info(f"broadcasting to {len(viewers)} viewers of task {task_id}")

        for user_id in viewers:
            await self.send_personal_message(user_id, message)


    async def broadcast_user_status(self, user_id: str, status: str):
       # Notify all users about a user's online status.


        await self.broadcast(
            {
                "type": "user_status",
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            exclude_user=user_id  # Don't send to the user themselves
        )

    def join_task_view(self, user_id: str, task_id: str):
        #Track that a user is viewing a task.
        if task_id not in self.task_viewers:
            self.task_viewers[task_id] = set()
        self.task_viewers[task_id].add(user_id)
        logger.info(f"User {user_id} joined task view {task_id}")

    def leave_task_view(self, user_id: str, task_id: str):
        #Track that a user stopped viewing a task.
        if task_id in self.task_viewers and user_id in self.task_viewers[task_id]:
            self.task_viewers[task_id].remove(user_id)
            if not self.task_viewers[task_id]:
                del self.task_viewers[task_id]
            logger.info(f"User {user_id} left task view {task_id}")

    def get_online_users(self) -> List[str]:
        #Get list of all currently connected user IDs.
        return list(self.active_connections.keys())

    def get_task_viewers(self, task_id: str) -> List[str]:
        #Get list of users currently viewing a task.
        return list(self.task_viewers.get(task_id, set()))

    def is_user_online(self, user_id: str) -> bool:
        #Check if a user has any active connections.
        return user_id in self.active_connections



manager = ConnectionManager()









