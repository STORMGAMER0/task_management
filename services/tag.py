from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.tag import Tag, task_tags
from models.task import Task
from models.user import User, UserRole
from schemas.tag import TagCreate, TagUpdate
from core.logger import get_logger

logger = get_logger(__name__)


class TagService:
    @staticmethod
    async def create_tag(db: AsyncSession, tag_data: TagCreate) -> Tag:

        # Check if tag already exists (case-insensitive)
        existing_tag_query = select(Tag).where(
            func.lower(Tag.name) == tag_data.name.lower()
        )
        result = await db.execute(existing_tag_query)
        existing_tag = result.scalar_one_or_none()

        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag_data.name}' already exists"
            )

        # Create tag
        new_tag = Tag(
            name=tag_data.name.strip().lower(),
            color=tag_data.color.upper()
        )

        db.add(new_tag)
        await db.commit()
        await db.refresh(new_tag)

        logger.info(f"Tag created: {new_tag.name}")
        return new_tag

    @staticmethod
    async def get_tags(
            db: AsyncSession,
            search: Optional[str] = None,
            page: int = 1,
            limit: int = 50
    ) -> dict:

        query = select(Tag).order_by(Tag.name)

        # Search filter
        if search:
            query = query.where(Tag.name.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # Paginate
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        tags = result.scalars().all()

        logger.info(f"Retrieved {len(tags)} tags")

        return {
            "tags": tags,
            "total": total_count,
            "page": page,
            "limit": limit
        }

    @staticmethod
    async def get_tag_by_id(db: AsyncSession, tag_id: str) -> Tag:
        query = select(Tag).where(Tag.id == tag_id)
        result = await db.execute(query)
        tag = result.scalar_one_or_none()

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )

        return tag

    @staticmethod
    async def update_tag(
            db: AsyncSession,
            tag_id: str,
            tag_update: TagUpdate
    ) -> Tag:

        tag = await TagService.get_tag_by_id(db, tag_id)

        # If updating name, check for duplicates
        if tag_update.name and tag_update.name.lower() != tag.name:
            existing_query = select(Tag).where(
                func.lower(Tag.name) == tag_update.name.lower()
            )
            result = await db.execute(existing_query)
            existing = result.scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tag '{tag_update.name}' already exists"
                )

            tag.name = tag_update.name.strip().lower()

        if tag_update.color:
            tag.color = tag_update.color.upper()

        await db.commit()
        await db.refresh(tag)

        logger.info(f"Tag {tag_id} updated")
        return tag

    @staticmethod
    async def delete_tag(db: AsyncSession, tag_id: str) -> bool:

        tag = await TagService.get_tag_by_id(db, tag_id)

        await db.delete(tag)
        await db.commit()

        logger.info(f"Tag {tag_id} deleted")
        return True

    @staticmethod
    async def add_tag_to_task(
            db: AsyncSession,
            task_id: str,
            tag_id: str,
            current_user: User
    ) -> Task:

        # Get task
        task_query = select(Task).options(
            selectinload(Task.tags),
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.comments)
        ).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Permission check
        if current_user.role == UserRole.MEMBER and task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add tags to this task"
            )

        # Get tag
        tag = await TagService.get_tag_by_id(db, tag_id)

        # Check if tag already added
        existing_tags = list(task.tags)
        if tag in existing_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag already added to this task"
            )

        # Add tag
        task.tags.append(tag)
        await db.commit()
        await db.refresh(task)
        refresh_query = select(Task).options(
            selectinload(Task.tags),
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.comments)
        ).where(Task.id == task_id)
        refresh_result = await db.execute(refresh_query)
        task = refresh_result.scalar_one()

        logger.info(f"Tag {tag_id} added to task {task_id}")
        return task

    @staticmethod
    async def remove_tag_from_task(
            db: AsyncSession,
            task_id: str,
            tag_id: str,
            current_user: User
    ) -> Task:

        # Get task
        task_query = select(Task).options(
            selectinload(Task.tags),
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.comments)
        ).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Permission check
        if current_user.role == UserRole.MEMBER and task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to remove tags from this task"
            )

        # Get tag
        tag = await TagService.get_tag_by_id(db, tag_id)

        # Check if tag is on task
        existing_tags = list(task.tags)
        if tag not in existing_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag not found on this task"
            )

        # Remove tag
        task.tags.remove(tag)
        await db.commit()
        await db.refresh(task)
        refresh_query = select(Task).options(
            selectinload(Task.tags),
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.comments)
        ).where(Task.id == task_id)
        refresh_result = await db.execute(refresh_query)
        task = refresh_result.scalar_one()

        logger.info(f"Tag {tag_id} removed from task {task_id}")
        return task

    @staticmethod
    async def get_task_tags(db: AsyncSession, task_id: str) -> List[Tag]:
        """Get all tags for a specific task."""
        task_query = select(Task).options(
            selectinload(Task.tags)
        ).where(Task.id == task_id)
        result = await db.execute(task_query)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        return list(task.tags)

    @staticmethod
    async def get_popular_tags(db: AsyncSession, limit: int = 10) -> List[dict]:

        from sqlalchemy import select, func

        query = select(
            Tag.id,
            Tag.name,
            Tag.color,
            func.count(task_tags.c.task_id).label('task_count')
        ).outerjoin(
            task_tags, Tag.id == task_tags.c.tag_id
        ).group_by(
            Tag.id
        ).order_by(
            func.count(task_tags.c.task_id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": str(row.id),
                "name": row.name,
                "color": row.color,
                "task_count": row.task_count
            }
            for row in rows
        ]