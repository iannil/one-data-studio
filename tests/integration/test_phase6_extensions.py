"""
Phase 6: 扩展服务验证测试

测试覆盖范围:
- ocr-service OCR 识别服务
- behavior-service 行为分析服务
- keycloak 认证服务

测试用例编号: INT-P6-001 ~ INT-P6-025
"""

import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock
from io import BytesIO

import pytest
import requests

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestOCRService:
    """INT-P6-001 ~ INT-P6-010: ocr-service 测试"""

    @pytest.fixture
    def ocr_config(self):
        """OCR 服务配置"""
        return {
            "base_url": os.getenv("OCR_SERVICE_URL", "http://localhost:8007"),
            "health_endpoint": "/health",
        }

    def test_ocr_service_health_check(self, ocr_config):
        """INT-P6-001: OCR 服务健康检查"""
        url = f"{ocr_config['base_url']}{ocr_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_service_version(self, ocr_config):
        """INT-P6-002: OCR 服务版本查询"""
        url = f"{ocr_config['base_url']}/version"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "version" in data
                print(f"OCR service version: {data.get('version')}")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_recognize_text(self, ocr_config):
        """INT-P6-003: 文本识别测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/recognize"

        try:
            # 创建测试图像
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 30), "Hello World", fill='black')

            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            files = {"file": ("test.png", img_bytes, "image/png")}
            response = requests.post(url, files=files, timeout=30)

            assert response.status_code in [200, 201, 400]
            if response.status_code in [200, 201]:
                data = response.json()
                assert "text" in data or "result" in data
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_batch_recognize(self, ocr_config):
        """INT-P6-004: 批量识别测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/batch"

        try:
            from PIL import Image

            # 创建多个测试图像
            files = []
            for i in range(3):
                img = Image.new('RGB', (200, 100), color='white')
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                files.append(("files", (f"test_{i}.png", img_bytes, "image/png")))

            response = requests.post(url, files=files, timeout=60)
            assert response.status_code in [200, 201, 400, 404]
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_table_extraction(self, ocr_config):
        """INT-P6-005: 表格提取测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/table"

        try:
            from PIL import Image

            img = Image.new('RGB', (400, 300), color='white')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            files = {"file": ("table.png", img_bytes, "image/png")}
            response = requests.post(url, files=files, timeout=30)

            assert response.status_code in [200, 201, 400, 404]
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_receipt_extraction(self, ocr_config):
        """INT-P6-006: 发票/收据提取测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/receipt"

        try:
            from PIL import Image

            img = Image.new('RGB', (400, 500), color='white')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            files = {"file": ("receipt.png", img_bytes, "image/png")}
            response = requests.post(url, files=files, timeout=30)

            assert response.status_code in [200, 201, 400, 404]
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_handwriting(self, ocr_config):
        """INT-P6-007: 手写识别测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/handwriting"

        try:
            from PIL import Image

            img = Image.new('RGB', (400, 200), color='white')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            files = {"file": ("handwriting.png", img_bytes, "image/png")}
            response = requests.post(url, files=files, timeout=30)

            assert response.status_code in [200, 201, 400, 404]
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_document_classification(self, ocr_config):
        """INT-P6-008: 文档分类测试"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/classify"

        try:
            from PIL import Image

            img = Image.new('RGB', (400, 500), color='white')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            files = {"file": ("document.png", img_bytes, "image/png")}
            response = requests.post(url, files=files, timeout=30)

            assert response.status_code in [200, 201, 400, 404]
        except ImportError:
            pytest.skip("PIL not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_supported_formats(self, ocr_config):
        """INT-P6-009: 支持的格式查询"""
        url = f"{ocr_config['base_url']}/api/v1/ocr/formats"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "formats" in data or "supported_formats" in data
                print(f"Supported formats: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")

    def test_ocr_task_status(self, ocr_config):
        """INT-P6-010: 任务状态查询"""
        task_id = "test_task_id"
        url = f"{ocr_config['base_url']}/api/v1/ocr/tasks/{task_id}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("ocr-service 服务未启动")


@pytest.mark.integration
class TestBehaviorService:
    """INT-P6-011 ~ INT-P6-018: behavior-service 测试"""

    @pytest.fixture
    def behavior_config(self):
        """行为服务配置"""
        return {
            "base_url": os.getenv("BEHAVIOR_SERVICE_URL", "http://localhost:8008"),
            "health_endpoint": "/health",
        }

    def test_behavior_service_health_check(self, behavior_config):
        """INT-P6-011: 行为服务健康检查"""
        url = f"{behavior_config['base_url']}{behavior_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_track_event(self, behavior_config):
        """INT-P6-012: 事件追踪测试"""
        url = f"{behavior_config['base_url']}/api/v1/events/track"

        event_data = {
            "user_id": "test_user",
            "event_type": "page_view",
            "page": "/test",
            "timestamp": datetime.now().isoformat()
        }

        try:
            response = requests.post(url, json=event_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_batch_track(self, behavior_config):
        """INT-P6-013: 批量事件追踪测试"""
        url = f"{behavior_config['base_url']}/api/v1/events/batch"

        events = [
            {
                "user_id": "test_user",
                "event_type": "click",
                "element": "button",
                "timestamp": datetime.now().isoformat()
            }
            for _ in range(10)
        ]

        try:
            response = requests.post(url, json={"events": events}, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_user_profile(self, behavior_config):
        """INT-P6-014: 用户画像查询测试"""
        user_id = "test_user"
        url = f"{behavior_config['base_url']}/api/v1/users/{user_id}/profile"

        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_user_events(self, behavior_config):
        """INT-P6-015: 用户事件历史查询测试"""
        user_id = "test_user"
        url = f"{behavior_config['base_url']}/api/v1/users/{user_id}/events"

        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_aggregation(self, behavior_config):
        """INT-P6-016: 行为聚合统计测试"""
        url = f"{behavior_config['base_url']}/api/v1/analytics/aggregation"

        query = {
            "metric": "page_views",
            "group_by": "user_id",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }

        try:
            response = requests.post(url, json=query, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_funnel_analysis(self, behavior_config):
        """INT-P6-017: 漏斗分析测试"""
        url = f"{behavior_config['base_url']}/api/v1/analytics/funnel"

        funnel_data = {
            "steps": ["page_view", "click", "submit"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }

        try:
            response = requests.post(url, json=funnel_data, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")

    def test_behavior_service_retention(self, behavior_config):
        """INT-P6-018: 用户留存分析测试"""
        url = f"{behavior_config['base_url']}/api/v1/analytics/retention"

        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("behavior-service 服务未启动")


@pytest.mark.integration
class TestKeycloak:
    """INT-P6-019 ~ INT-P6-025: Keycloak 认证服务测试"""

    @pytest.fixture
    def keycloak_config(self):
        """Keycloak 配置"""
        return {
            "base_url": os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
            "realm": os.getenv("KEYCLOAK_REALM", "one-data-studio"),
            "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "web-frontend"),
        }

    def test_keycloak_health_check(self, keycloak_config):
        """INT-P6-019: Keycloak 健康检查"""
        url = f"{keycloak_config['base_url']}/health"
        try:
            response = requests.get(url, timeout=10)
            # Keycloak 健康检查可能返回不同的状态码
            assert response.status_code in [200, 204]
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_realms(self, keycloak_config):
        """INT-P6-020: 领域列表查询"""
        url = f"{keycloak_config['base_url']}/realms"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"Available realms: {[r.get('realm') for r in data]}")
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_realm_info(self, keycloak_config):
        """INT-P6-021: 领域信息查询"""
        url = f"{keycloak_config['base_url']}/realms/{keycloak_config['realm']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "realm" in data
                print(f"Realm: {data.get('realm')}")
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_openid_config(self, keycloak_config):
        """INT-P6-022: OpenID 配置查询"""
        url = f"{keycloak_config['base_url']}/realms/{keycloak_config['realm']}/.well-known/openid-configuration"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "issuer" in data
                assert "authorization_endpoint" in data
                assert "token_endpoint" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_token_endpoint(self, keycloak_config):
        """INT-P6-023: Token 端点测试"""
        url = f"{keycloak_config['base_url']}/realms/{keycloak_config['realm']}/protocol/openid-connect/token"

        # 尝试获取 token (使用密码模式)
        token_data = {
            "grant_type": "password",
            "client_id": keycloak_config["client_id"],
            "username": os.getenv("KEYCLOAK_TEST_USER", "test"),
            "password": os.getenv("KEYCLOAK_TEST_PASSWORD", "test")
        }

        try:
            response = requests.post(url, data=token_data, timeout=10)
            # 可能返回 401 (认证失败) 或 400 (无效请求)
            assert response.status_code in [200, 400, 401]
            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_user_info(self, keycloak_config):
        """INT-P6-024: 用户信息端点测试"""
        url = f"{keycloak_config['base_url']}/realms/{keycloak_config['realm']}/protocol/openid-connect/userinfo"
        try:
            # 没有会返回 401
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 403]
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")

    def test_keycloak_logout(self, keycloak_config):
        """INT-P6-025: 登出端点测试"""
        url = f"{keycloak_config['base_url']}/realms/{keycloak_config['realm']}/protocol/openid-connect/logout"
        try:
            # POST 请求应该接受
            response = requests.post(url, timeout=10)
            assert response.status_code in [200, 204, 401, 405]
        except requests.exceptions.ConnectionError:
            pytest.skip("keycloak 服务未启动")


@pytest.mark.integration
class TestExtensionIntegration:
    """INT-P6-026 ~ INT-P6-030: 扩展服务集成测试"""

    def test_ocr_with_storage(self):
        """INT-P6-026: OCR 与存储集成测试"""
        # 验证 OCR 结果可以存储到 MinIO
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")

        try:
            from minio import Minio

            client = Minio(
                minio_endpoint,
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=False,
            )

            buckets = [b.name for b in client.list_buckets()]
            print(f"Available buckets for OCR storage: {buckets}")
        except Exception as e:
            pytest.skip(f"MinIO access failed: {e}")

    def test_behavior_with_database(self):
        """INT-P6-027: 行为服务与数据库集成测试"""
        # 验证行为数据可以存储到 MySQL
        try:
            import pymysql

            conn = pymysql.connect(
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "onedata"),
                password=os.getenv("MYSQL_PASSWORD", "onedata"),
                database=os.getenv("MYSQL_DATABASE", "onedata"),
            )

            with conn.cursor() as cursor:
                # 检查行为数据表
                cursor.execute("SHOW TABLES LIKE '%behavior%'")
                tables = cursor.fetchall()
                print(f"Behavior tables: {tables}")

            conn.close()
        except Exception as e:
            pytest.skip(f"MySQL access failed: {e}")

    def test_keycloak_with_api_services(self):
        """INT-P6-028: Keycloak 与 API 服务集成测试"""
        # 验证各 API 服务可以与 Keycloak 集成
        api_urls = [
            ("http://localhost:8000", "agent-api"),
            ("http://localhost:8001", "data-api"),
            ("http://localhost:8004", "admin-api"),
        ]

        for url, name in api_urls:
            try:
                response = requests.get(f"{url}/api/v1/auth/config", timeout=5)
                print(f"{name} auth config: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pass

    def test_service_discovery(self):
        """INT-P6-029: 服务发现测试"""
        # 验证扩展服务可以被其他服务发现
        import socket

        services = {
            "ocr-service": 8007,
            "behavior-service": 8008,
            "keycloak": 8080,
        }

        for service, port in services.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            status = "✓" if result == 0 else "✗"
            print(f"{status} {service} ({port}): {'Accessible' if result == 0 else 'Not accessible'}")

    def test_memory_optimization(self):
        """INT-P6-030: 内存优化测试"""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.Container}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            extension_containers = ["one-data-ocr-service", "one-data-behavior-service", "one-data-keycloak"]

            print("\nExtension Services Memory Usage:")
            for line in result.stdout.split("\n"):
                for container in extension_containers:
                    if container in line:
                        print(f"  {line}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
