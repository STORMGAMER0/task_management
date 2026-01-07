from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List
import re


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$")

    @field_validator('name')
    def validate_name(cls, v):
        return v.strip().lower()

    @field_validator('color')
    def validate_color(cls, v):
        return v.upper()


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")

    @field_validator('name')
    def validate_name(cls, v):
        if v:
            return v.strip().lower()
        return v

    @field_validator('color')
    def validate_color(cls, v):
        if v:
            return v.upper()
        return v


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Paginated list of tags"""
    tags: List[TagResponse]
    total: int
    page: int
    limit: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit