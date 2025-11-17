from uuid import UUID
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.task import TaskCreate, TaskUpdate
from core.logger import get_logger

logger = get_logger(__name__)

class TaskService:
    @staticmethod

    async def create_task(db: AsyncSession, task: TaskCreate, created_by: UUID):
        from models.task import Task,TaskStatus
        try:
            new_task = Task(
                title = task.title,
                description = task.description,
                priority = task.priority,
                due_date = task.due_date,
                assigned_to = task.assigned_to,
                created_by = created_by
            )
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)

            logger.info(f"Task created with id {new_task.id}")
            return new_task

        except Exception as e:
            await db.rollback()
            logger.exception(f"failed to create task: {e}")
            raise HTTPException(
                status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail= "failed to create user"
            )





