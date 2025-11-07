from fastapi import APIRouter, Depends, HTTPException,status
from typing import TYPE_CHECKING
from schemas.auth import RegisterUser, TokenResponse, Login
from schemas.user import UserResponse

from core.database import get_db, AsyncSession
from core.logger import get_logger



auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: RegisterUser, db: AsyncSession = Depends(get_db) ):
    from services.auth import AuthService
    new_user = await AuthService.register_user(db, user)
    logger.info(f"new user registered: {user.email}")
    return new_user

@auth_router.post("/login", response_model = TokenResponse )
async def login(login_data: Login, db: AsyncSession = Depends(get_db)):
    from services.auth import AuthService

    user = await AuthService.authenticate_user(db, login_data)
    tokens = AuthService.create_tokens(user)
    logger.info(f"User logged in: {user.email}")
    return TokenResponse(**tokens)




