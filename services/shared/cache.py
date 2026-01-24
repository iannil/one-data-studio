"""
缓存管理模块
Sprint 8: API 响应缓存
Sprint 14: Redis Sentinel 高可用支持

提供 Redis 缓存功能，支持多种缓存策略和 TTL 配置
"""

import json
import logging
import pickle
from typing import Any, Optional, Callable, TypeVar, Union, Dict
from functools import wraps
from datetime import timedelta

try:
    import redis
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .config import get_config

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheBackend:
    """缓存后端接口"""

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        return False

    def clear(self) -> bool:
        """清空所有缓存"""
        return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return False


class MemoryCache(CacheBackend):
    """内存缓存实现 - 用于本地开发或 Redis 不可用时的回退"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        import time

        # 检查是否过期
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                self.delete(key)
                return None

        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        import time

        self._cache[key] = value
        if ttl:
            self._expiry[key] = time.time() + ttl
        return True

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        return True

    def clear(self) -> bool:
        """清空所有缓存"""
        self._cache.clear()
        self._expiry.clear()
        return True

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        import time

        if key not in self._cache:
            return False

        # 检查是否过期
        if key in self._expiry and time.time() > self._expiry[key]:
            self.delete(key)
            return False

        return True

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        import fnmatch

        count = 0
        keys_to_delete = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            self.delete(k)
            count += 1
        return count


class RedisCache(CacheBackend):
    """Redis 缓存实现 - Sprint 14: 支持 Sentinel 高可用"""

    def __init__(self, redis_client=None):
        """
        初始化 Redis 缓存

        Args:
            redis_client: Redis 客户端实例（可选）
        """
        if redis_client:
            self.client = redis_client
            self._sentinel = None
        else:
            self.client, self._sentinel = self._create_client()

    def _create_client(self):
        """创建 Redis 客户端 - 支持 Sentinel 模式"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory cache fallback")
            return None, None

        config = get_config()
        redis_config = config.redis

        if not redis_config.enabled:
            logger.info("Redis is disabled")
            return None, None

        try:
            # Sprint 14: Sentinel 模式
            if redis_config.sentinel_enabled:
                return self._create_sentinel_client(redis_config)
            else:
                return self._create_standalone_client(redis_config), None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using memory cache fallback")
            return None, None

    def _create_standalone_client(self, redis_config):
        """创建独立 Redis 客户端"""
        client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
            max_connections=redis_config.max_connections,
            socket_timeout=redis_config.socket_timeout,
            socket_connect_timeout=redis_config.socket_connect_timeout,
            decode_responses=False,  # 使用二进制模式支持 pickle
            retry_on_timeout=redis_config.retry_on_timeout,
        )
        # 测试连接
        client.ping()
        logger.info(f"Redis connected (standalone): {redis_config.host}:{redis_config.port}")
        return client

    def _create_sentinel_client(self, redis_config):
        """创建 Sentinel 模式 Redis 客户端"""
        sentinel_addresses = redis_config.sentinel_addresses

        # 创建 Sentinel 连接
        sentinel = Sentinel(
            sentinel_addresses,
            socket_timeout=redis_config.socket_timeout,
            password=redis_config.sentinel_password,
        )

        # 获取 Master 连接
        master = sentinel.master_for(
            redis_config.sentinel_master,
            socket_timeout=redis_config.socket_timeout,
            password=redis_config.password,
            db=redis_config.db,
            decode_responses=False,
            retry_on_timeout=redis_config.retry_on_timeout,
        )

        # 测试连接
        master.ping()
        logger.info(f"Redis connected (Sentinel mode): master={redis_config.sentinel_master}")
        return master, sentinel

    def get_replica(self):
        """获取只读副本连接 (用于读取负载均衡)"""
        if self._sentinel is None:
            return self.client

        config = get_config()
        redis_config = config.redis

        try:
            slave = self._sentinel.slave_for(
                redis_config.sentinel_master,
                socket_timeout=redis_config.socket_timeout,
                password=redis_config.password,
                db=redis_config.db,
                decode_responses=False,
            )
            return slave
        except Exception as e:
            logger.warning(f"Failed to get replica, using master: {e}")
            return self.client

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.client:
            return _get_memory_cache().get(key)

        try:
            data = self.client.get(self._make_key(key))
            if data:
                # 尝试 pickle 反序列化
                try:
                    return pickle.loads(data)
                except (pickle.PickleError, EOFError):
                    # 回退到 JSON
                    return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.client:
            return _get_memory_cache().set(key, value, ttl)

        try:
            serialized = pickle.dumps(value)
            if ttl:
                return self.client.setex(self._make_key(key), ttl, serialized)
            else:
                return self.client.set(self._make_key(key), serialized)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.client:
            return _get_memory_cache().delete(key)

        try:
            return self.client.delete(self._make_key(key)) > 0
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    def clear(self) -> bool:
        """清空所有缓存"""
        if not self.client:
            return _get_memory_cache().clear()

        try:
            # 只清除带前缀的键
            config = get_config()
            pattern = f"{config.service.bisheng_api_url}:*"
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys) > 0
            return True
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            return _get_memory_cache().exists(key)

        try:
            return self.client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.warning(f"Redis exists error: {e}")
            return False

    def _make_key(self, key: str) -> str:
        """生成带命名空间的键"""
        return f"bisheng:{key}"

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self.client:
            return _get_memory_cache().delete_pattern(pattern)

        try:
            full_pattern = f"bisheng:{pattern}"
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis delete_pattern error: {e}")
            return 0


# 内存缓存回退实例
_memory_cache: Optional[MemoryCache] = None


def _get_memory_cache() -> MemoryCache:
    """获取内存缓存实例"""
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = MemoryCache()
    return _memory_cache


# 全局缓存实例
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    key_builder: Optional[Callable[..., str]] = None,
    cache_condition: Optional[Callable[..., bool]] = None
):
    """
    缓存装饰器

    Args:
        ttl: 缓存时间（秒）
        key_prefix: 缓存键前缀
        key_builder: 自定义键生成函数
        cache_condition: 缓存条件函数，返回 True 才缓存

    Usage:
        @cached(ttl=300, key_prefix="metadata")
        def get_metadata(id):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 检查缓存条件
            if cache_condition and not cache_condition(*args, **kwargs):
                return func(*args, **kwargs)

            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认键生成策略
                parts = [key_prefix, func.__name__]
                if args:
                    parts.extend(str(a) for a in args)
                if kwargs:
                    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(parts)

            # 尝试从缓存获取
            cache = get_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 执行函数并缓存结果
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            # 只缓存非 None 结果
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # 添加缓存清除方法
        def clear_cache(*args, **kwargs):
            """清除此函数的缓存"""
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                parts = [key_prefix, func.__name__]
                if args:
                    parts.extend(str(a) for a in args)
                if kwargs:
                    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(parts)

            cache = get_cache()
            cache.delete(cache_key)

        wrapper.clear_cache = clear_cache
        wrapper.cache_key_prefix = key_prefix or func.__name__

        return wrapper

    return decorator


def clear_cache_pattern(pattern: str) -> int:
    """清除匹配模式的所有缓存"""
    cache = get_cache()
    return cache.delete_pattern(pattern)


# 预定义的缓存装饰器
cached_metadata = cached(ttl=300, key_prefix="metadata")
cached_model_list = cached(ttl=600, key_prefix="models")
cached_workflow = cached(ttl=180, key_prefix="workflow")
cached_search_result = cached(ttl=60, key_prefix="search")
