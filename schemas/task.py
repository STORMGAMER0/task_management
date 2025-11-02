from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel,Field, field_validator
from typing import Optional
from models.task import TaskStatus, TaskPriority
from schemas.user import UserResponse


class TaskBase:
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=400)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date:Optional[datetime]

class TaskCreate(TaskBase):
    assigned_to : Optional[UUID]

    @field_validator('due_date')
    def validate_due_date(cls, v):
        if v and v < datetime.now(timezone.utc):
            raise ValueError('due date must be in the future')
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=400)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None

    @field_validator('due date')
    def validate_due_date(cls, v):

        if v and v < datetime.utcnow():
            raise ValueError('Due date must be in the future')
        return v

class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    created_by: UUID
    assigned_to: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
        }


class TaskWithCreator(TaskResponse):

    creator: "UserResponse"  # Forward reference

    class Config:
        from_attributes = True


class TaskWithAssignee(TaskResponse):
    assignee: Optional["UserResponse"] = None

    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    creator: "UserResponse"
    assignee: Optional["UserResponse"] = None
    tags: list["TagResponse"] = []
    comments_count: int = 0

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    limit: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit