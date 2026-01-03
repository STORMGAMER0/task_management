from celery import Celery
from celery.schedules import crontab
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

celery_app = Celery("task_management",
                    broker=settings.celery_broker_url or settings.redis_url,

                    backend=settings.celery_broker_backend or settings.redis_url,

                    include=[
                        "tasks.email",
                        "tasks.reminders",
                        "tasks.reports"
                    ])

celery_app.conf.update(
    task_time_limit=600,

    task_soft_time_limit=540,

    task_serializer='json',

    result_serializer=['json'],

    timezone='UTC',

    enable_utc=True,

    result_expires=86400,
    result_extended=True,

    worker_max_tasks_per_child=1000,

    worker_prefetch_multiplier=4,

    worker_disable_rate_limits=True,

    worker_hijack_root_logger=False,

    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',

)

celery_app.conf.beat_schedule = {
    'check-task-reminders-every-hour': {
        'task': 'tasks.reminders.send_task_reminders',
        'schedule': crontab(minute=0),
        'options': {'expires': 3600}
    },

    'check-overdue-tasks-daily': {
        'task': 'tasks.reminders.notify_overdue_tasks',
        'schedule': crontab(hour=9, minute=0),
        'options': {'expires': 86400}
    },

    'send-daily-digest': {
        'task': 'tasks.reports.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
        'options': {'expires': 86400}
    },

    'send-weekly-report': {
        'task': 'tasks.reports.send_weekly_report',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),  # Monday at 9:00 AM
        'options': {'expires': 604800}  # Expires after 1 week
    },

    'cleanup-old-notifications': {
        'task': 'tasks.reports.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2:00 AM
        'options': {'expires': 86400}
    },
}

celery_app.conf.task_routes = {
    # Email tasks: High priority queue
    'tasks.email.*': {'queue': 'priority'},

    # Reminder tasks: Default queue
    'tasks.reminders.*': {'queue': 'default'},

    # Report tasks: Heavy processing queue (fewer workers)
    'tasks.reports.*': {'queue': 'heavy'},
}


def get_celery_app():
    return celery_app


@celery_app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')
    return 'Celery is working!'


logger.info("Celery app configured")
logger.info(f"Broker: {settings.celery_broker_url or settings.redis_url}")
logger.info(f"Backend: {settings.celery_broker_backend or settings.redis_url}")
