import json
import hashlib
from typing import Optional, Any
from redis import asyncio as aioredis
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

class CacheService:
    #redis based caching service

    _redis_client: Optional[aioredis.Redis] = None

    @classmethod
    async def get_redis(cls) ->Optional[aioredis.Redis] :
        #this gets or creates a redis connection and returns None if redis url is not configured

        if not settings.redis_url:
            logger.warning("redis URL not configured, caching disabled")
            return None
        if cls._redis_client is None:
            try:
                cls._redis_client = await aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses = True, max_connections=10)
                await cls._redis_client.ping()
                logger.info("redis connection established")
            except Exception as e:
                logger.error(f"failed to connect to redis: {e}")
                cls._redis_client = None
                return None
        return cls._redis_client

    @classmethod
    async def close(cls):
        #close redis connection on shutdown
        if cls._redis_client:
            await cls._redis_client.close()
            logger.info("redis connection closed")

    @staticmethod
    def _serialize(value:Any)-> str:
        #this serializes objects to JSON string
        try:
            if hasattr(value, 'model_dump'):
                return json.dumps(value.model_dump())
            return json.dumps(value)
        except Exception as e:
            logger.error(f"serialization error: {e}")
            raise
    @staticmethod
    def _deserialize(value: str)-> Any:
        # this serializes JSON back to objects
