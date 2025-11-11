
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.user import User
from core.logger import get_logger
from schemas.user import UserUpdate
from core.security import hash_password

logger = get_logger(__name__)

class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str):
        result = await db.execute(select(User). where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"get user request by id {user_id} failed")
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="user not found")
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user: User, data: UserUpdate):

        try:
            if data.email and data.email != user.email:
                result = await db.execute(select(User).where(User.email == data.email))
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use"
                    )
                user.email = data.email

            if data.password:
                user.password_hash = hash_password(data.password)
                logger.info(f"Password updated for user {user.id}")

            updated_data = data.model_dump(exclude_unset=True, exclude={"password", "email"}  )
            for field, value in updated_data.items():
                setattr(user, field, value)
            logger.info(f"user {user.id} updated their profile")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            print(f"user email is{user.email}")
            await db.rollback()
            raise ValueError(f"Failed to update user: {str(e)}")
        return user



