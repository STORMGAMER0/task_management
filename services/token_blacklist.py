from typing import Optional
from datetime import datetime, timedelta
import hashlib

from services.cache import CacheService
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class TokenBlacklistService:

    @staticmethod
    def _hash_token(token: str) -> str:

        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    async def blacklist_token(
            token: str,
            token_type: str = "access",
            expiry_seconds: Optional[int] = None
    ) -> bool:

        redis = await CacheService.get_redis()
        if not redis:

            logger.warning("Redis unavailable, cannot blacklist token")
            return False


        token_hash = TokenBlacklistService._hash_token(token)


        if expiry_seconds is None:
            if token_type == "access":
                expiry_seconds = settings.jwt_access_token_expires_minutes * 60
            else:  # refresh
                expiry_seconds = settings.jwt_refresh_token_expire_days * 24 * 60 * 60


        key = f"blacklist:token:{token_hash}"

        try:
            await redis.setex(
                key,
                expiry_seconds,
                datetime.now().isoformat()  # Store blacklist timestamp
            )

            logger.info(f"Token blacklisted (type={token_type}, ttl={expiry_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    @staticmethod
    async def is_token_blacklisted(token: str) -> bool:

        redis = await CacheService.get_redis()
        if not redis:
            # If Redis is down, allow the token (fail open)
            # Alternative: fail closed (return True) for security
            return False

        token_hash = TokenBlacklistService._hash_token(token)
        key = f"blacklist:token:{token_hash}"

        try:
            exists = await redis.exists(key)

            if exists:
                logger.warning(f"Attempted use of blacklisted token")

            return bool(exists)

        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False  # Fail open

    @staticmethod
    async def clear_user_tokens(user_id: str) -> int:



        logger.warning(
            f"clear_user_tokens called for user {user_id} "
            "but not fully implemented due to token hashing"
        )

        # TODO: Implement user -> tokens mapping if needed
        return 0

    @staticmethod
    async def blacklist_all_user_tokens(
            user_id: str,
            access_token: Optional[str] = None,
            refresh_token: Optional[str] = None
    ) -> bool:

        success = False

        if access_token:
            result = await TokenBlacklistService.blacklist_token(
                access_token,
                token_type="access"
            )
            success = success or result

        if refresh_token:
            result = await TokenBlacklistService.blacklist_token(
                refresh_token,
                token_type="refresh"
            )
            success = success or result

        if success:
            logger.info(f"User {user_id} tokens blacklisted (logout)")

        return success