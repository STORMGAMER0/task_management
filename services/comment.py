from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.comment import Comment
from models.task import Task
from models.user import User, UserRole
from schemas.comment import CommentCreate, CommentUpdate
from core.logger import get_logger
from services.notification import WebSocketNotificationService
from tasks.email import send_task_comment_notification

logger = get_logger(__name__)


class CommentService:
    @staticmethod
    async def create_comment(
            db: AsyncSession,
            task_id: str,
            comment_data: CommentCreate,
            current_user: User
    ):

        task_query = select(Task).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        # Permission check: can only comment on tasks you can view
        if current_user.role == UserRole.MEMBER:
            if task.created_by != current_user.id and task.assigned_to != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to comment on this task"
                )

            new_comment = Comment(
                task_id=task_id,
                user_id=current_user.id,
                content=comment_data.content
            )

            db.add(new_comment)
            await db.commit()
            await db.refresh(new_comment)

            comment_query = select(Comment).options(
                selectinload(Comment.author)
            ).where(Comment.id == new_comment.id)
            comment_result = await db.execute(comment_query)
            comment_with_author = comment_result.scalar_one()

            logger.info(f"Comment created on task {task_id} by user {current_user.id}")

            comment_data_dict = {
                "id": str(comment_with_author.id),
                "task_id": str(task_id),
                "user_id": str(current_user.id),
                "content": comment_with_author.content,
                "author_name": current_user.full_name,
                "created_at": comment_with_author.created_at.isoformat()
            }

            await WebSocketNotificationService.notify_comment_added(
                str(task_id),
                comment_data_dict,
                str(current_user.id)
            )

            try:
                # Get task creator and assignee
                users_to_notify = set()
                if task.created_by and task.created_by != current_user.id:
                    users_to_notify.add(task.created_by)
                if task.assigned_to and task.assigned_to != current_user.id:
                    users_to_notify.add(task.assigned_to)

                # Send emails
                for user_id in users_to_notify:
                    user_query = select(User).where(User.id == user_id)
                    user_result = await db.execute(user_query)
                    user = user_result.scalar_one_or_none()

                    if user:
                        send_task_comment_notification.delay(
                            user_email=user.email,
                            task_title=task.title,
                            commenter_name=current_user.full_name,
                            comment_text=comment_data.content
                        )
                        logger.info(f"Comment notification email queued for {user.email}")
            except Exception as e:
                logger.error(f"failed to queue comment notification emails: {e}")
        return comment_with_author

    @staticmethod
    async def get_comments(
            db: AsyncSession,
            task_id: str,
            current_user: User,
            page: int = 1,
            limit: int = 50
    ) -> dict:
        # Check if task exists and user has access
        task_query = select(Task).where(Task.id == task_id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Permission check
        if current_user.role == UserRole.MEMBER:
            if task.created_by != current_user.id and task.assigned_to != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this task's comments"
                )

        query = select(Comment).options(
            selectinload(Comment.author)
        ).where(
            and_(
                Comment.task_id == task_id,
                Comment.deleted_at.is_(None)
            )
        ).order_by(Comment.created_at.desc())

        # Count total
        count_query = select(func.count()).select_from(
            select(Comment).where(
                and_(
                    Comment.task_id == task_id,
                    Comment.deleted_at.is_(None)
                )
            ).subquery()
        )
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # Paginate
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        comments = result.scalars().all()

        logger.info(f"Retrieved {len(comments)} comments for task {task_id}")

        return {
            "comments": comments,
            "total": total_count,
            "page": page,
            "limit": limit
        }

    @staticmethod
    async def update_comment(
            db: AsyncSession,
            comment_id: str,
            comment_update: CommentUpdate,
            current_user: User
    ) -> Comment:
        #Update a comment (only by author)
        # Get comment
        query = select(Comment).options(
            selectinload(Comment.author)
        ).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        # Permission check: only author can edit
        if comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this comment"
            )

        # Update
        comment.content = comment_update.content
        await db.commit()
        await db.refresh(comment)

        logger.info(f"Comment {comment_id} updated by user {current_user.id}")

        return comment

    @staticmethod
    async def delete_comment(
            db: AsyncSession,
            comment_id: str,
            current_user: User
    ) -> bool:

        #Delete a comment (soft delete).
        #Only author or admin can delete.

        # Get comment
        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        # Permission check: author or admin
        if comment.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment"
            )

        # Soft delete
        from datetime import datetime, timezone
        comment.deleted_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"Comment {comment_id} deleted by user {current_user.id}")

        return True