from fastapi import APIRouter, Depends, HTTPException
from schemas.auth import RegisterUser

from core.database import get_db, AsyncSession
from core.logger import get_logger






auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)

@auth_router.post("/register")
def register(user: RegisterUser, db: AsyncSession = Depends(get_db) )
    new_user = user