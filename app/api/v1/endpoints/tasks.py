from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.task import TaskPriority
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatus, TaskResponse, TaskListResponse, TaskDetailResponse
from app.api.dependencies import get_current_user
from services.task import TaskService

task_router = APIRouter(prefix="/tasks", tags=["Task"])


@task_router.post("/",response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, current_user: User= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_task = await TaskService.create_task(db,task,current_user.id)
    return new_task

@task_router.get("/", response_model=TaskListResponse, status_code=status.HTTP_200_OK)
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

@task_router.get("/{task_id}", response_model=TaskDetailResponse, status_code=status.HTTP_200_OK)
async def get_task(task_id:str, current_user: User= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await TaskService.get_task_by_id(db, task_id, current_user)

    # Convert to response format
    tags_list = list(task.tags) if task.tags else []


    comments_count = len(list(task.comments)) if task.comments else 0


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
        tags=tags_list,
        comments_count=comments_count
    )

