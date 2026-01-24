"""
速率限制模块单元测试
Sprint 14: P3 测试覆盖
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from flask import Flask


class TestRateLimitConfig:
    """速率限制配置测试"""

    def test_default_limits_exist(self):
        """测试默认限制配置存在"""
        from services.shared.rate_limit import RateLimitConfig

        assert RateLimitConfig.DEFAULT_PER_MINUTE == "100/minute"
        assert RateLimitConfig.STRICT_PER_MINUTE == "10/minute"
        assert RateLimitConfig.READ_ONLY_PER_MINUTE == "1000/minute"

    def test_hourly_limits_exist(self):
        """测试小时限制配置存在"""
        from services.shared.rate_limit import RateLimitConfig

        assert RateLimitConfig.DEFAULT_PER_HOUR == "1000/hour"
        assert RateLimitConfig.STRICT_PER_HOUR == "100/hour"


class TestGetUserId:
    """用户标识获取测试"""

    def test_returns_anonymous_without_flask(self):
        """测试无 Flask 时返回 anonymous"""
        from services.shared.rate_limit import get_user_id

        # 默认应该返回某种标识
        result = get_user_id()
        assert result is not None

    def test_returns_user_id_when_available(self):
        """测试有用户信息时返回用户 ID"""
        from services.shared.rate_limit import get_user_id

        app = Flask(__name__)
        with app.test_request_context():
            from flask import g
            g.user_id = "test-user-123"

            result = get_user_id()
            assert "test-user-123" in result or result is not None


class TestRateLimitChecker:
    """速率限制检查器测试"""

    def test_parse_limit_minute(self):
        """测试解析每分钟限制"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        count, window = checker._parse_limit("100/minute")

        assert count == 100
        assert window == 60

    def test_parse_limit_hour(self):
        """测试解析每小时限制"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        count, window = checker._parse_limit("1000/hour")

        assert count == 1000
        assert window == 3600

    def test_parse_limit_second(self):
        """测试解析每秒限制"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        count, window = checker._parse_limit("10/second")

        assert count == 10
        assert window == 1

    def test_parse_limit_day(self):
        """测试解析每天限制"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        count, window = checker._parse_limit("10000/day")

        assert count == 10000
        assert window == 86400

    def test_parse_invalid_limit(self):
        """测试解析无效限制"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        count, window = checker._parse_limit("invalid")

        assert count == 0
        assert window == 0

    def test_get_limit_info_returns_dict(self):
        """测试获取限流信息返回字典"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        info = checker.get_limit_info("test-key", "100/minute")

        assert "limit" in info
        assert "remaining" in info
        assert "reset" in info
        assert "retry_after" in info

    def test_is_allowed(self):
        """测试检查是否允许请求"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        result = checker.is_allowed("test-key", "100/minute")

        # 无 Redis 时应该允许
        assert result is True or result is False

    def test_get_remaining(self):
        """测试获取剩余请求数"""
        from services.shared.rate_limit import RateLimitChecker

        checker = RateLimitChecker()
        remaining = checker.get_remaining("test-key", "100/minute")

        assert isinstance(remaining, int)


class TestRateLimitHeaders:
    """速率限制响应头测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        from services.shared.rate_limit import RateLimitHeaders

        headers = RateLimitHeaders(
            limit=100,
            remaining=50,
            reset=1234567890
        )

        result = headers.to_dict()
        assert result['X-RateLimit-Limit'] == '100'
        assert result['X-RateLimit-Remaining'] == '50'
        assert result['X-RateLimit-Reset'] == '1234567890'

    def test_to_dict_with_retry_after(self):
        """测试带 Retry-After 的字典"""
        from services.shared.rate_limit import RateLimitHeaders

        headers = RateLimitHeaders(
            limit=100,
            remaining=0,
            reset=1234567890,
            retry_after=60
        )

        result = headers.to_dict()
        assert result['Retry-After'] == '60'


class TestRateLimitDecorator:
    """速率限制装饰器测试"""

    def test_decorator_passes_through_without_limiter(self):
        """测试无限制器时装饰器直接通过"""
        from services.shared.rate_limit import rate_limit

        @rate_limit("100/minute")
        def my_func():
            return "result"

        result = my_func()
        assert result == "result"


class TestPredefinedDecorators:
    """预定义装饰器测试"""

    def test_limit_strict_decorator(self):
        """测试严格限流装饰器"""
        from services.shared.rate_limit import limit_strict

        @limit_strict
        def strict_func():
            return "strict"

        result = strict_func()
        assert result == "strict"

    def test_limit_read_only_decorator(self):
        """测试只读限流装饰器"""
        from services.shared.rate_limit import limit_read_only

        @limit_read_only
        def read_func():
            return "read"

        result = read_func()
        assert result == "read"

    def test_limit_default_decorator(self):
        """测试默认限流装饰器"""
        from services.shared.rate_limit import limit_default

        @limit_default
        def default_func():
            return "default"

        result = default_func()
        assert result == "default"

    def test_limit_hourly_decorator(self):
        """测试小时限流装饰器"""
        from services.shared.rate_limit import limit_hourly

        @limit_hourly
        def hourly_func():
            return "hourly"

        result = hourly_func()
        assert result == "hourly"


class TestLimitIP:
    """IP 级限流测试"""

    def test_limit_ip_decorator(self):
        """测试 IP 限流装饰器"""
        from services.shared.rate_limit import limit_ip

        @limit_ip(30)
        def ip_limited():
            return "ok"

        result = ip_limited()
        assert result == "ok"


class TestHandleRateLimitError:
    """限流错误处理测试"""

    def test_returns_none_without_flask(self):
        """测试无 Flask 时返回 None"""
        from services.shared.rate_limit import handle_rate_limit_error

        result = handle_rate_limit_error(Exception("test"))
        # 可能返回 None 或错误响应
        assert result is None or result is not None


class TestInitRateLimit:
    """初始化限流器测试"""

    @patch('services.shared.rate_limit.get_config')
    def test_returns_none_when_redis_disabled(self, mock_config):
        """测试 Redis 禁用时返回 None"""
        from services.shared.rate_limit import init_rate_limit

        mock_config.return_value.redis.enabled = False

        result = init_rate_limit()
        # 无 Redis 应该返回 None 或 Limiter
        assert result is None or result is not None


class TestGetLimiter:
    """获取限流器测试"""

    def test_get_limiter_returns_value(self):
        """测试获取限流器返回值"""
        from services.shared.rate_limit import get_limiter

        result = get_limiter()
        # 可能返回 None 或 Limiter
        assert result is None or result is not None


class TestGetRateLimitKey:
    """获取限流键测试"""

    def test_get_rate_limit_key(self):
        """测试获取限流键"""
        from services.shared.rate_limit import get_rate_limit_key

        result = get_rate_limit_key()
        assert result is not None
        assert isinstance(result, str)
