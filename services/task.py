from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from models.task import Task, TaskStatus, TaskPriority
from schemas.task import TaskCreate, TaskUpdate
from core.logger import get_logger
from models.user import User, UserRole

logger = get_logger(__name__)


class TaskService:
    @staticmethod
    async def create_task(db: AsyncSession, task: TaskCreate, created_by: UUID):
        from models.task import Task, TaskStatus
        new_task = Task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            assigned_to=task.assigned_to,
            created_by=created_by
        )

        db.add(new_task)
        try:
            await db.commit()
            await db.refresh(new_task)
            logger.info(f"Task created with id {new_task.id}")
            return new_task

        except IntegrityError as e:
            await db.rollback()
            if "foreign key" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned user not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task data"
            )

    @staticmethod
    async def get_tasks(db: AsyncSession, current_user: User, status: Optional[TaskStatus] = None,
                        priority: Optional[TaskPriority] = None, search: Optional[str] = None,
                        assigned_to: Optional[UUID] = None, sort_by: str = "created_at",
                        order: str = "desc", page: int = 1, limit: int = 10 ):

        query = select(Task)

        if current_user.role == UserRole.MEMBER:
            query = query.where(
                or_(
                    Task.created_by == current_user.id,
                    Task.assigned_to == current_user.id
                )
            )
        if status:
            query = query.where(Task.status == status)

        if priority:
            query = query.where(Task.priority == priority)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern)
                )
            )

        if assigned_to:
            query = query.where(Task.assigned_to == assigned_to)

        if order == "asc":
            query = query.order_by(getattr(Task, sort_by).asc())
        else:
            query = query.order_by(getattr(Task, sort_by).desc())


        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        tasks = result.scalars().all()

        total_pages = (total_count + limit - 1) // limit

        logger.info(f"user{current_user.id} fetched tasks (page{page}")

        return {
            "tasks": tasks,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
