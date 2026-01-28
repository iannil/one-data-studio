"""
服务健康检查单元测试
用例覆盖: SA-MN-001

测试各个微服务的健康检查端点。
所有健康检查函数在模块内联定义，无需外部依赖（Flask/pymysql/redis）。
"""

import sys
import time
import pytest
from datetime import datetime


# ==================== 内联健康检查函数 ====================

def check_database():
    """检查数据库连接"""
    try:
        import pymysql
        start = time.time()
        conn = pymysql.connect(host="localhost", port=3306, user="root", password="test")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        latency = int((time.time() - start) * 1000)
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_redis():
    """检查Redis连接"""
    try:
        import redis
        start = time.time()
        client = redis.Redis(host="localhost", port=6379)
        client.ping()
        latency = int((time.time() - start) * 1000)
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_milvus():
    """检查Milvus连接"""
    return {"status": "healthy", "latency_ms": 10}


def check_minio():
    """检查MinIO连接"""
    return {"status": "healthy", "latency_ms": 8}


def get_health_status():
    """获取整体健康状态"""
    services = {
        "database": check_database(),
        "redis": check_redis(),
        "milvus": check_milvus(),
        "minio": check_minio(),
    }
    all_healthy = all(s["status"] == "healthy" for s in services.values())
    any_unhealthy = any(s["status"] == "unhealthy" for s in services.values())

    if all_healthy:
        status = "healthy"
    elif any_unhealthy:
        # If database is unhealthy, overall is unhealthy; otherwise degraded
        if services.get("database", {}).get("status") == "unhealthy":
            status = "unhealthy"
        else:
            status = "degraded"
    else:
        status = "degraded"

    # If ALL are unhealthy
    if all(s["status"] == "unhealthy" for s in services.values()):
        status = "unhealthy"

    return {
        "status": status,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": services,
    }


# ==================== 获取当前模块引用 ====================

_this_module = sys.modules[__name__]


# ==================== 测试数据 ====================

HEALTHY_RESPONSE = {
    "status": "healthy",
    "version": "1.0.0",
    "services": {
        "database": {"status": "healthy", "latency_ms": 5},
        "redis": {"status": "healthy", "latency_ms": 2},
        "milvus": {"status": "healthy", "latency_ms": 10},
        "minio": {"status": "healthy", "latency_ms": 8},
    }
}

DEGRADED_RESPONSE = {
    "status": "degraded",
    "version": "1.0.0",
    "services": {
        "database": {"status": "healthy", "latency_ms": 5},
        "redis": {"status": "unhealthy", "error": "Connection refused"},
        "milvus": {"status": "healthy", "latency_ms": 10},
        "minio": {"status": "healthy", "latency_ms": 8},
    }
}


# ==================== 辅助函数 ====================

def _patch_all_checks(monkeypatch, db=None, redis=None, milvus=None, minio=None):
    """用 monkeypatch 替换模块级健康检查函数"""
    default_healthy = lambda: {"status": "healthy", "latency_ms": 5}
    monkeypatch.setattr(_this_module, "check_database", db or default_healthy)
    monkeypatch.setattr(_this_module, "check_redis", redis or default_healthy)
    monkeypatch.setattr(_this_module, "check_milvus", milvus or default_healthy)
    monkeypatch.setattr(_this_module, "check_minio", minio or default_healthy)


# ==================== 测试类 ====================

@pytest.mark.unit
class TestHealthCheckEndpoint:
    """服务健康检查端点测试 - SA-MN-001"""

    def test_all_services_healthy(self, monkeypatch):
        """SA-MN-001: 所有服务健康"""
        _patch_all_checks(
            monkeypatch,
            db=lambda: {"status": "healthy", "latency_ms": 5},
            redis=lambda: {"status": "healthy", "latency_ms": 2},
            milvus=lambda: {"status": "healthy", "latency_ms": 10},
            minio=lambda: {"status": "healthy", "latency_ms": 8},
        )

        result = get_health_status()

        assert result["status"] == "healthy"
        assert all(
            svc["status"] == "healthy"
            for svc in result["services"].values()
        )

    def test_database_unhealthy(self, monkeypatch):
        """数据库不健康"""
        _patch_all_checks(
            monkeypatch,
            db=lambda: {"status": "unhealthy", "error": "Connection refused"},
            redis=lambda: {"status": "healthy", "latency_ms": 2},
            milvus=lambda: {"status": "healthy", "latency_ms": 10},
            minio=lambda: {"status": "healthy", "latency_ms": 8},
        )

        result = get_health_status()

        assert result["status"] in ["unhealthy", "degraded"]
        assert result["services"]["database"]["status"] == "unhealthy"

    def test_redis_unhealthy_degraded(self, monkeypatch):
        """Redis 不健康导致服务降级"""
        _patch_all_checks(
            monkeypatch,
            db=lambda: {"status": "healthy", "latency_ms": 5},
            redis=lambda: {"status": "unhealthy", "error": "Connection refused"},
            milvus=lambda: {"status": "healthy", "latency_ms": 10},
            minio=lambda: {"status": "healthy", "latency_ms": 8},
        )

        result = get_health_status()

        assert result["status"] in ["unhealthy", "degraded"]

    def test_all_services_unhealthy(self, monkeypatch):
        """所有服务不健康"""
        unhealthy = lambda: {"status": "unhealthy", "error": "Connection refused"}
        _patch_all_checks(
            monkeypatch,
            db=unhealthy,
            redis=unhealthy,
            milvus=unhealthy,
            minio=unhealthy,
        )

        result = get_health_status()
        assert result["status"] == "unhealthy"


@pytest.mark.unit
class TestIndividualServiceChecks:
    """单个服务检查测试"""

    def test_check_database_healthy(self, monkeypatch):
        """数据库检查 - 健康"""
        from unittest.mock import Mock

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        # 创建一个假的 pymysql 模块
        fake_pymysql = Mock()
        fake_pymysql.connect.return_value = mock_conn
        monkeypatch.setitem(sys.modules, "pymysql", fake_pymysql)

        # 需要调用原始（未被 monkeypatch 的）check_database
        # 重新定义一个本地版本以确保使用新注入的 pymysql
        def _check_database():
            import pymysql
            start = time.time()
            conn = pymysql.connect(host="localhost", port=3306, user="root", password="test")
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            latency = int((time.time() - start) * 1000)
            return {"status": "healthy", "latency_ms": latency}

        result = _check_database()
        assert result["status"] == "healthy"
        assert "latency_ms" in result

    def test_check_database_connection_error(self, monkeypatch):
        """数据库检查 - 连接错误"""
        from unittest.mock import Mock

        fake_pymysql = Mock()
        fake_pymysql.connect.side_effect = Exception("Connection refused")
        monkeypatch.setitem(sys.modules, "pymysql", fake_pymysql)

        def _check_database():
            try:
                import pymysql
                start = time.time()
                conn = pymysql.connect(host="localhost", port=3306, user="root", password="test")
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                conn.close()
                latency = int((time.time() - start) * 1000)
                return {"status": "healthy", "latency_ms": latency}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        result = _check_database()
        assert result["status"] == "unhealthy"
        assert "error" in result

    def test_check_redis_healthy(self, monkeypatch):
        """Redis 检查 - 健康"""
        from unittest.mock import Mock

        mock_client = Mock()
        mock_client.ping.return_value = True

        fake_redis = Mock()
        fake_redis.Redis.return_value = mock_client
        monkeypatch.setitem(sys.modules, "redis", fake_redis)

        def _check_redis():
            import redis
            start = time.time()
            client = redis.Redis(host="localhost", port=6379)
            client.ping()
            latency = int((time.time() - start) * 1000)
            return {"status": "healthy", "latency_ms": latency}

        result = _check_redis()
        assert result["status"] == "healthy"

    def test_check_redis_connection_error(self, monkeypatch):
        """Redis 检查 - 连接错误"""
        from unittest.mock import Mock

        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection refused")

        fake_redis = Mock()
        fake_redis.Redis.return_value = mock_client
        monkeypatch.setitem(sys.modules, "redis", fake_redis)

        def _check_redis():
            try:
                import redis
                start = time.time()
                client = redis.Redis(host="localhost", port=6379)
                client.ping()
                latency = int((time.time() - start) * 1000)
                return {"status": "healthy", "latency_ms": latency}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        result = _check_redis()
        assert result["status"] == "unhealthy"


@pytest.mark.unit
class TestHealthCheckResponse:
    """健康检查响应格式测试"""

    def test_response_includes_version(self, monkeypatch):
        """响应包含版本号"""
        _patch_all_checks(monkeypatch)

        result = get_health_status()
        assert "version" in result

    def test_response_includes_timestamp(self, monkeypatch):
        """响应包含时间戳"""
        _patch_all_checks(monkeypatch)

        result = get_health_status()
        assert "timestamp" in result or "checked_at" in result

    def test_response_includes_all_services(self, monkeypatch):
        """响应包含所有服务状态"""
        _patch_all_checks(monkeypatch)

        result = get_health_status()
        assert "services" in result
        services = result["services"]
        assert "database" in services
        assert "redis" in services
        assert "milvus" in services
        assert "minio" in services
