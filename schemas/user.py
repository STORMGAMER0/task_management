from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

from sqlalchemy import UUID

from models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserUpdate(BaseModel):
    email:Optional[EmailStr] = None
    full_name: Optional[str]= Field(None, min_length=2, max_length=255)
    password: Optional[str]= Field(None, min_length=8, max_length=100)

    @field_validator('password')
    def validate_password(cls, v):
        if v is None:
            return v
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
        }

class UserResponseWithStats(UserResponse):
    tasks_created_count: int = 0
    tasks_assigned_count: int = 0
    comments_count: int = 0


