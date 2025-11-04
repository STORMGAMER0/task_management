from fastapi import APIRouter, Depends, HTTPException,status
from typing import TYPE_CHECKING
from schemas.auth import RegisterUser
from schemas.user import UserResponse
from core.database import get_db, AsyncSession
from core.logger import get_logger

if TYPE_CHECKING:
    from services.auth import AuthService




auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: RegisterUser, db: AsyncSession = Depends(get_db) ):
    from services.auth import AuthService
    new_user = await AuthService.register_user(db, user)
    logger.info(f"new user registered: {user.email}")
    return new_user

