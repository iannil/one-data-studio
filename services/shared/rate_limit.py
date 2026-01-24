"""
API 限流模块
Sprint 9: 安全加固
Sprint 30: 速率限制响应头

基于 Flask-Limiter 实现的 API 限流功能，包括：
- 标准速率限制响应头 (RFC 6585)
- 多种限流策略
- 限流状态检查
"""

import logging
import time
from typing import Optional, Callable, Dict, Any, Tuple
from functools import wraps
from dataclasses import dataclass

try:
    from flask import request, g, Response
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_LIMITER_AVAILABLE = True
except ImportError:
    FLASK_LIMITER_AVAILABLE = False
    Limiter = None
    get_remote_address = None
    Response = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from .config import get_config

logger = logging.getLogger(__name__)


# 限流配置类
class RateLimitConfig:
    """限流配置"""

    # 默认限制：每分钟 100 次
    DEFAULT_PER_MINUTE = "100/minute"

    # 严格限制：每分钟 10 次（敏感操作）
    STRICT_PER_MINUTE = "10/minute"

    # 宽松限制：每分钟 1000 次（只读操作）
    READ_ONLY_PER_MINUTE = "1000/minute"

    # 每小时限制
    DEFAULT_PER_HOUR = "1000/hour"
    STRICT_PER_HOUR = "100/hour"


def get_user_id() -> str:
    """
    获取用户标识用于限流

    优先级：
    1. 已登录用户的 user_id
    2. API Key
    3. IP 地址
    """
    if not FLASK_LIMITER_AVAILABLE:
        return "anonymous"

    # 尝试从 Flask g 对象获取用户信息
    try:
        from flask import g
        if hasattr(g, 'user_id'):
            return f"user:{g.user_id}"
        if hasattr(g, 'api_key'):
            return f"apikey:{g.api_key}"
    except ImportError:
        pass

    # 回退到 IP 地址
    return get_remote_address() if get_remote_address else "anonymous"


def get_rate_limit_key() -> str:
    """获取限流键（用户/IP）"""
    return get_user_id()


# 全局限流器实例
_limiter: Optional['Limiter'] = None


def get_limiter():
    """获取全局限流器实例"""
    global _limiter
    return _limiter


def init_rate_limit(app=None) -> Optional['Limiter']:
    """
    初始化限流器

    Args:
        app: Flask 应用实例

    Returns:
        Limiter 实例或 None
    """
    global _limiter

    if not FLASK_LIMITER_AVAILABLE:
        logger.warning("Flask-Limiter not available, rate limiting disabled")
        return None

    if _limiter is not None:
        return _limiter

    config = get_config()

    # 检查是否启用限流
    if not config.redis.enabled:
        logger.info("Rate limiting disabled (Redis not enabled)")
        return None

    try:
        _limiter = Limiter(
            app=app,
            key_func=get_rate_limit_key,
            default_limits=[RateLimitConfig.DEFAULT_PER_MINUTE],
            storage_uri=config.redis.url,
            strategy="fixed-window",  # 固定窗口策略
            on_breach=on_rate_limit_breach
        )
        logger.info("Rate limiting initialized")
        return _limiter
    except Exception as e:
        logger.warning(f"Failed to initialize rate limiter: {e}")
        return None


def on_rate_limit_breach(limit):
    """限流触发时的回调"""
    logger.warning(f"Rate limit breached: {limit.key} - {limit.limit}")


# 限流装饰器
def rate_limit(limit: str, key_func: Optional[Callable] = None, per_method: bool = False):
    """
    限流装饰器

    Args:
        limit: 限流规则，如 "100/minute", "1000/hour"
        key_func: 自定义键生成函数
        per_method: 是否按 HTTP 方法分别限流

    Usage:
        @rate_limit("10/minute")
        def sensitive_operation():
            ...

        @rate_limit("1000/minute", per_method=True)
        def api_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if _limiter is None:
                return func(*args, **kwargs)

            # 使用 Flask-Limiter 的装饰器
            limiter_decorator = _limiter.limit(
                limit,
                key_func=key_func or get_rate_limit_key,
                per_method=per_method,
                methods=None if not per_method else None
            )

            wrapped_func = limiter_decorator(func)
            return wrapped_func(*args, **kwargs)

        return wrapper

    return decorator


# 预定义的限流装饰器
def limit_strict(func):
    """严格限流：每分钟 10 次（敏感操作）"""
    return rate_limit(RateLimitConfig.STRICT_PER_MINUTE)(func)


def limit_read_only(func):
    """只读操作限流：每分钟 1000 次"""
    return rate_limit(RateLimitConfig.READ_ONLY_PER_MINUTE)(func)


def limit_default(func):
    """默认限流：每分钟 100 次"""
    return rate_limit(RateLimitConfig.DEFAULT_PER_MINUTE)(func)


def limit_hourly(func):
    """每小时限流：1000 次"""
    return rate_limit(RateLimitConfig.DEFAULT_PER_HOUR)(func)


# IP 级限流（用于防 DDoS）
def limit_ip(requests_per_minute: int = 60):
    """
    IP 级限流装饰器

    Args:
        requests_per_minute: 每分钟请求数

    Usage:
        @limit_ip(30)
        def login_endpoint():
            ...
    """
    return rate_limit(f"{requests_per_minute}/minute", key_func=get_remote_address)


# 自定义错误响应
def handle_rate_limit_error(e):
    """
    处理限流错误

    Args:
        e: 限流异常

    Returns:
        Flask 响应
    """
    if not FLASK_LIMITER_AVAILABLE:
        return None

    try:
        from flask import jsonify
        from werkzeug.exceptions import TooManyRequests

        if isinstance(e, TooManyRequests) or hasattr(e, 'description'):
            return jsonify({
                "code": 10005,
                "message": "Rate limit exceeded",
                "details": {
                    "retry_after": getattr(e, 'retry_after', 60)
                }
            }), 429
    except ImportError:
        pass

    return None


# 限流检查工具
class RateLimitChecker:
    """
    限流检查器

    Sprint 30: 实现速率限制状态查询和响应头生成

    用于手动检查限流状态和获取限流信息
    """

    # Redis 键前缀
    KEY_PREFIX = "ratelimit:"

    def __init__(self, redis_client=None):
        self.limiter = get_limiter()
        self._redis = redis_client
        self._init_redis()

    def _init_redis(self):
        """初始化 Redis 客户端"""
        if self._redis is None and REDIS_AVAILABLE:
            try:
                config = get_config()
                if config.redis.enabled:
                    self._redis = redis.Redis(
                        host=config.redis.host,
                        port=config.redis.port,
                        db=config.redis.db,
                        password=config.redis.password,
                        decode_responses=True
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize Redis for rate limit: {e}")
                self._redis = None

    def _parse_limit(self, limit_str: str) -> Tuple[int, int]:
        """
        解析限流规则字符串

        Args:
            limit_str: 限流规则，如 "100/minute", "1000/hour"

        Returns:
            (请求数, 窗口秒数)
        """
        parts = limit_str.split('/')
        if len(parts) != 2:
            return 0, 0

        count = int(parts[0])
        period = parts[1].lower()

        period_seconds = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }

        window = period_seconds.get(period, 60)
        return count, window

    def _get_redis_key(self, key: str, limit: str) -> str:
        """生成 Redis 键"""
        _, window = self._parse_limit(limit)
        # 计算当前窗口
        current_window = int(time.time() / window)
        return f"{self.KEY_PREFIX}{key}:{window}:{current_window}"

    def get_limit_info(self, key: str, limit: str) -> Dict[str, Any]:
        """
        获取限流信息

        Args:
            key: 限流键（用户ID或IP）
            limit: 限流规则

        Returns:
            {
                'limit': 总限制数,
                'remaining': 剩余请求数,
                'reset': 重置时间戳,
                'retry_after': 需要等待的秒数（仅在限流时）
            }
        """
        max_requests, window_seconds = self._parse_limit(limit)

        if max_requests == 0:
            return {
                'limit': -1,
                'remaining': -1,
                'reset': 0,
                'retry_after': None
            }

        # 计算重置时间
        current_time = int(time.time())
        current_window = current_time // window_seconds
        reset_time = (current_window + 1) * window_seconds

        # 获取当前使用量
        used = 0
        if self._redis:
            try:
                redis_key = self._get_redis_key(key, limit)
                used = int(self._redis.get(redis_key) or 0)
            except Exception as e:
                logger.debug(f"Failed to get rate limit from Redis: {e}")

        remaining = max(0, max_requests - used)
        retry_after = None if remaining > 0 else (reset_time - current_time)

        return {
            'limit': max_requests,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': retry_after
        }

    def is_allowed(self, key: str, limit: str) -> bool:
        """
        检查是否允许请求

        Args:
            key: 限流键
            limit: 限流规则

        Returns:
            是否允许请求
        """
        info = self.get_limit_info(key, limit)
        return info['remaining'] > 0

    def get_remaining(self, key: str, limit: str) -> int:
        """获取剩余请求数"""
        info = self.get_limit_info(key, limit)
        return info['remaining']

    def increment(self, key: str, limit: str) -> int:
        """
        增加使用计数

        Args:
            key: 限流键
            limit: 限流规则

        Returns:
            当前使用量
        """
        if not self._redis:
            return 0

        _, window_seconds = self._parse_limit(limit)
        redis_key = self._get_redis_key(key, limit)

        try:
            pipe = self._redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning(f"Failed to increment rate limit counter: {e}")
            return 0


@dataclass
class RateLimitHeaders:
    """速率限制响应头（RFC 6585 兼容）"""
    limit: int
    remaining: int
    reset: int
    retry_after: Optional[int] = None

    def to_dict(self) -> Dict[str, str]:
        """转换为响应头字典"""
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(self.reset),
        }
        if self.retry_after is not None:
            headers['Retry-After'] = str(self.retry_after)
        return headers

    def apply_to_response(self, response: 'Response') -> 'Response':
        """将响应头应用到 Flask Response"""
        for key, value in self.to_dict().items():
            response.headers[key] = value
        return response


def add_rate_limit_headers(limit: str = RateLimitConfig.DEFAULT_PER_MINUTE):
    """
    添加速率限制响应头的装饰器

    Sprint 30: 所有 API 返回标准速率限制头

    Args:
        limit: 限流规则

    Usage:
        @app.route("/api/v1/resource")
        @add_rate_limit_headers("100/minute")
        def get_resource():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取限流键
            key = get_rate_limit_key()

            # 获取限流信息
            checker = RateLimitChecker()
            info = checker.get_limit_info(key, limit)

            # 执行原函数
            result = func(*args, **kwargs)

            # 创建响应头
            headers = RateLimitHeaders(
                limit=info['limit'],
                remaining=info['remaining'],
                reset=info['reset'],
                retry_after=info.get('retry_after')
            )

            # 如果结果是元组 (response, status_code) 或 Response 对象
            if isinstance(result, tuple):
                response_data, status_code = result[0], result[1] if len(result) > 1 else 200
                from flask import jsonify, make_response
                if isinstance(response_data, dict):
                    response = make_response(jsonify(response_data), status_code)
                else:
                    response = make_response(response_data, status_code)
                headers.apply_to_response(response)
                return response
            elif hasattr(result, 'headers'):
                headers.apply_to_response(result)
                return result
            else:
                from flask import make_response, jsonify
                if isinstance(result, dict):
                    response = make_response(jsonify(result))
                else:
                    response = make_response(result)
                headers.apply_to_response(response)
                return response

        return wrapper
    return decorator


def rate_limit_middleware(app):
    """
    Flask 速率限制中间件

    Sprint 30: 自动为所有响应添加速率限制头

    Usage:
        app = Flask(__name__)
        rate_limit_middleware(app)
    """
    @app.after_request
    def add_rate_limit_headers_to_response(response):
        # 跳过静态文件和健康检查
        if request.path.startswith('/static') or request.path in ['/health', '/ready']:
            return response

        # 获取限流键
        key = get_rate_limit_key()

        # 获取默认限流规则
        limit = RateLimitConfig.DEFAULT_PER_MINUTE

        # 根据端点调整限流规则
        if request.path.startswith('/api/v1/admin'):
            limit = RateLimitConfig.STRICT_PER_MINUTE
        elif request.method == 'GET':
            limit = RateLimitConfig.READ_ONLY_PER_MINUTE

        # 获取限流信息
        checker = RateLimitChecker()
        info = checker.get_limit_info(key, limit)

        # 添加响应头
        response.headers['X-RateLimit-Limit'] = str(info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset'])

        if info.get('retry_after'):
            response.headers['Retry-After'] = str(info['retry_after'])

        return response

    return app
