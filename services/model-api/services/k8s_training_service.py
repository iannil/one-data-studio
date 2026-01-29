"""
Kubernetes 训练任务服务

提供将训练任务提交到 Kubernetes 集群的功能：
- 创建 TrainingJob/PyTorchJob 资源
- 支持 GPU 资源调度
- 任务状态监控和日志流式获取
- 支持分布式训练
"""

import logging
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
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


@dataclass
class GPUResource:
    """GPU 资源配置"""
    count: int = 1
    type: str = "nvidia.com/gpu"  # GPU 类型标识
    memory: Optional[str] = None  # 每个GPU的内存 (如 "16Gi")


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
        """构建容器规格"""
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
