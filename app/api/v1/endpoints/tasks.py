from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.task import TaskPriority
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatus, TaskResponse
from app.api.dependencies import get_current_user
from services.task import TaskService

task_router = APIRouter(prefix="/tasks", tags=["Task"])


@task_router.post("/",response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, current_user: User= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_task = await TaskService.create_task(db,task,current_user.id)
    return new_task

@task_router.get("/", response_model=list[TaskResponse], status_code=status.HTTP_200_OK)
async def get_tasks(status:Optional[TaskStatus] = Query(None, description="filter by status"),
                    priority: Optional[TaskPriority] = Query(None, description="filter by priority"),
                    search: Optional[str] = Query(None, description="search in title and description"),
                    assigned_to: Optional[UUID] = Query(None, description="filter by assigned to"),
                    sort_by : str = Query("created_at", description="Sort field"),
                    order: str = Query("desc", description="sort order: asc or desc"),
                    page: int = Query(1, ge=1, description= "page number"),
                    limit: int = Query(10, ge=1, le=100, description="items per page"),
                    current_user: User = Depends (get_current_user),
                    db: AsyncSession = Depends(get_db)
                    ):

    tasks = await TaskService.get_tasks(db=db,
        current_user=current_user,
        status=status,
        priority=priority,
        search=search,
        assigned_to=assigned_to,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit)

    return tasks

