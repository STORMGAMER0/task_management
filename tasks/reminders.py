from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.logger import get_logger
from core.database import async_session_maker
from models.task import Task, TaskStatus
from models.user import User
from tasks.email import send_task_reminder_email

logger = get_logger(__name__)

@celery_app.task(
    bind=True,
    name='tasks.reminders.send_task_reminders'
)

def send_task_reminders(self):
    try:
        logger.info(" Checking for tasks due soon...")

        # TODO: Implement database query for tasks due soon


        logger.info("Task reminders check complete")
        return {"status": "complete", "reminders_sent": 0}

    except Exception as exc:
        logger.error(f"Failed to send task reminders: {exc}")
        raise



@celery_app.task(
    bind=True,
    name='tasks.reminders.notify_overdue_tasks'
)
def notify_overdue_tasks(self):

    try:
        logger.info("⚠Checking for overdue tasks")

        # TODO: Implement database query for overdue tasks

        logger.info("Overdue tasks check complete")
        return {"status": "complete", "notifications_sent": 0}

    except Exception as exc:
        logger.error(f"Failed to notify overdue tasks: {exc}")
        raise
