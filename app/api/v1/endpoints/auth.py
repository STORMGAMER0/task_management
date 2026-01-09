from fastapi import APIRouter, Depends, HTTPException,status
from typing import TYPE_CHECKING
from schemas.auth import RegisterUser, TokenResponse, Login, TokenRefreshRequest, TokenRefreshResponse, LogoutRequest
from schemas.user import UserResponse

from core.database import get_db, AsyncSession
from core.logger import get_logger

from core.security import decode_token, create_access_token
from app.api.dependencies import get_current_user
from models.user import User
from services.token_blacklist import TokenBlacklistService
from jose import JWTError

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


@auth_router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
        refresh_data: TokenRefreshRequest,
        db: AsyncSession = Depends(get_db)
):

    try:
        # Check if refresh token is blacklisted
        is_blacklisted = await TokenBlacklistService.is_token_blacklisted(
            refresh_data.refresh_token
        )

        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        # Decode refresh token
        payload = decode_token(refresh_data.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Verify user still exists and is active
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new access token
        new_access_token = create_access_token({"sub": str(user.id)})

        logger.info(f"Access token refreshed for user: {user.email}")

        return TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer"
        )

    except JWTError as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
        logout_data: LogoutRequest,
        current_user: User = Depends(get_current_user)
):
    """
    Logout user by blacklisting their tokens.

    Blacklists:
    - The current access token (from Authorization header)
    - The refresh token (if provided in request body)
    """
    # Get access token from header
    if logout_data.refresh_token:
        await TokenBlacklistService.blacklist_token(
            logout_data.refresh_token,
            token_type="refresh"
        )
        logger.info(f"User logged out (refresh token blacklisted): {current_user.email}")
    else:
        logger.info(f"User logged out (no tokens blacklisted): {current_user.email}")

    return None