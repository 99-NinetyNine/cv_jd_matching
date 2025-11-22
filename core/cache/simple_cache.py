from functools import lru_cache
import hashlib

class SimpleCache:
    def __init__(self, maxsize=1000):
        self._cache = {}
        self._maxsize = maxsize
        
    def get(self, key):
        return self._cache.get(key)
        
    def set(self, key, value):
        if len(self._cache) >= self._maxsize:
            # Simple eviction: remove random or first
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value

# Global instance
embedding_cache = SimpleCache()

def get_cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()
