"""
Celery Configuration for Background Task Processing
Minimal working version to get started quickly.
"""

from celery import Celery
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "task_management",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_broker_backend or settings.redis_url,
    include=[
        'tasks.email',
        'tasks.reminders',
        'tasks.reports',
    ]
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
)

# Remove autodiscover - we use 'include' instead
# celery_app.autodiscover_tasks(['tasks'])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test if Celery is working."""
    logger.info(f'Request: {self.request!r}')
    return 'Celery is working!'


logger.info("✅ Celery app configured")