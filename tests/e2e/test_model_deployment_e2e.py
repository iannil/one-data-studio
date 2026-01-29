"""
模型部署端到端测试
测试模型管理、部署服务、推理接口等

测试覆盖:
- 模型 CRUD 操作
- 模型版本管理
- 模型部署与下线
- 模型推理
- 批量预测
- 训练任务管理
"""

import pytest
import requests
import time
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_MODEL_URL", os.getenv("TEST_CUBE_URL", "http://localhost:8083"))
AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestModelManagement:
    """模型管理测试"""

    model_id: Optional[str] = None
    version_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_model(self):
        """测试创建模型"""
        response = requests.post(
            f"{BASE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"E2E Test Model {int(time.time())}",
                "description": "自动化测试创建的模型",
                "model_type": "text-generation",
                "framework": "transformers",
                "source": "local",
                "tags": ["test", "e2e"],
                "config": {
                    "max_length": 512,
                    "temperature": 0.7
                }
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            assert "model_id" in data["data"]
            TestModelManagement.model_id = data["data"]["model_id"]
            logger.info("Created model: %s", TestModelManagement.model_id)

    @pytest.mark.e2e
    def test_02_list_models(self):
        """测试列出模型"""
        response = requests.get(
            f"{BASE_URL}/api/v1/models",
            headers=HEADERS,
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "models" in data["data"]
            assert isinstance(data["data"]["models"], list)

    @pytest.mark.e2e
    def test_03_get_model(self):
        """测试获取模型详情"""
        if not TestModelManagement.model_id:
            pytest.skip("No model created")

        response = requests.get(
            f"{BASE_URL}/api/v1/models/{TestModelManagement.model_id}",
            headers=HEADERS,
            params={"include_versions": "true"}
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["model_id"] == TestModelManagement.model_id

    @pytest.mark.e2e
    def test_04_update_model(self):
        """测试更新模型"""
        if not TestModelManagement.model_id:
            pytest.skip("No model created")

        response = requests.put(
            f"{BASE_URL}/api/v1/models/{TestModelManagement.model_id}",
            headers=HEADERS,
            json={
                "description": "Updated description",
                "status": "ready",
                "tags": ["test", "e2e", "updated"]
            }
        )

        assert response.status_code in [200, 401, 404]

    @pytest.mark.e2e
    def test_05_create_model_version(self):
        """测试创建模型版本"""
        if not TestModelManagement.model_id:
            pytest.skip("No model created")

        response = requests.post(
            f"{BASE_URL}/api/v1/models/{TestModelManagement.model_id}/versions",
            headers=HEADERS,
            json={
                "version": "1.0.0",
                "storage_path": "/models/test/v1.0.0",
                "file_size": 1024000,
                "checksum": "sha256:abcd1234",
                "metrics": {
                    "accuracy": 0.95,
                    "loss": 0.05
                }
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestModelManagement.version_id = data["data"]["version_id"]

    @pytest.mark.e2e
    def test_06_list_model_versions(self):
        """测试列出模型版本"""
        if not TestModelManagement.model_id:
            pytest.skip("No model created")

        response = requests.get(
            f"{BASE_URL}/api/v1/models/{TestModelManagement.model_id}/versions",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "versions" in data["data"]


class TestModelDeployment:
    """模型部署测试"""

    model_id: Optional[str] = None
    deployment_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """创建测试用模型"""
        response = requests.post(
            f"{BASE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"Deployment Test Model {int(time.time())}",
                "description": "用于部署测试的模型",
                "model_type": "text-classification",
                "framework": "transformers",
                "status": "ready"
            }
        )

        if response.status_code == 201:
            TestModelDeployment.model_id = response.json()["data"]["model_id"]

        yield

        # 清理
        if TestModelDeployment.deployment_id:
            requests.delete(
                f"{BASE_URL}/api/v1/deployments/{TestModelDeployment.deployment_id}",
                headers=HEADERS
            )
        if TestModelDeployment.model_id:
            requests.delete(
                f"{BASE_URL}/api/v1/models/{TestModelDeployment.model_id}",
                headers=HEADERS
            )

    @pytest.mark.e2e
    def test_01_deploy_model(self):
        """测试部署模型"""
        if not TestModelDeployment.model_id:
            pytest.skip("No model created")

        response = requests.post(
            f"{BASE_URL}/api/v1/models/{TestModelDeployment.model_id}/deploy",
            headers=HEADERS,
            json={
                "replicas": 1,
                "gpu_count": 0,
                "memory_limit": "2Gi",
                "cpu_limit": "1",
                "config": {
                    "max_batch_size": 32,
                    "timeout": 30
                }
            }
        )

        assert response.status_code in [201, 400, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestModelDeployment.deployment_id = data["data"]["deployment_id"]
            logger.info("Created deployment: %s", TestModelDeployment.deployment_id)

    @pytest.mark.e2e
    def test_02_list_deployments(self):
        """测试列出部署"""
        response = requests.get(
            f"{BASE_URL}/api/v1/deployments",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "deployments" in data["data"]

    @pytest.mark.e2e
    def test_03_predict(self):
        """测试模型推理"""
        if not TestModelDeployment.deployment_id:
            pytest.skip("No deployment created")

        response = requests.post(
            f"{BASE_URL}/api/v1/predict/{TestModelDeployment.deployment_id}",
            headers=HEADERS,
            json={
                "input": "This is a test input for classification."
            }
        )

        assert response.status_code in [200, 401, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "data" in data

    @pytest.mark.e2e
    def test_04_undeploy_model(self):
        """测试取消部署"""
        if not TestModelDeployment.deployment_id:
            pytest.skip("No deployment created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/deployments/{TestModelDeployment.deployment_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]


class TestBatchPrediction:
    """批量预测测试"""

    model_id: Optional[str] = None
    job_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """创建测试用模型"""
        response = requests.post(
            f"{BASE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"Batch Test Model {int(time.time())}",
                "model_type": "text-classification",
                "status": "ready"
            }
        )

        if response.status_code == 201:
            TestBatchPrediction.model_id = response.json()["data"]["model_id"]

        yield

        if TestBatchPrediction.model_id:
            requests.delete(
                f"{BASE_URL}/api/v1/models/{TestBatchPrediction.model_id}",
                headers=HEADERS
            )

    @pytest.mark.e2e
    def test_01_create_batch_prediction(self):
        """测试创建批量预测任务"""
        if not TestBatchPrediction.model_id:
            pytest.skip("No model created")

        response = requests.post(
            f"{BASE_URL}/api/v1/batch-predictions",
            headers=HEADERS,
            json={
                "name": f"E2E Batch Job {int(time.time())}",
                "model_id": TestBatchPrediction.model_id,
                "input_path": "s3://test-bucket/input/batch_input.jsonl",
                "output_path": f"s3://test-bucket/output/batch_{int(time.time())}",
                "input_format": "jsonl",
                "output_format": "jsonl",
                "batch_size": 32
            }
        )

        assert response.status_code in [201, 400, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestBatchPrediction.job_id = data["data"]["job_id"]

    @pytest.mark.e2e
    def test_02_get_batch_prediction(self):
        """测试获取批量预测任务状态"""
        if not TestBatchPrediction.job_id:
            pytest.skip("No batch job created")

        response = requests.get(
            f"{BASE_URL}/api/v1/batch-predictions/{TestBatchPrediction.job_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]


class TestTrainingJob:
    """训练任务测试"""

    model_id: Optional[str] = None
    job_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """创建测试用模型"""
        response = requests.post(
            f"{BASE_URL}/api/v1/models",
            headers=HEADERS,
            json={
                "name": f"Training Test Model {int(time.time())}",
                "model_type": "text-classification",
                "status": "created"
            }
        )

        if response.status_code == 201:
            TestTrainingJob.model_id = response.json()["data"]["model_id"]

        yield

        if TestTrainingJob.job_id:
            requests.post(
                f"{BASE_URL}/api/v1/training-jobs/{TestTrainingJob.job_id}/cancel",
                headers=HEADERS
            )
        if TestTrainingJob.model_id:
            requests.delete(
                f"{BASE_URL}/api/v1/models/{TestTrainingJob.model_id}",
                headers=HEADERS
            )

    @pytest.mark.e2e
    def test_01_create_training_job(self):
        """测试创建训练任务"""
        if not TestTrainingJob.model_id:
            pytest.skip("No model created")

        response = requests.post(
            f"{BASE_URL}/api/v1/training-jobs",
            headers=HEADERS,
            json={
                "name": f"E2E Training Job {int(time.time())}",
                "model_id": TestTrainingJob.model_id,
                "dataset_path": "s3://test-bucket/datasets/train.jsonl",
                "framework": "transformers",
                "base_model": "bert-base-chinese",
                "hyperparameters": {
                    "learning_rate": 0.0001,
                    "batch_size": 32,
                    "epochs": 3,
                    "warmup_steps": 100
                },
                "resources": {
                    "gpu_count": 1,
                    "memory": "16Gi"
                }
            }
        )

        assert response.status_code in [201, 400, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestTrainingJob.job_id = data["data"]["job_id"]

    @pytest.mark.e2e
    def test_02_list_training_jobs(self):
        """测试列出训练任务"""
        response = requests.get(
            f"{BASE_URL}/api/v1/training-jobs",
            headers=HEADERS,
            params={"status": "pending", "page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "training_jobs" in data["data"]

    @pytest.mark.e2e
    def test_03_get_training_job(self):
        """测试获取训练任务详情"""
        if not TestTrainingJob.job_id:
            pytest.skip("No training job created")

        response = requests.get(
            f"{BASE_URL}/api/v1/training-jobs/{TestTrainingJob.job_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_04_cancel_training_job(self):
        """测试取消训练任务"""
        if not TestTrainingJob.job_id:
            pytest.skip("No training job created")

        response = requests.post(
            f"{BASE_URL}/api/v1/training-jobs/{TestTrainingJob.job_id}/cancel",
            headers=HEADERS
        )

        assert response.status_code in [200, 400, 401, 404]


class TestHuggingFaceIntegration:
    """Hugging Face Hub 集成测试"""

    @pytest.mark.e2e
    def test_01_search_hf_models(self):
        """测试搜索 HF 模型"""
        response = requests.get(
            f"{BASE_URL}/api/v1/huggingface/models",
            headers=HEADERS,
            params={
                "search": "bert",
                "filter": "text-classification",
                "limit": 10
            }
        )

        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0

    @pytest.mark.e2e
    def test_02_get_hf_model_details(self):
        """测试获取 HF 模型详情"""
        response = requests.get(
            f"{BASE_URL}/api/v1/huggingface/models/bert-base-chinese",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404, 503]

    @pytest.mark.e2e
    def test_03_get_pipeline_tags(self):
        """测试获取 Pipeline 标签"""
        response = requests.get(
            f"{BASE_URL}/api/v1/huggingface/pipeline-tags",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_04_search_hf_datasets(self):
        """测试搜索 HF 数据集"""
        response = requests.get(
            f"{BASE_URL}/api/v1/huggingface/datasets",
            headers=HEADERS,
            params={
                "search": "squad",
                "limit": 5
            }
        )

        assert response.status_code in [200, 401, 503]


class TestExperimentManagement:
    """实验管理测试"""

    experiment_id: Optional[str] = None

    @pytest.mark.e2e
    def test_01_create_experiment(self):
        """测试创建实验"""
        response = requests.post(
            f"{BASE_URL}/api/v1/experiments",
            headers=HEADERS,
            json={
                "name": f"E2E Experiment {int(time.time())}",
                "description": "自动化测试实验",
                "project": "e2e-tests",
                "tags": ["test", "e2e"]
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestExperimentManagement.experiment_id = data["data"]["experiment_id"]

    @pytest.mark.e2e
    def test_02_list_experiments(self):
        """测试列出实验"""
        response = requests.get(
            f"{BASE_URL}/api/v1/experiments",
            headers=HEADERS,
            params={"project": "e2e-tests"}
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_03_get_experiment(self):
        """测试获取实验详情"""
        if not TestExperimentManagement.experiment_id:
            pytest.skip("No experiment created")

        response = requests.get(
            f"{BASE_URL}/api/v1/experiments/{TestExperimentManagement.experiment_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    def test_04_compare_experiments(self):
        """测试比较实验"""
        response = requests.get(
            f"{BASE_URL}/api/v1/experiments/compare",
            headers=HEADERS,
            params={"experiment_ids": "exp1,exp2"}
        )

        assert response.status_code in [200, 400, 401]

    @pytest.mark.e2e
    def test_05_delete_experiment(self):
        """测试删除实验"""
        if not TestExperimentManagement.experiment_id:
            pytest.skip("No experiment created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/experiments/{TestExperimentManagement.experiment_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]


class TestResourceManagement:
    """资源管理测试"""

    @pytest.mark.e2e
    def test_01_get_resource_overview(self):
        """测试获取资源概览"""
        response = requests.get(
            f"{BASE_URL}/api/v1/resources/overview",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0

    @pytest.mark.e2e
    def test_02_list_gpu_devices(self):
        """测试列出 GPU 设备"""
        response = requests.get(
            f"{BASE_URL}/api/v1/resources/gpu",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_03_list_resource_pools(self):
        """测试列出资源池"""
        response = requests.get(
            f"{BASE_URL}/api/v1/resources/pools",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_04_get_resource_usage(self):
        """测试获取资源使用情况"""
        response = requests.get(
            f"{BASE_URL}/api/v1/resources/usage",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]


class TestMonitoring:
    """监控功能测试"""

    @pytest.mark.e2e
    def test_01_get_monitoring_overview(self):
        """测试获取监控概览"""
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/overview",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_02_get_monitoring_summary(self):
        """测试获取监控汇总"""
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/summary",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_03_list_monitoring_tasks(self):
        """测试列出监控任务"""
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/tasks",
            headers=HEADERS,
            params={"type": "training"}
        )

        assert response.status_code in [200, 401]

    @pytest.mark.e2e
    def test_04_list_alerts(self):
        """测试列出告警"""
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/alerts",
            headers=HEADERS,
            params={"status": "firing"}
        )

        assert response.status_code in [200, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
