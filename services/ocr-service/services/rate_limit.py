"""
速率限制服务
防止API滥用，保护服务稳定性
"""

import time
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """速率限制错误"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after} seconds")


class LimitType(str, Enum):
    """限制类型"""
    REQUESTS_PER_SECOND = "rps"       # 每秒请求数
    REQUESTS_PER_MINUTE = "rpm"       # 每分钟请求数
    REQUESTS_PER_HOUR = "rph"         # 每小时请求数
    CONCURRENT_REQUESTS = "concurrent" # 并发请求数


@dataclass
class RateLimit:
    """速率限制配置"""
    requests: int          # 请求数量
    window: int            # 时间窗口（秒）
    limit_type: LimitType  # 限制类型

    @property
    def window_ms(self) -> int:
        return self.window * 1000


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self._limits: Dict[str, RateLimit] = {}
        self._counters: Dict[str, list] = defaultdict(list)
        self._concurrent: Dict[str, int] = defaultdict(int)
        self._last_cleanup = time.time()

    def add_limit(self, name: str, limit: RateLimit):
        """添加速率限制规则"""
        self._limits[name] = limit

    def check(self, key: str, limit_name: str = "default") -> bool:
        """
        检查是否超过限制

        Args:
            key: 限制键（通常是用户ID、IP地址等）
            limit_name: 限制规则名称

        Returns:
            True表示允许，False表示超过限制
        """
        limit = self._limits.get(limit_name)
        if not limit:
            return True

        if limit.limit_type == LimitType.CONCURRENT_REQUESTS:
            return self._check_concurrent(key, limit)
        else:
            return self._check_sliding_window(key, limit)

    def _check_sliding_window(self, key: str, limit: RateLimit) -> bool:
        """检查滑动窗口限制"""
        now = time.time()
        window_start = now - limit.window

        # 清理过期记录
        self._cleanup_if_needed()

        # 获取当前计数器
        counter_key = f"{key}:{limit.limit_type.value}"
        timestamps = self._counters[counter_key]

        # 移除窗口外的记录
        timestamps[:] = [ts for ts in timestamps if ts > window_start]

        # 检查是否超过限制
        if len(timestamps) >= limit.requests:
            logger.warning(f"Rate limit exceeded for {key}: {len(timestamps)}/{limit.requests}")
            return False

        # 添加当前请求
        timestamps.append(now)
        return True

    def _check_concurrent(self, key: str, limit: RateLimit) -> bool:
        """检查并发限制"""
        current = self._concurrent[key]

        if current >= limit.requests:
            logger.warning(f"Concurrent limit exceeded for {key}: {current}/{limit.requests}")
            return False

        self._concurrent[key] += 1
        return True

    def release_concurrent(self, key: str):
        """释放并发计数"""
        if self._concurrent[key] > 0:
            self._concurrent[key] -= 1

    def get_retry_after(self, key: str, limit_name: str = "default") -> int:
        """获取重试等待时间"""
        limit = self._limits.get(limit_name)
        if not limit:
            return 0

        counter_key = f"{key}:{limit.limit_type.value}"
        timestamps = self._counters.get(counter_key, [])

        if not timestamps:
            return 0

        now = time.time()
        window_start = now - limit.window

        # 找到最早的请求
        oldest = min(ts for ts in timestamps if ts > window_start)
        return int(oldest + limit.window - now) + 1

    def reset(self, key: str):
        """重置计数器"""
        for limit_type in LimitType:
            counter_key = f"{key}:{limit_type.value}"
            if counter_key in self._counters:
                del self._counters[counter_key]

    def _cleanup_if_needed(self):
        """定期清理过期数据"""
        now = time.time()
        if now - self._last_cleanup > 60:  # 每分钟清理一次
            self._cleanup()
            self._last_cleanup = now

    def _cleanup(self):
        """清理过期数据"""
        now = time.time()

        for key, timestamps in list(self._counters.items()):
            # 获取对应的窗口时间
            limit_type = key.split(":")[-1]
            window = 60  # 默认窗口

            for limit in self._limits.values():
                if limit.limit_type.value == limit_type:
                    window = limit.window
                    break

            window_start = now - window
            timestamps[:] = [ts for ts in timestamps if ts > window_start]

            # 如果窗口为空，删除记录
            if not timestamps:
                del self._counters[key]

    def get_stats(self, key: str) -> Dict:
        """获取统计信息"""
        stats = {
            "key": key,
            "limits": {},
            "current": {}
        }

        for limit_name, limit in self._limits.items():
            counter_key = f"{key}:{limit.limit_type.value}"
            timestamps = self._counters.get(counter_key, [])

            now = time.time()
            window_start = now - limit.window
            in_window = len([ts for ts in timestamps if ts > window_start])

            stats["limits"][limit_name] = {
                "max": limit.requests,
                "window": limit.window
            }
            stats["current"][limit_name] = in_window

        # 并发统计
        stats["current"]["concurrent"] = self._concurrent.get(key, 0)

        return stats


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def init_rate_limiter() -> RateLimiter:
    """初始化速率限制器"""
    global _rate_limiter
    _rate_limiter = RateLimiter()

    # 添加默认限制规则
    _rate_limiter.add_limit("default", RateLimit(
        requests=10,
        window=1,
        limit_type=LimitType.REQUESTS_PER_SECOND
    ))

    _rate_limiter.add_limit("strict", RateLimit(
        requests=100,
        window=60,
        limit_type=LimitType.REQUESTS_PER_MINUTE
    ))

    _rate_limiter.add_limit("concurrent", RateLimit(
        requests=5,
        window=0,
        limit_type=LimitType.CONCURRENT_REQUESTS
    ))

    return _rate_limiter


def get_rate_limiter() -> Optional[RateLimiter]:
    """获取速率限制器实例"""
    return _rate_limiter


def check_rate_limit(
    key: str,
    limit_name: str = "default",
    raise_error: bool = False
) -> bool:
    """
    检查速率限制

    Args:
        key: 限制键
        limit_name: 限制规则名称
        raise_error: 是否在超过限制时抛出异常

    Returns:
        是否允许请求

    Raises:
        RateLimitError: 当超过限制且raise_error=True时
    """
    limiter = get_rate_limiter()
    if not limiter:
        return True

    allowed = limiter.check(key, limit_name)

    if not allowed and raise_error:
        retry_after = limiter.get_retry_after(key, limit_name)
        raise RateLimitError(retry_after)

    return allowed


def get_client_key(
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    ip_address: Optional[str] = None
) -> str:
    """
    生成客户端限制键

    优先级: user_id > api_key > ip_address

    Returns:
        限制键
    """
    if user_id:
        return f"user:{user_id}"
    elif api_key:
        # 对API key进行哈希以保护隐私
        return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    elif ip_address:
        return f"ip:{ip_address}"
    else:
        return "anonymous"


# FastAPI依赖
async def rate_limit_dependency(
    limit_name: str = "default",
    raise_error: bool = True
):
    """
    FastAPI速率限制依赖

    Usage:
        @router.get("/api/endpoint")
        async def endpoint(
            _: None = Depends(rate_limit_dependency("strict"))
        ):
            pass
    """
    from fastapi import Request, HTTPException

    async def _limit(request: Request):
        # 尝试从请求中获取标识
        user_id = getattr(request.state, "user_id", None)
        api_key = request.headers.get("X-API-Key")
        ip_address = request.client.host if request.client else None

        key = get_client_key(user_id, api_key, ip_address)

        if not check_rate_limit(key, limit_name, raise_error):
            limiter = get_rate_limiter()
            retry_after = limiter.get_retry_after(key, limit_name) if limiter else 60
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        return None

    return _limit


# 装饰器
def rate_limit(limit_name: str = "default"):
    """
    速率限制装饰器

    Usage:
        @rate_limit("strict")
        def my_function(user_id: str):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试从参数中获取user_id
            user_id = kwargs.get("user_id") or (
                args[0] if args and isinstance(args[0], str) else None
            )

            key = get_client_key(user_id=user_id) if user_id else "anonymous"

            if not check_rate_limit(key, limit_name, raise_error=True):
                return None

            return func(*args, **kwargs)
        return wrapper
    return decorator


# 清理函数
def release_concurrent(key: str):
    """释放并发限制（在使用并发限制后必须调用）"""
    limiter = get_rate_limiter()
    if limiter:
        limiter.release_concurrent(key)


# 上下文管理器
class RateLimitContext:
    """速率限制上下文管理器（用于并发限制）"""

    def __init__(self, key: str, limit_name: str = "concurrent"):
        self.key = key
        self.limit_name = limit_name
        self._allowed = False

    def __enter__(self):
        self._allowed = check_rate_limit(self.key, self.limit_name, raise_error=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._allowed:
            release_concurrent(self.key)
        return False


def concurrent_rate_limit(key: str, limit_name: str = "concurrent"):
    """
    并发速率限制上下文管理器

    Usage:
        with concurrent_rate_limit(f"task:{task_id}"):
            process_task()
    """
    return RateLimitContext(key, limit_name)
