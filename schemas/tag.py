from pydantic import BaseModel,Field,field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional
import re

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., regex="^#[0-9A-Fa-f]{6}$")

    @field_validator('color')
    def validate_color(cls, v):
        return v.strip().lower()

    @validate_color('color')
    def validate_color(cls, v):
        return v.upper()


class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")

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
        json_encoders = {
            UUID: str,
        }
