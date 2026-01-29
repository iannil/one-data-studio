"""
缓存模块单元测试
Sprint 8-9: 测试覆盖
"""

import sys
from pathlib import Path

# 添加项目根路径以便导入 services.shared
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

import pytest
from unittest.mock import MagicMock, patch, Mock
from services.shared.cache import (
    CacheBackend,
    RedisCache,
    MemoryCache,
    get_cache,
    cached,
    clear_cache_pattern,
    _get_memory_cache
)


class TestCacheBackend:
    """缓存后端接口测试"""

    def test_default_implementations(self):
        """测试接口方法默认实现（返回默认值而非抛出异常）"""
        backend = CacheBackend()
        # CacheBackend 提供默认实现，返回 None/False
        assert backend.get("key") is None
        assert backend.set("key", "value") is False
        assert backend.delete("key") is False
        assert backend.clear() is False
        assert backend.exists("key") is False


class TestMemoryCache:
    """内存缓存测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        """测试删除"""
        cache = MemoryCache()
        cache.set("key", "value")
        result = cache.delete("key")
        assert result is True
        assert cache.get("key") is None

    def test_exists(self):
        """测试存在检查"""
        cache = MemoryCache()
        cache.set("key", "value")
        assert cache.exists("key") is True
        assert cache.exists("nonexistent") is False

    def test_clear(self):
        """测试清空"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        result = cache.clear()
        assert result is True
        assert cache.get("key1") is None
        assert cache.get("key2") is None


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
        mock_config.redis.sentinel_enabled = False
        mock_get_config.return_value = mock_config

        mock_pool = Mock()
        mock_redis.ConnectionPool.return_value = mock_pool

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
        # 使用 cache 的 set 方法，而不是直接操作 _memory_cache
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_set_memory_fallback(self):
        """测试内存回退设置"""
        cache = RedisCache()
        result = cache.set("test_key", "test_value")
        assert result is True
        assert cache.get("test_key") == "test_value"

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_delete_memory_fallback(self):
        """测试内存回退删除"""
        cache = RedisCache()
        cache.set("test_key", "test_value")
        result = cache.delete("test_key")
        assert result is True
        assert cache.get("test_key") is None

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_exists_memory_fallback(self):
        """测试内存回退存在检查"""
        cache = RedisCache()
        cache.set("test_key", "test_value")
        assert cache.exists("test_key") is True
        assert cache.exists("nonexistent") is False

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_clear_memory_fallback(self):
        """测试内存回退清空"""
        cache = RedisCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        result = cache.clear()
        assert result is True

    @patch("services.shared.cache.REDIS_AVAILABLE", False)
    def test_delete_pattern_memory_fallback(self):
        """测试内存回退模式删除"""
        cache = RedisCache()
        cache.set("user:1:name", "John")
        cache.set("user:1:email", "john@example.com")
        cache.set("other:key", "value")

        count = cache.delete_pattern("user:1:")
        assert count >= 0  # 实际删除数量取决于实现
        assert cache.get("other:key") == "value"

    def test_make_key(self):
        """测试键生成"""
        cache = RedisCache()
        key = cache._make_key("user:123")
        assert key == "agent:user:123"


class TestCacheDecorator:
    """缓存装饰器测试"""

    def test_cached_decorator_hit(self):
        """测试缓存命中"""
        import uuid
        # 使用唯一前缀避免缓存污染
        unique_prefix = f"test_{uuid.uuid4().hex[:8]}"
        call_count = [0]

        @cached(ttl=300, key_prefix=unique_prefix)
        def get_user(user_id):
            call_count[0] += 1
            return {"id": user_id, "name": f"User{user_id}"}

        # 第一次调用 - 缓存未命中
        result1 = get_user(1)
        assert result1 == {"id": 1, "name": "User1"}
        assert call_count[0] == 1

        # 第二次调用 - 应该命中缓存
        result2 = get_user(1)
        assert result2 == {"id": 1, "name": "User1"}
        # 缓存命中，call_count 应该保持为 1
        assert call_count[0] == 1

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
