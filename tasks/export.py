import csv
import io
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
import asyncio
from typing import Optional, List
from uuid import UUID

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.celery_app import celery_app
from core.logger import get_logger
from core.database import async_session_maker
from models.task import Task, TaskStatus, TaskPriority
from models.user import User, UserRole

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name='tasks.export.export_tasks_csv'
)
def export_tasks_csv(
        self,
        user_id: str,
        filters: dict = None
):

    try:
        logger.info(f"Starting CSV export for user {user_id}")

        result = asyncio.run(_export_tasks_csv_async(user_id, filters or {}))

        logger.info(f"✅ CSV export complete: {result['task_count']} tasks")
        return result

    except Exception as exc:
        logger.error(f"CSV export failed: {exc}", exc_info=True)
        raise


async def _export_tasks_csv_async(user_id: str, filters: dict):
    async with async_session_maker() as db:
        try:
            # Get user
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Build query
            query = select(Task)

            # Apply role-based filtering
            if user.role == UserRole.MEMBER:
                query = query.where(
                    or_(
                        Task.created_by == user.id,
                        Task.assigned_to == user.id
                    )
                )

            # Apply filters with proper type conversion
            if filters.get('status'):
                try:
                    query = query.where(Task.status == TaskStatus(filters['status']))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid status filter: {filters['status']}")

            if filters.get('priority'):
                try:
                    query = query.where(Task.priority == TaskPriority(filters['priority']))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid priority filter: {filters['priority']}")

            if filters.get('assigned_to'):
                try:
                    # Convert string UUID to UUID object
                    assigned_to_uuid = UUID(filters['assigned_to']) if isinstance(filters['assigned_to'], str) else filters['assigned_to']
                    query = query.where(Task.assigned_to == assigned_to_uuid)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid assigned_to filter: {filters['assigned_to']}")

            # Execute query
            result = await db.execute(query)
            tasks = result.scalars().all()

            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    'ID', 'Title', 'Description', 'Status', 'Priority',
                    'Due Date', 'Created By', 'Assigned To',
                    'Created At', 'Updated At'
                ]
            )

            writer.writeheader()

            for task in tasks:
                writer.writerow({
                    'ID': str(task.id),
                    'Title': task.title,
                    'Description': task.description or '',
                    'Status': task.status.value,
                    'Priority': task.priority.value,
                    'Due Date': task.due_date.isoformat() if task.due_date else '',
                    'Created By': str(task.created_by),
                    'Assigned To': str(task.assigned_to) if task.assigned_to else '',
                    'Created At': task.created_at.isoformat(),
                    'Updated At': task.updated_at.isoformat()
                })

            csv_content = output.getvalue()
            output.close()

            return {
                "status": "complete",
                "task_count": len(tasks),
                "csv_content": csv_content,
                "filename": f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }

        except Exception as e:
            logger.error(f"CSV generation failed: {e}", exc_info=True)
            raise


@celery_app.task(
    bind=True,
    name='tasks.export.export_tasks_pdf'
)
def export_tasks_pdf(
        self,
        user_id: str,
        filters: dict = None
):
    """
    Export tasks to PDF format.

    Args:
        user_id: User requesting the export
        filters: Dict of filters

    Returns:
        PDF content as base64 string
    """
    try:
        logger.info(f"Starting PDF export for user {user_id}")

        result = asyncio.run(_export_tasks_pdf_async(user_id, filters or {}))

        logger.info(f"✅ PDF export complete: {result['task_count']} tasks")
        return result

    except Exception as exc:
        logger.error(f"PDF export failed: {exc}", exc_info=True)
        raise


async def _export_tasks_pdf_async(user_id: str, filters: dict):
    """Async helper for PDF generation."""
    async with async_session_maker() as db:
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.units import inch
            import base64

            # Get user
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Build query (same as CSV)
            query = select(Task)

            if user.role == UserRole.MEMBER:
                query = query.where(
                    or_(
                        Task.created_by == user.id,
                        Task.assigned_to == user.id
                    )
                )

            # Apply filters with proper type conversion
            if filters.get('status'):
                try:
                    query = query.where(Task.status == TaskStatus(filters['status']))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid status filter: {filters['status']}")

            if filters.get('priority'):
                try:
                    query = query.where(Task.priority == TaskPriority(filters['priority']))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid priority filter: {filters['priority']}")

            if filters.get('assigned_to'):
                try:
                    # Convert string UUID to UUID object
                    assigned_to_uuid = UUID(filters['assigned_to']) if isinstance(filters['assigned_to'], str) else filters['assigned_to']
                    query = query.where(Task.assigned_to == assigned_to_uuid)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid assigned_to filter: {filters['assigned_to']}")

            # Execute query
            result = await db.execute(query)
            tasks = result.scalars().all()

            # Generate PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            # Styles
            styles = getSampleStyleSheet()

            # Title
            title = Paragraph(
                f"<b>Task Export Report</b><br/>"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                f"User: {user.full_name}",
                styles['Title']
            )
            elements.append(title)
            elements.append(Spacer(1, 0.3 * inch))

            # Table data
            data = [['Title', 'Status', 'Priority', 'Due Date']]

            for task in tasks:
                data.append([
                    task.title[:40],  # Truncate long titles
                    task.status.value,
                    task.priority.value,
                    task.due_date.strftime('%Y-%m-%d') if task.due_date else 'No due date'
                ])

            # Create table
            table = Table(data, colWidths=[3.5 * inch, 1.2 * inch, 1 * inch, 1.3 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(table)

            # Build PDF
            doc.build(elements)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # Convert to base64 for storage/transmission
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

            return {
                "status": "complete",
                "task_count": len(tasks),
                "pdf_content": pdf_base64,
                "filename": f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }

        except ImportError:
            logger.error("reportlab not installed. Run: pip install reportlab")
            raise
        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            raise