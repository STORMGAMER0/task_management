from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatus, TaskResponse
from app.api.dependencies import get_current_user
from services.task import TaskService

task_router = APIRouter(prefix="/tasks", tags=["Task"])


@task_router.post("/",response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, current_user: User= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_task = await TaskService.create_task(db,task,current_user.id)
    return new_task



