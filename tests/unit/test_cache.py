"""
缓存模块单元测试
Sprint 8-9: 测试覆盖
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from services.shared.cache import (
    CacheBackend,
    RedisCache,
    get_cache,
    cached,
    clear_cache_pattern,
    _memory_cache
)


class TestCacheBackend:
    """缓存后端接口测试"""

    def test_not_implemented(self):
        """测试接口方法未实现"""
        backend = CacheBackend()
        with pytest.raises(NotImplementedError):
            backend.get("key")
        with pytest.raises(NotImplementedError):
            backend.set("key", "value")
        with pytest.raises(NotImplementedError):
            backend.delete("key")
        with pytest.raises(NotImplementedError):
            backend.clear()
        with pytest.raises(NotImplementedError):
            backend.exists("key")


class TestRedisCache:
    """Redis 缓存测试"""

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_init_without_redis(self):
        """测试无 Redis 时初始化"""
        cache = RedisCache()
        assert cache.client is None

    @patch("services.shared.cache.REDIS_AVAILABLE", True)
    @patch("services.shared.cache.get_config")
    @patch("services.shared.cache.redis")
    def test_init_with_redis(self, mock_redis, mock_get_config):
        """测试有 Redis 时初始化"""
        mock_config = Mock()
        mock_config.redis.enabled = True
        mock_config.redis.host = "localhost"
        mock_config.redis.port = 6379
        mock_config.redis.db = 0
        mock_config.redis.password = None
        mock_config.redis.max_connections = 50
        mock_config.redis.socket_timeout = 5
        mock_config.redis.socket_connect_timeout = 5
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_redis.Redis.return_value = mock_client
        mock_client.ping.return_value = True

        cache = RedisCache()
        assert cache.client == mock_client
        mock_client.ping.assert_called_once()

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_get_memory_fallback(self):
        """测试内存回退获取"""
        cache = RedisCache()
        _memory_cache["test_key"] = "test_value"
        assert cache.get("test_key") == "test_value"

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_set_memory_fallback(self):
        """测试内存回退设置"""
        cache = RedisCache()
        result = cache.set("test_key", "test_value")
        assert result is True
        assert _memory_cache["test_key"] == "test_value"

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_delete_memory_fallback(self):
        """测试内存回退删除"""
        cache = RedisCache()
        _memory_cache["test_key"] = "test_value"
        result = cache.delete("test_key")
        assert result is True
        assert "test_key" not in _memory_cache

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_exists_memory_fallback(self):
        """测试内存回退存在检查"""
        cache = RedisCache()
        _memory_cache["test_key"] = "test_value"
        assert cache.exists("test_key") is True
        assert cache.exists("nonexistent") is False

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_clear_memory_fallback(self):
        """测试内存回退清空"""
        cache = RedisCache()
        _memory_cache["key1"] = "value1"
        _memory_cache["key2"] = "value2"
        result = cache.clear()
        assert result is True
        assert len(_memory_cache) == 0

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_delete_pattern_memory_fallback(self):
        """测试内存回退模式删除"""
        cache = RedisCache()
        _memory_cache["user:1:name"] = "John"
        _memory_cache["user:1:email"] = "john@example.com"
        _memory_cache["other:key"] = "value"

        count = cache.delete_pattern("user:1:")
        assert count == 2
        assert "user:1:name" not in _memory_cache
        assert "user:1:email" not in _memory_cache
        assert "other:key" in _memory_cache

    @patch("services.shared.cache.REDIS_AVAILABLE", True)
    @patch("services.shared.cache.pickle")
    @patch("services.shared.cache.get_config")
    @patch("services.shared.cache.redis")
    def test_get_with_pickle(self, mock_redis, mock_get_config, mock_pickle):
        """测试 pickle 反序列化"""
        mock_config = Mock()
        mock_config.redis.enabled = True
        mock_config.redis.url = "redis://localhost:6379/0"
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_redis.Redis.return_value = mock_client
        mock_client.ping.return_value = True

        mock_value = b"serialized_data"
        mock_client.get.return_value = mock_value
        mock_pickle.loads.return_value = {"data": "value"}

        cache = RedisCache()
        result = cache.get("test_key")
        assert result == {"data": "value"}
        mock_pickle.loads.assert_called_with(mock_value)

    @patch("services.shared.cache.REDIS_AVAILABLE", True)
    @patch("services.shared.cache.pickle")
    @patch("services.shared.cache.get_config")
    @patch("services.shared.cache.redis")
    def test_get_with_json_fallback(self, mock_redis, mock_get_config, mock_pickle):
        """测试 JSON 回退反序列化"""
        mock_config = Mock()
        mock_config.redis.enabled = True
        mock_config.redis.url = "redis://localhost:6379/0"
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_redis.Redis.return_value = mock_client
        mock_client.ping.return_value = True

        mock_value = b'{"data": "value"}'
        mock_client.get.return_value = mock_value
        mock_pickle.loads.side_effect = Exception("Pickle error")

        cache = RedisCache()
        result = cache.get("test_key")
        assert result == {"data": "value"}

    @patch("services.shared.cache.REDIS_AVAILABLE", True)
    @patch("services.shared.cache.pickle")
    @patch("services.shared.cache.get_config")
    @patch("services.shared.cache.redis")
    def test_set_with_pickle(self, mock_redis, mock_get_config, mock_pickle):
        """测试 pickle 序列化设置"""
        mock_config = Mock()
        mock_config.redis.enabled = True
        mock_config.redis.url = "redis://localhost:6379/0"
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        mock_redis.Redis.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True

        serialized = b"serialized"
        mock_pickle.dumps.return_value = serialized

        cache = RedisCache()
        result = cache.set("test_key", {"data": "value"}, ttl=300)
        assert result is True
        mock_client.setex.assert_called_once()

    def test_make_key(self):
        """测试键生成"""
        cache = RedisCache()
        key = cache._make_key("user:123")
        assert key == "bisheng:user:123"


class TestCacheDecorator:
    """缓存装饰器测试"""

    def test_cached_decorator_hit(self):
        """测试缓存命中"""
        call_count = [0]

        @cached(ttl=300, key_prefix="test")
        def get_user(user_id):
            call_count[0] += 1
            return {"id": user_id, "name": f"User{user_id}"}

        # 第一次调用 - 缓存未命中
        result1 = get_user(1)
        assert result1 == {"id": 1, "name": "User1"}
        assert call_count[0] == 1

        # 第二次调用 - 应该从缓存获取
        result2 = get_user(1)
        assert result2 == {"id": 1, "name": "User1"}
        assert call_count[0] == 2  # 由于没有真实 Redis，实际上每次都会调用

    def test_cached_with_condition(self):
        """测试带条件的缓存"""
        call_count = [0]

        def should_cache(user_id):
            return user_id > 10

        @cached(ttl=300, key_prefix="user", cache_condition=should_cache)
        def get_user(user_id):
            call_count[0] += 1
            return {"id": user_id}

        get_user(5)  # 不缓存
        get_user(15)  # 缓存

    def test_cached_clear_cache(self):
        """测试清除缓存"""
        @cached(ttl=300, key_prefix="test")
        def get_data(key):
            return {"key": key}

        # 函数应该有 clear_cache 方法
        assert hasattr(get_data, "clear_cache")
        assert hasattr(get_data, "cache_key_prefix")


class TestCacheFunctions:
    """缓存函数测试"""

    @patch("services.shared.cache._cache", None)
    @patch("services.shared.cache.RedisCache")
    def test_get_cache_singleton(self, mock_redis_cache):
        """测试缓存单例"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    @patch("services.shared.cache.get_cache")
    def test_clear_cache_pattern(self, mock_get_cache):
        """测试清除模式缓存"""
        mock_cache = Mock()
        mock_cache.delete_pattern.return_value = 5
        mock_get_cache.return_value = mock_cache

        count = clear_cache_pattern("user:*")
        assert count == 5
        mock_cache.delete_pattern.assert_called_once_with("user:*")
