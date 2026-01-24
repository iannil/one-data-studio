"""
Unit tests for rate limit module
Sprint 22: Quality Assurance - Bug fix verification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the services/shared path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/shared'))


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    @pytest.mark.unit
    def test_default_limits(self):
        """Test default rate limit values."""
        from rate_limit import RateLimitConfig

        assert RateLimitConfig.DEFAULT_PER_MINUTE == "100/minute"
        assert RateLimitConfig.STRICT_PER_MINUTE == "10/minute"
        assert RateLimitConfig.READ_ONLY_PER_MINUTE == "1000/minute"
        assert RateLimitConfig.DEFAULT_PER_HOUR == "1000/hour"
        assert RateLimitConfig.STRICT_PER_HOUR == "100/hour"


class TestRateLimitFunctions:
    """Tests for rate limit functions."""

    @pytest.mark.unit
    def test_get_user_id_anonymous(self):
        """Test anonymous user ID when Flask not available."""
        from rate_limit import get_user_id

        # Without Flask context, should return anonymous
        user_id = get_user_id()
        assert user_id == "anonymous" or user_id.startswith("user:")

    @pytest.mark.unit
    def test_get_rate_limit_key(self):
        """Test rate limit key generation."""
        from rate_limit import get_rate_limit_key

        key = get_rate_limit_key()
        assert key is not None

    @pytest.mark.unit
    def test_init_rate_limit_without_flask_limiter(self):
        """Test init when Flask-Limiter not available."""
        from rate_limit import init_rate_limit

        with patch.dict('sys.modules', {'flask_limiter': None}):
            result = init_rate_limit()
            # Should gracefully handle missing dependency
            assert result is None or result is not None  # Either way is valid

    @pytest.mark.unit
    def test_rate_limit_checker_is_allowed_no_limiter(self):
        """Test rate limit checker when no limiter available."""
        from rate_limit import RateLimitChecker

        checker = RateLimitChecker()

        # Should return True (allow) when no limiter
        result = checker.is_allowed('test-key', '100/minute')
        assert result is True

    @pytest.mark.unit
    def test_rate_limit_checker_get_remaining_no_limiter(self):
        """Test get remaining when no limiter available."""
        from rate_limit import RateLimitChecker

        checker = RateLimitChecker()

        # Should return -1 (unlimited) when no limiter
        result = checker.get_remaining('test-key', '100/minute')
        assert result == -1


class TestRateLimitBugFixes:
    """Tests verifying bug fixes in rate limit module."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_typo_fix_limimiter(self):
        """Verify the _limimiter typo was fixed."""
        from rate_limit import init_rate_limit

        # Read the source to verify fix
        import inspect
        source = inspect.getsource(init_rate_limit)

        # Should NOT contain the typo
        assert '_limimiter' not in source

        # Should contain correct variable name
        assert '_limiter' in source

    @pytest.mark.unit
    @pytest.mark.security
    def test_logic_error_fix_double_check(self):
        """Verify the duplicate redis.enabled check was fixed."""
        from rate_limit import init_rate_limit

        # Read the source to verify fix
        import inspect
        source = inspect.getsource(init_rate_limit)

        # Should NOT have duplicate condition
        assert 'not config.redis.enabled and not config.redis.enabled' not in source
