from core.celery_app import celery_app
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name='tasks.email.send_task_assigned_email',
    max_retries=3,
    default_retry_delay=60
)
def send_task_assigned_email(self, user_email: str, task_title: str, assigned_by: str):
    try:
        logger.info(f"Sending assignment email to {user_email}")

        logger.info(f" Assignment email sent to {user_email}")
        return {"status": "sent", "email": user_email}

    except Exception as exc:
        logger.error(f"Failed to send email to {user_email}: {exc}")

        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name='tasks.email.send_task_reminder_email',
    max_retries=3,
    default_retry_delay=60
)
def send_task_reminder_email(self, user_email: str, task_title: str, due_date: str):
    try:
        logger.info(f"Sending reminder email to {user_email}")

        # TODO: Implement actual email sending
        subject = f"Reminder: {task_title} is due soon"
        body = f"Your task '{task_title}' is due on {due_date}"

        logger.info(f"Reminder email sent to {user_email}")
        return {"status": "sent", "email": user_email}

    except Exception as exc:
        logger.error(f"Failed to send reminder to {user_email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name='tasks.email.send_task_comment_notification',
    max_retries=3
)
def send_task_comment_notification(self, user_email: str, task_title: str,
                                   commenter_name: str, comment_text: str):
    try:
        logger.info(f"Sending comment notification to {user_email}")

        # TODO: Implement email
        subject = f"New comment on: {task_title}"
        body = f"{commenter_name} commented: {comment_text}"

        logger.info(f"Comment notification sent to {user_email}")
        return {"status": "sent", "email": user_email}

    except Exception as exc:
        logger.error(f"Failed to send notification to {user_email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name='tasks.email.send_welcome_email',
    max_retries=3
)
def send_welcome_email(self, user_email: str, user_name: str):

    try:
        logger.info(f"Sending welcome email to {user_email}")

        # TODO: Implement with nice HTML template
        subject = "Welcome to Task Manager!"
        body = f"Hi {user_name}, welcome to our task management system!"

        logger.info(f" Welcome email sent to {user_email}")
        return {"status": "sent", "email": user_email}

    except Exception as exc:
        logger.error(f"Failed to send welcome email to {user_email}: {exc}")
        raise self.retry(exc=exc)



@celery_app.task(
    bind=True,
    name='tasks.email.send_bulk_notification',
    max_retries=1  # Don't retry bulk operations
)
def send_bulk_notification(self, email_list: list, subject: str, body: str):

    try:
        logger.info(f"Sending bulk notification to {len(email_list)} users")

        sent_count = 0
        failed_count = 0

        for email in email_list:
            try:
                # TODO: Send email
                logger.debug(f"Sent to {email}")
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {email}: {e}")
                failed_count += 1

        logger.info(f"Bulk notification complete: {sent_count} sent, {failed_count} failed")
        return {
            "status": "complete",
            "sent": sent_count,
            "failed": failed_count
        }

    except Exception as exc:
        logger.error(f"Bulk notification failed: {exc}")
        raise



def get_email_task_status(task_id: str):

    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }
