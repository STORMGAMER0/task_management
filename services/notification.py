from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from core.websocket import manager
from core.logger import get_logger

logger = get_logger(__name__)


class WebSocketNotificationService:
    #this service sends real time notifications via the websocket

    @staticmethod
    async def notify_task_created(task_id: str, task_data: dict, created_by: str):
        message= {
            "type" : "task_created",
            "task_id" : task_id,
            "created_by" : created_by,
            "timestamp" : datetime.now(timezone.utc).isoformat()
        }

        await manager.broadcast(message, exclude_user= created_by)
        logger.info(f"Broadcast task_created: {task_id}")

    @staticmethod
    async def notify_task_updated(task_id: str, task_data:dict, updated_by: str, changes: dict= None):
        message = {
            "type": "task_updated",
            "task_id": task_id,
            "task": task_data,
            "updated_by": updated_by,
            "changes": changes or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.broadcast_to_task_viewers(task_id, message)

        assigned_to = task_data.get("assigned_to")
        created_by = task_data.get("created_by")

        if assigned_to and assigned_to != updated_by:
            await manager.send_personal_message(assigned_to, message)

        if created_by and created_by != updated_by and created_by != assigned_to:
            await manager.send_personal_message(created_by, message)

        logger.info(f"Broadcast task_updated: {task_id}")

    @staticmethod
    async def notify_task_deleted(task_id: str, deleted_by: str):
        message = {
            "type": "task_deleted",
            "task_id": task_id,
            "deleted_by": deleted_by,
            "timestamp": datetime.now(timezone.utc).isoformat()

        }

        await manager.broadcast(message, exclude_user=deleted_by)
        logger.info(f"Broadcast task_deleted: {task_id}")

    @staticmethod
    async def notify_task_assigned(task_id: str, task_data: dict, assigned_to: str, assigned_by: str):

        message = {
            "type": "task_assigned",
            "task_id": task_id,
            "task": task_data,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send directly to assigned user
        await manager.send_personal_message(assigned_to, message)
        logger.info(f"Notified user {assigned_to} of task assignment: {task_id}")

    @staticmethod
    async def notify_comment_added(task_id: str, comment_data: dict, author_id: str):

        message = {
            "type": "comment_added",
            "task_id": task_id,
            "comment": comment_data,
            "author_id": author_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send to all task viewers
        await manager.broadcast_to_task_viewers(task_id, message)
        logger.info(f"Broadcast comment_added on task: {task_id}")

    @staticmethod
    async def notify_status_changed(task_id: str, old_status: str, new_status: str, changed_by: str):

        message = {
            "type": "task_status_changed",
            "task_id": task_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await manager.broadcast_to_task_viewers(task_id, message)
        logger.info(f"Broadcast status_changed: {task_id} ({old_status} -> {new_status})")

    @staticmethod
    async def send_custom_notification(user_id: str, notification_type: str, data: dict):

        message = {
            "type": notification_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await manager.send_personal_message(user_id, message)
        logger.info(f"Sent custom notification to {user_id}: {notification_type}")