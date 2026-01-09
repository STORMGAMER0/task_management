from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

from models.user import UserRole


class RegisterUser(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(..., max_length=100)
    role: Optional[UserRole] = None

    @field_validator('password')
    def validate_password(cls, v) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('password must contain at least one lowercase letter')
        return v

    @field_validator('full_name')
    def validate_full_name(cls, v):
        if any(char.isdigit() for char in v):
            raise ValueError('name can not contain numbers')
        return v.strip()


class Login(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


