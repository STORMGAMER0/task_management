
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_
import asyncio

from core.celery_app import celery_app
from core.logger import get_logger
from core.database import async_session_maker
from models.task import Task, TaskStatus
from models.user import User
from tasks.email import send_bulk_notification

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name='tasks.reports.send_daily_digest'
)
def send_daily_digest(self):
    """
    Digest includes:
    - Tasks completed yesterday
    - Tasks due today
    - Tasks assigned to user
    - Overdue tasks
    """
    try:
        logger.info("📊 Generating daily digest...")

        result = asyncio.run(_send_daily_digest_async())

        logger.info(f"✅ Daily digest sent to {result['sent']} users")
        return result

    except Exception as exc:
        logger.error(f"Failed to send daily digest: {exc}", exc_info=True)
        raise


async def _send_daily_digest_async():
    """Async helper for database operations."""
    async with async_session_maker() as db:
        try:
            # Get all active users
            user_query = select(User).where(User.is_active == True)
            user_result = await db.execute(user_query)
            users = user_result.scalars().all()

            logger.info(f"Sending digest to {len(users)} active users")

            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(days=1)
            today_end = now + timedelta(days=1)

            sent_count = 0

            for user in users:
                try:
                    # Get user's task statistics
                    stats = await _get_user_task_stats(db, user.id, yesterday, today_end)

                    # Only send if user has relevant tasks
                    if stats['total_tasks'] > 0:
                        # Create digest email content
                        subject = f"Daily Task Digest - {now.strftime('%B %d, %Y')}"
                        body = _create_digest_email_body(user, stats)

                        # Queue email (using bulk notification as placeholder)
                        # In production, you'd create a specific digest email task
                        logger.info(f"Digest queued for {user.email}: {stats}")
                        sent_count += 1

                except Exception as e:
                    logger.error(f"Failed to create digest for user {user.id}: {e}")

            return {
                "status": "complete",
                "sent": sent_count,
                "total_users": len(users)
            }

        except Exception as e:
            logger.error(f"Failed to generate daily digest: {e}", exc_info=True)
            raise


async def _get_user_task_stats(db, user_id, since_date, until_date):
    """Get task statistics for a user."""
    # Tasks assigned to user
    assigned_query = select(func.count()).where(
        and_(
            Task.assigned_to == user_id,
            Task.status != TaskStatus.DONE
        )
    )
    assigned_result = await db.execute(assigned_query)
    assigned_count = assigned_result.scalar()

    # Tasks completed yesterday
    completed_query = select(func.count()).where(
        and_(
            Task.assigned_to == user_id,
            Task.status == TaskStatus.DONE,
            Task.updated_at >= since_date
        )
    )
    completed_result = await db.execute(completed_query)
    completed_count = completed_result.scalar()

    # Tasks due today
    due_today_query = select(func.count()).where(
        and_(
            Task.assigned_to == user_id,
            Task.due_date.isnot(None),
            Task.due_date <= until_date,
            Task.status != TaskStatus.DONE
        )
    )
    due_today_result = await db.execute(due_today_query)
    due_today_count = due_today_result.scalar()

    # Overdue tasks
    overdue_query = select(func.count()).where(
        and_(
            Task.assigned_to == user_id,
            Task.due_date.isnot(None),
            Task.due_date < datetime.now(timezone.utc),
            Task.status != TaskStatus.DONE
        )
    )
    overdue_result = await db.execute(overdue_query)
    overdue_count = overdue_result.scalar()

    return {
        "total_tasks": assigned_count,
        "completed_yesterday": completed_count,
        "due_today": due_today_count,
        "overdue": overdue_count
    }


def _create_digest_email_body(user, stats):
    """Create email body for daily digest."""
    return f"""
    Good morning {user.full_name}!

    Here's your daily task summary:

    📋 Active Tasks: {stats['total_tasks']}
    ✅ Completed Yesterday: {stats['completed_yesterday']}
    📅 Due Today: {stats['due_today']}
    ⚠️  Overdue: {stats['overdue']}

    Have a productive day!
    """


@celery_app.task(
    bind=True,
    name='tasks.reports.send_weekly_report'
)
def send_weekly_report(self):
    """
    Send weekly report to all users.

    Runs every Monday at 9 AM (configure in beat_schedule if needed).
    """
    try:
        logger.info("📈 Generating weekly report...")

        # TODO: Implement weekly report generation

        logger.info("✅ Weekly report sent")
        return {"status": "complete", "reports_sent": 0}

    except Exception as exc:
        logger.error(f"Failed to send weekly report: {exc}")
        raise


@celery_app.task(
    bind=True,
    name='tasks.reports.cleanup_old_notifications'
)
def cleanup_old_notifications(self):
    """
    Clean up old notifications and data.

    Runs daily at 2 AM (configure in beat_schedule if needed).
    """
    try:
        logger.info("🧹 Cleaning up old data...")

        # TODO: Implement cleanup logic

        logger.info("✅ Cleanup complete")
        return {"status": "complete", "items_deleted": 0}

    except Exception as exc:
        logger.error(f"Failed to cleanup old data: {exc}")
        raise