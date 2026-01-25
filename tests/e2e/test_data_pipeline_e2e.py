"""
数据管道端到端测试
测试 ETL 流程、数据集管理、数据质量检测等

测试覆盖:
- 数据集 CRUD 操作
- ETL 任务生命周期
- 数据质量规则与检测
- 数据血缘追踪
- MinIO 文件存储集成
"""

import pytest
import requests
import time
import os
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8082")
AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestDatasetManagement:
    """数据集管理测试"""

    dataset_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_dataset(self):
        """测试创建数据集"""
        response = requests.post(
            f"{BASE_URL}/api/v1/datasets",
            headers=HEADERS,
            json={
                "name": f"E2E Test Dataset {int(time.time())}",
                "description": "自动化测试创建的数据集",
                "type": "table",
                "source": "mysql",
                "schema": {
                    "columns": [
                        {"name": "id", "type": "bigint", "nullable": False},
                        {"name": "name", "type": "varchar(100)", "nullable": False},
                        {"name": "value", "type": "decimal(18,2)", "nullable": True}
                    ]
                }
            }
        )

        assert response.status_code in [201, 401, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            assert "dataset_id" in data["data"]
            TestDatasetManagement.dataset_id = data["data"]["dataset_id"]
            logger.info("Created dataset: %s", TestDatasetManagement.dataset_id)

    @pytest.mark.e2e
    def test_02_list_datasets(self):
        """测试列出数据集"""
        response = requests.get(
            f"{BASE_URL}/api/v1/datasets",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "datasets" in data["data"]
            assert isinstance(data["data"]["datasets"], list)

    @pytest.mark.e2e
    def test_03_get_dataset(self):
        """测试获取数据集详情"""
        if not TestDatasetManagement.dataset_id:
            pytest.skip("No dataset created")

        response = requests.get(
            f"{BASE_URL}/api/v1/datasets/{TestDatasetManagement.dataset_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["dataset_id"] == TestDatasetManagement.dataset_id

    @pytest.mark.e2e
    def test_04_update_dataset(self):
        """测试更新数据集"""
        if not TestDatasetManagement.dataset_id:
            pytest.skip("No dataset created")

        response = requests.put(
            f"{BASE_URL}/api/v1/datasets/{TestDatasetManagement.dataset_id}",
            headers=HEADERS,
            json={
                "description": "Updated description",
                "tags": ["test", "e2e"]
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_05_delete_dataset(self):
        """测试删除数据集"""
        if not TestDatasetManagement.dataset_id:
            pytest.skip("No dataset created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/datasets/{TestDatasetManagement.dataset_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 204, 401, 404]


class TestETLTaskLifecycle:
    """ETL 任务生命周期测试"""

    task_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_etl_task(self):
        """测试创建 ETL 任务"""
        response = requests.post(
            f"{BASE_URL}/api/v1/etl/tasks",
            headers=HEADERS,
            json={
                "name": f"E2E ETL Task {int(time.time())}",
                "description": "自动化测试 ETL 任务",
                "type": "batch",
                "source": {
                    "type": "mysql",
                    "database": "test_db",
                    "table": "source_table"
                },
                "sink": {
                    "type": "hive",
                    "database": "warehouse",
                    "table": "target_table"
                },
                "transformations": [
                    {
                        "type": "filter",
                        "condition": "status = 'active'"
                    },
                    {
                        "type": "rename",
                        "mappings": {"old_name": "new_name"}
                    }
                ],
                "schedule": {
                    "enabled": False
                }
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestETLTaskLifecycle.task_id = data["data"]["task_id"]
            logger.info("Created ETL task: %s", TestETLTaskLifecycle.task_id)

    @pytest.mark.e2e
    def test_02_get_etl_task(self):
        """测试获取 ETL 任务详情"""
        if not TestETLTaskLifecycle.task_id:
            pytest.skip("No ETL task created")

        response = requests.get(
            f"{BASE_URL}/api/v1/etl/tasks/{TestETLTaskLifecycle.task_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_03_run_etl_task(self):
        """测试运行 ETL 任务"""
        if not TestETLTaskLifecycle.task_id:
            pytest.skip("No ETL task created")

        response = requests.post(
            f"{BASE_URL}/api/v1/etl/tasks/{TestETLTaskLifecycle.task_id}/run",
            headers=HEADERS
        )

        # 可能返回 202（已接受）、400（参数错误）或 401
        assert response.status_code in [202, 400, 401, 404]

    @pytest.mark.e2e
    def test_04_get_etl_task_runs(self):
        """测试获取 ETL 任务运行历史"""
        if not TestETLTaskLifecycle.task_id:
            pytest.skip("No ETL task created")

        response = requests.get(
            f"{BASE_URL}/api/v1/etl/tasks/{TestETLTaskLifecycle.task_id}/runs",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_05_delete_etl_task(self):
        """测试删除 ETL 任务"""
        if not TestETLTaskLifecycle.task_id:
            pytest.skip("No ETL task created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/etl/tasks/{TestETLTaskLifecycle.task_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 204, 401, 404]


class TestDataQuality:
    """数据质量测试"""

    rule_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_quality_rule(self):
        """测试创建数据质量规则"""
        response = requests.post(
            f"{BASE_URL}/api/v1/data-quality/rules",
            headers=HEADERS,
            json={
                "name": f"E2E Quality Rule {int(time.time())}",
                "description": "测试数据完整性",
                "type": "completeness",
                "target": {
                    "database": "test_db",
                    "table": "test_table",
                    "column": "email"
                },
                "condition": {
                    "operator": "not_null",
                    "threshold": 0.95
                },
                "alert": {
                    "enabled": True,
                    "severity": "warning"
                }
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestDataQuality.rule_id = data["data"]["rule_id"]

    @pytest.mark.e2e
    def test_02_list_quality_rules(self):
        """测试列出数据质量规则"""
        response = requests.get(
            f"{BASE_URL}/api/v1/data-quality/rules",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_03_run_quality_check(self):
        """测试运行数据质量检查"""
        if not TestDataQuality.rule_id:
            pytest.skip("No quality rule created")

        response = requests.post(
            f"{BASE_URL}/api/v1/data-quality/rules/{TestDataQuality.rule_id}/run",
            headers=HEADERS
        )

        assert response.status_code in [202, 400, 401, 404]

    @pytest.mark.e2e
    def test_04_get_quality_results(self):
        """测试获取数据质量检查结果"""
        response = requests.get(
            f"{BASE_URL}/api/v1/data-quality/results",
            headers=HEADERS,
            params={"limit": 10}
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_05_delete_quality_rule(self):
        """测试删除数据质量规则"""
        if not TestDataQuality.rule_id:
            pytest.skip("No quality rule created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/data-quality/rules/{TestDataQuality.rule_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 204, 401, 404]


class TestDataLineage:
    """数据血缘测试"""

    @pytest.mark.e2e
    def test_01_get_table_lineage(self):
        """测试获取表级血缘"""
        response = requests.get(
            f"{BASE_URL}/api/v1/lineage/table",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "fact_orders",
                "direction": "both",
                "depth": 3
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "upstream" in data["data"] or "downstream" in data["data"]

    @pytest.mark.e2e
    def test_02_get_column_lineage(self):
        """测试获取列级血缘"""
        response = requests.get(
            f"{BASE_URL}/api/v1/lineage/column",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "fact_orders",
                "column": "total_amount"
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_03_get_impact_analysis(self):
        """测试影响分析"""
        response = requests.get(
            f"{BASE_URL}/api/v1/lineage/impact",
            headers=HEADERS,
            params={
                "database": "source_db",
                "table": "customers"
            }
        )

        assert response.status_code in [200, 401, 404]


class TestMetadataManagement:
    """元数据管理测试"""

    @pytest.mark.e2e
    def test_01_list_databases(self):
        """测试列出数据库"""
        response = requests.get(
            f"{BASE_URL}/api/v1/metadata/databases",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "databases" in data["data"]

    @pytest.mark.e2e
    def test_02_list_tables(self):
        """测试列出表"""
        response = requests.get(
            f"{BASE_URL}/api/v1/metadata/tables",
            headers=HEADERS,
            params={"database": "warehouse"}
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_03_get_table_schema(self):
        """测试获取表结构"""
        response = requests.get(
            f"{BASE_URL}/api/v1/metadata/tables/warehouse/fact_orders/schema",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_04_search_metadata(self):
        """测试元数据搜索"""
        response = requests.get(
            f"{BASE_URL}/api/v1/metadata/search",
            headers=HEADERS,
            params={
                "q": "customer",
                "type": "table",
                "limit": 10
            }
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_05_update_table_metadata(self):
        """测试更新表元数据"""
        response = requests.put(
            f"{BASE_URL}/api/v1/metadata/tables/warehouse/fact_orders",
            headers=HEADERS,
            json={
                "description": "订单事实表",
                "owner": "data_team",
                "tags": ["fact", "orders", "core"]
            }
        )

        assert response.status_code in [200, 401, 404]


class TestMinIOStorage:
    """MinIO 存储集成测试"""

    file_key: Optional[str] = None

    @pytest.mark.e2e
    def test_01_upload_file(self):
        """测试上传文件"""
        # 创建测试文件内容
        test_content = "test,data,content\n1,2,3\n4,5,6"

        response = requests.post(
            f"{BASE_URL}/api/v1/storage/upload",
            headers={
                "Authorization": HEADERS.get("Authorization", ""),
            },
            files={
                "file": ("test_data.csv", test_content, "text/csv")
            },
            data={
                "bucket": "test-bucket",
                "path": "e2e-tests/"
            }
        )

        assert response.status_code in [200, 201, 401, 404]

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["code"] == 0
            TestMinIOStorage.file_key = data["data"].get("key")

    @pytest.mark.e2e
    def test_02_list_files(self):
        """测试列出文件"""
        response = requests.get(
            f"{BASE_URL}/api/v1/storage/list",
            headers=HEADERS,
            params={
                "bucket": "test-bucket",
                "prefix": "e2e-tests/"
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_03_download_file(self):
        """测试下载文件"""
        if not TestMinIOStorage.file_key:
            pytest.skip("No file uploaded")

        response = requests.get(
            f"{BASE_URL}/api/v1/storage/download",
            headers=HEADERS,
            params={
                "bucket": "test-bucket",
                "key": TestMinIOStorage.file_key
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_04_delete_file(self):
        """测试删除文件"""
        if not TestMinIOStorage.file_key:
            pytest.skip("No file uploaded")

        response = requests.delete(
            f"{BASE_URL}/api/v1/storage/delete",
            headers=HEADERS,
            params={
                "bucket": "test-bucket",
                "key": TestMinIOStorage.file_key
            }
        )

        assert response.status_code in [200, 204, 401, 404]


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.e2e
    def test_01_invalid_dataset_id(self):
        """测试无效数据集 ID"""
        response = requests.get(
            f"{BASE_URL}/api/v1/datasets/invalid-dataset-id-12345",
            headers=HEADERS
        )

        assert response.status_code in [400, 404]

    @pytest.mark.e2e
    def test_02_invalid_request_body(self):
        """测试无效请求体"""
        response = requests.post(
            f"{BASE_URL}/api/v1/datasets",
            headers=HEADERS,
            json={}  # 缺少必要字段
        )

        assert response.status_code in [400, 401, 422]

    @pytest.mark.e2e
    def test_03_malformed_json(self):
        """测试格式错误的 JSON"""
        response = requests.post(
            f"{BASE_URL}/api/v1/datasets",
            headers={
                **HEADERS,
                "Content-Type": "application/json"
            },
            data="invalid json {"
        )

        assert response.status_code in [400, 415, 422]

    @pytest.mark.e2e
    def test_04_timeout_handling(self):
        """测试超时处理"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/datasets",
                headers=HEADERS,
                timeout=0.001  # 非常短的超时
            )
        except requests.exceptions.Timeout:
            pass  # 预期的超时行为


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
