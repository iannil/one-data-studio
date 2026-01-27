"""
缓存服务
支持Redis和内存缓存，用于提高OCR服务性能
"""

import json
import logging
import pickle
from typing import Optional, Any, Union, List
from datetime import timedelta
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class CacheBackend:
    """缓存后端接口"""

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """删除缓存"""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        raise NotImplementedError

    def clear(self) -> bool:
        """清空缓存"""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000):
        self._cache: dict = {}
        self._ttl: dict = {}
        self._max_size = max_size
        self._access_count: dict = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        # 检查TTL
        if key in self._ttl:
            import time
            if time.time() > self._ttl[key]:
                del self._cache[key]
                del self._ttl[key]
                return None

        self._access_count[key] = self._access_count.get(key, 0) + 1
        return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # 检查容量
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        self._cache[key] = value
        self._access_count[key] = 0

        if ttl:
            import time
            self._ttl[key] = time.time() + ttl

        return True

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            if key in self._ttl:
                del self._ttl[key]
            if key in self._access_count:
                del self._access_count[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> bool:
        self._cache.clear()
        self._ttl.clear()
        self._access_count.clear()
        return True

    def _evict_lru(self):
        """淘汰最少使用的项"""
        if not self._access_count:
            return

        lru_key = min(self._access_count, key=self._access_count.get)
        del self._cache[lru_key]
        if lru_key in self._ttl:
            del self._ttl[lru_key]
        del self._access_count[lru_key]

    def size(self) -> int:
        """返回缓存大小"""
        return len(self._cache)


class RedisCache(CacheBackend):
    """Redis缓存实现"""

    def __init__(self, redis_client, key_prefix: str = "ocr:"):
        self._redis = redis_client
        self._prefix = key_prefix

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._redis.get(self._make_key(key))
            if value is None:
                return None

            # 尝试JSON解析
            try:
                return json.loads(value)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 尝试pickle解析
                try:
                    return pickle.loads(value)
                except:
                    return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                try:
                    serialized = json.dumps(value)
                except TypeError:
                    serialized = pickle.dumps(value)

            redis_key = self._make_key(key)

            if ttl:
                return self._redis.setex(redis_key, ttl, serialized)
            else:
                return self._redis.set(redis_key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return self._redis.delete(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            return self._redis.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    def clear(self) -> bool:
        """清空所有OCR相关的缓存"""
        try:
            keys = self._redis.keys(f"{self._prefix}*")
            if keys:
                return self._redis.delete(*keys) > 0
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


class CacheService:
    """缓存服务"""

    def __init__(self, backend: CacheBackend):
        self._backend = backend
        self._default_ttl = 3600  # 1小时

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if ttl is None:
            ttl = self._default_ttl
        return self._backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self._backend.delete(key)

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self._backend.exists(key)

    def clear(self) -> bool:
        """清空缓存"""
        return self._backend.clear()

    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存，如果不存在则通过工厂函数创建

        Args:
            key: 缓存键
            factory: 值工厂函数
            ttl: 过期时间（秒）

        Returns:
            缓存值
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value

    def set_default_ttl(self, ttl: int):
        """设置默认TTL"""
        self._default_ttl = ttl

    def cache_multi(self, items: dict, ttl: Optional[int] = None) -> dict:
        """批量设置缓存"""
        results = {}
        for key, value in items.items():
            results[key] = self.set(key, value, ttl)
        return results

    def get_multi(self, keys: List[str]) -> dict:
        """批量获取缓存"""
        results = {}
        for key in keys:
            results[key] = self.get(key)
        return results

    def delete_multi(self, keys: List[str]) -> dict:
        """批量删除缓存"""
        results = {}
        for key in keys:
            results[key] = self.delete(key)
        return results


# 缓存装饰器
def cached(
    key_prefix: str,
    ttl: int = 3600,
    key_builder: Optional[callable] = None
):
    """
    缓存装饰器

    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒）
        key_builder: 自定义键构建函数

    Example:
        @cached("template", ttl=600)
        def get_template(template_id: str):
            return db.query(template_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构建缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认键构建方式
                key_parts = [key_prefix]
                for arg in args:
                    if arg is not None:
                        key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    if v is not None:
                        key_parts.append(f"{k}:{v}")
                cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cache = get_cache()
            value = cache.get(cache_key)
            if value is not None:
                return value

            # 执行函数并缓存结果
            value = func(*args, **kwargs)
            cache.set(cache_key, value, ttl)
            return value

        return wrapper
    return decorator


def compute_hash_key(data: Any) -> str:
    """计算数据的哈希值作为缓存键"""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)
    return hashlib.md5(data_str.encode()).hexdigest()


# 全局缓存实例
_cache_service: Optional[CacheService] = None


def init_cache(redis_client=None, key_prefix: str = "ocr:"):
    """初始化缓存服务"""
    global _cache_service

    if redis_client:
        backend = RedisCache(redis_client, key_prefix)
        logger.info("Using Redis cache backend")
    else:
        backend = MemoryCache()
        logger.info("Using memory cache backend")

    _cache_service = CacheService(backend)
    return _cache_service


def get_cache() -> Optional[CacheService]:
    """获取缓存服务实例"""
    return _cache_service


# 便捷函数
def cache_get(key: str) -> Optional[Any]:
    """获取缓存"""
    cache = get_cache()
    return cache.get(key) if cache else None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存"""
    cache = get_cache()
    return cache.set(key, value, ttl) if cache else False


def cache_delete(key: str) -> bool:
    """删除缓存"""
    cache = get_cache()
    return cache.delete(key) if cache else False


# 预定义的缓存键
class CacheKeys:
    """预定义的缓存键"""

    @staticmethod
    def template(template_id: str) -> str:
        return f"template:{template_id}"

    @staticmethod
    def template_list(tenant_id: str) -> str:
        return f"templates:tenant:{tenant_id}"

    @staticmethod
    def task_result(task_id: str) -> str:
        return f"task:result:{task_id}"

    @staticmethod
    def document_hash(file_hash: str) -> str:
        return f"document:hash:{file_hash}"

    @staticmethod
    def ocr_result(file_hash: str, doc_type: str) -> str:
        return f"ocr:result:{doc_type}:{file_hash}"

    @staticmethod
    def document_type(content_hash: str) -> str:
        return f"document:type:{content_hash}"
