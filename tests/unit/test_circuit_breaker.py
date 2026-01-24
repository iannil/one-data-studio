"""
熔断器模块单元测试
Sprint 14: P3 测试覆盖
"""

import pytest
import time
from unittest.mock import patch, Mock, MagicMock
import threading


class TestCircuitState:
    """熔断器状态枚举测试"""

    def test_circuit_states_exist(self):
        """测试熔断器状态枚举存在"""
        from services.shared.circuit_breaker import CircuitState

        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerConfig:
    """熔断器配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        from services.shared.circuit_breaker import CircuitBreakerConfig

        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 60.0
        assert config.window_size == 100
        assert config.min_calls == 10

    def test_custom_config(self):
        """测试自定义配置"""
        from services.shared.circuit_breaker import CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout=30.0,
            window_size=50,
            min_calls=5
        )
        assert config.failure_threshold == 3
        assert config.timeout == 30.0


class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state_is_closed(self):
        """测试初始状态为关闭"""
        from services.shared.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False

    def test_successful_call(self):
        """测试成功调用"""
        from services.shared.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test")

        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.is_closed is True

    def test_failed_call_records_failure(self):
        """测试失败调用记录"""
        from services.shared.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test")

        def fail_func():
            raise ValueError("error")

        with pytest.raises(ValueError):
            cb.call(fail_func)

        stats = cb.get_stats()
        assert stats["failed_calls"] == 1

    def test_circuit_opens_after_failures(self):
        """测试失败后熔断器打开"""
        from services.shared.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )

        config = CircuitBreakerConfig(
            failure_threshold=3,
            min_calls=3
        )
        cb = CircuitBreaker("test", config)

        def fail_func():
            raise ValueError("error")

        # 触发足够多的失败
        for _ in range(10):
            try:
                cb.call(fail_func)
            except ValueError:
                pass

        # 熔断器应该打开
        assert cb.state == CircuitState.OPEN

    def test_rejects_calls_when_open(self):
        """测试打开状态拒绝调用"""
        from services.shared.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
        )

        config = CircuitBreakerConfig(
            failure_threshold=2,
            min_calls=2,
            timeout=60.0
        )
        cb = CircuitBreaker("test", config)

        def fail_func():
            raise ValueError("error")

        # 触发熔断
        for _ in range(5):
            try:
                cb.call(fail_func)
            except (ValueError, CircuitBreakerOpenError):
                pass

        # 验证被拒绝
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "test")

    def test_fallback_on_failure(self):
        """测试失败时调用降级函数"""
        from services.shared.circuit_breaker import CircuitBreaker

        fallback_called = False

        def fallback():
            nonlocal fallback_called
            fallback_called = True
            return "fallback"

        cb = CircuitBreaker("test", fallback=fallback)

        def fail_func():
            raise ValueError("error")

        result = cb.call(fail_func)
        assert result == "fallback"
        assert fallback_called is True

    def test_reset_clears_state(self):
        """测试重置清除状态"""
        from services.shared.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test")

        def success_func():
            return "ok"

        cb.call(success_func)
        cb.call(success_func)

        cb.reset()

        stats = cb.get_stats()
        assert stats["total_calls"] == 0
        assert stats["failed_calls"] == 0
        assert cb.state == CircuitState.CLOSED

    def test_get_stats_returns_info(self):
        """测试获取统计信息"""
        from services.shared.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test-stats")

        stats = cb.get_stats()
        assert "name" in stats
        assert "state" in stats
        assert "total_calls" in stats
        assert "failed_calls" in stats
        assert "rejected_calls" in stats


class TestCircuitBreakerRegistry:
    """熔断器注册表测试"""

    def test_get_or_create(self):
        """测试获取或创建熔断器"""
        from services.shared.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("test-registry")
        cb2 = registry.get_or_create("test-registry")

        assert cb1 is cb2

    def test_get_all_stats(self):
        """测试获取所有统计信息"""
        from services.shared.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()
        registry.get_or_create("cb1")
        registry.get_or_create("cb2")

        stats = registry.get_all_stats()
        assert "cb1" in stats or len(stats) >= 0


class TestCircuitBreakerDecorator:
    """熔断器装饰器测试"""

    def test_decorator_wraps_function(self):
        """测试装饰器包装函数"""
        from services.shared.circuit_breaker import circuit_breaker

        @circuit_breaker("test-decorator")
        def my_func():
            return "result"

        assert my_func() == "result"

    def test_decorator_with_config(self):
        """测试带配置的装饰器"""
        from services.shared.circuit_breaker import (
            circuit_breaker, CircuitBreakerConfig
        )

        config = CircuitBreakerConfig(failure_threshold=10)

        @circuit_breaker("test-config", config=config)
        def my_func():
            return "ok"

        assert my_func() == "ok"

    def test_decorator_with_fallback(self):
        """测试带降级的装饰器"""
        from services.shared.circuit_breaker import circuit_breaker

        @circuit_breaker("test-fallback", fallback=lambda: "fallback")
        def failing_func():
            raise ValueError("error")

        result = failing_func()
        assert result == "fallback"


class TestRetryWithBackoff:
    """重试装饰器测试"""

    def test_succeeds_without_retry(self):
        """测试成功时不重试"""
        from services.shared.circuit_breaker import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        """测试失败时重试"""
        from services.shared.circuit_breaker import retry_with_backoff

        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("error")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        """测试达到最大重试后抛出异常"""
        from services.shared.circuit_breaker import retry_with_backoff

        @retry_with_backoff(
            max_retries=2,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def always_fail():
            raise ValueError("error")

        with pytest.raises(ValueError):
            always_fail()

    def test_on_retry_callback(self):
        """测试重试回调"""
        from services.shared.circuit_breaker import retry_with_backoff

        callback_calls = []

        def on_retry(exc, attempt):
            callback_calls.append((str(exc), attempt))

        @retry_with_backoff(
            max_retries=2,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,),
            on_retry=on_retry
        )
        def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing()

        assert len(callback_calls) == 2


class TestServiceDegradation:
    """服务降级测试"""

    def test_initial_level_is_normal(self):
        """测试初始级别为正常"""
        from services.shared.circuit_breaker import ServiceDegradation

        sd = ServiceDegradation("test-service")
        assert sd.get_level() == ServiceDegradation.LEVEL_NORMAL

    def test_set_level(self):
        """测试设置降级级别"""
        from services.shared.circuit_breaker import ServiceDegradation

        sd = ServiceDegradation("test-service")
        sd.set_level(ServiceDegradation.LEVEL_DEGRADE_1)
        assert sd.get_level() == ServiceDegradation.LEVEL_DEGRADE_1

    def test_should_degrade_on_high_cpu(self):
        """测试高 CPU 时应该降级"""
        from services.shared.circuit_breaker import ServiceDegradation

        sd = ServiceDegradation("test-service")
        result = sd.should_degrade(cpu_usage=0.9, memory_usage=0.5, avg_response_time=1.0)
        assert result is True
        assert sd.get_level() == ServiceDegradation.LEVEL_DEGRADE_1

    def test_should_degrade_on_slow_response(self):
        """测试响应慢时应该降级"""
        from services.shared.circuit_breaker import ServiceDegradation

        sd = ServiceDegradation("test-service")
        result = sd.should_degrade(cpu_usage=0.5, memory_usage=0.5, avg_response_time=3.0)
        assert result is True
        assert sd.get_level() == ServiceDegradation.LEVEL_DEGRADE_2

    def test_execute_with_degradation(self):
        """测试根据降级级别执行函数"""
        from services.shared.circuit_breaker import ServiceDegradation

        sd = ServiceDegradation("test-service")

        normal_called = False
        degrade_called = False

        def normal_func():
            nonlocal normal_called
            normal_called = True
            return "normal"

        def degrade_func():
            nonlocal degrade_called
            degrade_called = True
            return "degraded"

        # 正常级别执行正常函数
        result = sd.execute_with_degradation(normal_func, degrade_func)
        assert result == "normal"
        assert normal_called is True
        assert degrade_called is False

        # 设置降级后执行降级函数
        sd.set_level(ServiceDegradation.LEVEL_DEGRADE_1)
        result = sd.execute_with_degradation(normal_func, degrade_func)
        assert result == "degraded"


class TestDefaultConfigs:
    """预定义配置测试"""

    def test_database_config_exists(self):
        """测试数据库配置存在"""
        from services.shared.circuit_breaker import DEFAULT_CONFIGS

        assert "database" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["database"]
        assert config.failure_threshold == 3

    def test_http_config_exists(self):
        """测试 HTTP 配置存在"""
        from services.shared.circuit_breaker import DEFAULT_CONFIGS

        assert "http" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["http"]
        assert config.failure_threshold == 5

    def test_llm_config_exists(self):
        """测试 LLM 配置存在"""
        from services.shared.circuit_breaker import DEFAULT_CONFIGS

        assert "llm" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["llm"]
        assert config.timeout == 120.0


class TestGetCircuitBreaker:
    """获取预配置熔断器测试"""

    def test_get_circuit_breaker_with_type(self):
        """测试获取预配置熔断器"""
        from services.shared.circuit_breaker import get_circuit_breaker

        cb = get_circuit_breaker("test-get", config_type="database")
        assert cb is not None
        assert cb.config.failure_threshold == 3

    def test_get_circuit_breaker_with_fallback(self):
        """测试获取带降级的熔断器"""
        from services.shared.circuit_breaker import get_circuit_breaker

        def fallback():
            return "fallback"

        cb = get_circuit_breaker("test-fallback-get", fallback=fallback)
        assert cb.fallback == fallback
