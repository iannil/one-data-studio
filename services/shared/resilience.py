"""
弹性与容错模块
Sprint 25: 生产就绪 - 可靠性增强

提供数据库连接重试、Redis 熔断器和外部服务调用的指数退避重试。

功能:
- 数据库连接重试（支持 tenacity）
- Redis 熔断器模式
- 外部服务调用的指数退避重试
- 统一的重试配置
"""

import os
import time
import logging
import functools
from typing import Callable, Optional, Any, TypeVar, Dict
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import random

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


# ============================================
# 配置类
# ============================================

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = field(default_factory=lambda: int(os.getenv('RETRY_MAX_RETRIES', '3')))
    base_delay: float = field(default_factory=lambda: float(os.getenv('RETRY_BASE_DELAY', '1.0')))
    max_delay: float = field(default_factory=lambda: float(os.getenv('RETRY_MAX_DELAY', '30.0')))
    exponential_base: float = field(default_factory=lambda: float(os.getenv('RETRY_EXPONENTIAL_BASE', '2.0')))
    jitter: bool = field(default_factory=lambda: os.getenv('RETRY_JITTER', 'true').lower() == 'true')

    def calculate_delay(self, attempt: int) -> float:
        """计算当前尝试的延迟时间（指数退避 + 可选抖动）"""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            # 添加 0-25% 的随机抖动
            delay = delay * (1 + random.uniform(0, 0.25))
        return delay


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = field(default_factory=lambda: int(os.getenv('CB_FAILURE_THRESHOLD', '5')))
    success_threshold: int = field(default_factory=lambda: int(os.getenv('CB_SUCCESS_THRESHOLD', '3')))
    timeout: float = field(default_factory=lambda: float(os.getenv('CB_TIMEOUT', '60.0')))
    half_open_max_calls: int = field(default_factory=lambda: int(os.getenv('CB_HALF_OPEN_MAX_CALLS', '3')))


# ============================================
# 熔断器
# ============================================

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，允许请求
    OPEN = "open"          # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许有限请求进行测试


class CircuitBreaker:
    """
    熔断器模式实现

    状态转换:
    - CLOSED -> OPEN: 连续失败次数达到阈值
    - OPEN -> HALF_OPEN: 超时时间到达
    - HALF_OPEN -> CLOSED: 连续成功次数达到阈值
    - HALF_OPEN -> OPEN: 任何失败

    Usage:
        redis_breaker = CircuitBreaker(name="redis", config=CircuitBreakerConfig())

        @redis_breaker
        def get_from_redis(key):
            return redis_client.get(key)
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态（检查是否需要转换）"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # 检查是否应该转换到半开状态
                if time.time() - self._last_failure_time >= self.config.timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    logger.info(f"CircuitBreaker[{self.name}]: OPEN -> HALF_OPEN")
            return self._state

    def _record_success(self):
        """记录成功"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"CircuitBreaker[{self.name}]: HALF_OPEN -> CLOSED")
            elif self._state == CircuitState.CLOSED:
                # 重置失败计数
                self._failure_count = 0

    def _record_failure(self, error: Exception):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下任何失败都转换到打开状态
                self._state = CircuitState.OPEN
                logger.warning(f"CircuitBreaker[{self.name}]: HALF_OPEN -> OPEN (failure: {error})")
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"CircuitBreaker[{self.name}]: CLOSED -> OPEN "
                        f"(failures: {self._failure_count})"
                    )

    def can_execute(self) -> bool:
        """检查是否允许执行"""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            with self._lock:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器用法"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.execute(func, *args, **kwargs)
        return wrapper

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """执行函数（带熔断保护）"""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"CircuitBreaker[{self.name}] is OPEN. Service unavailable."
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            }
        }


class CircuitBreakerOpenError(Exception):
    """熔断器打开时的异常"""
    pass


# ============================================
# 重试装饰器
# ============================================

def retry_with_backoff(
    config: RetryConfig = None,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[int, Exception, float], None] = None
):
    """
    带指数退避的重试装饰器

    Args:
        config: 重试配置
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数 (attempt, exception, delay)

    Usage:
        @retry_with_backoff()
        def call_external_service():
            ...

        # 自定义配置
        @retry_with_backoff(
            config=RetryConfig(max_retries=5, base_delay=2.0),
            exceptions=(ConnectionError, TimeoutError),
            on_retry=lambda a, e, d: logger.warning(f"Retry {a} after {d}s: {e}")
        )
        def call_api():
            ...
    """
    config = config or RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)

                        if on_retry:
                            on_retry(attempt + 1, e, delay)
                        else:
                            logger.warning(
                                f"Retry {attempt + 1}/{config.max_retries} for {func.__name__}: "
                                f"{type(e).__name__}: {e}. Waiting {delay:.2f}s"
                            )

                        time.sleep(delay)

            # 所有重试都失败
            logger.error(
                f"All {config.max_retries} retries failed for {func.__name__}: "
                f"{type(last_exception).__name__}: {last_exception}"
            )
            raise last_exception

        return wrapper
    return decorator


# ============================================
# 数据库连接重试
# ============================================

def get_db_session_with_retry(
    session_factory,
    retry_config: RetryConfig = None
):
    """
    获取数据库会话（带重试）

    Args:
        session_factory: SQLAlchemy SessionLocal 工厂
        retry_config: 重试配置

    Returns:
        数据库会话

    Usage:
        from models import SessionLocal
        session = get_db_session_with_retry(SessionLocal)
    """
    config = retry_config or RetryConfig(max_retries=3, base_delay=1.0)

    @retry_with_backoff(
        config=config,
        exceptions=(Exception,),  # 捕获所有数据库连接异常
        on_retry=lambda a, e, d: logger.warning(
            f"Database connection retry {a}: {e}. Waiting {d:.2f}s"
        )
    )
    def _get_session():
        session = session_factory()
        # 测试连接
        session.execute("SELECT 1")
        return session

    return _get_session()


# ============================================
# Redis 客户端（带熔断器）
# ============================================

# 全局 Redis 熔断器实例
_redis_circuit_breaker: Optional[CircuitBreaker] = None


def get_redis_circuit_breaker() -> CircuitBreaker:
    """获取 Redis 熔断器（单例）"""
    global _redis_circuit_breaker
    if _redis_circuit_breaker is None:
        _redis_circuit_breaker = CircuitBreaker(
            name="redis",
            config=CircuitBreakerConfig()
        )
    return _redis_circuit_breaker


def redis_with_circuit_breaker(
    func: Callable[..., T] = None,
    fallback: Callable[..., T] = None
) -> Callable[..., T]:
    """
    Redis 操作熔断器装饰器

    Args:
        func: 被装饰的函数
        fallback: 熔断时的回退函数

    Usage:
        @redis_with_circuit_breaker
        def get_cached_data(key):
            return redis_client.get(key)

        # 带回退
        @redis_with_circuit_breaker(fallback=lambda key: None)
        def get_cached_data(key):
            return redis_client.get(key)
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        breaker = get_redis_circuit_breaker()

        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> T:
            try:
                return breaker.execute(f, *args, **kwargs)
            except CircuitBreakerOpenError:
                if fallback:
                    logger.warning(
                        f"Redis circuit breaker open, using fallback for {f.__name__}"
                    )
                    return fallback(*args, **kwargs)
                raise

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


# ============================================
# 外部服务调用辅助
# ============================================

def call_external_service(
    url: str,
    method: str = "GET",
    timeout: float = 30.0,
    retry_config: RetryConfig = None,
    circuit_breaker: CircuitBreaker = None,
    **kwargs
) -> Any:
    """
    调用外部服务（带重试和熔断）

    Args:
        url: 服务 URL
        method: HTTP 方法
        timeout: 请求超时
        retry_config: 重试配置
        circuit_breaker: 熔断器实例
        **kwargs: 传递给 requests 的其他参数

    Returns:
        响应对象

    Usage:
        response = call_external_service(
            "http://api.example.com/data",
            method="POST",
            json={"key": "value"},
            timeout=10
        )
    """
    import requests

    config = retry_config or RetryConfig()

    @retry_with_backoff(
        config=config,
        exceptions=(requests.RequestException,)
    )
    def _make_request():
        response = requests.request(
            method=method,
            url=url,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        return response

    if circuit_breaker:
        return circuit_breaker.execute(_make_request)
    else:
        return _make_request()


# ============================================
# 健康检查辅助
# ============================================

def check_service_health(
    name: str,
    check_func: Callable[[], bool],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    检查服务健康状态

    Args:
        name: 服务名称
        check_func: 健康检查函数（返回 True/False）
        timeout: 超时时间

    Returns:
        健康状态字典
    """
    start_time = time.time()
    try:
        is_healthy = check_func()
        latency = (time.time() - start_time) * 1000
        return {
            "name": name,
            "status": "healthy" if is_healthy else "unhealthy",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return {
            "name": name,
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(latency, 2)
        }
