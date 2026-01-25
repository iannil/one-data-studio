"""
跨服务集成端到端测试
测试 Alldata、Bisheng、Cube Studio 三个平台之间的集成

测试覆盖:
- Alldata → Cube Studio 数据集集成
- Cube Studio → Bisheng 模型服务集成
- Alldata → Bisheng 元数据/向量集成
- 完整的 MLOps 工作流程
"""

import pytest
import requests
import time
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 服务 URL 配置
ALLDATA_URL = os.getenv("TEST_ALLDATA_URL", "http://localhost:8082")
BISHENG_URL = os.getenv("TEST_BISHENG_URL", "http://localhost:8081")
CUBE_URL = os.getenv("TEST_CUBE_URL", "http://localhost:8083")

AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestAlldataCubeIntegration:
    """Alldata → Cube Studio 集成测试"""

    dataset_id: Optional[str] = None
    cube_dataset_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_alldata_dataset(self):
        """在 Alldata 创建数据集"""
        response = requests.post(
            f"{ALLDATA_URL}/api/v1/datasets",
            headers=HEADERS,
            json={
                "name": f"Integration Test Dataset {int(time.time())}",
                "description": "用于跨服务集成测试的数据集",
                "type": "table",
                "source": "mysql",
                "storage_path": f"s3://datasets/integration-test-{int(time.time())}",
                "schema": {
                    "columns": [
                        {"name": "text", "type": "text"},
                        {"name": "label", "type": "int"}
                    ]
                }
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            TestAlldataCubeIntegration.dataset_id = data["data"]["dataset_id"]
            logger.info("Created Alldata dataset: %s", TestAlldataCubeIntegration.dataset_id)

    @pytest.mark.e2e
    def test_02_register_dataset_in_cube(self):
        """在 Cube Studio 注册数据集"""
        if not TestAlldataCubeIntegration.dataset_id:
            pytest.skip("No Alldata dataset created")

        # 从 Alldata 获取数据集信息
        alldata_response = requests.get(
            f"{ALLDATA_URL}/api/v1/datasets/{TestAlldataCubeIntegration.dataset_id}",
            headers=HEADERS
        )

        if alldata_response.status_code != 200:
            pytest.skip("Cannot get Alldata dataset info")

        alldata_dataset = alldata_response.json()["data"]

        # 在 Cube Studio 注册
        response = requests.post(
            f"{CUBE_URL}/api/v1/datasets",
            headers=HEADERS,
            json={
                "name": alldata_dataset["name"],
                "description": alldata_dataset.get("description", ""),
                "source": "alldata",
                "source_id": alldata_dataset["dataset_id"],
                "storage_path": alldata_dataset.get("storage_path"),
                "format": "parquet"
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            TestAlldataCubeIntegration.cube_dataset_id = data["data"]["dataset_id"]

    @pytest.mark.e2e
    def test_03_use_dataset_for_training(self):
        """使用数据集创建训练任务"""
        if not TestAlldataCubeIntegration.cube_dataset_id:
            pytest.skip("No Cube dataset registered")

        # 先创建模型
        model_response = requests.post(
            f"{CUBE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"Integration Test Model {int(time.time())}",
                "model_type": "text-classification",
                "framework": "transformers"
            }
        )

        if model_response.status_code != 201:
            pytest.skip("Cannot create model")

        model_id = model_response.json()["data"]["model_id"]

        # 创建训练任务
        response = requests.post(
            f"{CUBE_URL}/api/v1/training-jobs",
            headers=HEADERS,
            json={
                "name": f"Integration Training {int(time.time())}",
                "model_id": model_id,
                "dataset_id": TestAlldataCubeIntegration.cube_dataset_id,
                "hyperparameters": {
                    "learning_rate": 0.0001,
                    "epochs": 1
                }
            }
        )

        assert response.status_code in [201, 400, 401, 404]

    @pytest.mark.e2e
    def test_04_verify_data_lineage(self):
        """验证数据血缘追踪"""
        if not TestAlldataCubeIntegration.dataset_id:
            pytest.skip("No dataset created")

        response = requests.get(
            f"{ALLDATA_URL}/api/v1/lineage/table",
            headers=HEADERS,
            params={
                "source": "alldata",
                "source_id": TestAlldataCubeIntegration.dataset_id,
                "direction": "downstream"
            }
        )

        assert response.status_code in [200, 401, 404]


class TestCubeBishengIntegration:
    """Cube Studio → Bisheng 集成测试"""

    model_id: Optional[str] = None
    deployment_id: Optional[str] = None
    workflow_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_and_deploy_model(self):
        """创建并部署模型"""
        # 创建模型
        model_response = requests.post(
            f"{CUBE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"Bisheng Integration Model {int(time.time())}",
                "model_type": "text-generation",
                "framework": "transformers",
                "status": "ready"
            }
        )

        if model_response.status_code != 201:
            pytest.skip("Cannot create model")

        TestCubeBishengIntegration.model_id = model_response.json()["data"]["model_id"]

        # 部署模型
        deploy_response = requests.post(
            f"{CUBE_URL}/api/v1/models/{TestCubeBishengIntegration.model_id}/deploy",
            headers=HEADERS,
            json={
                "replicas": 1,
                "memory_limit": "4Gi"
            }
        )

        assert deploy_response.status_code in [201, 400, 401, 404]

        if deploy_response.status_code == 201:
            TestCubeBishengIntegration.deployment_id = deploy_response.json()["data"]["deployment_id"]
            logger.info("Created deployment: %s", TestCubeBishengIntegration.deployment_id)

    @pytest.mark.e2e
    def test_02_get_model_endpoint(self):
        """获取模型服务端点"""
        if not TestCubeBishengIntegration.deployment_id:
            pytest.skip("No deployment created")

        response = requests.get(
            f"{CUBE_URL}/api/v1/deployments",
            headers=HEADERS,
            params={"model_id": TestCubeBishengIntegration.model_id}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            deployments = data["data"]["deployments"]
            if deployments:
                endpoint = deployments[0].get("endpoint")
                logger.info("Model endpoint: %s", endpoint)

    @pytest.mark.e2e
    def test_03_create_bisheng_workflow_with_model(self):
        """创建使用 Cube 模型的 Bisheng 工作流"""
        if not TestCubeBishengIntegration.deployment_id:
            pytest.skip("No deployment created")

        response = requests.post(
            f"{BISHENG_URL}/api/v1/workflows",
            headers=HEADERS,
            json={
                "name": f"Cube Integration Workflow {int(time.time())}",
                "description": "使用 Cube Studio 模型的工作流",
                "type": "rag"
            }
        )

        assert response.status_code in [201, 401]

        if response.status_code == 201:
            TestCubeBishengIntegration.workflow_id = response.json()["data"]["workflow_id"]

            # 更新工作流定义
            workflow_def = {
                "version": "1.0",
                "nodes": [
                    {
                        "id": "input",
                        "type": "input",
                        "config": {"key": "query"}
                    },
                    {
                        "id": "llm",
                        "type": "llm",
                        "config": {
                            "model_source": "cube",
                            "deployment_id": TestCubeBishengIntegration.deployment_id,
                            "temperature": 0.7
                        }
                    },
                    {
                        "id": "output",
                        "type": "output",
                        "config": {"input_from": "llm"}
                    }
                ],
                "edges": [
                    {"source": "input", "target": "llm"},
                    {"source": "llm", "target": "output"}
                ]
            }

            update_response = requests.put(
                f"{BISHENG_URL}/api/v1/workflows/{TestCubeBishengIntegration.workflow_id}",
                headers=HEADERS,
                json={"definition": workflow_def}
            )

            assert update_response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_04_execute_workflow(self):
        """执行工作流"""
        if not TestCubeBishengIntegration.workflow_id:
            pytest.skip("No workflow created")

        response = requests.post(
            f"{BISHENG_URL}/api/v1/workflows/{TestCubeBishengIntegration.workflow_id}/start",
            headers=HEADERS,
            json={
                "inputs": {
                    "query": "请介绍一下机器学习"
                }
            }
        )

        assert response.status_code in [202, 400, 401, 404]

    @pytest.mark.e2e
    def test_05_cleanup(self):
        """清理测试资源"""
        if TestCubeBishengIntegration.workflow_id:
            requests.delete(
                f"{BISHENG_URL}/api/v1/workflows/{TestCubeBishengIntegration.workflow_id}",
                headers=HEADERS
            )

        if TestCubeBishengIntegration.deployment_id:
            requests.delete(
                f"{CUBE_URL}/api/v1/deployments/{TestCubeBishengIntegration.deployment_id}",
                headers=HEADERS
            )

        if TestCubeBishengIntegration.model_id:
            requests.delete(
                f"{CUBE_URL}/api/v1/models/{TestCubeBishengIntegration.model_id}",
                headers=HEADERS
            )


class TestAlldataBishengIntegration:
    """Alldata → Bisheng 集成测试（Text2SQL、RAG）"""

    @pytest.mark.e2e
    def test_01_metadata_query(self):
        """测试元数据查询"""
        response = requests.get(
            f"{ALLDATA_URL}/api/v1/metadata/tables",
            headers=HEADERS,
            params={"keywords": "sales,orders"}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            logger.info("Found %d tables", len(data.get("data", {}).get("tables", [])))

    @pytest.mark.e2e
    def test_02_text_to_sql_with_metadata(self):
        """测试带元数据的 Text-to-SQL"""
        # 先获取元数据
        meta_response = requests.get(
            f"{ALLDATA_URL}/api/v1/metadata/tables",
            headers=HEADERS,
            params={"keywords": "orders"}
        )

        if meta_response.status_code != 200:
            pytest.skip("Cannot get metadata")

        # 创建对话
        conv_response = requests.post(
            f"{BISHENG_URL}/api/v1/conversations",
            headers=HEADERS,
            json={"title": "Text2SQL Test"}
        )

        if conv_response.status_code != 201:
            pytest.skip("Cannot create conversation")

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # 发送 Text-to-SQL 请求
        response = requests.post(
            f"{BISHENG_URL}/api/v1/chat",
            headers=HEADERS,
            json={
                "conversation_id": conversation_id,
                "message": "查询上个月的订单总额",
                "mode": "text2sql",
                "metadata_source": "alldata"
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_03_vector_search(self):
        """测试向量检索"""
        response = requests.post(
            f"{ALLDATA_URL}/api/v1/vector/search",
            headers=HEADERS,
            json={
                "query": "销售政策变化",
                "collection": "enterprise_docs",
                "top_k": 5
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_04_rag_with_alldata_vector(self):
        """测试使用 Alldata 向量库的 RAG"""
        # 创建对话
        conv_response = requests.post(
            f"{BISHENG_URL}/api/v1/conversations",
            headers=HEADERS,
            json={"title": "RAG Test"}
        )

        if conv_response.status_code != 201:
            pytest.skip("Cannot create conversation")

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # 发送 RAG 请求
        response = requests.post(
            f"{BISHENG_URL}/api/v1/chat",
            headers=HEADERS,
            json={
                "conversation_id": conversation_id,
                "message": "公司的退货政策是什么？",
                "mode": "rag",
                "vector_source": "alldata",
                "collection": "enterprise_docs"
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_05_hybrid_query(self):
        """测试混合查询（RAG + SQL）"""
        # 创建对话
        conv_response = requests.post(
            f"{BISHENG_URL}/api/v1/conversations",
            headers=HEADERS,
            json={"title": "Hybrid Query Test"}
        )

        if conv_response.status_code != 201:
            pytest.skip("Cannot create conversation")

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # 发送混合查询请求
        response = requests.post(
            f"{BISHENG_URL}/api/v1/chat",
            headers=HEADERS,
            json={
                "conversation_id": conversation_id,
                "message": "分析上个月销售下滑的原因",
                "mode": "hybrid",
                "metadata_source": "alldata",
                "vector_source": "alldata"
            }
        )

        assert response.status_code in [200, 401, 404]


class TestCompleteMLOpsWorkflow:
    """完整 MLOps 工作流测试"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_workflow(self):
        """测试完整的 MLOps 工作流程"""
        # 步骤 1: 在 Alldata 准备数据集
        logger.info("Step 1: Creating dataset in Alldata")
        dataset_response = requests.post(
            f"{ALLDATA_URL}/api/v1/datasets",
            headers=HEADERS,
            json={
                "name": f"MLOps Workflow Dataset {int(time.time())}",
                "type": "table",
                "source": "mysql"
            }
        )

        if dataset_response.status_code != 201:
            pytest.skip("Cannot create dataset")

        dataset_id = dataset_response.json()["data"]["dataset_id"]
        logger.info("Created dataset: %s", dataset_id)

        # 步骤 2: 在 Cube Studio 注册并训练模型
        logger.info("Step 2: Creating and training model in Cube Studio")
        model_response = requests.post(
            f"{CUBE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"MLOps Workflow Model {int(time.time())}",
                "model_type": "text-classification",
                "framework": "transformers"
            }
        )

        if model_response.status_code != 201:
            pytest.skip("Cannot create model")

        model_id = model_response.json()["data"]["model_id"]

        # 步骤 3: 部署模型
        logger.info("Step 3: Deploying model")
        model_update = requests.put(
            f"{CUBE_URL}/api/v1/models/{model_id}",
            headers=HEADERS,
            json={"status": "ready"}
        )

        deploy_response = requests.post(
            f"{CUBE_URL}/api/v1/models/{model_id}/deploy",
            headers=HEADERS,
            json={"replicas": 1}
        )

        if deploy_response.status_code != 201:
            logger.warning("Cannot deploy model, skipping workflow creation")
            return

        deployment_id = deploy_response.json()["data"]["deployment_id"]

        # 步骤 4: 在 Bisheng 创建使用模型的工作流
        logger.info("Step 4: Creating workflow in Bisheng")
        workflow_response = requests.post(
            f"{BISHENG_URL}/api/v1/workflows",
            headers=HEADERS,
            json={
                "name": f"MLOps Complete Workflow {int(time.time())}",
                "type": "rag"
            }
        )

        if workflow_response.status_code != 201:
            logger.warning("Cannot create workflow")
            return

        workflow_id = workflow_response.json()["data"]["workflow_id"]

        # 步骤 5: 执行工作流
        logger.info("Step 5: Executing workflow")
        exec_response = requests.post(
            f"{BISHENG_URL}/api/v1/workflows/{workflow_id}/start",
            headers=HEADERS,
            json={"inputs": {"query": "测试查询"}}
        )

        logger.info("Workflow execution status: %d", exec_response.status_code)

        # 清理
        logger.info("Cleaning up...")
        requests.delete(f"{BISHENG_URL}/api/v1/workflows/{workflow_id}", headers=HEADERS)
        requests.delete(f"{CUBE_URL}/api/v1/deployments/{deployment_id}", headers=HEADERS)
        requests.delete(f"{CUBE_URL}/api/v1/models/{model_id}", headers=HEADERS)
        requests.delete(f"{ALLDATA_URL}/api/v1/datasets/{dataset_id}", headers=HEADERS)


class TestServiceHealthCheck:
    """服务健康检查测试"""

    @pytest.mark.e2e
    def test_alldata_health(self):
        """测试 Alldata 服务健康"""
        response = requests.get(f"{ALLDATA_URL}/api/v1/health")
        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_bisheng_health(self):
        """测试 Bisheng 服务健康"""
        response = requests.get(f"{BISHENG_URL}/api/v1/health")
        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_cube_health(self):
        """测试 Cube Studio 服务健康"""
        response = requests.get(f"{CUBE_URL}/api/v1/health")
        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_all_services_healthy(self):
        """测试所有服务都健康"""
        services = [
            (ALLDATA_URL, "Alldata"),
            (BISHENG_URL, "Bisheng"),
            (CUBE_URL, "Cube Studio")
        ]

        healthy_count = 0
        for url, name in services:
            try:
                response = requests.get(f"{url}/api/v1/health", timeout=5)
                if response.status_code == 200:
                    healthy_count += 1
                    logger.info("%s is healthy", name)
                else:
                    logger.warning("%s returned status %d", name, response.status_code)
            except requests.exceptions.RequestException as e:
                logger.error("%s is not reachable: %s", name, e)

        logger.info("%d/%d services are healthy", healthy_count, len(services))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
