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
                        "tasks.reminders"
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
