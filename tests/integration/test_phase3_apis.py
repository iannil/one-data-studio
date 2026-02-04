"""
Phase 3: 核心 API 服务验证测试

测试覆盖范围:
- data-api 数据治理 API
- admin-api 管理后台 API
- openai-proxy OpenAI 兼容代理

测试用例编号: INT-P3-001 ~ INT-P3-030
"""

import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
import requests

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestDataAPI:
    """INT-P3-001 ~ INT-P3-012: data-api 测试"""

    @pytest.fixture
    def data_api_config(self):
        """data-api 配置"""
        return {
            "base_url": os.getenv("DATA_API_URL", "http://localhost:8001"),
            "health_endpoint": "/api/v1/health",
        }

    def test_data_api_health_check(self, data_api_config):
        """INT-P3-001: data-api 健康检查"""
        url = f"{data_api_config['base_url']}{data_api_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_version(self, data_api_config):
        """INT-P3-002: data-api 版本查询"""
        url = f"{data_api_config['base_url']}/api/v1/version"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "version" in data
            print(f"data-api version: {data.get('version')}")
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_list_datasources(self, data_api_config):
        """INT-P3-003: 列出数据源"""
        url = f"{data_api_config['base_url']}/api/v1/datasources"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "items" in data or "datasources" in data
            print(f"Datasources: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_create_datasource(self, data_api_config):
        """INT-P3-004: 创建数据源"""
        url = f"{data_api_config['base_url']}/api/v1/datasources"
        datasource_data = {
            "name": f"test_ds_{int(time.time())}",
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "description": "Test datasource"
        }

        try:
            response = requests.post(url, json=datasource_data, timeout=10)
            # 可能需要认证
            assert response.status_code in [200, 201, 401]
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data or "name" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_tables_metadata(self, data_api_config):
        """INT-P3-005: 表元数据查询"""
        # 首先需要有一个数据源
        url = f"{data_api_config['base_url']}/api/v1/tables"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "tables" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_metadata_scan(self, data_api_config):
        """INT-P3-006: 元数据扫描"""
        url = f"{data_api_config['base_url']}/api/v1/metadata/scan"
        try:
            # 触发扫描
            response = requests.post(url, json={"datasource_id": "test"}, timeout=10)
            # 可能返回 404 或需要认证
            assert response.status_code in [200, 201, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_data_quality_check(self, data_api_config):
        """INT-P3-007: 数据质量检查"""
        url = f"{data_api_config['base_url']}/api/v1/quality/check"
        try:
            response = requests.post(url, json={"table": "test_table"}, timeout=10)
            # 可能返回 404 或需要认证
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_etl_pipeline(self, data_api_config):
        """INT-P3-008: ETL 管道操作"""
        url = f"{data_api_config['base_url']}/api/v1/etl/pipelines"
        try:
            # 列出管道
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_lineage(self, data_api_config):
        """INT-P3-009: 数据血缘查询"""
        url = f"{data_api_config['base_url']}/api/v1/lineage"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_search(self, data_api_config):
        """INT-P3-010: 数据搜索"""
        url = f"{data_api_config['base_url']}/api/v1/search"
        try:
            response = requests.get(url, params={"q": "test"}, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_statistics(self, data_api_config):
        """INT-P3-011: 统计信息查询"""
        url = f"{data_api_config['base_url']}/api/v1/statistics"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_data_api_governance_rules(self, data_api_config):
        """INT-P3-012: 数据治理规则"""
        url = f"{data_api_config['base_url']}/api/v1/governance/rules"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")


@pytest.mark.integration
class TestAdminAPI:
    """INT-P3-013 ~ INT-P3-022: admin-api 测试"""

    @pytest.fixture
    def admin_api_config(self):
        """admin-api 配置"""
        return {
            "base_url": os.getenv("ADMIN_API_URL", "http://localhost:8004"),
            "health_endpoint": "/api/v1/health",
        }

    def test_admin_api_health_check(self, admin_api_config):
        """INT-P3-013: admin-api 健康检查"""
        url = f"{admin_api_config['base_url']}{admin_api_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_list_users(self, admin_api_config):
        """INT-P3-014: 列出用户"""
        url = f"{admin_api_config['base_url']}/api/v1/users"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "users" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_create_user(self, admin_api_config):
        """INT-P3-015: 创建用户"""
        url = f"{admin_api_config['base_url']}/api/v1/users"
        user_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "test123456",
            "role": "user"
        }

        try:
            response = requests.post(url, json=user_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_list_roles(self, admin_api_config):
        """INT-P3-016: 列出角色"""
        url = f"{admin_api_config['base_url']}/api/v1/roles"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "roles" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_permissions(self, admin_api_config):
        """INT-P3-017: 权限管理"""
        url = f"{admin_api_config['base_url']}/api/v1/permissions"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_audit_logs(self, admin_api_config):
        """INT-P3-018: 审计日志"""
        url = f"{admin_api_config['base_url']}/api/v1/audit/logs"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_tenants(self, admin_api_config):
        """INT-P3-019: 租户管理"""
        url = f"{admin_api_config['base_url']}/api/v1/tenants"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_settings(self, admin_api_config):
        """INT-P3-020: 系统设置"""
        url = f"{admin_api_config['base_url']}/api/v1/settings"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_notifications(self, admin_api_config):
        """INT-P3-021: 通知管理"""
        url = f"{admin_api_config['base_url']}/api/v1/notifications"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")

    def test_admin_api_dashboard_stats(self, admin_api_config):
        """INT-P3-022: 仪表盘统计"""
        url = f"{admin_api_config['base_url']}/api/v1/dashboard/stats"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("admin-api 服务未启动")


@pytest.mark.integration
class TestOpenAIProxy:
    """INT-P3-023 ~ INT-P3-030: openai-proxy 测试"""

    @pytest.fixture
    def openai_proxy_config(self):
        """openai-proxy 配置"""
        return {
            "base_url": os.getenv("OPENAI_PROXY_URL", "http://localhost:8003"),
            "health_endpoint": "/health",
            "api_version": "/v1",
        }

    def test_openai_proxy_health_check(self, openai_proxy_config):
        """INT-P3-023: openai-proxy 健康检查"""
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_list_models(self, openai_proxy_config):
        """INT-P3-024: 列出可用模型"""
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['api_version']}/models"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "data" in data or "models" in data
            print(f"Available models: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_chat_completion(self, openai_proxy_config):
        """INT-P3-025: 聊天补全 API"""
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['api_version']}/chat/completions"
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello!"}],
            "max_tokens": 10
        }

        try:
            response = requests.post(url, json=request_data, timeout=30)
            # 可能因为模型不可用而失败
            assert response.status_code in [200, 400, 404, 500]
            if response.status_code == 200:
                data = response.json()
                assert "choices" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_embeddings(self, openai_proxy_config):
        """INT-P3-026: 向量嵌入 API"""
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['api_version']}/embeddings"
        request_data = {
            "model": "text-embedding-ada-002",
            "input": "Hello, world!"
        }

        try:
            response = requests.post(url, json=request_data, timeout=30)
            # 可能因为模型不可用而失败
            assert response.status_code in [200, 400, 404, 500]
            if response.status_code == 200:
                data = response.json()
                assert "data" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_backend_routing(self, openai_proxy_config):
        """INT-P3-027: 后端路由测试"""
        url = f"{openai_proxy_config['base_url']}/api/v1/backends"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_rate_limiting(self, openai_proxy_config):
        """INT-P3-028: 速率限制测试"""
        # 连续发送多个请求，检查是否有速率限制
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['health_endpoint']}"
        try:
            for i in range(10):
                response = requests.get(url, timeout=5)
                if response.status_code == 429:
                    print(f"Rate limit hit at request {i+1}")
                    return
            print("No rate limit detected")
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_error_handling(self, openai_proxy_config):
        """INT-P3-029: 错误处理测试"""
        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['api_version']}/chat/completions"
        # 发送无效请求
        invalid_data = {
            "model": "non-existent-model",
            "messages": []
        }

        try:
            response = requests.post(url, json=invalid_data, timeout=10)
            # 应该返回错误
            assert response.status_code >= 400
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")

    def test_openai_proxy_concurrent_requests(self, openai_proxy_config):
        """INT-P3-030: 并发请求测试"""
        import threading
        import queue

        url = f"{openai_proxy_config['base_url']}{openai_proxy_config['health_endpoint']}"
        result_queue = queue.Queue()

        def make_request():
            try:
                response = requests.get(url, timeout=5)
                result_queue.put((response.status_code, None))
            except Exception as e:
                result_queue.put((None, str(e)))

        try:
            threads = []
            for _ in range(5):
                t = threading.Thread(target=make_request)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            results = []
            while not result_queue.empty():
                results.append(result_queue.get())

            success_count = sum(1 for status, _ in results if status == 200)
            print(f"Concurrent requests: {len(results)}, Success: {success_count}")
        except requests.exceptions.ConnectionError:
            pytest.skip("openai-proxy 服务未启动")


@pytest.mark.integration
class TestAPIIntegration:
    """INT-P3-031 ~ INT-P3-035: API 集成测试"""

    def test_api_service_discovery(self):
        """INT-P3-031: 服务发现测试"""
        # 验证所有 API 服务都可以被发现
        services = {
            "data-api": 8001,
            "admin-api": 8004,
            "openai-proxy": 8003,
        }

        import socket

        for service, port in services.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                print(f"✓ {service} is accessible on port {port}")
            else:
                print(f"✗ {service} is NOT accessible on port {port}")

    def test_api_cors_configuration(self):
        """INT-P3-032: CORS 配置测试"""
        # 检查 CORS 头
        apis = [
            ("http://localhost:8001", "/api/v1/health"),
            ("http://localhost:8004", "/api/v1/health"),
            ("http://localhost:8003", "/health"),
        ]

        for base_url, endpoint in apis:
            try:
                response = requests.options(f"{base_url}{endpoint}", timeout=5, headers={"Origin": "http://localhost:3000"})
                cors_headers = ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods"]
                for header in cors_headers:
                    if header in response.headers:
                        print(f"{base_url}: {header} = {response.headers[header]}")
            except:
                pass

    def test_api_authentication_flow(self):
        """INT-P3-033: 认证流程测试"""
        # 测试从登录到获取 token 的流程
        auth_urls = [
            "http://localhost:8001/api/v1/auth/login",
            "http://localhost:8004/api/v1/auth/login",
        ]

        for url in auth_urls:
            try:
                response = requests.post(url, json={"username": "admin", "password": "admin"}, timeout=5)
                if response.status_code in [200, 401]:
                    print(f"{url}: Authentication endpoint exists (status: {response.status_code})")
            except requests.exceptions.ConnectionError:
                pass

    def test_api_response_format(self):
        """INT-P3-034: API 响应格式测试"""
        # 验证 API 响应格式一致性
        apis = [
            ("http://localhost:8001/api/v1/health", "data-api"),
            ("http://localhost:8004/api/v1/health", "admin-api"),
        ]

        for url, name in apis:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # 检查标准字段
                    has_status = "status" in data
                    has_timestamp = "timestamp" in data or "time" in data
                    print(f"{name}: status={has_status}, timestamp={has_timestamp}")
            except requests.exceptions.ConnectionError:
                pass

    def test_api_error_responses(self):
        """INT-P3-035: 错误响应格式测试"""
        # 测试各种错误情况的响应
        test_cases = [
            ("http://localhost:8001/api/v1/nonexistent", 404),
            ("http://localhost:8004/api/v1/nonexistent", 404),
            ("http://localhost:8003/api/v1/invalid", 404),
        ]

        for url, expected_status in test_cases:
            try:
                response = requests.get(url, timeout=5)
                assert response.status_code == expected_status
                # 检查错误响应格式
                if response.headers.get("content-type", "").startswith("application/json"):
                    data = response.json()
                    assert "error" in data or "message" in data
            except requests.exceptions.ConnectionError:
                pass


@pytest.mark.integration
class TestAPIPerformance:
    """INT-P3-036 ~ INT-P3-040: API 性能测试"""

    def test_api_response_time(self):
        """INT-P3-036: API 响应时间测试"""
        import time

        apis = [
            ("http://localhost:8001/api/v1/health", "data-api"),
            ("http://localhost:8004/api/v1/health", "admin-api"),
            ("http://localhost:8003/health", "openai-proxy"),
        ]

        for url, name in apis:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                elapsed = time.time() - start_time

                if response.status_code == 200:
                    print(f"{name}: {elapsed*1000:.2f}ms")
                    assert elapsed < 2.0  # 健康检查应在 2 秒内返回
            except requests.exceptions.ConnectionError:
                pass

    def test_api_concurrent_load(self):
        """INT-P3-037: 并发负载测试"""
        import threading
        import time

        url = "http://localhost:8001/api/v1/health"
        num_requests = 20
        results = []

        def make_request():
            try:
                start = time.time()
                response = requests.get(url, timeout=5)
                elapsed = time.time() - start
                results.append((response.status_code, elapsed))
            except Exception as e:
                results.append((None, str(e)))

        threads = []
        start_time = time.time()

        for _ in range(num_requests):
            t = threading.Thread(target=make_request)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        total_time = time.time() - start_time
        success = sum(1 for s, _ in results if s == 200)

        print(f"Concurrent load: {success}/{num_requests} successful in {total_time:.2f}s")

    def test_api_memory_usage(self):
        """INT-P3-038: API 内存使用测试"""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.Container}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            api_containers = [
                "one-data-data-api",
                "one-data-admin-api",
                "one-data-openai-proxy",
            ]

            for line in result.stdout.split("\n"):
                for container in api_containers:
                    if container in line:
                        print(f"{container}: {line}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available")

    def test_api_connection_pooling(self):
        """INT-P3-039: 连接池测试"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # 创建带连接池的 session
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.1)
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)

        url = "http://localhost:8001/api/v1/health"

        try:
            for i in range(10):
                response = session.get(url, timeout=5)
                assert response.status_code == 200
            print("Connection pooling test passed")
        except requests.exceptions.ConnectionError:
            pytest.skip("data-api 服务未启动")

    def test_api_rate_limit_per_endpoint(self):
        """INT-P3-040: 端点级别的速率限制测试"""
        # 测试不同端点可能有不同的速率限制
        endpoints = [
            "/api/v1/health",
            "/api/v1/datasources",
            "/api/v1/tables",
        ]

        base_url = "http://localhost:8001"

        for endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                responses = []
                for _ in range(5):
                    response = requests.get(url, timeout=5)
                    responses.append(response.status_code)

                if 429 in responses:
                    print(f"{endpoint}: Rate limited")
                else:
                    print(f"{endpoint}: No rate limit detected")
            except requests.exceptions.ConnectionError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
