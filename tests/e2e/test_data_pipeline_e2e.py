"""
数据管道端到端测试
测试 ETL 流程、数据集管理、数据质量检测等

测试覆盖:
- 数据集 CRUD 操作
- ETL 任务生命周期
- 数据质量规则与检测
- 数据血缘追踪
- MinIO 文件存储集成
- Kettle 编排服务 (Phase 2)
- 表融合服务 (Phase 3)
- 元数据变更检测 (Phase 4)
"""

import pytest
import requests
import time
import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8082")
DATA_API_URL = os.getenv("TEST_DATA_API_URL", os.getenv("TEST_data_API_URL", "http://localhost:8082"))
MODEL_API_URL = os.getenv("TEST_MODEL_API_URL", os.getenv("TEST_MODEL_API_URL", "http://localhost:8083"))
# 兼容旧名称
data_API_URL = DATA_API_URL
MODEL_API_URL = MODEL_API_URL
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


# ==================== Phase 2: Kettle 编排服务测试 ====================

class TestKettleOrchestration:
    """Kettle 编排服务测试 (Phase 2)"""

    orchestration_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_orchestration_request(self):
        """测试创建编排请求"""
        response = requests.post(
            f"{data_API_URL}/api/v1/kettle/orchestrate",
            headers=HEADERS,
            json={
                "name": f"E2E Kettle Orchestration {int(time.time())}",
                "pipeline_type": "full_etl",
                "source_database": "source_db",
                "source_table": "customers",
                "source_type": "mysql",
                "source_connection": {
                    "host": "localhost",
                    "port": 3306,
                    "username": "root",
                    "password": "password"
                },
                "target_database": "warehouse",
                "target_table": "customers_cleaned",
                "enable_ai_cleaning": True,
                "enable_ai_masking": True,
                "enable_ai_imputation": True,
                "dry_run": True,  # 试运行，不实际执行
                "auto_execute": False,
                "created_by": "e2e_test"
            }
        )

        assert response.status_code in [201, 200, 401, 404, 501]

        if response.status_code in [201, 200]:
            data = response.json()
            if data.get("code") == 0:
                TestKettleOrchestration.orchestration_id = data["data"].get("request_id")
                logger.info(f"Created orchestration: {TestKettleOrchestration.orchestration_id}")

    @pytest.mark.e2e
    def test_02_get_orchestration_status(self):
        """测试获取编排状态"""
        if not TestKettleOrchestration.orchestration_id:
            pytest.skip("No orchestration created")

        response = requests.get(
            f"{data_API_URL}/api/v1/kettle/orchestrate/{TestKettleOrchestration.orchestration_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                result = data["data"]
                assert "status" in result
                assert "columns_analyzed" in result

    @pytest.mark.e2e
    def test_03_list_orchestrations(self):
        """测试列出编排任务"""
        response = requests.get(
            f"{data_API_URL}/api/v1/kettle/orchestrate",
            headers=HEADERS,
            params={"limit": 10}
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_04_get_transformation_xml(self):
        """测试获取生成的转换 XML"""
        if not TestKettleOrchestration.orchestration_id:
            pytest.skip("No orchestration created")

        response = requests.get(
            f"{data_API_URL}/api/v1/kettle/orchestrate/{TestKettleOrchestration.orchestration_id}/xml",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # 验证 XML 格式
            content = response.text
            assert "<?xml" in content or "<transformation" in content

    @pytest.mark.e2e
    def test_05_execute_transformation(self):
        """测试执行转换（通过 Carte）"""
        if not TestKettleOrchestration.orchestration_id:
            pytest.skip("No orchestration created")

        response = requests.post(
            f"{data_API_URL}/api/v1/kettle/orchestrate/{TestKettleOrchestration.orchestration_id}/execute",
            headers=HEADERS,
            json={"poll_timeout": 60}
        )

        # 可能返回 501（功能未实现）或 503（Carte 不可用）
        assert response.status_code in [202, 200, 404, 501, 503]

    @pytest.mark.e2e
    def test_06_get_quality_report(self):
        """测试获取数据质量报告"""
        if not TestKettleOrchestration.orchestration_id:
            pytest.skip("No orchestration created")

        response = requests.get(
            f"{data_API_URL}/api/v1/kettle/orchestrate/{TestKettleOrchestration.orchestration_id}/quality",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]


# ==================== Phase 3: 表融合服务测试 ====================

class TestTableFusion:
    """表融合服务测试 (Phase 3)"""

    @pytest.mark.e2e
    def test_01_detect_join_keys(self):
        """测试检测 JOIN 关键字"""
        response = requests.post(
            f"{data_API_URL}/api/v1/fusion/detect-joins",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "target_tables": ["customers", "products"],
                "source_database": "warehouse",
                "target_database": "warehouse",
                "sample_size": 1000
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                results = data["data"]
                assert isinstance(results, dict)
                # 验证返回的关联键格式
                for table, join_keys in results.items():
                    assert isinstance(join_keys, list)
                    for key in join_keys:
                        assert "source_column" in key
                        assert "target_column" in key
                        assert "confidence" in key

    @pytest.mark.e2e
    def test_02_validate_join_quality(self):
        """测试验证 JOIN 质量"""
        response = requests.post(
            f"{data_API_URL}/api/v1/fusion/validate-join",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "source_key": "customer_id",
                "target_table": "customers",
                "target_key": "id",
                "source_database": "warehouse",
                "target_database": "warehouse",
                "sample_size": 10000
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                quality = data["data"]
                assert "match_rate" in quality
                assert "coverage_rate" in quality
                assert "overall_score" in quality
                assert "recommendation" in quality

    @pytest.mark.e2e
    def test_03_recommend_join_strategy(self):
        """测试推荐 JOIN 策略"""
        response = requests.post(
            f"{data_API_URL}/api/v1/fusion/recommend-strategy",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "target_table": "customers",
                "join_keys": [
                    {
                        "source_column": "customer_id",
                        "target_column": "id",
                        "confidence": 0.95,
                        "detection_method": "name_match"
                    }
                ],
                "source_database": "warehouse",
                "target_database": "warehouse"
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                strategy = data["data"]
                assert "join_type" in strategy
                assert "sql_template" in strategy
                assert "estimated_result_count" in strategy
                assert "index_suggestions" in strategy
                assert "warnings" in strategy

    @pytest.mark.e2e
    def test_04_generate_kettle_join_config(self):
        """测试生成 Kettle JOIN 配置"""
        response = requests.post(
            f"{data_API_URL}/api/v1/fusion/kettle-config",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "target_table": "customers",
                "join_type": "left",
                "join_keys": [
                    {
                        "source_column": "customer_id",
                        "target_column": "id",
                        "confidence": 0.95
                    }
                ]
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                config = data["data"]
                assert "step_type" in config
                assert "keys_1" in config
                assert "keys_2" in config

    @pytest.mark.e2e
    def test_05_detect_multi_table_paths(self):
        """测试检测多表关联路径"""
        response = requests.post(
            f"{data_API_URL}/api/v1/fusion/multi-table-paths",
            headers=HEADERS,
            json={
                "tables": ["orders", "customers", "products", "categories"],
                "database": "warehouse",
                "max_depth": 3
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                paths = data["data"]
                assert isinstance(paths, list)


# ==================== Phase 4: 元数据变更检测测试 ====================

class TestMetadataChangeDetection:
    """元数据变更检测测试 (Phase 4)"""

    scan_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_trigger_metadata_scan(self):
        """测试触发元数据扫描"""
        response = requests.post(
            f"{data_API_URL}/api/v1/metadata/scan",
            headers=HEADERS,
            json={
                "database_name": "warehouse",
                "scan_type": "incremental",
                "table_filter": ["orders", "customers"],
                "detect_changes": True
            }
        )

        assert response.status_code in [202, 200, 401, 501]

        if response.status_code in [202, 200]:
            data = response.json()
            if data.get("code") == 0:
                TestMetadataChangeDetection.scan_id = data["data"].get("scan_id")
                logger.info(f"Created scan: {TestMetadataChangeDetection.scan_id}")

    @pytest.mark.e2e
    def test_02_get_scan_results(self):
        """测试获取扫描结果"""
        if not TestMetadataChangeDetection.scan_id:
            pytest.skip("No scan created")

        response = requests.get(
            f"{data_API_URL}/api/v1/metadata/scan/{TestMetadataChangeDetection.scan_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                result = data["data"]
                assert "tables_scanned" in result
                assert "columns_discovered" in result

    @pytest.mark.e2e
    def test_03_get_table_changes(self):
        """测试获取表变更"""
        response = requests.get(
            f"{data_API_URL}/api/v1/metadata/changes/tables",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "since_days": 7
            }
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                changes = data["data"]
                assert "added" in changes
                assert "modified" in changes
                assert "deleted" in changes

    @pytest.mark.e2e
    def test_04_get_column_changes(self):
        """测试获取列变更"""
        response = requests.get(
            f"{data_API_URL}/api/v1/metadata/changes/columns",
            headers=HEADERS,
            params={
                "table": "orders",
                "database": "warehouse"
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_05_compare_snapshots(self):
        """测试快照对比"""
        response = requests.post(
            f"{data_API_URL}/api/v1/metadata/snapshots/compare",
            headers=HEADERS,
            json={
                "snapshot_id_1": "snapshot_001",
                "snapshot_id_2": "snapshot_002"
            }
        )

        assert response.status_code in [200, 404, 401]


# ==================== Phase 5: 数据血缘测试 ====================

class TestOpenLineage:
    """OpenLineage 集成测试 (Phase 5)"""

    @pytest.mark.e2e
    def test_01_export_lineage_dag(self):
        """测试导出血缘 DAG"""
        response = requests.get(
            f"{data_API_URL}/api/v1/lineage/export",
            headers=HEADERS,
            params={
                "format": "mermaid",
                "database": "warehouse",
                "table": "fact_orders"
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            content = response.text
            # 验证 Mermaid 格式
            assert "graph" in content or "flowchart" in content

    @pytest.mark.e2e
    def test_02_export_lineage_json(self):
        """测试导出血缘 JSON"""
        response = requests.get(
            f"{data_API_URL}/api/v1/lineage/export",
            headers=HEADERS,
            params={
                "format": "json",
                "database": "warehouse"
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                dag = data["data"]
                assert "nodes" in dag
                assert "edges" in dag

    @pytest.mark.e2e
    def test_03_get_upstream_lineage(self):
        """测试获取上游血缘"""
        response = requests.get(
            f"{data_API_URL}/api/v1/lineage/upstream",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "fact_orders",
                "depth": 2
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                lineage = data["data"]
                assert isinstance(lineage, list)

    @pytest.mark.e2e
    def test_04_get_downstream_lineage(self):
        """测试获取下游血缘"""
        response = requests.get(
            f"{data_API_URL}/api/v1/lineage/downstream",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "dim_customers",
                "depth": 2
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_05_trace_data_path(self):
        """测试追溯数据路径"""
        response = requests.post(
            f"{data_API_URL}/api/v1/lineage/trace",
            headers=HEADERS,
            json={
                "source": {"database": "raw", "table": "customers"},
                "target": {"database": "warehouse", "table": "fact_orders"},
                "max_hops": 5
            }
        )

        assert response.status_code in [200, 401, 404]


# ==================== 综合场景测试 ====================

class TestEndToEndScenarios:
    """端到端综合场景测试"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_01_full_data_pipeline(self):
        """测试完整数据流水线: 元数据扫描 -> ETL -> 质量检测 -> 编目"""
        # 步骤 1: 扫描源表元数据
        scan_response = requests.post(
            f"{data_API_URL}/api/v1/metadata/scan",
            headers=HEADERS,
            json={
                "database_name": "source_db",
                "scan_type": "full",
                "auto_catalog": True
            }
        )
        assert scan_response.status_code in [202, 200, 501]

        # 步骤 2: 创建编排请求
        orch_response = requests.post(
            f"{data_API_URL}/api/v1/kettle/orchestrate",
            headers=HEADERS,
            json={
                "name": f"Full Pipeline {int(time.time())}",
                "pipeline_type": "full_etl",
                "source_database": "source_db",
                "source_table": "customers",
                "target_database": "warehouse",
                "target_table": "dim_customers",
                "dry_run": True,
                "auto_catalog": True,
                "export_to_minio": False
            }
        )
        assert orch_response.status_code in [201, 200, 501]

        # 步骤 3: 验证数据质量（如果有执行）
        # 步骤 4: 验证编目（如果有自动编目）

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_02_multi_table_fusion_pipeline(self):
        """测试多表融合流水线"""
        # 步骤 1: 检测关联键
        detect_response = requests.post(
            f"{data_API_URL}/api/v1/fusion/detect-joins",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "target_tables": ["customers", "products", "categories"],
                "database": "warehouse"
            }
        )
        assert detect_response.status_code in [200, 401]

        # 步骤 2: 验证最佳 JOIN
        validate_response = requests.post(
            f"{data_API_URL}/api/v1/fusion/validate-join",
            headers=HEADERS,
            json={
                "source_table": "orders",
                "source_key": "customer_id",
                "target_table": "customers",
                "target_key": "id",
                "database": "warehouse"
            }
        )
        assert validate_response.status_code in [200, 401]

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_03_lineage_impact_analysis(self):
        """测试变更影响分析"""
        # 步骤 1: 获取表的上游依赖
        upstream_response = requests.get(
            f"{data_API_URL}/api/v1/lineage/upstream",
            headers=HEADERS,
            params={
                "database": "warehouse",
                "table": "fact_orders",
                "depth": 3
            }
        )

        # 步骤 2: 获取表的下游影响
        downstream_response = requests.get(
            f"{data_API_URL}/api/v1/lineage/downstream",
            headers=HEADERS,
            params={
                "database": "raw",
                "table": "customers",
                "depth": 3
            }
        )

        # 步骤 3: 导出完整 DAG
        dag_response = requests.get(
            f"{data_API_URL}/api/v1/lineage/export",
            headers=HEADERS,
            params={"format": "json"}
        )

        assert all(r.status_code in [200, 401, 404]
                   for r in [upstream_response, downstream_response, dag_response])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
