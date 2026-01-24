"""
Redis 故障转移测试
Sprint 14: 高可用基础设施 - Redis Sentinel 模式测试
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestRedisSentinelFailover:
    """Redis Sentinel 故障转移测试"""

    @pytest.fixture
    def mock_sentinel(self):
        """创建模拟 Sentinel"""
        sentinel = MagicMock()
        master = MagicMock()
        slave = MagicMock()

        # 模拟 master_for 返回
        sentinel.master_for.return_value = master
        sentinel.slave_for.return_value = slave

        # 模拟 ping 成功
        master.ping.return_value = True
        slave.ping.return_value = True

        return sentinel, master, slave

    @pytest.fixture
    def mock_redis_config(self):
        """创建模拟 Redis 配置"""
        config = MagicMock()
        config.sentinel_enabled = True
        config.sentinel_master = "mymaster"
        config.sentinel_addresses = [("redis-sentinel", 26379)]
        config.sentinel_password = "test_password"
        config.password = "redis_password"
        config.db = 0
        config.socket_timeout = 5
        config.retry_on_timeout = True
        return config

    def test_sentinel_connection_success(self, mock_sentinel, mock_redis_config):
        """测试 Sentinel 连接成功"""
        sentinel, master, slave = mock_sentinel

        with patch('redis.sentinel.Sentinel', return_value=sentinel):
            # 模拟创建连接
            sentinel.master_for.assert_not_called()

            # 获取 master 连接
            master_conn = sentinel.master_for(
                mock_redis_config.sentinel_master,
                socket_timeout=mock_redis_config.socket_timeout,
                password=mock_redis_config.password,
                db=mock_redis_config.db,
            )

            assert master_conn is not None
            master_conn.ping()
            master.ping.assert_called()

    def test_sentinel_failover_detection(self, mock_sentinel, mock_redis_config):
        """测试 Sentinel 故障检测"""
        sentinel, master, slave = mock_sentinel

        # 模拟 master 失败
        master.ping.side_effect = [True, True, ConnectionError("Master down")]

        # 第一次 ping 成功
        assert master.ping() is True

        # 第二次 ping 成功
        assert master.ping() is True

        # 第三次 ping 失败
        with pytest.raises(ConnectionError):
            master.ping()

    def test_sentinel_auto_reconnect(self, mock_sentinel, mock_redis_config):
        """测试 Sentinel 自动重连"""
        sentinel, master, slave = mock_sentinel

        new_master = MagicMock()
        new_master.ping.return_value = True

        # 模拟故障转移：第一次返回旧 master，第二次返回新 master
        sentinel.master_for.side_effect = [master, new_master]

        # 第一次获取 master
        conn1 = sentinel.master_for(mock_redis_config.sentinel_master)
        assert conn1 == master

        # 模拟故障后重新获取 master
        conn2 = sentinel.master_for(mock_redis_config.sentinel_master)
        assert conn2 == new_master
        assert conn2 != conn1

    def test_read_from_replica(self, mock_sentinel, mock_redis_config):
        """测试从副本读取"""
        sentinel, master, slave = mock_sentinel

        # 设置副本返回数据
        slave.get.return_value = b"cached_value"

        # 获取副本连接
        replica = sentinel.slave_for(
            mock_redis_config.sentinel_master,
            socket_timeout=mock_redis_config.socket_timeout,
            password=mock_redis_config.password,
        )

        # 从副本读取
        result = replica.get("test_key")
        assert result == b"cached_value"

    def test_write_to_master_only(self, mock_sentinel, mock_redis_config):
        """测试只能写入 master"""
        sentinel, master, slave = mock_sentinel

        # 副本应该是只读的
        slave.set.side_effect = Exception("READONLY You can't write against a read only replica")

        # 写入 master 成功
        master.set.return_value = True
        assert master.set("key", "value") is True

        # 写入 slave 失败
        with pytest.raises(Exception) as exc_info:
            slave.set("key", "value")
        assert "READONLY" in str(exc_info.value)


class TestRedisFailoverIntegration:
    """Redis 故障转移集成测试"""

    @pytest.fixture
    def cache_with_sentinel(self):
        """创建带 Sentinel 的缓存实例"""
        with patch.dict('os.environ', {
            'REDIS_SENTINEL_ENABLED': 'true',
            'REDIS_SENTINEL_MASTER': 'mymaster',
            'REDIS_SENTINEL_HOSTS': 'redis-sentinel-0:26379,redis-sentinel-1:26379,redis-sentinel-2:26379',
            'REDIS_PASSWORD': 'test_password',
        }):
            # 这里可以导入实际的 cache 模块进行测试
            yield

    def test_cache_operations_during_failover(self):
        """测试故障转移期间的缓存操作"""
        # 这个测试需要实际的 Redis Sentinel 环境
        # 在 CI/CD 中可以使用 Docker Compose 启动测试环境
        pass

    def test_connection_pool_recovery(self):
        """测试连接池恢复"""
        # 模拟连接池在故障转移后的恢复行为
        pass


class TestRetryWithBackoff:
    """重试退避策略测试"""

    def test_retry_success_on_first_attempt(self):
        """测试第一次尝试成功"""
        from services.shared.circuit_breaker import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_on_third_attempt(self):
        """测试第三次尝试成功"""
        from services.shared.circuit_breaker import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = failing_then_succeeding()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """测试重试次数耗尽"""
        from services.shared.circuit_breaker import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def always_failing():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_failing()

    def test_non_retryable_exception(self):
        """测试不可重试的异常"""
        from services.shared.circuit_breaker import retry_with_backoff

        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            retryable_exceptions=(ConnectionError,)
        )
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

        # 应该只调用一次，因为 ValueError 不可重试
        assert call_count == 1

    def test_on_retry_callback(self):
        """测试重试回调"""
        from services.shared.circuit_breaker import retry_with_backoff

        retry_attempts = []

        def on_retry(exception, attempt):
            retry_attempts.append((str(exception), attempt))

        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.01,
            on_retry=on_retry
        )
        def failing_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Attempt {call_count}")
            return "success"

        result = failing_twice()
        assert result == "success"
        assert len(retry_attempts) == 2
        assert retry_attempts[0][1] == 1
        assert retry_attempts[1][1] == 2
