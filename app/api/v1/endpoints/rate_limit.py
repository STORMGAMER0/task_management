from fastapi import APIRouter, Depends, status
from models.user import User
from app.api.dependencies import get_current_user
from utils.rate_limiter import RateLimiter

rate_limit_router = APIRouter(prefix="/rate-limit", tags=["Rate Limiting"])


@rate_limit_router.get("/status", status_code=status.HTTP_200_OK)
async def get_rate_limit_status(current_user: User = Depends(get_current_user)):

    info = await RateLimiter.get_rate_limit_info(str(current_user.id))
    return info