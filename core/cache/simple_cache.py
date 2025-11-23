from core.cache.redis_cache import redis_client
import hashlib
import pickle
from typing import Any, Optional

# We keep the interface similar but delegate to Redis
class CacheWrapper:
    def get(self, key: str) -> Optional[Any]:
        data = redis_client.get(key)
        if data:
            try:
                return pickle.loads(data)
            except:
                return data # Return raw bytes if pickle fails
        return None
        
    def set(self, key: str, value: Any, ttl: int = 3600):
        if not isinstance(value, (bytes, str)):
            try:
                value = pickle.dumps(value)
            except:
                pass # Should handle error
        redis_client.set(key, value, ttl)

# Global instance
embedding_cache = CacheWrapper()

def get_cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()
