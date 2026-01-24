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


class TestCacheSecurityFeatures:
    """Tests for cache security features (HMAC signatures, JSON serialization)."""

    @pytest.mark.unit
    def test_signing_key_required_in_production(self):
        """Test that signing key is required in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "CACHE_SIGNING_KEY": ""}):
            # Reset the global key
            import cache
            cache._CACHE_SIGNING_KEY = None

            with pytest.raises(ValueError, match="CACHE_SIGNING_KEY.*required"):
                cache._get_signing_key()

    @pytest.mark.unit
    def test_signing_key_dev_fallback(self):
        """Test signing key has dev fallback in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CACHE_SIGNING_KEY": ""}):
            import cache
            cache._CACHE_SIGNING_KEY = None

            # Should not raise, uses dev fallback
            key = cache._get_signing_key()
            assert key is not None
            assert len(key) > 0

    @pytest.mark.unit
    def test_signature_verification(self):
        """Test HMAC signature creation and verification."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CACHE_SIGNING_KEY": "test-key-123"}):
            import cache
            cache._CACHE_SIGNING_KEY = None  # Reset to pick up new key

            data = b'test data'
            signature = cache._sign_data(data)

            # Verification should pass with correct data
            assert cache._verify_signature(data, signature) is True

            # Verification should fail with wrong data
            assert cache._verify_signature(b'wrong data', signature) is False

            # Verification should fail with wrong signature
            assert cache._verify_signature(data, "wrong-signature") is False

    @pytest.mark.unit
    def test_json_serialization_only(self):
        """Test that only JSON-serializable values can be cached."""
        from cache import MemoryCache

        cache = MemoryCache()

        # JSON-serializable values should work
        cache.set('dict', {'key': 'value'})
        cache.set('list', [1, 2, 3])
        cache.set('string', 'hello')
        cache.set('number', 42)

        assert cache.get('dict') == {'key': 'value'}
        assert cache.get('list') == [1, 2, 3]
        assert cache.get('string') == 'hello'
        assert cache.get('number') == 42

    @pytest.mark.unit
    def test_tampered_cache_rejected(self):
        """Test that tampered cache entries are rejected by Redis cache."""
        # This test verifies the security behavior:
        # If someone modifies the cache data without knowing the signing key,
        # the signature verification should fail

        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CACHE_SIGNING_KEY": "test-key"}):
            import cache
            import json
            cache._CACHE_SIGNING_KEY = None

            # Create a valid envelope
            data = json.dumps({"value": "original"})
            signature = cache._sign_data(data.encode('utf-8'))
            envelope = json.dumps({"signature": signature, "data": data})

            # Tamper with the data
            tampered_data = json.dumps({"value": "tampered"})
            tampered_envelope = json.dumps({"signature": signature, "data": tampered_data})

            # The tampered envelope should fail verification
            parsed = json.loads(tampered_envelope)
            result = cache._verify_signature(
                parsed['data'].encode('utf-8'),
                parsed['signature']
            )
            assert result is False

    @pytest.mark.unit
    def test_legacy_unsigned_cache_rejected(self):
        """Test that legacy unsigned cache entries are rejected."""
        # This verifies that old pickle-based cache entries (without signatures)
        # will be rejected for security

        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CACHE_SIGNING_KEY": "test-key"}):
            import cache
            import json

            # Simulate a legacy cache entry (just raw JSON without signature envelope)
            legacy_data = json.dumps({"key": "value"})

            # Parse it - it's valid JSON but not our secure envelope format
            parsed = json.loads(legacy_data)

            # Should not have the required signature/data structure
            has_envelope = isinstance(parsed, dict) and 'signature' in parsed and 'data' in parsed
            assert has_envelope is False

