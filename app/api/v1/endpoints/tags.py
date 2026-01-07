
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse
from schemas.task import TaskDetailResponse
from app.api.dependencies import get_current_user
from services.tag import TagService

tag_router = APIRouter(prefix="/tags", tags=["Tags"])

@tag_router.post(
    "/",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_tag(
        tag: TagCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    new_tag = await TagService.create_tag(db, tag)
    return new_tag

@tag_router.get("/", response_model=TagListResponse)
async def get_tags(
    search: str = Query(None, description="Search tags by name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Tags per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all tags with optional search."""
    tags = await TagService.get_tags(db, search, page, limit)
    return tags

@tag_router.get(
    "/popular",
    response_model=List[dict],
    status_code=status.HTTP_200_OK
)
async def get_popular_tags(
        limit: int = Query(10, ge=1, le=50, description="Number of tags to return"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    popular_tags = await TagService.get_popular_tags(db, limit)
    return popular_tags


@tag_router.get(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK
)
async def get_tag(
        tag_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Get a specific tag by ID."""
    tag = await TagService.get_tag_by_id(db, tag_id)
    return tag


@tag_router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK
)
async def update_tag(
        tag_id: str,
        tag_update: TagUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    updated_tag = await TagService.update_tag(db, tag_id, tag_update)
    return updated_tag


@tag_router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_tag(
        tag_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    await TagService.delete_tag(db, tag_id)
    return None


# Task-Tag Association Endpoints
task_tag_router = APIRouter(prefix="/tasks/{task_id}/tags", tags=["Task Tags"])


@task_tag_router.post(
    "/{tag_id}",
    response_model=TaskDetailResponse,
    status_code=status.HTTP_200_OK
)
async def add_tag_to_task(
        task_id: str,
        tag_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    task = await TagService.add_tag_to_task(db, task_id, tag_id, current_user)

    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        created_by=task.created_by,
        assigned_to=task.assigned_to,
        created_at=task.created_at,
        updated_at=task.updated_at,
        creator=task.creator,
        assignee=task.assignee,
        tags=list(task.tags),
        comments_count=len(task.comments) if hasattr(task, 'comments') else 0
    )


@task_tag_router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_tag_from_task(
        task_id: str,
        tag_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    await TagService.remove_tag_from_task(db, task_id, tag_id, current_user)
    return None


@task_tag_router.get(
    "/",
    response_model=List[TagResponse],
    status_code=status.HTTP_200_OK
)
async def get_task_tags(
        task_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Get all tags for a specific task."""
    tags = await TagService.get_task_tags(db, task_id)
    return tags
