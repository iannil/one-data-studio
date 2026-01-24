"""
ONE-DATA-STUDIO Circuit Breaker Implementation
Sprint 11.1: 服务网格与流量管理 - 熔断器实现
Sprint 14: 连接重试逻辑增强
Sprint 31: Prometheus 指标导出

提供应用层熔断器实现，与 Istio 熔断器配合使用。
"""

import time
import threading
from enum import Enum
from typing import Callable, Optional, Any, Dict, List, Type, Tuple
from functools import wraps
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Gauge, Histogram, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Gauge = None
    Histogram = None
    REGISTRY = None

# Initialize Prometheus metrics
_metrics_initialized = False
_circuit_breaker_state = None
_circuit_breaker_calls_total = None
_circuit_breaker_failures_total = None
_circuit_breaker_rejected_total = None
_circuit_breaker_failure_rate = None
_circuit_breaker_call_duration = None


def _init_prometheus_metrics():
    """Initialize Prometheus metrics (lazy initialization)"""
    global _metrics_initialized, _circuit_breaker_state, _circuit_breaker_calls_total
    global _circuit_breaker_failures_total, _circuit_breaker_rejected_total
    global _circuit_breaker_failure_rate, _circuit_breaker_call_duration

    if _metrics_initialized or not PROMETHEUS_AVAILABLE:
        return

    try:
        _circuit_breaker_state = Gauge(
            'circuit_breaker_state',
            'Current state of circuit breaker (0=closed, 1=open, 2=half_open)',
            ['name']
        )

        _circuit_breaker_calls_total = Counter(
            'circuit_breaker_calls_total',
            'Total number of calls through circuit breaker',
            ['name', 'result']
        )

        _circuit_breaker_failures_total = Counter(
            'circuit_breaker_failures_total',
            'Total number of failed calls',
            ['name']
        )

        _circuit_breaker_rejected_total = Counter(
            'circuit_breaker_rejected_total',
            'Total number of rejected calls (circuit open)',
            ['name']
        )

        _circuit_breaker_failure_rate = Gauge(
            'circuit_breaker_failure_rate',
            'Current failure rate of circuit breaker',
            ['name']
        )

        _circuit_breaker_call_duration = Histogram(
            'circuit_breaker_call_duration_seconds',
            'Duration of calls through circuit breaker',
            ['name'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
        )

        _metrics_initialized = True
        logger.info("Circuit breaker Prometheus metrics initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Prometheus metrics: {e}")


class CircuitState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"       # 关闭状态：正常工作
    OPEN = "open"           # 开启状态：熔断中，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态：尝试恢复


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5         # 失败阈值
    success_threshold: int = 2         # 半开状态成功阈值
    timeout: float = 60.0              # 熔断超时时间（秒）
    window_size: int = 100             # 滑动窗口大小
    min_calls: int = 10                # 最小调用次数
    slow_call_duration: float = 5.0    # 慢调用阈值（秒）
    slow_call_threshold: float = 0.5   # 慢调用比例阈值


@dataclass
class CallResult:
    """调用结果"""
    success: bool
    duration: float
    timestamp: float = field(default_factory=time.time)
    error: Optional[Exception] = None


class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """熔断器开启异常：服务被熔断"""
    pass


class CircuitBreaker:
    """
    熔断器实现

    基于状态机的熔断器：
    - CLOSED (关闭): 正常状态，请求正常通过
    - OPEN (开启): 熔断状态，直接拒绝请求
    - HALF_OPEN (半开): 尝试恢复状态，允许少量请求通过

    状态转换:
    - CLOSED -> OPEN: 失败率超过阈值
    - OPEN -> HALF_OPEN: 超时时间到
    - HALF_OPEN -> OPEN: 恢复尝试失败
    - HALF_OPEN -> CLOSED: 恢复尝试成功
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback

        # 状态
        self._state = CircuitState.CLOSED
        self._state_lock = threading.RLock()

        # 滑动窗口
        self._calls: List[CallResult] = []
        self._calls_lock = threading.RLock()

        # 熔断时间
        self._opened_at: Optional[float] = None

        # 统计
        self._total_calls = 0
        self._failed_calls = 0
        self._rejected_calls = 0

        # Initialize Prometheus metrics
        _init_prometheus_metrics()
        self._record_state_metric()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._state_lock:
            return self._state

    @property
    def is_open(self) -> bool:
        """是否处于开启状态"""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """是否处于关闭状态"""
        return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """是否处于半开状态"""
        return self.state == CircuitState.HALF_OPEN

    def _should_attempt_reset(self) -> bool:
        """是否尝试重置（从 OPEN 到 HALF_OPEN）"""
        if self._opened_at is None:
            return False
        return time.time() - self._opened_at >= self.config.timeout

    def _record_state_metric(self):
        """Record current state to Prometheus metric"""
        if _circuit_breaker_state is not None:
            # State values: closed=0, open=1, half_open=2
            state_value = {
                CircuitState.CLOSED: 0,
                CircuitState.OPEN: 1,
                CircuitState.HALF_OPEN: 2,
            }.get(self._state, 0)
            _circuit_breaker_state.labels(name=self.name).set(state_value)

    def _record_call(self, success: bool, duration: float, error: Optional[Exception] = None):
        """记录调用结果"""
        with self._calls_lock:
            self._calls.append(CallResult(success, duration, error=error))
            # 保持滑动窗口
            if len(self._calls) > self.config.window_size:
                self._calls.pop(0)

            self._total_calls += 1
            if not success:
                self._failed_calls += 1

        # Record Prometheus metrics
        if _circuit_breaker_calls_total is not None:
            result = "success" if success else "failure"
            _circuit_breaker_calls_total.labels(name=self.name, result=result).inc()

        if not success and _circuit_breaker_failures_total is not None:
            _circuit_breaker_failures_total.labels(name=self.name).inc()

        if _circuit_breaker_call_duration is not None:
            _circuit_breaker_call_duration.labels(name=self.name).observe(duration)

        # Update failure rate
        if _circuit_breaker_failure_rate is not None:
            failure_rate = self._get_failure_rate()
            _circuit_breaker_failure_rate.labels(name=self.name).set(failure_rate)

    def _get_failure_rate(self) -> float:
        """获取失败率"""
        with self._calls_lock:
            if len(self._calls) < self.config.min_calls:
                return 0.0
            failed = sum(1 for c in self._calls if not c.success)
            return failed / len(self._calls)

    def _get_slow_call_rate(self) -> float:
        """获取慢调用率"""
        with self._calls_lock:
            if len(self._calls) < self.config.min_calls:
                return 0.0
            slow = sum(1 for c in self._calls if c.duration > self.config.slow_call_duration)
            return slow / len(self._calls)

    def _should_trip(self) -> bool:
        """判断是否应该触发熔断"""
        failure_rate = self._get_failure_rate()
        slow_rate = self._get_slow_call_rate()

        # 失败率过高
        if failure_rate >= (1.0 / self.config.failure_threshold):
            return True

        # 慢调用比例过高
        if slow_rate >= self.config.slow_call_threshold:
            return True

        return False

    def _transition_to(self, new_state: CircuitState):
        """状态转换"""
        old_state = self._state
        self._state = new_state

        # Record state change to Prometheus
        self._record_state_metric()

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            logger.warning(f"CircuitBreaker '{self.name}' opened: {old_state} -> {new_state}")
        elif new_state == CircuitState.CLOSED:
            self._opened_at = None
            with self._calls_lock:
                self._calls.clear()
            logger.info(f"CircuitBreaker '{self.name}' closed: {old_state} -> {new_state}")
        elif new_state == CircuitState.HALF_OPEN:
            logger.info(f"CircuitBreaker '{self.name}' half-open: {old_state} -> {new_state}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行受保护的函数调用

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器开启时拒绝请求
            Exception: 原函数的异常
        """
        start_time = time.time()

        with self._state_lock:
            # 检查是否需要从 OPEN 转到 HALF_OPEN
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)

            # 拒绝请求
            if self._state == CircuitState.OPEN:
                self._rejected_calls += 1
                # Record rejection to Prometheus
                if _circuit_breaker_rejected_total is not None:
                    _circuit_breaker_rejected_total.labels(name=self.name).inc()
                raise CircuitBreakerOpenError(
                    f"CircuitBreaker '{self.name}' is open. Requests are rejected."
                )

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            with self._state_lock:
                self._record_call(True, duration)

                # HALF_OPEN 状态下成功则转到 CLOSED
                if self._state == CircuitState.HALF_OPEN:
                    recent_success = sum(
                        1 for c in self._calls[-self.config.success_threshold:]
                        if c.success
                    )
                    if recent_success >= self.config.success_threshold:
                        self._transition_to(CircuitState.CLOSED)

            return result

        except Exception as e:
            duration = time.time() - start_time

            with self._state_lock:
                self._record_call(False, duration, error=e)

                # 检查是否需要熔断
                if self._state == CircuitState.CLOSED and self._should_trip():
                    self._transition_to(CircuitState.OPEN)
                elif self._state == CircuitState.HALF_OPEN:
                    # HALF_OPEN 失败立即回到 OPEN
                    self._transition_to(CircuitState.OPEN)

            # 执行降级逻辑
            if self.fallback:
                try:
                    return self.fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback failed for '{self.name}': {fallback_error}"
                    )

            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._calls_lock:
            recent_calls = len(self._calls)
            if recent_calls > 0:
                failed = sum(1 for c in self._calls if not c.success)
                failure_rate = failed / recent_calls
                avg_duration = sum(c.duration for c in self._calls) / recent_calls
            else:
                failure_rate = 0.0
                avg_duration = 0.0

        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._total_calls,
            "failed_calls": self._failed_calls,
            "rejected_calls": self._rejected_calls,
            "recent_calls": recent_calls,
            "failure_rate": failure_rate,
            "avg_duration": avg_duration,
            "opened_at": self._opened_at,
        }

    def reset(self):
        """重置熔断器"""
        with self._state_lock:
            self._state = CircuitState.CLOSED
            self._opened_at = None
            # Record state change to Prometheus
            self._record_state_metric()
        with self._calls_lock:
            self._calls.clear()
        self._total_calls = 0
        self._failed_calls = 0
        self._rejected_calls = 0
        # Reset failure rate metric
        if _circuit_breaker_failure_rate is not None:
            _circuit_breaker_failure_rate.labels(name=self.name).set(0.0)
        logger.info(f"CircuitBreaker '{self.name}' reset")


class CircuitBreakerRegistry:
    """熔断器注册表"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
        return cls._instance

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config, fallback)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器的统计信息"""
        return {name: cb.get_stats() for name, cb in self._breakers.items()}


def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """
    熔断器装饰器

    Usage:
        @circuit_breaker("my-service")
        def call_external_service():
            return requests.get("http://example.com")

        @circuit_breaker(
            name="api-call",
            config=CircuitBreakerConfig(failure_threshold=3, timeout=30),
            fallback=lambda: {"error": "service unavailable"}
        )
        def api_function():
            return backend_api.call()
    """
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        registry = CircuitBreakerRegistry()

        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = registry.get_or_create(breaker_name, config, fallback)
            return breaker.call(func, *args, **kwargs)

        # 添加获取熔断器状态的方法
        wrapper.get_circuit_breaker = lambda: registry.get(breaker_name)

        return wrapper

    return decorator


class ServiceDegradation:
    """
    服务降级策略

    在高负载或故障时返回简化/缓存的结果
    """

    # 降级级别
    LEVEL_NORMAL = 0    # 正常
    LEVEL_DEGRADE_1 = 1  # 轻度降级
    LEVEL_DEGRADE_2 = 2  # 中度降级
    LEVEL_DEGRADE_3 = 3  # 重度降级

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._current_level = self.LEVEL_NORMAL
        self._level_lock = threading.RLock()

        # 降级触发条件
        self._cpu_threshold = 0.8
        self._memory_threshold = 0.85
        self._response_time_threshold = 2.0  # 秒

    def get_level(self) -> int:
        """获取当前降级级别"""
        return self._current_level

    def set_level(self, level: int):
        """设置降级级别"""
        with self._level_lock:
            old_level = self._current_level
            self._current_level = level
            if old_level != level:
                logger.info(
                    f"Service '{self.service_name}' degradation level: "
                    f"{old_level} -> {level}"
                )

    def should_degrade(self, cpu_usage: float, memory_usage: float, avg_response_time: float) -> bool:
        """
        判断是否应该降级

        Args:
            cpu_usage: CPU 使用率 (0-1)
            memory_usage: 内存使用率 (0-1)
            avg_response_time: 平均响应时间（秒）
        """
        if cpu_usage > self._cpu_threshold or memory_usage > self._memory_threshold:
            self.set_level(self.LEVEL_DEGRADE_1)
            return True

        if avg_response_time > self._response_time_threshold:
            self.set_level(self.LEVEL_DEGRADE_2)
            return True

        self.set_level(self.LEVEL_NORMAL)
        return False

    def execute_with_degradation(
        self,
        normal_func: Callable,
        degrade_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        根据降级级别执行相应函数

        Args:
            normal_func: 正常函数
            degrade_func: 降级函数
            *args: 参数
            **kwargs: 关键字参数
        """
        if self._current_level > self.LEVEL_NORMAL:
            logger.debug(
                f"Service '{self.service_name}' executing degraded "
                f"function at level {self._current_level}"
            )
            return degrade_func(*args, **kwargs)
        return normal_func(*args, **kwargs)


# 预定义的熔断器配置
DEFAULT_CONFIGS = {
    "database": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=30.0,
        window_size=50,
        slow_call_duration=2.0,
    ),
    "http": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0,
        window_size=100,
        slow_call_duration=5.0,
    ),
    "llm": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=120.0,
        window_size=50,
        slow_call_duration=30.0,
    ),
    "vector_store": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=45.0,
        window_size=80,
        slow_call_duration=3.0,
    ),
}


def get_circuit_breaker(
    name: str,
    config_type: str = "http",
    fallback: Optional[Callable] = None
) -> CircuitBreaker:
    """
    获取预配置的熔断器

    Args:
        name: 熔断器名称
        config_type: 配置类型 (database, http, llm, vector_store)
        fallback: 降级函数
    """
    config = DEFAULT_CONFIGS.get(config_type, CircuitBreakerConfig())
    registry = CircuitBreakerRegistry()
    return registry.get_or_create(name, config, fallback)


# Sprint 14: 连接重试逻辑
@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (ConnectionError, TimeoutError, OSError)
    )


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    带指数退避的重试装饰器

    Sprint 14: 用于数据库和 Redis 连接重试

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试时的回调函数

    Usage:
        @retry_with_backoff(max_retries=3, retryable_exceptions=(ConnectionError,))
        def connect_to_database():
            return create_connection()
    """
    if retryable_exceptions is None:
        retryable_exceptions = (ConnectionError, TimeoutError, OSError)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # 计算延迟
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # 添加抖动
                    if jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # 回调
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")

                    time.sleep(delay)

            # 不应该到达这里
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class ConnectionPool:
    """
    连接池管理器

    Sprint 14: 支持连接健康检查和自动重连
    """

    def __init__(
        self,
        factory: Callable[[], Any],
        max_size: int = 10,
        health_check: Optional[Callable[[Any], bool]] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        初始化连接池

        Args:
            factory: 创建连接的工厂函数
            max_size: 最大连接数
            health_check: 健康检查函数
            retry_config: 重试配置
        """
        self.factory = factory
        self.max_size = max_size
        self.health_check = health_check or (lambda _: True)
        self.retry_config = retry_config or RetryConfig()

        self._pool: List[Any] = []
        self._in_use: Dict[int, Any] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def get(self, timeout: Optional[float] = None) -> Any:
        """
        获取连接

        Args:
            timeout: 等待超时时间

        Returns:
            连接对象
        """
        start_time = time.time()

        with self._condition:
            while True:
                # 尝试从池中获取
                while self._pool:
                    conn = self._pool.pop()
                    if self._is_healthy(conn):
                        self._in_use[id(conn)] = conn
                        return conn
                    else:
                        logger.debug("Discarding unhealthy connection")
                        self._close_connection(conn)

                # 如果可以创建新连接
                if len(self._in_use) < self.max_size:
                    conn = self._create_connection()
                    if conn:
                        self._in_use[id(conn)] = conn
                        return conn

                # 等待连接归还
                if timeout is not None:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        raise TimeoutError("Connection pool exhausted")
                    if not self._condition.wait(timeout=remaining):
                        raise TimeoutError("Connection pool exhausted")
                else:
                    self._condition.wait()

    def put(self, conn: Any):
        """归还连接"""
        with self._condition:
            conn_id = id(conn)
            if conn_id in self._in_use:
                del self._in_use[conn_id]
                if self._is_healthy(conn):
                    self._pool.append(conn)
                else:
                    self._close_connection(conn)
                self._condition.notify()

    def _create_connection(self) -> Optional[Any]:
        """创建新连接（带重试）"""
        config = self.retry_config

        for attempt in range(config.max_retries + 1):
            try:
                return self.factory()
            except config.retryable_exceptions as e:
                if attempt == config.max_retries:
                    logger.error(f"Failed to create connection after {config.max_retries + 1} attempts")
                    return None

                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                if config.jitter:
                    import random
                    delay = delay * (0.5 + random.random())

                logger.warning(f"Connection creation failed (attempt {attempt + 1}): {e}. Retrying...")
                time.sleep(delay)

        return None

    def _is_healthy(self, conn: Any) -> bool:
        """检查连接健康状态"""
        try:
            return self.health_check(conn)
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def _close_connection(self, conn: Any):
        """关闭连接"""
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._pool:
                self._close_connection(conn)
            for conn in self._in_use.values():
                self._close_connection(conn)
            self._pool.clear()
            self._in_use.clear()

    def stats(self) -> Dict[str, int]:
        """获取连接池统计"""
        with self._lock:
            return {
                "available": len(self._pool),
                "in_use": len(self._in_use),
                "max_size": self.max_size,
            }


def create_database_connection_pool(
    create_engine_func: Callable,
    pool_size: int = 10,
    retry_config: Optional[RetryConfig] = None
) -> ConnectionPool:
    """
    创建数据库连接池

    Args:
        create_engine_func: 创建数据库引擎的函数
        pool_size: 连接池大小
        retry_config: 重试配置
    """
    if retry_config is None:
        retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )

    def health_check(conn):
        try:
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    return ConnectionPool(
        factory=create_engine_func,
        max_size=pool_size,
        health_check=health_check,
        retry_config=retry_config,
    )
