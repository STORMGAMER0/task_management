
from typing import Optional
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import time

from services.cache import CacheService
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis sliding window algorithm.

    How it works:
    1. Key format: "rate_limit:user_id:endpoint"
    2. Store timestamps of requests in Redis list
    3. Remove old timestamps (> 1 minute)
    4. Count remaining timestamps
    5. Allow if count < limit, else reject
    """

    @staticmethod
    async def check_rate_limit(
            user_id: str,
            endpoint: str = "api",
            limit: Optional[int] = None,
            window_seconds: int = 60
    ) -> bool:

        # Use config default if not specified
        if limit is None:
            limit = settings.rate_limit_per_minute

        redis = await CacheService.get_redis()
        if not redis:
            # If Redis is unavailable, allow request (fail open)
            logger.warning("Redis unavailable, rate limiting disabled")
            return True

        # Generate rate limit key
        key = f"rate_limit:{user_id}:{endpoint}"
        current_time = time.time()
        window_start = current_time - window_seconds

        try:
            # Remove old entries (outside time window)
            await redis.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = await redis.zcard(key)

            if request_count >= limit:
                # Rate limit exceeded
                # Get oldest timestamp to calculate retry-after
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window_seconds - current_time)
                else:
                    retry_after = window_seconds

                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint}: "
                    f"{request_count}/{limit} requests"
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

            # Add current request
            await redis.zadd(key, {str(current_time): current_time})

            # Set expiry on key (cleanup)
            await redis.expire(key, window_seconds)

            # Log remaining requests
            remaining = limit - request_count - 1
            logger.debug(f"Rate limit check passed for user {user_id}: {remaining} requests remaining")

            return True

        except HTTPException:
            # Re-raise rate limit errors
            raise
        except Exception as e:
            # Log error but allow request (fail open)
            logger.error(f"Rate limit check failed: {e}")
            return True

    @staticmethod
    async def get_rate_limit_info(
            user_id: str,
            endpoint: str = "api",
            limit: Optional[int] = None,
            window_seconds: int = 60
    ) -> dict:
        """
        Get current rate limit status for a user.

        Returns:
            {
                "limit": 100,
                "remaining": 85,
                "reset_at": "2026-01-05T12:34:56Z"
            }
        """
        if limit is None:
            limit = settings.rate_limit_per_minute

        redis = await CacheService.get_redis()
        if not redis:
            return {
                "limit": limit,
                "remaining": limit,
                "reset_at": None
            }

        key = f"rate_limit:{user_id}:{endpoint}"
        current_time = time.time()
        window_start = current_time - window_seconds

        try:
            # Remove old entries
            await redis.zremrangebyscore(key, 0, window_start)

            # Count current requests
            request_count = await redis.zcard(key)
            remaining = max(0, limit - request_count)

            # Calculate reset time
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_timestamp = oldest[0][1] + window_seconds
                reset_at = datetime.fromtimestamp(reset_timestamp).isoformat()
            else:
                reset_at = None

            return {
                "limit": limit,
                "remaining": remaining,
                "reset_at": reset_at,
                "used": request_count
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "reset_at": None
            }

    @staticmethod
    async def reset_rate_limit(user_id: str, endpoint: str = "api"):
        """
        Reset rate limit for a user (admin function).

        Useful for testing or emergency overrides.
        """
        redis = await CacheService.get_redis()
        if not redis:
            return False

        key = f"rate_limit:{user_id}:{endpoint}"

        try:
            await redis.delete(key)
            logger.info(f"Rate limit reset for user {user_id} on {endpoint}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


# Convenience function for dependency injection
async def check_rate_limit(user_id: str, endpoint: str = "api"):
    """
    Dependency function for FastAPI routes.

    Usage in endpoints:
        @app.get("/api/v1/tasks")
        async def get_tasks(
            current_user: User = Depends(get_current_user),
            _: bool = Depends(lambda u=Depends(get_current_user): check_rate_limit(str(u.id)))
        ):
            ...
    """
    return await RateLimiter.check_rate_limit(user_id, endpoint)