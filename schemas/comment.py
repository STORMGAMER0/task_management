from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from schemas.user import UserResponse


class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=1000)

class CommentResponse(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentWithAuthor(CommentResponse):
    author: "UserResponse"

    class Config:
        from_attributes = True

class CommentListResponse(BaseModel):

    comments: List[CommentWithAuthor]
    total: int
    page: int
    limit: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit