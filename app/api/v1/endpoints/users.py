import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from core.logger import get_logger
from core.database import get_db
from schemas.user import UserResponse, UserUpdate
from services.user import UserService
from app.api.dependencies import get_current_user
from models.user import User



user_router = APIRouter(prefix="/users", tags=["User"])
logger = get_logger(__name__)

@user_router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@user_router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(user_id:str, current_user: User= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user_by_id(db, user_id)
    return user

@user_router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user_profile(update:UserUpdate, db: AsyncSession = Depends(get_db), current_user: User= Depends(get_current_user)):
    updated_data = await UserService.update_user(db,current_user,update)
    return updated_data





