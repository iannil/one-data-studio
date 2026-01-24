"""
实用工具节点
Sprint 18: 工作流节点扩展

包含:
- CacheNode: 缓存中间结果
- RetryNode: 失败重试
"""

import logging
import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# CacheNode - 缓存节点
# =============================================================================

@dataclass
class CacheNodeConfig:
    """缓存节点配置"""
    cache_key: str = ""  # 缓存键（支持模板）
    ttl: int = 300  # 缓存过期时间（秒）
    cache_type: str = "memory"  # 缓存类型 (memory, redis)
    namespace: str = "workflow"  # 缓存命名空间
    skip_if_exists: bool = True  # 如果存在则跳过执行


# 内存缓存
_memory_cache: Dict[str, Dict[str, Any]] = {}


class CacheNode:
    """
    缓存节点
    Sprint 18: 工作流节点扩展

    支持:
    - 缓存中间结果
    - TTL 过期控制
    - 内存/Redis 缓存
    - 条件跳过执行
    """

    node_type = "cache"
    name = "CacheNode"
    description = "缓存中间计算结果"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = CacheNodeConfig(
            cache_key=config.get("cache_key", ""),
            ttl=config.get("ttl", 300),
            cache_type=config.get("cache_type", "memory"),
            namespace=config.get("namespace", "workflow"),
            skip_if_exists=config.get("skip_if_exists", True),
        ) if config else CacheNodeConfig()

    def _get_cache_key(self, input_data: Dict[str, Any]) -> str:
        """生成缓存键"""
        if self.config.cache_key:
            # 支持模板变量
            key = self.config.cache_key
            for k, v in input_data.items():
                key = key.replace(f"${{{k}}}", str(v))
            return f"{self.config.namespace}:{key}"
        else:
            # 基于输入数据生成哈希键
            data_hash = hashlib.md5(
                json.dumps(input_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            return f"{self.config.namespace}:{data_hash}"

    async def get_cached(self, cache_key: str) -> Optional[Any]:
        """获取缓存"""
        if self.config.cache_type == "memory":
            if cache_key in _memory_cache:
                cached = _memory_cache[cache_key]
                if cached["expires_at"] > datetime.now():
                    return cached["value"]
                else:
                    del _memory_cache[cache_key]
            return None
        elif self.config.cache_type == "redis":
            try:
                from shared.cache import get_cache
                cache = get_cache()
                return cache.get(cache_key)
            except ImportError:
                logger.warning("Redis cache not available, using memory cache")
                return None
        return None

    async def set_cached(self, cache_key: str, value: Any):
        """设置缓存"""
        if self.config.cache_type == "memory":
            _memory_cache[cache_key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=self.config.ttl)
            }
        elif self.config.cache_type == "redis":
            try:
                from shared.cache import get_cache
                cache = get_cache()
                cache.set(cache_key, value, ttl=self.config.ttl)
            except ImportError:
                logger.warning("Redis cache not available, using memory cache")
                _memory_cache[cache_key] = {
                    "value": value,
                    "expires_at": datetime.now() + timedelta(seconds=self.config.ttl)
                }

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        inner_func: Callable = None
    ) -> Dict[str, Any]:
        """
        执行缓存节点

        Args:
            input_data: 输入数据
            context: 执行上下文
            inner_func: 被缓存的内部函数

        Returns:
            执行结果
        """
        cache_key = self._get_cache_key(input_data)

        # 检查缓存
        if self.config.skip_if_exists:
            cached_value = await self.get_cached(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return {
                    "success": True,
                    "from_cache": True,
                    "cache_key": cache_key,
                    "output": cached_value
                }

        # 执行内部函数
        if inner_func:
            try:
                if asyncio.iscoroutinefunction(inner_func):
                    result = await inner_func(input_data, context)
                else:
                    result = inner_func(input_data, context)

                # 缓存结果
                await self.set_cached(cache_key, result)

                return {
                    "success": True,
                    "from_cache": False,
                    "cache_key": cache_key,
                    "output": result
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        else:
            # 仅存储输入数据
            await self.set_cached(cache_key, input_data)
            return {
                "success": True,
                "from_cache": False,
                "cache_key": cache_key,
                "output": input_data
            }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": {
                "cache_key": {"type": "string"},
                "ttl": {"type": "integer", "default": 300},
                "cache_type": {"type": "string", "enum": ["memory", "redis"]},
                "skip_if_exists": {"type": "boolean", "default": True},
            },
            "outputs": {
                "success": {"type": "boolean"},
                "from_cache": {"type": "boolean"},
                "output": {"type": "object"},
            }
        }


# =============================================================================
# RetryNode - 重试节点
# =============================================================================

@dataclass
class RetryNodeConfig:
    """重试节点配置"""
    max_retries: int = 3
    initial_delay: float = 1.0  # 初始延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加随机抖动
    retry_on_exceptions: List[str] = None  # 触发重试的异常类型


class RetryNode:
    """
    重试节点
    Sprint 18: 工作流节点扩展

    支持:
    - 失败自动重试
    - 指数退避
    - 最大重试次数
    - 特定异常类型重试
    """

    node_type = "retry"
    name = "RetryNode"
    description = "失败自动重试"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = RetryNodeConfig(
            max_retries=config.get("max_retries", 3),
            initial_delay=config.get("initial_delay", 1.0),
            max_delay=config.get("max_delay", 60.0),
            exponential_base=config.get("exponential_base", 2.0),
            jitter=config.get("jitter", True),
            retry_on_exceptions=config.get("retry_on_exceptions"),
        ) if config else RetryNodeConfig()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        inner_func: Callable = None
    ) -> Dict[str, Any]:
        """
        执行重试节点

        Args:
            input_data: 输入数据
            context: 执行上下文
            inner_func: 被重试的内部函数

        Returns:
            执行结果
        """
        if not inner_func:
            return {
                "success": False,
                "error": "No inner function to retry"
            }

        last_error = None
        attempts = []

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Retry attempt {attempt + 1}/{self.config.max_retries + 1}")

                if asyncio.iscoroutinefunction(inner_func):
                    result = await inner_func(input_data, context)
                else:
                    result = inner_func(input_data, context)

                return {
                    "success": True,
                    "attempt": attempt + 1,
                    "total_attempts": attempt + 1,
                    "output": result
                }

            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                attempts.append({
                    "attempt": attempt + 1,
                    "error": str(e),
                    "error_type": error_type
                })

                # 检查是否应该重试
                if self.config.retry_on_exceptions:
                    if error_type not in self.config.retry_on_exceptions:
                        logger.debug(f"Error type {error_type} not in retry list, stopping")
                        break

                if attempt < self.config.max_retries:
                    # 计算延迟
                    delay = min(
                        self.config.initial_delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )

                    # 添加抖动
                    if self.config.jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    logger.debug(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

        return {
            "success": False,
            "total_attempts": len(attempts),
            "attempts": attempts,
            "error": str(last_error) if last_error else "Unknown error"
        }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": {
                "max_retries": {"type": "integer", "default": 3},
                "initial_delay": {"type": "number", "default": 1.0},
                "max_delay": {"type": "number", "default": 60.0},
                "exponential_base": {"type": "number", "default": 2.0},
                "jitter": {"type": "boolean", "default": True},
            },
            "outputs": {
                "success": {"type": "boolean"},
                "attempt": {"type": "integer"},
                "output": {"type": "object"},
            }
        }
