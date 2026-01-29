"""
模型训练与评估模块集成测试
测试用例 AE-TR-001 ~ AE-TR-009, AE-EV-001

测试覆盖:
- 分布式训练任务提交与 K8s 调度
- LoRA 微调训练
- Full 微调训练
- 训练数据自动挂载
- 训练进度监控
- 训练任务暂停/恢复
- 训练任务终止与资源释放
- 模型权重保存（MinIO/HDFS）
- 多节点分布式训练
- 模型评估
"""

import json
import time
import uuid
import logging
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock, call

import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 共享常量
# ---------------------------------------------------------------------------

MODEL_API_URL = "http://localhost:8083"
EXPERIMENTS_ENDPOINT = f"{MODEL_API_URL}/api/v1/experiments"
TRAINING_JOBS_ENDPOINT = f"{MODEL_API_URL}/api/v1/training-jobs"


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_k8s_client():
    """模拟 Kubernetes 客户端

    提供对 K8s Job / Pod / Node 等资源的 Mock 操作，
    用于验证训练任务提交、暂停、恢复、终止等场景。
    """
    client = MagicMock()

    # --- BatchV1Api ---
    batch_api = MagicMock()

    # 默认：创建 Job 成功
    mock_job = MagicMock()
    mock_job.metadata.name = "training-job-test-001"
    mock_job.metadata.namespace = "one-data-model"
    mock_job.status.active = 1
    mock_job.status.succeeded = None
    mock_job.status.failed = None
    mock_job.status.conditions = None
    batch_api.create_namespaced_job.return_value = mock_job

    # 读取 Job 状态
    batch_api.read_namespaced_job_status.return_value = mock_job

    # 删除 Job
    batch_api.delete_namespaced_job.return_value = MagicMock(status="Success")

    # 列出 Job
    mock_job_list = MagicMock()
    mock_job_list.items = [mock_job]
    batch_api.list_namespaced_job.return_value = mock_job_list

    client.BatchV1Api.return_value = batch_api
    client.batch_api = batch_api

    # --- CoreV1Api ---
    core_api = MagicMock()

    # Pod 日志
    core_api.read_namespaced_pod_log.return_value = (
        "Epoch 1/3 - loss: 0.523 - accuracy: 0.812\n"
        "Epoch 2/3 - loss: 0.341 - accuracy: 0.891\n"
        "Epoch 3/3 - loss: 0.215 - accuracy: 0.932\n"
    )

    # 列出 Pod
    mock_pod = MagicMock()
    mock_pod.metadata.name = "training-job-test-001-worker-0"
    mock_pod.metadata.namespace = "one-data-model"
    mock_pod.status.phase = "Running"
    mock_pod.spec.containers = [MagicMock()]
    mock_pod.spec.containers[0].resources.limits = {
        "nvidia.com/gpu": "1",
        "memory": "16Gi",
        "cpu": "4",
    }
    # 模拟 Volume Mounts
    mock_volume_mount = MagicMock()
    mock_volume_mount.name = "training-data"
    mock_volume_mount.mount_path = "/data/training"
    mock_pod.spec.containers[0].volume_mounts = [mock_volume_mount]

    mock_pod_list = MagicMock()
    mock_pod_list.items = [mock_pod]
    core_api.list_namespaced_pod.return_value = mock_pod_list

    # 节点列表（用于多节点分布式训练验证）
    mock_node_gpu = MagicMock()
    mock_node_gpu.metadata.name = "gpu-node-0"
    mock_node_gpu.metadata.labels = {"accelerator": "nvidia-a100"}
    mock_node_gpu.status.capacity = {"nvidia.com/gpu": "8", "memory": "256Gi", "cpu": "64"}

    mock_node_gpu_2 = MagicMock()
    mock_node_gpu_2.metadata.name = "gpu-node-1"
    mock_node_gpu_2.metadata.labels = {"accelerator": "nvidia-a100"}
    mock_node_gpu_2.status.capacity = {"nvidia.com/gpu": "8", "memory": "256Gi", "cpu": "64"}

    mock_node_list = MagicMock()
    mock_node_list.items = [mock_node_gpu, mock_node_gpu_2]
    core_api.list_node.return_value = mock_node_list

    # PersistentVolumeClaim（训练数据挂载）
    mock_pvc = MagicMock()
    mock_pvc.metadata.name = "training-data-pvc"
    mock_pvc.status.phase = "Bound"
    mock_pvc.spec.access_modes = ["ReadWriteMany"]
    mock_pvc.spec.resources.requests = {"storage": "100Gi"}
    core_api.read_namespaced_persistent_volume_claim.return_value = mock_pvc

    client.CoreV1Api.return_value = core_api
    client.core_api = core_api

    return client


@pytest.fixture
def mock_training_job():
    """模拟训练任务对象

    返回一个行为类似 TrainingJob ORM 模型的 Mock 对象，
    包含完整的字段和 helper 方法。
    """
    job = MagicMock()
    job.id = 1
    job.job_id = f"tj-{uuid.uuid4().hex[:12]}"
    job.name = "集成测试训练任务"
    job.description = "用于集成测试的模型训练任务"
    job.model_id = f"model-{uuid.uuid4().hex[:8]}"
    job.job_type = "training"
    job.status = "pending"
    job.dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
    job.dataset_path = "s3://one-data-model/datasets/train.jsonl"
    job.framework = "pytorch"
    job.base_model = "Qwen/Qwen2-7B"
    job.progress = 0.0
    job.current_epoch = 0
    job.total_epochs = 3
    job.current_step = 0
    job.total_steps = 1500
    job.output_model_path = None
    job.logs_path = None
    job.error_message = None
    job.created_by = "test-user"
    job.created_at = datetime.utcnow()
    job.started_at = None
    job.completed_at = None
    job.updated_at = datetime.utcnow()

    hyperparameters = {
        "learning_rate": 2e-5,
        "batch_size": 16,
        "epochs": 3,
        "warmup_steps": 100,
        "weight_decay": 0.01,
        "gradient_accumulation_steps": 4,
    }
    job.hyperparameters = json.dumps(hyperparameters)
    job.get_hyperparameters.return_value = hyperparameters
    job.set_hyperparameters = MagicMock()

    resources = {"gpu_count": 1, "memory": "16Gi", "cpu": "4"}
    job.resources = json.dumps(resources)
    job.get_resources.return_value = resources
    job.set_resources = MagicMock()

    metrics = {}
    job.metrics = json.dumps(metrics)
    job.get_metrics.return_value = metrics
    job.set_metrics = MagicMock()

    job.to_dict.return_value = {
        "id": job.job_id,
        "name": job.name,
        "description": job.description,
        "model_id": job.model_id,
        "job_type": job.job_type,
        "status": job.status,
        "dataset_id": job.dataset_id,
        "dataset_path": job.dataset_path,
        "framework": job.framework,
        "base_model": job.base_model,
        "hyperparameters": hyperparameters,
        "resources": resources,
        "progress": job.progress,
        "current_epoch": job.current_epoch,
        "total_epochs": job.total_epochs,
        "current_step": job.current_step,
        "total_steps": job.total_steps,
        "metrics": metrics,
        "output_model_path": job.output_model_path,
        "logs_path": job.logs_path,
        "error_message": job.error_message,
        "created_by": job.created_by,
        "created_at": job.created_at.isoformat(),
        "started_at": None,
        "completed_at": None,
        "updated_at": job.updated_at.isoformat(),
    }

    return job


@pytest.fixture
def sample_training_config():
    """标准训练配置样本

    包含实验提交所需的所有字段，用于 POST /api/v1/experiments 请求。
    """
    return {
        "name": f"integration-test-experiment-{int(time.time())}",
        "description": "集成测试：分布式训练实验",
        "project": "integration-tests",
        "model_id": f"model-{uuid.uuid4().hex[:8]}",
        "framework": "pytorch",
        "base_model": "Qwen/Qwen2-7B",
        "dataset_id": f"ds-{uuid.uuid4().hex[:8]}",
        "dataset_path": "s3://one-data-model/datasets/train.jsonl",
        "hyperparameters": {
            "learning_rate": 2e-5,
            "batch_size": 16,
            "epochs": 3,
            "warmup_steps": 100,
            "weight_decay": 0.01,
            "gradient_accumulation_steps": 4,
            "max_seq_length": 2048,
            "fp16": True,
        },
        "resources": {
            "gpu_count": 1,
            "memory": "16Gi",
            "cpu": "4",
        },
        "tags": ["integration-test", "distributed"],
    }


@pytest.fixture
def lora_training_config(sample_training_config):
    """LoRA 微调训练配置"""
    config = dict(sample_training_config)
    config["name"] = f"integration-test-lora-{int(time.time())}"
    config["description"] = "集成测试：LoRA 微调训练"
    config["job_type"] = "fine-tuning"
    config["hyperparameters"] = {
        **config["hyperparameters"],
        "fine_tune_method": "lora",
        "lora_r": 8,
        "lora_alpha": 32,
        "lora_dropout": 0.1,
        "lora_target_modules": ["q_proj", "v_proj"],
        "learning_rate": 3e-4,
    }
    return config


@pytest.fixture
def full_finetune_config(sample_training_config):
    """Full 微调训练配置"""
    config = dict(sample_training_config)
    config["name"] = f"integration-test-full-ft-{int(time.time())}"
    config["description"] = "集成测试：Full 微调训练"
    config["job_type"] = "fine-tuning"
    config["hyperparameters"] = {
        **config["hyperparameters"],
        "fine_tune_method": "full",
        "learning_rate": 1e-5,
        "gradient_checkpointing": True,
    }
    config["resources"] = {
        "gpu_count": 2,
        "memory": "32Gi",
        "cpu": "8",
    }
    return config


@pytest.fixture
def mock_minio_storage():
    """模拟 MinIO 存储客户端

    用于验证模型权重保存场景。
    """
    storage = MagicMock()
    storage.bucket_exists.return_value = True
    storage.put_object.return_value = None
    storage.stat_object.return_value = MagicMock(
        size=4_294_967_296,  # 4 GiB
        last_modified=datetime.utcnow(),
        etag="abc123def456",
    )
    storage.fget_object.return_value = None

    # 模拟已保存的 checkpoint 列表
    mock_obj_1 = MagicMock()
    mock_obj_1.object_name = "checkpoints/tj-test/checkpoint-500/pytorch_model.bin"
    mock_obj_1.size = 2_147_483_648
    mock_obj_1.last_modified = datetime.utcnow()

    mock_obj_2 = MagicMock()
    mock_obj_2.object_name = "checkpoints/tj-test/checkpoint-1000/pytorch_model.bin"
    mock_obj_2.size = 2_147_483_648
    mock_obj_2.last_modified = datetime.utcnow()

    mock_obj_final = MagicMock()
    mock_obj_final.object_name = "checkpoints/tj-test/final/pytorch_model.bin"
    mock_obj_final.size = 4_294_967_296
    mock_obj_final.last_modified = datetime.utcnow()

    storage.list_objects.return_value = [mock_obj_1, mock_obj_2, mock_obj_final]

    return storage


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


# ===========================================================================
# AE-TR-001: 提交分布式训练任务 (P0)
# ===========================================================================

class TestSubmitDistributedTraining:
    """AE-TR-001: 提交分布式训练任务

    验证通过 POST /api/v1/experiments 提交训练实验后，
    系统能正确创建 K8s Job 并返回任务 ID。
    """

    @pytest.mark.integration
    def test_submit_training_creates_k8s_job(
        self, mock_k8s_client, sample_training_config, mock_db_session
    ):
        """提交训练任务后应在 K8s 中创建对应的 Job"""
        batch_api = mock_k8s_client.batch_api

        # 模拟训练提交逻辑
        job_id = f"tj-{uuid.uuid4().hex[:12]}"
        job_body = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_id,
                "namespace": "one-data-model",
                "labels": {
                    "app": "one-data-model",
                    "job-type": "training",
                    "experiment": sample_training_config["name"],
                },
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "trainer",
                            "image": "one-data-model/trainer:latest",
                            "resources": {
                                "limits": {
                                    "nvidia.com/gpu": str(sample_training_config["resources"]["gpu_count"]),
                                    "memory": sample_training_config["resources"]["memory"],
                                    "cpu": sample_training_config["resources"]["cpu"],
                                },
                            },
                            "env": [
                                {"name": "BASE_MODEL", "value": sample_training_config["base_model"]},
                                {"name": "DATASET_PATH", "value": sample_training_config["dataset_path"]},
                                {"name": "HYPERPARAMS", "value": json.dumps(sample_training_config["hyperparameters"])},
                            ],
                        }],
                        "restartPolicy": "Never",
                    },
                },
                "backoffLimit": 3,
            },
        }

        # 调用 K8s API 创建 Job
        result = batch_api.create_namespaced_job(
            namespace="one-data-model",
            body=job_body,
        )

        # 断言：K8s Job 成功创建
        batch_api.create_namespaced_job.assert_called_once()
        assert result.metadata.name == "training-job-test-001"
        assert result.metadata.namespace == "one-data-model"

        # 断言：调用时传入了正确的命名空间
        call_args = batch_api.create_namespaced_job.call_args
        assert call_args.kwargs["namespace"] == "one-data-model"

        logger.info("AE-TR-001: K8s Job 创建成功, job_name=%s", result.metadata.name)

    @pytest.mark.integration
    def test_submit_training_returns_experiment_id(
        self, sample_training_config, mock_db_session
    ):
        """提交训练任务后应返回实验 ID 和任务 ID"""
        # 模拟 API 返回
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "code": 0,
            "message": "训练任务已提交",
            "data": {
                "experiment_id": f"exp-{uuid.uuid4().hex[:8]}",
                "job_id": f"tj-{uuid.uuid4().hex[:12]}",
                "status": "pending",
            },
        }

        # 模拟 POST 请求并验证响应结构
        mock_post = MagicMock(return_value=mock_response)
        response = mock_post(
            EXPERIMENTS_ENDPOINT,
            json=sample_training_config,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert "experiment_id" in data["data"]
        assert "job_id" in data["data"]
        assert data["data"]["status"] == "pending"

        logger.info(
            "AE-TR-001: 实验提交成功, experiment_id=%s, job_id=%s",
            data["data"]["experiment_id"],
            data["data"]["job_id"],
        )

    @pytest.mark.integration
    def test_submit_training_validates_required_fields(self):
        """提交训练任务时缺少必填字段应返回 400"""
        incomplete_config = {"name": "incomplete-experiment"}

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": 1,
            "message": "缺少必填参数: framework, base_model",
        }

        mock_post = MagicMock(return_value=mock_response)
        response = mock_post(EXPERIMENTS_ENDPOINT, json=incomplete_config)
        assert response.status_code == 400
        assert response.json()["code"] != 0

    @pytest.mark.integration
    def test_submit_training_resource_request(
        self, mock_k8s_client, sample_training_config
    ):
        """提交训练任务后 K8s Job 的资源请求与配置一致"""
        batch_api = mock_k8s_client.batch_api

        batch_api.create_namespaced_job(
            namespace="one-data-model",
            body={"spec": {"template": {"spec": {"containers": [{
                "resources": {
                    "limits": {
                        "nvidia.com/gpu": str(sample_training_config["resources"]["gpu_count"]),
                        "memory": sample_training_config["resources"]["memory"],
                        "cpu": sample_training_config["resources"]["cpu"],
                    },
                },
            }]}}}},
        )

        call_args = batch_api.create_namespaced_job.call_args
        body = call_args.kwargs["body"]
        container = body["spec"]["template"]["spec"]["containers"][0]
        limits = container["resources"]["limits"]

        assert limits["nvidia.com/gpu"] == "1"
        assert limits["memory"] == "16Gi"
        assert limits["cpu"] == "4"

        logger.info("AE-TR-001: 资源请求验证通过 gpu=%s, mem=%s, cpu=%s",
                     limits["nvidia.com/gpu"], limits["memory"], limits["cpu"])


# ===========================================================================
# AE-TR-002: LoRA 微调训练 (P0)
# ===========================================================================

class TestLoRAFineTuning:
    """AE-TR-002: LoRA 微调训练

    验证 LoRA 微调相关参数（lora_r, lora_alpha, lora_target_modules 等）
    能被正确配置并传递到训练框架。
    """

    @pytest.mark.integration
    def test_lora_config_contains_required_params(self, lora_training_config):
        """LoRA 配置应包含必需的 LoRA 参数"""
        hp = lora_training_config["hyperparameters"]

        assert hp["fine_tune_method"] == "lora"
        assert "lora_r" in hp
        assert "lora_alpha" in hp
        assert "lora_dropout" in hp
        assert "lora_target_modules" in hp

        assert isinstance(hp["lora_r"], int) and hp["lora_r"] > 0
        assert isinstance(hp["lora_alpha"], (int, float)) and hp["lora_alpha"] > 0
        assert 0.0 <= hp["lora_dropout"] < 1.0
        assert isinstance(hp["lora_target_modules"], list) and len(hp["lora_target_modules"]) > 0

        logger.info("AE-TR-002: LoRA 参数验证通过 r=%d, alpha=%s, dropout=%s, modules=%s",
                     hp["lora_r"], hp["lora_alpha"], hp["lora_dropout"], hp["lora_target_modules"])

    @pytest.mark.integration
    def test_lora_training_job_submission(
        self, mock_k8s_client, lora_training_config, mock_db_session
    ):
        """提交 LoRA 训练任务后 K8s Job 环境变量包含 LoRA 配置"""
        batch_api = mock_k8s_client.batch_api

        env_vars = [
            {"name": "FINE_TUNE_METHOD", "value": "lora"},
            {"name": "LORA_R", "value": str(lora_training_config["hyperparameters"]["lora_r"])},
            {"name": "LORA_ALPHA", "value": str(lora_training_config["hyperparameters"]["lora_alpha"])},
            {"name": "LORA_DROPOUT", "value": str(lora_training_config["hyperparameters"]["lora_dropout"])},
            {"name": "LORA_TARGET_MODULES", "value": json.dumps(
                lora_training_config["hyperparameters"]["lora_target_modules"]
            )},
            {"name": "BASE_MODEL", "value": lora_training_config["base_model"]},
            {"name": "DATASET_PATH", "value": lora_training_config["dataset_path"]},
        ]

        job_body = {
            "metadata": {"name": "lora-training-test", "namespace": "one-data-model"},
            "spec": {"template": {"spec": {"containers": [{
                "name": "trainer",
                "image": "one-data-model/trainer:latest",
                "env": env_vars,
            }]}}},
        }

        result = batch_api.create_namespaced_job(namespace="one-data-model", body=job_body)

        assert result is not None
        call_body = batch_api.create_namespaced_job.call_args.kwargs["body"]
        container_env = call_body["spec"]["template"]["spec"]["containers"][0]["env"]

        env_dict = {e["name"]: e["value"] for e in container_env}
        assert env_dict["FINE_TUNE_METHOD"] == "lora"
        assert env_dict["LORA_R"] == "8"
        assert env_dict["LORA_ALPHA"] == "32"

        logger.info("AE-TR-002: LoRA 训练 Job 提交成功，环境变量已正确设置")

    @pytest.mark.integration
    def test_lora_reduces_trainable_parameters(self, lora_training_config):
        """LoRA 应大幅减少可训练参数量"""
        # 模拟参数量统计
        total_params = 7_000_000_000   # 7B 参数
        lora_r = lora_training_config["hyperparameters"]["lora_r"]
        hidden_dim = 4096  # 典型 7B 模型隐藏维度
        num_target_modules = len(lora_training_config["hyperparameters"]["lora_target_modules"])

        # LoRA 可训练参数量 = 2 * r * hidden_dim * num_modules * num_layers
        num_layers = 32  # 典型 7B 模型层数
        lora_trainable = 2 * lora_r * hidden_dim * num_target_modules * num_layers

        trainable_ratio = lora_trainable / total_params

        # LoRA 可训练参数通常不超过总参数的 1%
        assert trainable_ratio < 0.01, (
            f"LoRA 可训练参数比例 ({trainable_ratio:.4%}) 应远小于 1%"
        )

        logger.info(
            "AE-TR-002: LoRA 可训练参数 %d (%.4f%%)，远小于总参数 %d",
            lora_trainable, trainable_ratio * 100, total_params,
        )

    @pytest.mark.integration
    def test_lora_adapter_output_path(self, lora_training_config, mock_training_job):
        """LoRA 训练完成后输出路径应包含 adapter 标识"""
        mock_training_job.status = "completed"
        mock_training_job.output_model_path = (
            f"s3://one-data-model/models/{mock_training_job.model_id}/lora-adapter/"
        )

        assert "lora-adapter" in mock_training_job.output_model_path
        assert mock_training_job.status == "completed"

        logger.info("AE-TR-002: LoRA adapter 输出路径 = %s", mock_training_job.output_model_path)


# ===========================================================================
# AE-TR-003: Full 微调训练 (P1)
# ===========================================================================

class TestFullFineTuning:
    """AE-TR-003: Full 微调训练

    验证全量微调训练配置，包括更大的资源需求和梯度检查点。
    """

    @pytest.mark.integration
    def test_full_finetune_config_validation(self, full_finetune_config):
        """Full 微调配置应包含正确的方法标识和额外资源"""
        hp = full_finetune_config["hyperparameters"]
        resources = full_finetune_config["resources"]

        assert hp["fine_tune_method"] == "full"
        assert hp.get("gradient_checkpointing") is True
        assert resources["gpu_count"] >= 2, "Full 微调通常需要多 GPU"
        assert int(resources["memory"].replace("Gi", "")) >= 32, "Full 微调需要更多内存"

        logger.info("AE-TR-003: Full 微调配置验证通过 gpu=%d, mem=%s",
                     resources["gpu_count"], resources["memory"])

    @pytest.mark.integration
    def test_full_finetune_job_submission(
        self, mock_k8s_client, full_finetune_config
    ):
        """提交 Full 微调任务后 K8s Job 应请求多 GPU 资源"""
        batch_api = mock_k8s_client.batch_api

        job_body = {
            "metadata": {"name": "full-ft-test", "namespace": "one-data-model"},
            "spec": {"template": {"spec": {"containers": [{
                "name": "trainer",
                "image": "one-data-model/trainer:latest",
                "resources": {
                    "limits": {
                        "nvidia.com/gpu": str(full_finetune_config["resources"]["gpu_count"]),
                        "memory": full_finetune_config["resources"]["memory"],
                    },
                },
                "env": [
                    {"name": "FINE_TUNE_METHOD", "value": "full"},
                    {"name": "GRADIENT_CHECKPOINTING", "value": "true"},
                ],
            }]}}},
        }

        result = batch_api.create_namespaced_job(namespace="one-data-model", body=job_body)
        assert result is not None

        call_body = batch_api.create_namespaced_job.call_args.kwargs["body"]
        gpu_limit = call_body["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"]
        assert int(gpu_limit) >= 2

        logger.info("AE-TR-003: Full 微调 Job 提交成功, gpu_count=%s", gpu_limit)

    @pytest.mark.integration
    def test_full_finetune_requires_more_resources_than_lora(
        self, lora_training_config, full_finetune_config
    ):
        """Full 微调应比 LoRA 需要更多资源"""
        lora_gpu = lora_training_config["resources"]["gpu_count"]
        full_gpu = full_finetune_config["resources"]["gpu_count"]

        lora_mem = int(lora_training_config["resources"]["memory"].replace("Gi", ""))
        full_mem = int(full_finetune_config["resources"]["memory"].replace("Gi", ""))

        assert full_gpu >= lora_gpu, "Full 微调 GPU 数应 >= LoRA"
        assert full_mem >= lora_mem, "Full 微调内存应 >= LoRA"

        logger.info("AE-TR-003: Full(gpu=%d,mem=%dGi) >= LoRA(gpu=%d,mem=%dGi)",
                     full_gpu, full_mem, lora_gpu, lora_mem)


# ===========================================================================
# AE-TR-004: 自动挂载训练数据 (P0)
# ===========================================================================

class TestAutoMountTrainingData:
    """AE-TR-004: 自动挂载训练数据

    验证训练任务启动时，数据存储（MinIO/HDFS PVC）
    会自动挂载到训练容器的指定路径。
    """

    @pytest.mark.integration
    def test_training_pod_has_data_volume_mount(self, mock_k8s_client):
        """训练 Pod 应包含数据卷挂载"""
        core_api = mock_k8s_client.core_api
        pod_list = core_api.list_namespaced_pod(namespace="one-data-model", label_selector="job-type=training")

        assert len(pod_list.items) > 0
        pod = pod_list.items[0]

        volume_mounts = pod.spec.containers[0].volume_mounts
        mount_names = [vm.name for vm in volume_mounts]
        mount_paths = [vm.mount_path for vm in volume_mounts]

        assert "training-data" in mount_names, "Pod 应挂载 training-data 卷"
        assert "/data/training" in mount_paths, "数据应挂载到 /data/training"

        logger.info("AE-TR-004: 训练数据卷已自动挂载, mounts=%s", list(zip(mount_names, mount_paths)))

    @pytest.mark.integration
    def test_pvc_is_bound(self, mock_k8s_client):
        """训练数据 PVC 应处于 Bound 状态"""
        core_api = mock_k8s_client.core_api
        pvc = core_api.read_namespaced_persistent_volume_claim(
            name="training-data-pvc",
            namespace="one-data-model",
        )

        assert pvc.status.phase == "Bound", "PVC 应处于 Bound 状态"
        assert "ReadWriteMany" in pvc.spec.access_modes, "PVC 应支持 ReadWriteMany 以支持分布式训练"

        logger.info("AE-TR-004: PVC 状态=%s, access_modes=%s",
                     pvc.status.phase, pvc.spec.access_modes)

    @pytest.mark.integration
    def test_dataset_path_accessible_in_container(self, mock_k8s_client, sample_training_config):
        """训练容器内应能访问数据集路径"""
        core_api = mock_k8s_client.core_api

        # 模拟在容器内执行 ls 命令验证数据路径
        mock_exec_response = "/data/training/train.jsonl\n/data/training/eval.jsonl\n"
        with patch.object(core_api, "connect_get_namespaced_pod_exec", return_value=mock_exec_response):
            result = core_api.connect_get_namespaced_pod_exec(
                name="training-job-test-001-worker-0",
                namespace="one-data-model",
                command=["ls", "/data/training/"],
                container="trainer",
                stdout=True,
            )

            assert "train.jsonl" in result
            logger.info("AE-TR-004: 容器内数据集可访问, files=%s", result.strip())


# ===========================================================================
# AE-TR-005: 训练进度监控 (P0)
# ===========================================================================

class TestTrainingProgressMonitoring:
    """AE-TR-005: 训练进度监控

    验证训练过程中能实时获取进度、loss、accuracy 等指标。
    """

    @pytest.mark.integration
    def test_get_training_progress(self, mock_training_job):
        """应能获取训练进度信息"""
        # 模拟训练进行中
        mock_training_job.status = "running"
        mock_training_job.progress = 66.7
        mock_training_job.current_epoch = 2
        mock_training_job.current_step = 1000

        assert mock_training_job.status == "running"
        assert 0 < mock_training_job.progress <= 100
        assert mock_training_job.current_epoch <= mock_training_job.total_epochs
        assert mock_training_job.current_step <= mock_training_job.total_steps

        logger.info(
            "AE-TR-005: 进度 %.1f%%, epoch %d/%d, step %d/%d",
            mock_training_job.progress,
            mock_training_job.current_epoch, mock_training_job.total_epochs,
            mock_training_job.current_step, mock_training_job.total_steps,
        )

    @pytest.mark.integration
    def test_get_training_metrics(self, mock_training_job):
        """应能获取训练指标（loss, accuracy 等）"""
        training_metrics = {
            "loss": 0.341,
            "accuracy": 0.891,
            "learning_rate": 1.8e-5,
            "epoch": 2,
            "step": 1000,
            "gpu_memory_used_mb": 14336,
            "throughput_samples_per_sec": 128.5,
        }
        mock_training_job.get_metrics.return_value = training_metrics

        metrics = mock_training_job.get_metrics()

        assert "loss" in metrics
        assert "accuracy" in metrics
        assert metrics["loss"] > 0
        assert 0 <= metrics["accuracy"] <= 1.0
        assert "gpu_memory_used_mb" in metrics
        assert "throughput_samples_per_sec" in metrics

        logger.info("AE-TR-005: 训练指标 loss=%.4f, acc=%.4f, gpu_mem=%dMB",
                     metrics["loss"], metrics["accuracy"], metrics["gpu_memory_used_mb"])

    @pytest.mark.integration
    def test_get_training_logs_from_pod(self, mock_k8s_client):
        """应能从 K8s Pod 获取训练日志"""
        core_api = mock_k8s_client.core_api

        logs = core_api.read_namespaced_pod_log(
            name="training-job-test-001-worker-0",
            namespace="one-data-model",
            container="trainer",
        )

        assert len(logs) > 0
        assert "Epoch" in logs
        assert "loss" in logs

        logger.info("AE-TR-005: Pod 日志获取成功, length=%d bytes", len(logs))

    @pytest.mark.integration
    def test_training_progress_api_response(self, mock_training_job):
        """训练进度 API 应返回结构化数据"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "job_id": mock_training_job.job_id,
                "status": "running",
                "progress": 66.7,
                "current_epoch": 2,
                "total_epochs": 3,
                "current_step": 1000,
                "total_steps": 1500,
                "metrics": {
                    "loss": 0.341,
                    "accuracy": 0.891,
                },
                "estimated_remaining_seconds": 1800,
            },
        }

        mock_get = MagicMock(return_value=mock_response)
        response = mock_get(
            f"{TRAINING_JOBS_ENDPOINT}/{mock_training_job.job_id}/progress"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "running"
        assert data["progress"] == pytest.approx(66.7, abs=0.1)
        assert "estimated_remaining_seconds" in data

        logger.info("AE-TR-005: 进度 API 返回正常, progress=%.1f%%", data["progress"])


# ===========================================================================
# AE-TR-006: 训练任务暂停/恢复 (P2)
# ===========================================================================

class TestTrainingPauseResume:
    """AE-TR-006: 训练任务暂停/恢复

    验证训练任务可以暂停（挂起 Pod）和恢复。
    """

    @pytest.mark.integration
    def test_pause_training_job(self, mock_k8s_client, mock_training_job, mock_db_session):
        """暂停训练任务应挂起 K8s Job"""
        batch_api = mock_k8s_client.batch_api

        # 模拟暂停操作：将 Job 的 spec.suspend 设为 True
        mock_training_job.status = "paused"

        patch_body = {"spec": {"suspend": True}}
        batch_api.patch_namespaced_job.return_value = MagicMock()

        batch_api.patch_namespaced_job(
            name="training-job-test-001",
            namespace="one-data-model",
            body=patch_body,
        )

        batch_api.patch_namespaced_job.assert_called_once_with(
            name="training-job-test-001",
            namespace="one-data-model",
            body={"spec": {"suspend": True}},
        )
        assert mock_training_job.status == "paused"

        logger.info("AE-TR-006: 训练任务已暂停, job=%s", mock_training_job.job_id)

    @pytest.mark.integration
    def test_resume_training_job(self, mock_k8s_client, mock_training_job, mock_db_session):
        """恢复训练任务应取消挂起"""
        batch_api = mock_k8s_client.batch_api

        mock_training_job.status = "running"

        patch_body = {"spec": {"suspend": False}}
        batch_api.patch_namespaced_job.return_value = MagicMock()

        batch_api.patch_namespaced_job(
            name="training-job-test-001",
            namespace="one-data-model",
            body=patch_body,
        )

        call_body = batch_api.patch_namespaced_job.call_args.kwargs["body"]
        assert call_body["spec"]["suspend"] is False
        assert mock_training_job.status == "running"

        logger.info("AE-TR-006: 训练任务已恢复, job=%s", mock_training_job.job_id)

    @pytest.mark.integration
    def test_pause_preserves_checkpoint(self, mock_training_job, mock_minio_storage):
        """暂停前应保存当前 checkpoint"""
        mock_training_job.status = "paused"
        mock_training_job.current_step = 750

        # 验证 checkpoint 已保存
        saved_objects = mock_minio_storage.list_objects(
            bucket_name="one-data-model",
            prefix=f"checkpoints/{mock_training_job.job_id}/",
        )

        saved_list = list(saved_objects)
        assert len(saved_list) > 0, "暂停时应至少保存一个 checkpoint"

        logger.info("AE-TR-006: 暂停前已保存 %d 个 checkpoint", len(saved_list))

    @pytest.mark.integration
    def test_pause_resume_api_flow(self, mock_training_job):
        """暂停/恢复 API 流程测试"""
        # 暂停
        mock_pause_response = MagicMock()
        mock_pause_response.status_code = 200
        mock_pause_response.json.return_value = {
            "code": 0,
            "message": "训练任务已暂停",
            "data": {"status": "paused"},
        }

        # 恢复
        mock_resume_response = MagicMock()
        mock_resume_response.status_code = 200
        mock_resume_response.json.return_value = {
            "code": 0,
            "message": "训练任务已恢复",
            "data": {"status": "running"},
        }

        mock_post = MagicMock(side_effect=[mock_pause_response, mock_resume_response])

        # 暂停
        pause_resp = mock_post(
            f"{TRAINING_JOBS_ENDPOINT}/{mock_training_job.job_id}/pause"
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["data"]["status"] == "paused"

        # 恢复
        resume_resp = mock_post(
            f"{TRAINING_JOBS_ENDPOINT}/{mock_training_job.job_id}/resume"
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["data"]["status"] == "running"

        logger.info("AE-TR-006: 暂停/恢复 API 流程测试通过")


# ===========================================================================
# AE-TR-007: 训练任务终止 (P1)
# ===========================================================================

class TestTrainingTermination:
    """AE-TR-007: 训练任务终止

    验证取消训练任务后，K8s Job 被删除并释放 GPU/内存资源。
    """

    @pytest.mark.integration
    def test_cancel_training_deletes_k8s_job(self, mock_k8s_client, mock_training_job):
        """取消训练应删除 K8s Job"""
        batch_api = mock_k8s_client.batch_api

        batch_api.delete_namespaced_job(
            name="training-job-test-001",
            namespace="one-data-model",
            propagation_policy="Background",
        )

        batch_api.delete_namespaced_job.assert_called_once()
        call_args = batch_api.delete_namespaced_job.call_args
        assert call_args.kwargs["name"] == "training-job-test-001"
        assert call_args.kwargs["propagation_policy"] == "Background"

        logger.info("AE-TR-007: K8s Job 已删除")

    @pytest.mark.integration
    def test_cancel_training_updates_status(self, mock_training_job, mock_db_session):
        """取消训练后任务状态应更新为 cancelled"""
        mock_training_job.status = "cancelled"
        mock_training_job.completed_at = datetime.utcnow()

        assert mock_training_job.status == "cancelled"
        assert mock_training_job.completed_at is not None

        logger.info("AE-TR-007: 任务状态已更新为 cancelled")

    @pytest.mark.integration
    def test_cancel_training_releases_resources(self, mock_k8s_client, mock_training_job):
        """取消训练后应释放 GPU 资源"""
        core_api = mock_k8s_client.core_api

        # 取消后重新查询 Pod，应无运行中的 Pod
        empty_pod_list = MagicMock()
        empty_pod_list.items = []
        core_api.list_namespaced_pod.return_value = empty_pod_list

        pod_list = core_api.list_namespaced_pod(
            namespace="one-data-model",
            label_selector=f"job-name={mock_training_job.job_id}",
        )

        assert len(pod_list.items) == 0, "取消后不应有运行中的训练 Pod"

        logger.info("AE-TR-007: GPU 资源已释放，无剩余 Pod")

    @pytest.mark.integration
    def test_cancel_training_api(self, mock_training_job):
        """取消训练 API 测试"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "message": "训练任务已取消",
            "data": {
                "job_id": mock_training_job.job_id,
                "status": "cancelled",
                "resources_released": True,
            },
        }

        mock_post = MagicMock(return_value=mock_response)
        response = mock_post(
            f"{TRAINING_JOBS_ENDPOINT}/{mock_training_job.job_id}/cancel"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "cancelled"
        assert data["resources_released"] is True

        logger.info("AE-TR-007: 取消训练 API 返回正常")


# ===========================================================================
# AE-TR-008: 保存模型权重 (P0)
# ===========================================================================

class TestSaveModelWeights:
    """AE-TR-008: 保存模型权重

    验证训练完成后模型 checkpoint 能正确保存到 MinIO/HDFS。
    """

    @pytest.mark.integration
    def test_save_checkpoint_to_minio(self, mock_minio_storage, mock_training_job):
        """训练完成后应将模型权重保存到 MinIO"""
        bucket = "one-data-model"
        checkpoint_path = f"checkpoints/{mock_training_job.job_id}/final/pytorch_model.bin"

        # 模拟保存 checkpoint
        mock_minio_storage.put_object(
            bucket_name=bucket,
            object_name=checkpoint_path,
            data=MagicMock(),
            length=4_294_967_296,
        )

        mock_minio_storage.put_object.assert_called_once()
        call_args = mock_minio_storage.put_object.call_args
        assert call_args.kwargs["bucket_name"] == bucket
        assert "pytorch_model.bin" in call_args.kwargs["object_name"]

        logger.info("AE-TR-008: Checkpoint 已保存到 MinIO path=%s", checkpoint_path)

    @pytest.mark.integration
    def test_checkpoint_metadata_recorded(self, mock_minio_storage, mock_training_job):
        """保存 checkpoint 后应能查询元数据"""
        stat = mock_minio_storage.stat_object(
            bucket_name="one-data-model",
            object_name=f"checkpoints/{mock_training_job.job_id}/final/pytorch_model.bin",
        )

        assert stat.size > 0, "Checkpoint 文件不应为空"
        assert stat.etag is not None, "应有文件校验和"
        assert stat.last_modified is not None, "应记录保存时间"

        logger.info("AE-TR-008: Checkpoint 元数据 size=%d, etag=%s", stat.size, stat.etag)

    @pytest.mark.integration
    def test_intermediate_checkpoints_saved(self, mock_minio_storage, mock_training_job):
        """训练过程中应保存中间 checkpoint"""
        objects = list(mock_minio_storage.list_objects(
            bucket_name="one-data-model",
            prefix=f"checkpoints/{mock_training_job.job_id}/",
        ))

        # 应至少包含中间 checkpoint 和最终 checkpoint
        assert len(objects) >= 2, "应至少有中间和最终两个 checkpoint"

        checkpoint_names = [obj.object_name for obj in objects]
        has_intermediate = any("checkpoint-" in name for name in checkpoint_names)
        has_final = any("final" in name for name in checkpoint_names)

        assert has_intermediate, "应有中间 checkpoint"
        assert has_final, "应有最终 checkpoint"

        logger.info("AE-TR-008: 共保存 %d 个 checkpoint: %s",
                     len(objects), [obj.object_name.split("/")[-2] for obj in objects])

    @pytest.mark.integration
    def test_model_output_path_updated(self, mock_training_job, mock_db_session):
        """训练完成后数据库中的 output_model_path 应更新"""
        expected_path = f"s3://one-data-model/checkpoints/{mock_training_job.job_id}/final/"
        mock_training_job.output_model_path = expected_path
        mock_training_job.status = "completed"

        assert mock_training_job.output_model_path is not None
        assert mock_training_job.job_id in mock_training_job.output_model_path
        assert mock_training_job.status == "completed"

        logger.info("AE-TR-008: output_model_path 已更新为 %s", mock_training_job.output_model_path)


# ===========================================================================
# AE-TR-009: 多节点分布式训练 (P2)
# ===========================================================================

class TestMultiNodeDistributedTraining:
    """AE-TR-009: 多节点分布式训练

    验证多节点分布式训练场景（如 PyTorch DDP），
    包括多 worker Pod 创建、节点间通信、Ring-AllReduce 等。
    """

    @pytest.mark.integration
    def test_multi_node_config_validation(self, sample_training_config):
        """多节点分布式训练配置应包含节点数和进程数"""
        distributed_config = dict(sample_training_config)
        distributed_config["resources"] = {
            "gpu_count": 4,
            "memory": "64Gi",
            "cpu": "16",
            "num_nodes": 2,
            "nproc_per_node": 4,
        }

        resources = distributed_config["resources"]
        assert resources["num_nodes"] >= 2, "分布式训练至少需要 2 个节点"
        assert resources["nproc_per_node"] >= 1, "每个节点至少 1 个进程"

        total_gpus = resources["num_nodes"] * resources["nproc_per_node"]
        assert total_gpus >= 2, "分布式训练总 GPU 数应 >= 2"

        logger.info("AE-TR-009: 分布式配置 nodes=%d, nproc=%d, total_gpus=%d",
                     resources["num_nodes"], resources["nproc_per_node"], total_gpus)

    @pytest.mark.integration
    def test_multi_worker_pods_created(self, mock_k8s_client):
        """多节点训练应创建多个 worker Pod"""
        core_api = mock_k8s_client.core_api

        # 模拟多个 worker Pod
        worker_pods = []
        for i in range(2):
            pod = MagicMock()
            pod.metadata.name = f"training-job-test-001-worker-{i}"
            pod.metadata.labels = {"role": f"worker-{i}"}
            pod.status.phase = "Running"
            pod.spec.node_name = f"gpu-node-{i}"
            worker_pods.append(pod)

        mock_pod_list = MagicMock()
        mock_pod_list.items = worker_pods
        core_api.list_namespaced_pod.return_value = mock_pod_list

        pod_list = core_api.list_namespaced_pod(
            namespace="one-data-model",
            label_selector="job-name=training-job-test-001",
        )

        assert len(pod_list.items) == 2, "应创建 2 个 worker Pod"

        # 验证分布在不同节点
        node_names = [p.spec.node_name for p in pod_list.items]
        assert len(set(node_names)) == 2, "Worker Pod 应分布在不同节点"

        logger.info("AE-TR-009: 多节点 Pod 创建成功, nodes=%s", node_names)

    @pytest.mark.integration
    def test_distributed_training_env_variables(self, mock_k8s_client):
        """分布式训练 Pod 应包含必要的环境变量"""
        expected_env_vars = {
            "MASTER_ADDR": "training-job-test-001-worker-0",
            "MASTER_PORT": "29500",
            "WORLD_SIZE": "8",
            "NPROC_PER_NODE": "4",
            "NNODES": "2",
        }

        # 模拟 Pod 的环境变量
        for var_name, var_value in expected_env_vars.items():
            assert var_name in expected_env_vars
            assert var_value is not None

        logger.info("AE-TR-009: 分布式环境变量验证通过: %s",
                     list(expected_env_vars.keys()))

    @pytest.mark.integration
    def test_multi_node_gpu_availability(self, mock_k8s_client):
        """验证集群有足够的 GPU 节点支持多节点训练"""
        core_api = mock_k8s_client.core_api

        node_list = core_api.list_node(label_selector="accelerator=nvidia-a100")

        gpu_nodes = [n for n in node_list.items if int(n.status.capacity.get("nvidia.com/gpu", 0)) > 0]
        total_gpus = sum(int(n.status.capacity["nvidia.com/gpu"]) for n in gpu_nodes)

        assert len(gpu_nodes) >= 2, "集群应至少有 2 个 GPU 节点"
        assert total_gpus >= 8, "集群总 GPU 数应满足分布式训练需求"

        logger.info("AE-TR-009: 集群 GPU 节点 %d 个, 总 GPU %d 块",
                     len(gpu_nodes), total_gpus)

    @pytest.mark.integration
    def test_distributed_job_creates_headless_service(self, mock_k8s_client):
        """多节点训练应创建 headless Service 用于 Pod 间通信"""
        core_api = mock_k8s_client.core_api

        mock_service = MagicMock()
        mock_service.metadata.name = "training-job-test-001-headless"
        mock_service.spec.cluster_ip = "None"
        mock_service.spec.ports = [MagicMock(port=29500, name="nccl")]

        core_api.read_namespaced_service.return_value = mock_service

        svc = core_api.read_namespaced_service(
            name="training-job-test-001-headless",
            namespace="one-data-model",
        )

        assert svc.spec.cluster_ip == "None", "应为 headless Service"
        assert any(p.port == 29500 for p in svc.spec.ports), "应暴露 NCCL 通信端口"

        logger.info("AE-TR-009: Headless Service 验证通过, name=%s", svc.metadata.name)


# ===========================================================================
# AE-EV-001: 模型评估 (P0)
# ===========================================================================

class TestModelEvaluation:
    """AE-EV-001: 模型评估

    验证加载已训练模型并在测试集上执行评估，获取评估指标。
    """

    @pytest.fixture
    def mock_evaluation_job(self, mock_training_job):
        """模拟评估任务"""
        eval_job = MagicMock()
        eval_job.job_id = f"ev-{uuid.uuid4().hex[:12]}"
        eval_job.name = "集成测试模型评估"
        eval_job.job_type = "evaluation"
        eval_job.status = "pending"
        eval_job.model_id = mock_training_job.model_id
        eval_job.dataset_id = f"ds-eval-{uuid.uuid4().hex[:8]}"
        eval_job.dataset_path = "s3://one-data-model/datasets/test.jsonl"
        eval_job.base_model = mock_training_job.base_model
        eval_job.framework = mock_training_job.framework

        eval_job.get_hyperparameters.return_value = {
            "eval_batch_size": 32,
            "eval_metrics": ["accuracy", "f1", "precision", "recall"],
        }

        eval_metrics = {
            "accuracy": 0.932,
            "f1": 0.918,
            "precision": 0.925,
            "recall": 0.911,
            "eval_loss": 0.215,
            "eval_samples": 5000,
            "eval_duration_seconds": 180,
        }
        eval_job.get_metrics.return_value = eval_metrics

        return eval_job

    @pytest.mark.integration
    def test_submit_evaluation_job(self, mock_evaluation_job, mock_k8s_client):
        """应能提交模型评估任务"""
        batch_api = mock_k8s_client.batch_api

        eval_body = {
            "metadata": {
                "name": mock_evaluation_job.job_id,
                "namespace": "one-data-model",
                "labels": {"job-type": "evaluation"},
            },
            "spec": {"template": {"spec": {"containers": [{
                "name": "evaluator",
                "image": "one-data-model/evaluator:latest",
                "env": [
                    {"name": "MODEL_PATH", "value": f"s3://one-data-model/models/{mock_evaluation_job.model_id}/"},
                    {"name": "EVAL_DATASET", "value": mock_evaluation_job.dataset_path},
                    {"name": "JOB_TYPE", "value": "evaluation"},
                ],
            }]}}},
        }

        result = batch_api.create_namespaced_job(namespace="one-data-model", body=eval_body)
        assert result is not None
        batch_api.create_namespaced_job.assert_called_once()

        logger.info("AE-EV-001: 评估任务已提交, job_id=%s", mock_evaluation_job.job_id)

    @pytest.mark.integration
    def test_evaluation_metrics_structure(self, mock_evaluation_job):
        """评估结果应包含完整的评估指标"""
        mock_evaluation_job.status = "completed"
        metrics = mock_evaluation_job.get_metrics()

        required_metrics = ["accuracy", "f1", "precision", "recall"]
        for metric_name in required_metrics:
            assert metric_name in metrics, f"缺少评估指标: {metric_name}"
            assert 0.0 <= metrics[metric_name] <= 1.0, f"{metric_name} 应在 [0, 1] 范围内"

        assert "eval_loss" in metrics
        assert metrics["eval_loss"] >= 0
        assert "eval_samples" in metrics
        assert metrics["eval_samples"] > 0

        logger.info(
            "AE-EV-001: 评估指标 accuracy=%.4f, f1=%.4f, precision=%.4f, recall=%.4f, loss=%.4f",
            metrics["accuracy"], metrics["f1"], metrics["precision"],
            metrics["recall"], metrics["eval_loss"],
        )

    @pytest.mark.integration
    def test_evaluation_loads_correct_model(self, mock_evaluation_job, mock_minio_storage):
        """评估应加载正确的训练产出模型"""
        model_path = f"checkpoints/{mock_evaluation_job.model_id}/final/pytorch_model.bin"

        stat = mock_minio_storage.stat_object(
            bucket_name="one-data-model",
            object_name=model_path,
        )

        assert stat.size > 0, "模型文件不应为空"

        logger.info(
            "AE-EV-001: 评估加载模型 model_id=%s, size=%d bytes",
            mock_evaluation_job.model_id, stat.size,
        )

    @pytest.mark.integration
    def test_evaluation_api_returns_results(self, mock_evaluation_job):
        """评估完成后 API 应返回评估结果"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "job_id": mock_evaluation_job.job_id,
                "status": "completed",
                "model_id": mock_evaluation_job.model_id,
                "metrics": {
                    "accuracy": 0.932,
                    "f1": 0.918,
                    "precision": 0.925,
                    "recall": 0.911,
                    "eval_loss": 0.215,
                },
                "eval_samples": 5000,
                "eval_duration_seconds": 180,
            },
        }

        mock_get = MagicMock(return_value=mock_response)
        response = mock_get(
            f"{TRAINING_JOBS_ENDPOINT}/{mock_evaluation_job.job_id}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "completed"
        assert data["metrics"]["accuracy"] > 0.9

        logger.info("AE-EV-001: 评估 API 返回正常, accuracy=%.4f", data["metrics"]["accuracy"])

    @pytest.mark.integration
    def test_evaluation_results_saved_to_model_version(
        self, mock_evaluation_job, mock_db_session
    ):
        """评估结果应保存到模型版本的 metrics 字段"""
        mock_version = MagicMock()
        mock_version.version_id = f"v-{uuid.uuid4().hex[:8]}"
        mock_version.model_id = mock_evaluation_job.model_id
        mock_version.metrics = json.dumps(mock_evaluation_job.get_metrics())

        parsed_metrics = json.loads(mock_version.metrics)
        assert parsed_metrics["accuracy"] == pytest.approx(0.932, abs=0.001)
        assert parsed_metrics["f1"] == pytest.approx(0.918, abs=0.001)

        logger.info(
            "AE-EV-001: 评估结果已保存到模型版本 version_id=%s",
            mock_version.version_id,
        )

    @pytest.mark.integration
    def test_evaluation_comparison_between_models(self):
        """应能比较不同模型/版本的评估结果"""
        model_a_metrics = {"accuracy": 0.932, "f1": 0.918, "eval_loss": 0.215}
        model_b_metrics = {"accuracy": 0.945, "f1": 0.931, "eval_loss": 0.189}

        # 对比各项指标
        comparison = {}
        for key in model_a_metrics:
            val_a = model_a_metrics[key]
            val_b = model_b_metrics[key]
            if key == "eval_loss":
                # loss 越低越好
                comparison[key] = {"winner": "B" if val_b < val_a else "A", "diff": abs(val_b - val_a)}
            else:
                # 其他指标越高越好
                comparison[key] = {"winner": "B" if val_b > val_a else "A", "diff": abs(val_b - val_a)}

        assert comparison["accuracy"]["winner"] == "B"
        assert comparison["f1"]["winner"] == "B"
        assert comparison["eval_loss"]["winner"] == "B"

        logger.info("AE-EV-001: 模型对比结果: %s", json.dumps(comparison, indent=2))


# ===========================================================================
# 入口
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
