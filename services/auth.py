
from os import access
from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.api.v1.endpoints.auth import logger
from core.security import hash_password, verify_password, create_access_token,create_refresh_token
from schemas.auth import RegisterUser, Login
from models.user import User, UserRole
from tasks.email import send_welcome_email


class AuthService:

    @staticmethod
    async def register_user(db: AsyncSession, user_data:RegisterUser ):
        from models.user import User, UserRole

        try:

            result = await db.execute(select(User).where(User.email == user_data.email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.warning(f"Registration attempt with existing email: {user_data.email}")
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail= "Email already registered"
                )
            hashed_password = hash_password(user_data.password)
            new_user = User(
                email = user_data.email,
                password_hash = hashed_password,
                full_name = user_data.full_name,
                role = UserRole.MEMBER
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            logger.info(f"User registered: {new_user.email}")

            try:
                send_welcome_email.delay(
                    user_email=new_user.email,
                    user_name=new_user.full_name
                )
                logger.info(f"Welcome email queued for {new_user.email}")
            except Exception as e:
                # Don't fail registration if email fails
                logger.error(f"Failed to queue welcome email: {e}")

            return new_user

        except Exception as e:
            await db.rollback()
            logger.exception(f"Failed to register user: {e}")
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )



    @staticmethod
    async def authenticate_user(db: AsyncSession, login_data:Login ):
        #authenticate user by email and password(log them in essentially)
        result = await db.execute(select(User).where(User.email == login_data.email))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Login attempt with non-existent email: {login_data.email}")
            raise HTTPException(
                status_code= status.HTTP_401_UNAUTHORIZED,
                detail= "incorrect email or password"
            )

        logger.info(f"User found: {user.email}, checking password...")

        is_valid = verify_password(login_data.password, user.password_hash)
        logger.info(f"Password verification result: {is_valid}")  # ← Add this

        if not is_valid:
            logger.warning(f"Invalid password for user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.is_active:
            logger.warning(f"login attempt by inactive user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account is inactive"
            )

        logger.info(f"user authenticated: {user.email}")
        return user

    @staticmethod
    def create_tokens(user: User) -> dict :
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

