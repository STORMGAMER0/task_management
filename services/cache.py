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
        try:
            return json.loads(value)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise

    @classmethod
    async def get(cls, key: str)-> Optional[Any]:
        #this retrieves a value from the cache. it takes the cache key as an argument and returns the deserialized cache value or None if its not found
        redis = await cls.get_redis()
        if not redis:
            return None

        try:
            value = await redis.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return cls._deserialize(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    @classmethod
    async def set(cls, key:str, value:Any, ttl: Optional[int]= None)-> bool:
        #store a value in cache with optional TTL
        #arguments : key = cache key, value=cache value(it will be json serialized), ttl = Time to Live in seconds

        redis = await cls.get_redis()
        if not redis:
            return False

        try:
            serialized = cls._serialize(value)
            if ttl:
                await redis.setex(key, ttl, serialized)
            else:
                await redis.set(key, serialized)
            logger.debug(f"cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"cache set error for key {key}: {e}")
            return False

    @classmethod
    async def delete(cls, key: str) -> bool:
        #this deletes a key from cache
        redis = await cls.get_redis()
        if not redis:
            return False

        try:
            deleted = await redis.delete(key)
            logger.debug(f"cache DELETE: {key} (existed: {deleted > 0})")
            return deleted > 0
        except Exception as e:
            logger.error(f"cache delete error for key{key}: {e}")
            return False

    @classmethod
    async def delete_pattern(cls, pattern: str)-> int:
        #this deletes all keys that match a pattern and returns number of keys deleted
        redis = await cls.get_redis()
        if not redis:
            return 0
        try:
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                deleted = await redis.delete(*keys)
                logger.info(f"Cache DELETE pattern '{pattern}' : {deleted} keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"cache delete pattern error for '{pattern}': {e}")
            return 0

    @staticmethod
    def generate_cache_key(prefix: str, *args, **kwargs)-> str:
        #this generates a structured cache key
        # Example: generate_cache_key("user", user_id) -> "user:123"
        parts = [prefix] + [str(arg) for arg in args]

        #if there are key word arguments (query filters), hash them for the key
        if kwargs:
            #sorting the kwargs for consistent hashing
            sorted_kwargs = sorted(kwargs.items())

            #sorted items always returns a list so we'll convert them to a string so we can encode them as we can only hash encoded data
            kwargs_str = json.dumps(sorted_kwargs, sort_keys=True)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            parts.append(kwargs_hash)

        return ":".join(kwargs_hash)



async def cache_user_profile(user_id: str, user_data: Any)-> bool:
    #cache user profile
    key = CacheService.generate_cache_key("user", user_id)
    return await CacheService.set(key, user_data, ttl=settings.cache_ttl_user_profile)

async def get_cached_user_profile(user_id:str) -> Optional[Any]:
    key = CacheService.generate_cache_key("user", user_id)
    return await CacheService.get(key)

async def invalidate_user_cache(user_id:str)->bool:
    key = CacheService.generate_cache_key("user", user_id)
    return await CacheService.delete(key)

async def cache_task_detail(task_id: str, task_data: Any)-> bool:
    key = CacheService.generate_cache_key("task", task_id)
    return await CacheService.set(key, task_data, ttl=settings.cache_ttl_task_detail)

async def get_cached_task_detail(task_id:str)-> Optional[Any]:
    key = CacheService.generate_cache_key("task", task_id)
    return await CacheService.get(key)

async def invalidate_task_cache(task_id: str) -> bool:
    #Invalidate task cache when task is updated
    key = CacheService.generate_cache_key("task", task_id)
    return await CacheService.delete(key)

async def cache_task_list(user_id: str, filters: dict, task_data: Any)-> bool:
    #cache task list query results
    key = CacheService.generate_cache_key("tasks", "list", user_id, **filters)
    return await CacheService.set(key, task_data, ttl = settings.cache_ttl_task_list)

async def get_cached_task_list(user_id:str, filters: dict)-> bool:
    key = CacheService.generate_cache_key("tasks", "list", user_id, **filters)
    return await CacheService.get(key)

async def invalidate_all_task_lists()-> int:
    #invalidates all cached task lists. this is called when any task is created/updated/deleted.
    return await CacheService.delete_pattern("tasks:list:*")













