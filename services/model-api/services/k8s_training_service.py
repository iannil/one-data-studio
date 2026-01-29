"""
Kubernetes 训练任务服务

提供将训练任务提交到 Kubernetes 集群的功能：
- 创建 TrainingJob/PyTorchJob 资源
- 支持 GPU 资源调度
- 任务状态监控和日志流式获取
- 支持分布式训练
"""

import logging
import re
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class TrainingFramework(Enum):
    """训练框架"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    TRANSFORMERS = "transformers"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"


class JobType(Enum):
    """任务类型"""
    TRAINING = "training"
    FINE_TUNING = "fine-tuning"
    EVALUATION = "evaluation"
    INFERENCE = "inference"


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class AcceleratorType(Enum):
    """
    AI 加速器类型

    支持 NVIDIA GPU 及国产 AI 加速器：
    - 华为昇腾 NPU (Ascend 910/310)
    - 寒武纪 MLU
    - 天数智芯 GPU
    - 壁仞 GPU
    - 海光 DCU
    """
    NVIDIA_GPU = "nvidia.com/gpu"
    HUAWEI_NPU = "huawei.com/Ascend910"  # 华为昇腾 910
    HUAWEI_NPU_310 = "huawei.com/Ascend310"  # 华为昇腾 310
    CAMBRICON_MLU = "cambricon.com/mlu"  # 寒武纪
    ILUVATAR_GPU = "iluvatar.ai/gpu"  # 天数智芯
    BIREN_GPU = "biren.tech/gpu"  # 壁仞
    HYGON_DCU = "hygon.cn/dcu"  # 海光 DCU


@dataclass
class AcceleratorCapabilities:
    """
    加速器能力规格

    描述不同类型 AI 加速器的硬件能力和软件兼容性。
    """
    accelerator_type: AcceleratorType
    memory_gb: float  # 显存大小 (GB)
    fp16_tflops: float  # FP16 算力 (TFLOPS)
    bf16_tflops: float  # BF16 算力 (TFLOPS)
    fp32_tflops: float  # FP32 算力 (TFLOPS)
    supported_frameworks: List[str]  # 支持的训练框架
    driver_version: str = ""  # 驱动版本


# 常见加速器能力规格映射
ACCELERATOR_CAPABILITIES: Dict[AcceleratorType, AcceleratorCapabilities] = {
    AcceleratorType.NVIDIA_GPU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.NVIDIA_GPU,
        memory_gb=80.0,  # A100 80GB
        fp16_tflops=312.0,
        bf16_tflops=312.0,
        fp32_tflops=19.5,
        supported_frameworks=["pytorch", "tensorflow", "paddle", "mindspore"],
        driver_version="525.0+",
    ),
    AcceleratorType.HUAWEI_NPU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.HUAWEI_NPU,
        memory_gb=32.0,  # Ascend 910
        fp16_tflops=256.0,
        bf16_tflops=256.0,
        fp32_tflops=128.0,
        supported_frameworks=["mindspore", "pytorch"],  # 通过 CANN 支持
        driver_version="CANN 6.0+",
    ),
    AcceleratorType.HUAWEI_NPU_310: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.HUAWEI_NPU_310,
        memory_gb=16.0,  # Ascend 310
        fp16_tflops=22.0,
        bf16_tflops=22.0,
        fp32_tflops=11.0,
        supported_frameworks=["mindspore"],  # 主要用于推理
        driver_version="CANN 6.0+",
    ),
    AcceleratorType.CAMBRICON_MLU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.CAMBRICON_MLU,
        memory_gb=24.0,  # MLU370-X8
        fp16_tflops=128.0,
        bf16_tflops=128.0,
        fp32_tflops=48.0,
        supported_frameworks=["pytorch", "tensorflow"],  # 通过 Cambricon Neuware 支持
        driver_version="CNToolkit 3.0+",
    ),
    AcceleratorType.ILUVATAR_GPU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.ILUVATAR_GPU,
        memory_gb=32.0,  # BI-V100
        fp16_tflops=128.0,
        bf16_tflops=64.0,
        fp32_tflops=32.0,
        supported_frameworks=["pytorch", "tensorflow", "paddle"],
        driver_version="IXRT 3.0+",
    ),
    AcceleratorType.BIREN_GPU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.BIREN_GPU,
        memory_gb=32.0,  # BR100
        fp16_tflops=256.0,
        bf16_tflops=256.0,
        fp32_tflops=64.0,
        supported_frameworks=["pytorch", "tensorflow"],
        driver_version="BIRENSUPA 1.0+",
    ),
    AcceleratorType.HYGON_DCU: AcceleratorCapabilities(
        accelerator_type=AcceleratorType.HYGON_DCU,
        memory_gb=16.0,  # Z100L
        fp16_tflops=29.5,
        bf16_tflops=29.5,
        fp32_tflops=14.7,
        supported_frameworks=["pytorch", "tensorflow"],  # 通过 DTK 支持
        driver_version="DTK 23.04+",
    ),
}


def get_accelerator_node_selector(accelerator_type: AcceleratorType) -> Dict[str, str]:
    """
    获取加速器类型对应的节点选择器

    根据不同加速器类型返回适当的 K8s 节点选择器，用于将 Pod 调度到
    配备了指定加速器的节点上。

    Args:
        accelerator_type: 加速器类型

    Returns:
        节点选择器字典，包含 accelerator 类型标签
    """
    selector_map: Dict[AcceleratorType, Dict[str, str]] = {
        AcceleratorType.NVIDIA_GPU: {
            "accelerator": "nvidia-gpu",
            "nvidia.com/gpu.present": "true",
        },
        AcceleratorType.HUAWEI_NPU: {
            "accelerator": "huawei-npu",
            "huawei.com/Ascend910": "true",
        },
        AcceleratorType.HUAWEI_NPU_310: {
            "accelerator": "huawei-npu",
            "huawei.com/Ascend310": "true",
        },
        AcceleratorType.CAMBRICON_MLU: {
            "accelerator": "cambricon-mlu",
            "cambricon.com/mlu.present": "true",
        },
        AcceleratorType.ILUVATAR_GPU: {
            "accelerator": "iluvatar-gpu",
            "iluvatar.ai/gpu.present": "true",
        },
        AcceleratorType.BIREN_GPU: {
            "accelerator": "biren-gpu",
            "biren.tech/gpu.present": "true",
        },
        AcceleratorType.HYGON_DCU: {
            "accelerator": "hygon-dcu",
            "hygon.cn/dcu.present": "true",
        },
    }
    return selector_map.get(accelerator_type, {"accelerator": "nvidia-gpu"})


@dataclass
class GPUResource:
    """
    GPU/加速器资源配置

    支持 NVIDIA GPU 及国产 AI 加速器资源配置。
    """
    count: int = 1
    accelerator_type: AcceleratorType = AcceleratorType.NVIDIA_GPU
    memory: Optional[str] = None  # 每个加速器的显存 (如 "16Gi")

    @property
    def type(self) -> str:
        """获取加速器资源类型标识（用于 K8s 资源限制）"""
        return self.accelerator_type.value


@dataclass
class ResourceRequest:
    """资源请求"""
    cpu: str = "4"
    memory: str = "8Gi"
    gpu: Optional[GPUResource] = None
    storage: Optional[str] = None  # 临时存储

    def to_k8s_dict(self) -> Dict[str, Any]:
        """转换为 K8s 资源格式"""
        requests = {
            "cpu": self.cpu,
            "memory": self.memory,
        }
        limits = {
            "cpu": self.cpu,
            "memory": self.memory,
        }

        if self.gpu:
            limits[self.gpu.type] = str(self.gpu.count)

        if self.storage:
            requests["ephemeral-storage"] = self.storage
            limits["ephemeral-storage"] = self.storage

        return {
            "requests": requests,
            "limits": limits,
        }


@dataclass
class TrainingInput:
    """训练输入配置"""
    dataset_path: str  # 数据集路径 (MinIO/PV)
    model_path: Optional[str] = None  # 预训练模型路径
    config_path: Optional[str] = None  # 配置文件路径
    output_path: Optional[str] = None  # 输出路径


@dataclass
class Hyperparameters:
    """超参数配置"""
    learning_rate: float = 1e-4
    batch_size: int = 32
    epochs: int = 10
    warmup_steps: int = 0
    gradient_accumulation_steps: int = 1
    weight_decay: float = 0.01
    max_steps: Optional[int] = None
    save_steps: int = 500
    logging_steps: int = 100
    # LLM 特定参数
    lora_r: int = 8
    lora_alpha: int = 32
    lora_dropout: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "warmup_steps": self.warmup_steps,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "weight_decay": self.weight_decay,
            "max_steps": self.max_steps,
            "save_steps": self.save_steps,
            "logging_steps": self.logging_steps,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
        }


@dataclass
class TrainingJobSpec:
    """训练任务规格"""
    name: str
    framework: TrainingFramework
    job_type: JobType = JobType.TRAINING
    image: str = "python:3.10-slim"

    # 输入输出
    inputs: Optional[TrainingInput] = None
    output_path: str = "/mnt/models/output"

    # 训练配置
    command: Optional[List[str]] = None  # 自定义命令
    args: Optional[List[str]] = None  # 自定义参数
    working_dir: str = "/workspace"

    # 资源
    resources: Optional[ResourceRequest] = None
    num_workers: int = 1  # 分布式训练节点数
    node_selectors: Dict[str, str] = field(default_factory=dict)

    # 环境变量
    env_vars: Dict[str, str] = field(default_factory=dict)

    # 挂载卷
    volumes: List[Dict[str, Any]] = field(default_factory=list)

    # 超参数
    hyperparameters: Optional[Hyperparameters] = None


@dataclass
class JobResult:
    """任务执行结果"""
    job_id: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pod_name: Optional[str] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class K8sTrainingService:
    """
    Kubernetes 训练任务服务

    支持通过 Kubernetes Job 或 Training Operator 提交训练任务。
    """

    def __init__(
        self,
        namespace: str = "default",
        use_training_operator: bool = True,
        kube_config_path: Optional[str] = None,
    ):
        """
        初始化 K8s 训练服务

        Args:
            namespace: K8s 命名空间
            use_training_operator: 是否使用 Training Operator (如 Kubeflow Training Operator)
            kube_config_path: kubeconfig 路径，None 则使用集群内配置
        """
        self.namespace = namespace
        self.use_training_operator = use_training_operator
        self._kube_config_path = kube_config_path
        self._core_api = None
        self._batch_api = None
        self._custom_api = None

    def _ensure_clients(self):
        """确保 K8s 客户端已初始化"""
        if self._core_api is None:
            try:
                from kubernetes import client, config

                if self._kube_config_path:
                    config.load_kube_config(config_file=self._kube_config_path)
                else:
                    # 集群内配置
                    config.load_incluster_config()

                self._core_api = client.CoreV1Api()
                self._batch_api = client.BatchV1Api()
                self._custom_api = client.CustomObjectsApi()

                logger.info("Kubernetes clients initialized successfully")

            except ImportError:
                logger.error("kubernetes package not installed")
                raise ImportError(
                    "Please install kubernetes package: pip install kubernetes"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Kubernetes clients: {e}")
                raise

    def submit_training_job(
        self,
        spec: TrainingJobSpec,
    ) -> JobResult:
        """
        提交训练任务到 Kubernetes

        Args:
            spec: 训练任务规格

        Returns:
            任务结果
        """
        self._ensure_clients()

        job_id = f"train-{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()

        try:
            if self.use_training_operator and spec.framework == TrainingFramework.PYTORCH:
                # 使用 PyTorchJob (需要 Training Operator)
                return self._submit_pytorch_job(job_id, spec, start_time)
            else:
                # 使用标准 Kubernetes Job
                return self._submit_k8s_job(job_id, spec, start_time)

        except Exception as e:
            logger.error(f"Failed to submit training job: {e}")
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                error_message=str(e),
            )

    def _submit_k8s_job(
        self,
        job_id: str,
        spec: TrainingJobSpec,
        start_time: datetime,
    ) -> JobResult:
        """提交标准 Kubernetes Job"""
        from kubernetes import client

        # 构建容器规格
        container = self._build_container(spec)

        # 构建 Pod 模板
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                name=f"{spec.name}-pod",
                labels={"app": "training", "job-id": job_id},
            ),
            spec=client.V1PodSpec(
                containers=[container],
                restart_policy="OnFailure",
                volumes=self._build_volumes(spec),
            ),
        )

        # 添加节点选择器
        if spec.node_selectors:
            pod_template.spec.node_selector = spec.node_selectors

        # 构建 Job
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=f"{spec.name}-{job_id}",
                namespace=self.namespace,
                labels={"app": "training", "job-id": job_id},
            ),
            spec=client.V1JobSpec(
                template=pod_template,
                backoff_limit=3,
                ttl_seconds_after_finished=3600,  # 1小时后清理
            ),
        )

        # 创建 Job
        created_job = self._batch_api.create_namespaced_job(
            namespace=self.namespace,
            body=job,
        )

        logger.info(f"Created Kubernetes Job: {created_job.metadata.name}")

        return JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            started_at=start_time,
            pod_name=f"{spec.name}-{job_id}",
        )

    def _submit_pytorch_job(
        self,
        job_id: str,
        spec: TrainingJobSpec,
        start_time: datetime,
    ) -> JobResult:
        """提交 PyTorchJob (需要 Kubeflow Training Operator)"""
        # PyTorchJob CRD 格式
        pytorch_job = {
            "apiVersion": "kubeflow.org/v1",
            "kind": "PyTorchJob",
            "metadata": {
                "name": f"{spec.name}-{job_id}",
                "namespace": self.namespace,
                "labels": {"app": "training", "job-id": job_id},
            },
            "spec": {
                "pytorchReplicaSpecs": {
                    "Master": {
                        "replicas": 1,
                        "restartPolicy": "OnFailure",
                        "template": {
                            "metadata": {
                                "labels": {"app": "training", "job-id": job_id},
                            },
                            "spec": {
                                "containers": [self._build_container(spec, is_master=True)],
                                "volumes": self._build_volumes(spec),
                            },
                        },
                    },
                    "Worker": {
                        "replicas": max(0, spec.num_workers - 1),
                        "restartPolicy": "OnFailure",
                        "template": {
                            "metadata": {
                                "labels": {"app": "training", "job-id": job_id},
                            },
                            "spec": {
                                "containers": [self._build_container(spec, is_master=False)],
                                "volumes": self._build_volumes(spec),
                            },
                        },
                    },
                },
            },
        }

        # 添加节点选择器
        if spec.node_selectors:
            pytorch_job["spec"]["pytorchReplicaSpecs"]["Master"]["template"]["spec"][
                "nodeSelector"
            ] = spec.node_selectors
            if spec.num_workers > 1:
                pytorch_job["spec"]["pytorchReplicaSpecs"]["Worker"]["template"]["spec"][
                    "nodeSelector"
                ] = spec.node_selectors

        # 创建 PyTorchJob
        created_job = self._custom_api.create_namespaced_custom_object(
            group="kubeflow.org",
            version="v1",
            namespace=self.namespace,
            plural="pytorchjobs",
            body=pytorch_job,
        )

        logger.info(f"Created PyTorchJob: {created_job['metadata']['name']}")

        return JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            started_at=start_time,
            pod_name=f"{spec.name}-{job_id}-master-0",
        )

    def _build_container(
        self,
        spec: TrainingJobSpec,
        is_master: bool = True,
    ) -> Any:
        """
        构建容器规格

        根据任务规格构建 K8s 容器配置，包括：
        - 资源限制（CPU、内存、加速器）
        - 环境变量（包括加速器特定的环境变量）
        - 分布式训练配置
        - 超参数注入

        Args:
            spec: 训练任务规格
            is_master: 是否为主节点（用于分布式训练）

        Returns:
            K8s V1Container 对象
        """
        from kubernetes import client

        # 资源配置
        resources = None
        if spec.resources:
            resource_dict = spec.resources.to_k8s_dict()
            resources = client.V1ResourceRequirements(
                requests=resource_dict["requests"],
                limits=resource_dict["limits"],
            )

        # 环境变量
        env_list = []
        for name, value in spec.env_vars.items():
            env_list.append(client.V1EnvVar(name=name, value=value))

        # 加速器特定环境变量
        if spec.resources and spec.resources.gpu:
            accelerator_type = spec.resources.gpu.accelerator_type
            gpu_count = str(spec.resources.gpu.count)

            # 根据加速器类型设置相应的环境变量
            if accelerator_type == AcceleratorType.NVIDIA_GPU:
                env_list.extend([
                    client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value="all"),
                    client.V1EnvVar(name="CUDA_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                ])
            elif accelerator_type in (AcceleratorType.HUAWEI_NPU, AcceleratorType.HUAWEI_NPU_310):
                # 华为昇腾 NPU 环境变量
                env_list.extend([
                    client.V1EnvVar(name="ASCEND_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="ASCEND_DEVICE_ID", value="0"),
                    client.V1EnvVar(name="ASCEND_GLOBAL_LOG_LEVEL", value="3"),  # 0-DEBUG, 1-INFO, 2-WARNING, 3-ERROR
                    client.V1EnvVar(name="HCCL_WHITELIST_DISABLE", value="1"),  # 关闭白名单以支持更多网络配置
                ])
            elif accelerator_type == AcceleratorType.CAMBRICON_MLU:
                # 寒武纪 MLU 环境变量
                env_list.extend([
                    client.V1EnvVar(name="MLU_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="CNCL_DEBUG", value="INFO"),  # 寒武纪集合通信库调试级别
                ])
            elif accelerator_type == AcceleratorType.ILUVATAR_GPU:
                # 天数智芯 GPU 环境变量
                env_list.extend([
                    client.V1EnvVar(name="ILUVATAR_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="IXRT_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                ])
            elif accelerator_type == AcceleratorType.BIREN_GPU:
                # 壁仞 GPU 环境变量
                env_list.extend([
                    client.V1EnvVar(name="BIREN_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="SUPA_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                ])
            elif accelerator_type == AcceleratorType.HYGON_DCU:
                # 海光 DCU 环境变量（类似 AMD ROCm）
                env_list.extend([
                    client.V1EnvVar(name="HIP_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="ROCR_VISIBLE_DEVICES", value=",".join(str(i) for i in range(spec.resources.gpu.count))),
                    client.V1EnvVar(name="HSA_FORCE_FINE_GRAIN_PCIE", value="1"),
                ])

            # 添加加速器类型标识环境变量（供训练脚本识别）
            env_list.append(
                client.V1EnvVar(name="ACCELERATOR_TYPE", value=accelerator_type.name)
            )
            env_list.append(
                client.V1EnvVar(name="ACCELERATOR_COUNT", value=gpu_count)
            )

        # 分布式训练环境变量
        if spec.num_workers > 1:
            env_list.extend([
                client.V1EnvVar(name="WORLD_SIZE", value=str(spec.num_workers)),
                client.V1EnvVar(name="NCCL_DEBUG", value="INFO"),
            ])
            if is_master:
                env_list.append(client.V1EnvVar(name="RANK", value="0"))
            else:
                env_list.append(client.V1EnvVar(name="RANK", value="1"))

        # 超参数环境变量
        if spec.hyperparameters:
            for key, value in spec.hyperparameters.to_dict().items():
                env_list.append(
                    client.V1EnvVar(name=f"HP_{key.upper()}", value=str(value))
                )

        # 输入输出路径环境变量
        if spec.inputs:
            if spec.inputs.dataset_path:
                env_list.append(
                    client.V1EnvVar(name="DATASET_PATH", value=spec.inputs.dataset_path)
                )
            if spec.inputs.model_path:
                env_list.append(
                    client.V1EnvVar(name="MODEL_PATH", value=spec.inputs.model_path)
                )
        env_list.append(
            client.V1EnvVar(name="OUTPUT_PATH", value=spec.output_path)
        )

        return client.V1Container(
            name="trainer",
            image=spec.image,
            command=spec.command,
            args=spec.args,
            working_dir=spec.working_dir,
            resources=resources,
            env=env_list,
            volume_mounts=[
                client.V1VolumeMount(
                    name="data",
                    mount_path="/data",
                    read_only=True,
                ),
                client.V1VolumeMount(
                    name="output",
                    mount_path=spec.output_path,
                ),
            ],
        )

    def _build_volumes(self, spec: TrainingJobSpec) -> List[Any]:
        """构建卷规格"""
        from kubernetes import client

        volumes = [
            # 数据集卷 (PVC 或 hostPath)
            client.V1Volume(
                name="data",
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                    claim_name="training-dataset-pvc",
                    read_only=True,
                ),
            ),
            # 输出卷
            client.V1Volume(
                name="output",
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                    claim_name="training-output-pvc",
                ),
            ),
        ]

        # 添加自定义卷
        for volume_spec in spec.volumes:
            volumes.append(client.V1Volume(**volume_spec))

        return volumes

    def get_job_status(self, job_id: str, job_name: str) -> JobStatus:
        """
        获取任务状态

        Args:
            job_id: 任务ID
            job_name: Job名称

        Returns:
            任务状态
        """
        self._ensure_clients()

        try:
            # 尝试获取 PyTorchJob 状态
            if self.use_training_operator:
                try:
                    pytorch_job = self._custom_api.get_namespaced_custom_object(
                        group="kubeflow.org",
                        version="v1",
                        namespace=self.namespace,
                        plural="pytorchjobs",
                        name=job_name,
                    )
                    condition = pytorch_job.get("status", {}).get("conditions", [])
                    if condition:
                        status_type = condition[0].get("type", "")
                        if status_type == "Succeeded":
                            return JobStatus.SUCCEEDED
                        elif status_type == "Failed":
                            return JobStatus.FAILED
                        elif status_type == "Running":
                            return JobStatus.RUNNING
                except Exception:
                    pass

            # 回退到标准 Job 状态
            job = self._batch_api.read_namespaced_job_status(
                name=job_name,
                namespace=self.namespace,
            )

            if job.status.succeeded:
                return JobStatus.SUCCEEDED
            elif job.status.failed:
                return JobStatus.FAILED
            elif job.status.active:
                return JobStatus.RUNNING
            else:
                return JobStatus.PENDING

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return JobStatus.UNKNOWN

    def get_job_logs(
        self,
        job_name: str,
        follow: bool = False,
        tail_lines: int = 100,
    ) -> str:
        """
        获取任务日志

        Args:
            job_name: Job名称
            follow: 是否持续跟随日志
            tail_lines: 返回最后几行

        Returns:
            日志内容
        """
        self._ensure_clients()

        try:
            # 获取 Pod 名称
            pods = self._core_api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"job-name={job_name}",
            )

            if not pods.items:
                return "No pods found for this job"

            pod_name = pods.items[0].metadata.name

            # 获取日志
            logs = self._core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                follow=follow,
                tail_lines=tail_lines,
            )

            return logs

        except Exception as e:
            logger.error(f"Failed to get job logs: {e}")
            return f"Error getting logs: {str(e)}"

    def cancel_job(self, job_name: str) -> bool:
        """
        取消任务

        Args:
            job_name: Job名称

        Returns:
            是否成功取消
        """
        self._ensure_clients()
        from kubernetes import client

        try:
            # 尝试删除 PyTorchJob
            if self.use_training_operator:
                try:
                    self._custom_api.delete_namespaced_custom_object(
                        group="kubeflow.org",
                        version="v1",
                        namespace=self.namespace,
                        plural="pytorchjobs",
                        name=job_name,
                    )
                    logger.info(f"Cancelled PyTorchJob: {job_name}")
                    return True
                except Exception:
                    pass

            # 删除标准 Job
            self._batch_api.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(),
            )
            logger.info(f"Cancelled Job: {job_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            return False

    def list_jobs(self, label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有训练任务

        Args:
            label_selector: 标签选择器

        Returns:
            任务列表
        """
        self._ensure_clients()

        jobs = []

        # 列出标准 Jobs
        try:
            k8s_jobs = self._batch_api.list_namespaced_job(
                namespace=self.namespace,
                label_selector=label_selector or "app=training",
            )

            for job in k8s_jobs.items:
                jobs.append({
                    "name": job.metadata.name,
                    "type": "Job",
                    "status": self._get_job_status_from_k8s(job),
                    "created_at": job.metadata.creation_timestamp.isoformat(),
                    "labels": job.metadata.labels,
                })

        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")

        # 列出 PyTorchJobs
        if self.use_training_operator:
            try:
                pytorch_jobs = self._custom_api.list_namespaced_custom_object(
                    group="kubeflow.org",
                    version="v1",
                    namespace=self.namespace,
                    plural="pytorchjobs",
                    label_selector=label_selector or "app=training",
                )

                for job in pytorch_jobs.get("items", []):
                    jobs.append({
                        "name": job["metadata"]["name"],
                        "type": "PyTorchJob",
                        "status": self._get_pytorch_job_status(job),
                        "created_at": job["metadata"].get("creationTimestamp", ""),
                        "labels": job["metadata"].get("labels", {}),
                    })

            except Exception as e:
                logger.debug(f"Failed to list PyTorchJobs: {e}")

        return jobs

    def _get_job_status_from_k8s(self, job) -> str:
        """从 K8s Job 对象获取状态"""
        if job.status.succeeded:
            return "succeeded"
        elif job.status.failed:
            return "failed"
        elif job.status.active:
            return "running"
        return "pending"

    def _get_pytorch_job_status(self, job: Dict) -> str:
        """从 PyTorchJob 对象获取状态"""
        conditions = job.get("status", {}).get("conditions", [])
        if conditions:
            return conditions[0].get("type", "Unknown").lower()
        return "pending"

    def wait_for_completion(
        self,
        job_name: str,
        timeout: int = 3600,
        poll_interval: int = 10,
    ) -> JobStatus:
        """
        轮询等待任务完成

        Args:
            job_name: Job名称
            timeout: 超时时间（秒），默认3600秒
            poll_interval: 轮询间隔（秒），默认10秒

        Returns:
            最终任务状态
        """
        start_time = time.time()
        terminal_statuses = {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

        logger.info(
            f"开始等待任务完成: {job_name}, 超时={timeout}s, 轮询间隔={poll_interval}s"
        )

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(f"等待任务超时: {job_name}, 已耗时 {elapsed:.0f}s")
                return JobStatus.UNKNOWN

            status = self.get_job_status(job_id="", job_name=job_name)

            if status in terminal_statuses:
                logger.info(
                    f"任务已完成: {job_name}, 状态={status.value}, 耗时={elapsed:.0f}s"
                )
                return status

            logger.debug(
                f"任务仍在运行: {job_name}, 状态={status.value}, 已耗时={elapsed:.0f}s"
            )
            time.sleep(poll_interval)

    def cleanup_completed_jobs(
        self,
        max_age_hours: int = 24,
        label_selector: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        清理已完成或失败的过期任务

        Args:
            max_age_hours: 最大保留时间（小时），默认24小时
            label_selector: 标签选择器

        Returns:
            清理统计 {"deleted": 数量, "failed_to_delete": 数量}
        """
        self._ensure_clients()
        from kubernetes import client

        cutoff_time = datetime.now().astimezone() - timedelta(hours=max_age_hours)
        stats = {"deleted": 0, "failed_to_delete": 0}

        logger.info(
            f"开始清理已完成的过期任务, 最大保留时间={max_age_hours}小时"
        )

        # 清理标准 Jobs
        try:
            k8s_jobs = self._batch_api.list_namespaced_job(
                namespace=self.namespace,
                label_selector=label_selector or "app=training",
            )

            for job in k8s_jobs.items:
                # 仅清理已完成或失败的任务
                if not (job.status.succeeded or job.status.failed):
                    continue

                # 检查创建时间是否早于截止时间
                created_at = job.metadata.creation_timestamp
                if created_at and created_at < cutoff_time:
                    try:
                        self._batch_api.delete_namespaced_job(
                            name=job.metadata.name,
                            namespace=self.namespace,
                            body=client.V1DeleteOptions(
                                propagation_policy="Background"
                            ),
                        )
                        stats["deleted"] += 1
                        logger.info(f"已删除过期任务: {job.metadata.name}")
                    except Exception as e:
                        stats["failed_to_delete"] += 1
                        logger.error(
                            f"删除任务失败: {job.metadata.name}, 错误: {e}"
                        )

        except Exception as e:
            logger.error(f"列出任务失败: {e}")

        # 清理 PyTorchJobs
        if self.use_training_operator:
            try:
                pytorch_jobs = self._custom_api.list_namespaced_custom_object(
                    group="kubeflow.org",
                    version="v1",
                    namespace=self.namespace,
                    plural="pytorchjobs",
                    label_selector=label_selector or "app=training",
                )

                for job in pytorch_jobs.get("items", []):
                    # 检查状态是否为已完成或失败
                    job_status = self._get_pytorch_job_status(job)
                    if job_status not in ("succeeded", "failed"):
                        continue

                    # 检查创建时间
                    created_str = job["metadata"].get("creationTimestamp", "")
                    if not created_str:
                        continue

                    created_at = datetime.fromisoformat(
                        created_str.replace("Z", "+00:00")
                    )
                    if created_at < cutoff_time:
                        try:
                            self._custom_api.delete_namespaced_custom_object(
                                group="kubeflow.org",
                                version="v1",
                                namespace=self.namespace,
                                plural="pytorchjobs",
                                name=job["metadata"]["name"],
                            )
                            stats["deleted"] += 1
                            logger.info(
                                f"已删除过期 PyTorchJob: {job['metadata']['name']}"
                            )
                        except Exception as e:
                            stats["failed_to_delete"] += 1
                            logger.error(
                                f"删除 PyTorchJob 失败: {job['metadata']['name']}, "
                                f"错误: {e}"
                            )

            except Exception as e:
                logger.debug(f"列出 PyTorchJobs 失败: {e}")

        logger.info(
            f"清理完成: 已删除 {stats['deleted']} 个, "
            f"失败 {stats['failed_to_delete']} 个"
        )
        return stats

    def get_job_events(
        self,
        job_name: str,
    ) -> List[Dict[str, Any]]:
        """
        获取与任务相关的 Kubernetes 事件

        Args:
            job_name: Job名称

        Returns:
            事件列表，每个事件包含 type, reason, message, timestamp 等字段
        """
        self._ensure_clients()

        events = []

        try:
            # 获取与 Job 相关的事件
            field_selector = f"involvedObject.name={job_name}"
            event_list = self._core_api.list_namespaced_event(
                namespace=self.namespace,
                field_selector=field_selector,
            )

            for event in event_list.items:
                events.append({
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "timestamp": (
                        event.last_timestamp.isoformat()
                        if event.last_timestamp
                        else None
                    ),
                    "first_timestamp": (
                        event.first_timestamp.isoformat()
                        if event.first_timestamp
                        else None
                    ),
                    "count": event.count,
                    "source": (
                        event.source.component if event.source else None
                    ),
                })

            # 同时获取关联 Pod 的事件
            try:
                pods = self._core_api.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"job-name={job_name}",
                )

                for pod in pods.items:
                    pod_events = self._core_api.list_namespaced_event(
                        namespace=self.namespace,
                        field_selector=f"involvedObject.name={pod.metadata.name}",
                    )

                    for event in pod_events.items:
                        events.append({
                            "type": event.type,
                            "reason": event.reason,
                            "message": event.message,
                            "timestamp": (
                                event.last_timestamp.isoformat()
                                if event.last_timestamp
                                else None
                            ),
                            "first_timestamp": (
                                event.first_timestamp.isoformat()
                                if event.first_timestamp
                                else None
                            ),
                            "count": event.count,
                            "source": (
                                event.source.component if event.source else None
                            ),
                            "pod_name": pod.metadata.name,
                        })

            except Exception as e:
                logger.debug(f"获取 Pod 事件失败: {e}")

            # 按时间戳排序（最新的在前）
            events.sort(
                key=lambda e: e.get("timestamp") or "",
                reverse=True,
            )

        except Exception as e:
            logger.error(f"获取任务事件失败: {e}")

        return events

    def get_job_metrics(
        self,
        job_name: str,
        tail_lines: int = 1000,
        custom_patterns: Optional[Dict[str, str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        从训练日志中解析训练指标（loss、accuracy 等）

        通过正则表达式匹配日志中常见的训练指标输出格式。

        Args:
            job_name: Job名称
            tail_lines: 读取的日志行数，默认1000行
            custom_patterns: 自定义正则模式，格式为 {"指标名": "正则表达式"}
                            正则表达式中需要包含一个命名捕获组 (?P<value>...)

        Returns:
            指标字典，格式为 {"metric_name": [{"step": int, "value": float}, ...]}
        """
        # 获取日志内容
        logs = self.get_job_logs(job_name=job_name, tail_lines=tail_lines)

        if not logs or logs.startswith("Error") or logs.startswith("No pods"):
            logger.warning(f"无法获取任务日志用于指标解析: {job_name}")
            return {}

        # 内置指标匹配模式
        # 支持常见格式如:
        #   loss: 0.1234, step 100/1000
        #   Epoch 1/10, loss=0.5678, accuracy=0.89
        #   [Step 500] train_loss: 0.234, eval_loss: 0.345
        default_patterns = {
            "loss": r"(?:^|[\s,\[])loss[=:\s]+(?P<value>[\d]+\.[\d]+)",
            "train_loss": r"train[_\s]?loss[=:\s]+(?P<value>[\d]+\.[\d]+)",
            "eval_loss": r"(?:eval|val)[_\s]?loss[=:\s]+(?P<value>[\d]+\.[\d]+)",
            "accuracy": r"(?:accuracy|acc)[=:\s]+(?P<value>[\d]+\.[\d]+)",
            "learning_rate": r"(?:learning[_\s]?rate|lr)[=:\s]+(?P<value>[\d]+\.?[\d]*(?:e[+-]?\d+)?)",
            "epoch": r"[Ee]poch[=:\s]+(?P<value>[\d]+)",
            "step": r"[Ss]tep[=:\s]+(?P<value>[\d]+)",
        }

        # 合并自定义模式
        if custom_patterns:
            default_patterns.update(custom_patterns)

        # 步数模式（用于关联指标和步数）
        step_pattern = re.compile(
            r"(?:[Ss]tep|[Ii]ter(?:ation)?)[=:\s#]+(\d+)"
        )
        epoch_pattern = re.compile(
            r"[Ee]poch[=:\s#]+(\d+)"
        )

        metrics: Dict[str, List[Dict[str, Any]]] = {}
        lines = logs.split("\n")

        for line_idx, line in enumerate(lines):
            # 尝试提取当前行的步数和 epoch
            current_step = None
            current_epoch = None

            step_match = step_pattern.search(line)
            if step_match:
                current_step = int(step_match.group(1))

            epoch_match = epoch_pattern.search(line)
            if epoch_match:
                current_epoch = int(epoch_match.group(1))

            # 匹配各项指标
            for metric_name, pattern in default_patterns.items():
                # epoch 和 step 已在上面单独处理
                if metric_name in ("epoch", "step"):
                    continue

                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group("value"))
                    except (ValueError, IndexError):
                        continue

                    if metric_name not in metrics:
                        metrics[metric_name] = []

                    entry: Dict[str, Any] = {
                        "value": value,
                        "line": line_idx + 1,
                    }
                    if current_step is not None:
                        entry["step"] = current_step
                    if current_epoch is not None:
                        entry["epoch"] = current_epoch

                    metrics[metric_name].append(entry)

        # 生成摘要日志
        if metrics:
            summary_parts = []
            for name, values in metrics.items():
                if values:
                    latest = values[-1]["value"]
                    summary_parts.append(f"{name}={latest}")
            logger.info(
                f"从任务 {job_name} 日志中解析到指标: {', '.join(summary_parts)}"
            )
        else:
            logger.info(f"未从任务 {job_name} 日志中解析到训练指标")

        return metrics

    def list_available_accelerators(self) -> List[Dict[str, Any]]:
        """
        列出集群中可用的 AI 加速器

        查询 Kubernetes 集群中各类型加速器的可用数量，包括 NVIDIA GPU
        以及国产 AI 加速器（华为昇腾、寒武纪、天数智芯、壁仞、海光等）。

        Returns:
            加速器列表，每个条目包含：
            - type: 加速器类型 (AcceleratorType 的值)
            - name: 加速器名称（中文）
            - total: 集群总数
            - available: 可用数量
            - nodes: 配备该加速器的节点数
            - capabilities: 加速器能力规格（如已知）
        """
        self._ensure_clients()

        # 加速器类型到中文名称的映射
        accelerator_names: Dict[AcceleratorType, str] = {
            AcceleratorType.NVIDIA_GPU: "NVIDIA GPU",
            AcceleratorType.HUAWEI_NPU: "华为昇腾 910",
            AcceleratorType.HUAWEI_NPU_310: "华为昇腾 310",
            AcceleratorType.CAMBRICON_MLU: "寒武纪 MLU",
            AcceleratorType.ILUVATAR_GPU: "天数智芯 GPU",
            AcceleratorType.BIREN_GPU: "壁仞 GPU",
            AcceleratorType.HYGON_DCU: "海光 DCU",
        }

        accelerators: List[Dict[str, Any]] = []

        try:
            # 获取所有节点
            nodes = self._core_api.list_node()

            # 统计各类型加速器
            accelerator_stats: Dict[AcceleratorType, Dict[str, int]] = {}

            for node in nodes.items:
                # 检查节点容量和可分配资源
                capacity = node.status.capacity or {}
                allocatable = node.status.allocatable or {}

                for accel_type in AcceleratorType:
                    resource_key = accel_type.value

                    if resource_key in capacity:
                        total_count = int(capacity.get(resource_key, 0))
                        available_count = int(allocatable.get(resource_key, 0))

                        if accel_type not in accelerator_stats:
                            accelerator_stats[accel_type] = {
                                "total": 0,
                                "available": 0,
                                "nodes": 0,
                            }

                        accelerator_stats[accel_type]["total"] += total_count
                        accelerator_stats[accel_type]["available"] += available_count
                        accelerator_stats[accel_type]["nodes"] += 1

            # 构建返回结果
            for accel_type, stats in accelerator_stats.items():
                entry: Dict[str, Any] = {
                    "type": accel_type.value,
                    "type_enum": accel_type.name,
                    "name": accelerator_names.get(accel_type, accel_type.name),
                    "total": stats["total"],
                    "available": stats["available"],
                    "nodes": stats["nodes"],
                }

                # 添加能力规格（如果已知）
                if accel_type in ACCELERATOR_CAPABILITIES:
                    caps = ACCELERATOR_CAPABILITIES[accel_type]
                    entry["capabilities"] = {
                        "memory_gb": caps.memory_gb,
                        "fp16_tflops": caps.fp16_tflops,
                        "bf16_tflops": caps.bf16_tflops,
                        "fp32_tflops": caps.fp32_tflops,
                        "supported_frameworks": caps.supported_frameworks,
                        "driver_version": caps.driver_version,
                    }

                accelerators.append(entry)

            # 按总数降序排序
            accelerators.sort(key=lambda x: x["total"], reverse=True)

            accel_summary = ", ".join(
                f"{a['name']}={a['total']}" for a in accelerators
            )
            logger.info(f"集群加速器统计: {accel_summary}")

        except Exception as e:
            logger.error(f"列出加速器失败: {e}")

        return accelerators


# 全局实例
_k8s_training_service: Optional[K8sTrainingService] = None


def get_k8s_training_service(
    namespace: str = "default",
    use_training_operator: bool = True,
) -> K8sTrainingService:
    """获取 K8s 训练服务单例"""
    global _k8s_training_service
    if _k8s_training_service is None:
        _k8s_training_service = K8sTrainingService(
            namespace=namespace,
            use_training_operator=use_training_operator,
        )
    return _k8s_training_service
