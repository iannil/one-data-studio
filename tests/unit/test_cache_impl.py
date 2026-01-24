"""
Unit tests for cache module implementation
Sprint 22: Quality Assurance
"""

import pytest
import time
from unittest.mock import Mock, patch

# Add the services/shared path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/shared'))


class TestMemoryCache:
    """Tests for MemoryCache implementation."""

    @pytest.fixture
    def memory_cache(self):
        """Create MemoryCache instance."""
        from cache import MemoryCache
        return MemoryCache()

    @pytest.mark.unit
    def test_set_and_get(self, memory_cache):
        """Test basic set and get operations."""
        memory_cache.set('key1', 'value1')
        result = memory_cache.get('key1')

        assert result == 'value1'

    @pytest.mark.unit
    def test_get_nonexistent_key(self, memory_cache):
        """Test getting a nonexistent key."""
        result = memory_cache.get('nonexistent')

        assert result is None

    @pytest.mark.unit
    def test_set_with_ttl(self, memory_cache):
        """Test set with TTL expiration."""
        memory_cache.set('key1', 'value1', ttl=1)

        # Should exist immediately
        assert memory_cache.get('key1') == 'value1'

        # Wait for expiry
        time.sleep(1.5)

        # Should be expired
        assert memory_cache.get('key1') is None

    @pytest.mark.unit
    def test_delete(self, memory_cache):
        """Test delete operation."""
        memory_cache.set('key1', 'value1')
        result = memory_cache.delete('key1')

        assert result is True
        assert memory_cache.get('key1') is None

    @pytest.mark.unit
    def test_delete_nonexistent(self, memory_cache):
        """Test deleting nonexistent key."""
        result = memory_cache.delete('nonexistent')

        assert result is True  # delete always returns True

    @pytest.mark.unit
    def test_exists(self, memory_cache):
        """Test exists operation."""
        memory_cache.set('key1', 'value1')

        assert memory_cache.exists('key1') is True
        assert memory_cache.exists('nonexistent') is False

    @pytest.mark.unit
    def test_exists_with_expired_key(self, memory_cache):
        """Test exists with expired key."""
        memory_cache.set('key1', 'value1', ttl=1)

        time.sleep(1.5)

        assert memory_cache.exists('key1') is False

    @pytest.mark.unit
    def test_clear(self, memory_cache):
        """Test clear operation."""
        memory_cache.set('key1', 'value1')
        memory_cache.set('key2', 'value2')
        result = memory_cache.clear()

        assert result is True
        assert memory_cache.get('key1') is None
        assert memory_cache.get('key2') is None

    @pytest.mark.unit
    def test_delete_pattern(self, memory_cache):
        """Test delete by pattern."""
        memory_cache.set('user:1:name', 'Alice')
        memory_cache.set('user:2:name', 'Bob')
        memory_cache.set('product:1', 'Item')

        count = memory_cache.delete_pattern('user:*')

        assert count == 2
        assert memory_cache.get('user:1:name') is None
        assert memory_cache.get('user:2:name') is None
        assert memory_cache.get('product:1') == 'Item'

    @pytest.mark.unit
    def test_complex_values(self, memory_cache):
        """Test storing complex values."""
        data = {'name': 'test', 'items': [1, 2, 3], 'nested': {'key': 'value'}}
        memory_cache.set('complex', data)

        result = memory_cache.get('complex')

        assert result == data
        assert result['name'] == 'test'
        assert result['items'] == [1, 2, 3]


class TestCacheBackend:
    """Tests for CacheBackend base class."""

    @pytest.mark.unit
    def test_cache_backend_default_methods(self):
        """Test CacheBackend default implementations."""
        from cache import CacheBackend

        backend = CacheBackend()

        # Default implementations should not raise NotImplementedError
        assert backend.get('key') is None
        assert backend.set('key', 'value') is False
        assert backend.delete('key') is False
        assert backend.clear() is False
        assert backend.exists('key') is False


class TestCachedDecorator:
    """Tests for cached decorator."""

    @pytest.mark.unit
    def test_cached_decorator(self):
        """Test cached decorator basic functionality."""
        from cache import cached, _get_memory_cache

        # Clear any existing cache
        _get_memory_cache().clear()

        call_count = 0

        @cached(ttl=60, key_prefix='test')
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, didn't execute again

        # Different argument - should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.unit
    def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        from cache import cached, _get_memory_cache

        _get_memory_cache().clear()

        call_count = 0

        @cached(ttl=60, key_prefix='test_kwargs')
        def function_with_kwargs(a, b=10):
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = function_with_kwargs(5, b=20)
        assert result1 == 25
        assert call_count == 1

        result2 = function_with_kwargs(5, b=20)
        assert result2 == 25
        assert call_count == 1

    @pytest.mark.unit
    def test_cached_decorator_clear_cache(self):
        """Test clearing cache for decorated function."""
        from cache import cached, _get_memory_cache

        _get_memory_cache().clear()

        call_count = 0

        @cached(ttl=60, key_prefix='test_clear')
        def cacheable_function(x):
            nonlocal call_count
            call_count += 1
            return x

        # Cache it
        cacheable_function(5)
        assert call_count == 1

        # Clear cache
        cacheable_function.clear_cache(5)

        # Should re-execute
        cacheable_function(5)
        assert call_count == 2


class TestGetCache:
    """Tests for get_cache function."""

    @pytest.mark.unit
    def test_get_cache_singleton(self):
        """Test get_cache returns singleton."""
        from cache import get_cache

        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2
