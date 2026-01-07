from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentWithAuthor,
    CommentListResponse
)
from app.api.dependencies import get_current_user
from services.comment import CommentService


comment_router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


@comment_router.post("/", response_model=CommentWithAuthor, status_code= status.HTTP_201_CREATED)
async def create_comment(
        task_id: str,
        comment: CommentCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    new_comment = await CommentService.create_comment(
        db, task_id, comment, current_user
    )

    return new_comment

@comment_router.get("/", response_model=CommentListResponse, status_code = status.HTTP_200_OK)
async def get_comments(
        task_id: str,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(50, ge=1, le=100, description="Comments per page"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    comments = await CommentService.get_comments(db, task_id, current_user, page, limit)

    return comments

@comment_router.patch(
    "/{comment_id}",
    response_model = CommentWithAuthor,
    status_code = status.HTTP_200_OK
)
async def update_comment(
    task_id: str,
    comment_id: str,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    updated_comment = await CommentService.update_comment(db, comment_id, comment_update, current_user)

    return updated_comment

@comment_router.delete(
    "/{comment_id}",
    status_code = status.HTTP_204_NO_CONTENT
)
async def delete_comment(
        task_id: str,
        comment_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    await CommentService.delete_comment(db, comment_id, current_user)
    return None

