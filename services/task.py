from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.task import Task, TaskStatus, TaskPriority
from schemas.task import TaskCreate, TaskUpdate
from core.logger import get_logger
from models.user import User, UserRole
from services.cache import (get_cached_task_list, cache_task_list,
                            invalidate_all_task_lists,
                            get_cached_task_detail,
                            cache_task_detail,
                            invalidate_task_cache
                            )
from services.notification import WebSocketNotificationService
from tasks.email import send_task_assigned_email, send_task_comment_notification

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

            await invalidate_all_task_lists()

            task_data = {
                "id": str(new_task.id),
                "title": new_task.title,
                "description": new_task.description,
                "status": new_task.status.value,
                "priority": new_task.priority.value,
                "assigned_to": str(new_task.assigned_to) if new_task.assigned_to else None,
                "created_by": str(new_task.created_by)
            }
            await WebSocketNotificationService.notify_task_created(
                str(new_task.id),
                task_data,
                str(created_by)
            )

            if new_task.assigned_to:
                await WebSocketNotificationService.notify_task_assigned(
                    str(new_task.id),
                    task_data,
                    str(new_task.assigned_to),
                    str(created_by)
                )

                try:
                    from sqlalchemy import select
                    from models.user import User

                    # Get assignee and creator details
                    assignee_result = await db.execute(
                        select(User).where(User.id == new_task.assigned_to)
                    )
                    assignee = assignee_result.scalar_one_or_none()

                    creator_result = await db.execute(
                        select(User).where(User.id == created_by)
                    )
                    creator = creator_result.scalar_one_or_none()

                    if assignee and creator:
                        send_task_assigned_email.delay(
                            user_email=assignee.email,
                            task_title=new_task.title,
                            assigned_by=creator.full_name
                        )
                        logger.info(f"Assignment email queued for {assignee.email}")
                except Exception as e:
                    logger.error(f"Failed to queue assignment email: {e}")



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
                        order: str = "desc", page: int = 1, limit: int = 10):

        filters = {
            "status": status.value if status else None,
            "priority": priority.value if priority else None,
            "search": search,
            "assigned_to": str(assigned_to) if assigned_to else None,
            "sort_by": sort_by,
            "order": order,
            "page": page,
            "limit": limit
        }

        cached_result = await get_cached_task_list(str(current_user.id), filters)
        if cached_result:
            logger.info(f"Task list retrieved from cache for user {current_user.id}")
            return cached_result

        query = select(Task).options(
            selectinload(Task.creator),
            selectinload(Task.assignee)
        )

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

        response = {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_by": str(task.created_by),
                    "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat()
                }
                for task in tasks
            ],
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

        # Cache the result
        await cache_task_list(str(current_user.id), filters, response)
        logger.info(f"Task list cached for user {current_user.id}")

        return response
        # logger.info(f"user{current_user.id} fetched tasks (page{page}")
        #
        # return {
        #     "tasks": tasks,
        #     "total": total_count,
        #     "page": page,
        #     "limit": limit,
        #     "total_pages": total_pages
        # }

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: str, current_user: User) -> Task:
        cached_task = await get_cached_task_detail(str(task_id))
        if cached_task:
            logger.info(f"Task {task_id} retrieved from cache")

        query = select(Task).options(selectinload(Task.creator),
                                     selectinload(Task.assignee),
                                     selectinload(Task.tags),
                                     selectinload(Task.comments)
                                     ).where(Task.id == task_id)

        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail = "task not found"
            )

        if current_user.role == UserRole.MEMBER:
            if task.created_by != current_user.id and task.assigned_to != current_user.id:
                raise HTTPException(status_code= status.HTTP_403_FORBIDDEN,
                                    detail=" not authorized to view this task")


        task_dict = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_by": str(task.created_by),
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }

        await cache_task_detail(str(task_id), task_dict)

        return task

    @staticmethod
    async def update_task(
            db: AsyncSession,
            task_id: str,
            task_update: TaskUpdate,
            current_user: User
    )-> Task:

        task = await TaskService.get_task_by_id(db, task_id, current_user)

        if current_user.role == UserRole.MEMBER and task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this task"
            )
        #track changes for notifications
        changes = {}
        old_status = task.status.value if task.status else None
        old_assigned_to = str(task.assigned_to) if task.assigned_to else None

        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            old_value = getattr(task, field)
            if old_value != value:
                changes[field] = {"old": str(old_value), "new": str(value)}
            setattr(task, field, value)


        try:
            await db.commit()
            await db.refresh(task)

            # Invalidate caches
            await invalidate_task_cache(str(task_id))
            await invalidate_all_task_lists()

            # Prepare task data for notification
            task_data = {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                "created_by": str(task.created_by)
            }

            # Send WebSocket notification
            await WebSocketNotificationService.notify_task_updated(
                str(task_id),
                task_data,
                str(current_user.id),
                changes
            )

            # If status changed, send specific notification
            if "status" in changes:
                await WebSocketNotificationService.notify_status_changed(
                    str(task_id),
                    changes["status"]["old"],
                    changes["status"]["new"],
                    str(current_user.id)
                )

            # If assignment changed, notify new assignee
            new_assigned_to = str(task.assigned_to) if task.assigned_to else None
            if new_assigned_to and new_assigned_to != old_assigned_to:
                await WebSocketNotificationService.notify_task_assigned(
                    str(task_id),
                    task_data,
                    new_assigned_to,
                    str(current_user.id)
                )
            logger.info(f"Task {task_id} updated, caches invalidated")

            return task

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task"
            )

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: str, current_user: User) -> bool:
        task = await TaskService.get_task_by_id(db, task_id, current_user)


        if current_user.role == UserRole.MEMBER and task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this task"
            )

        try:
            await db.delete(task)
            await db.commit()


            await invalidate_task_cache(str(task_id))
            await invalidate_all_task_lists()

            await WebSocketNotificationService.notify_task_deleted(
                str(task_id),
                str(current_user.id)
            )
            logger.info(f"Task {task_id} deleted, caches invalidated")

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task"
            )


