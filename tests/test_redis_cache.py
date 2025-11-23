import pytest
from unittest.mock import MagicMock, patch
from core.cache.redis_cache import RedisCache

@pytest.fixture
def mock_redis():
    with patch("redis.Redis") as mock:
        yield mock

def test_redis_cache_singleton(mock_redis):
    cache1 = RedisCache()
    cache2 = RedisCache()
    assert cache1 is cache2

def test_redis_set_get(mock_redis):
    cache = RedisCache()
    # Mock client
    cache.client = MagicMock()
    cache.client.get.return_value = b"test_value"
    
    cache.set("key", "value")
    cache.client.setex.assert_called_with("key", 3600, "value")
    
    val = cache.get("key")
    assert val == b"test_value"
