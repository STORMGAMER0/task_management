from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError


from core.database import get_db
from core.security import decode_token
from models.user import User, UserRole
from core.logger import get_logger

logger = get_logger(__name__)

#OAuth2 scheme extracts token from authorization header

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="could not validate credentials", headers={"WWW-Authenticate": "Bearer"},)

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
                status_code= status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception

    #fetch the user from the database

    result = await db.execute(select(User).where)

