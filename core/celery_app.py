
from celery import Celery
from celery.schedules import crontab

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


celery_app = Celery(
    "task_management",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_broker_backend or settings.redis_url,
)

# Basic configuration
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    result_expires=3600,
    # Add timeout settings for Redis
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=30,
    broker_connection_max_retries=10,
)


celery_app.autodiscover_tasks(['tasks'], force=True)

try:
    from tasks import email, export, reminders, reports
    logger.info("✅ Task modules imported successfully")
except ImportError as e:
    logger.error(f"Failed to import task modules: {e}")


# Celery Beat Schedule for Periodic Tasks
celery_app.conf.beat_schedule = {
    # Send reminders for tasks due in 24 hours (runs at 9 AM daily)
    'send-daily-task-reminders': {
        'task': 'tasks.reminders.send_task_reminders',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9:00 AM
    },

    # Send daily summary report (runs at 8 AM daily)
    'send-daily-summary': {
        'task': 'tasks.reports.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),  # Every day at 8:00 AM
    },

    # Check for overdue tasks (runs every hour)
    'check-overdue-tasks': {
        'task': 'tasks.reminders.notify_overdue_tasks',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
}

@celery_app.task(bind=True)
def debug_task(self):

    logger.info(f'Request: {self.request!r}')
    return 'Celery is working!'


logger.info("✅ Celery app configured")