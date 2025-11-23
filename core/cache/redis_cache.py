import redis
import os
import json
import logging
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

class RedisCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        try:
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=False,  # Keep as bytes for flexibility
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.warning(f"Could not connect to Redis: {e}. Caching will be disabled.")
            self.client = None

    def get(self, key: str) -> Optional[bytes]:
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Union[bytes, str], ttl: int = 3600):
        if not self.client:
            return
        try:
            self.client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str):
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def flush(self):
        if not self.client:
            return
        try:
            self.client.flushdb()
        except Exception as e:
            logger.error(f"Redis flush error: {e}")

# Global instance
redis_client = RedisCache()
