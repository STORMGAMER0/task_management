from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from core.database import get_db
from core.security import decode_token
from models.user import User, UserRole
from core.logger import get_logger
from utils.rate_limiter import RateLimiter
from services.token_blacklist import TokenBlacklistService

logger = get_logger(__name__)

# OAuth2 scheme extracts token from authorization header

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                           db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"}, )
    token = credentials.credentials

    # Check if token is blacklisted (logged out)
    is_blacklisted = await TokenBlacklistService.is_token_blacklisted(token)
    if is_blacklisted:
        logger.warning("Attempt to use blacklisted token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception

    # fetch the user from the database

    logger.info(f"Decoded user_id from token: {user_id}")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

        # Check rate limit
    await RateLimiter.check_rate_limit(str(user.id), endpoint="api")

    return user
