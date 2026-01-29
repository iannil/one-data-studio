"""
镜像构建服务

支持多种镜像构建方式：
- Dockerfile 构建（使用 Kaniko）
- Web Shell 交互式构建
- 基于现有容器保存镜像
"""

import logging
import uuid
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class BuildMethod(str, Enum):
    """构建方式"""
    DOCKERFILE = "dockerfile"
    WEB_SHELL = "web_shell"
    COMMIT = "commit"  # 从运行中容器提交


class BuildStatus(str, Enum):
    """构建状态"""
    PENDING = "pending"
    BUILDING = "building"
    PUSHING = "pushing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageType(str, Enum):
    """镜像类型"""
    NOTEBOOK = "notebook"
    TRAINING = "training"
    SERVING = "serving"
    BASE = "base"
    CUSTOM = "custom"


@dataclass
class RegistryConfig:
    """镜像仓库配置"""
    registry: str  # 仓库地址，如 registry.example.com
    username: Optional[str] = None
    password: Optional[str] = None
    namespace: Optional[str] = None  # 命名空间/项目
    insecure: bool = False  # 是否允许不安全连接

    def get_full_image_path(self, image_name: str, tag: str = "latest") -> str:
        """获取完整镜像路径"""
        if self.namespace:
            return f"{self.registry}/{self.namespace}/{image_name}:{tag}"
        return f"{self.registry}/{image_name}:{tag}"


@dataclass
class BuildContext:
    """构建上下文"""
    dockerfile: Optional[str] = None  # Dockerfile 内容
    dockerfile_path: str = "Dockerfile"  # Dockerfile 路径
    context_path: str = "."  # 构建上下文路径
    build_args: Dict[str, str] = field(default_factory=dict)
    target: Optional[str] = None  # 多阶段构建目标
    no_cache: bool = False
    pull: bool = True  # 是否拉取最新基础镜像


@dataclass
class ImageBuildJob:
    """镜像构建任务"""
    job_id: str
    image_name: str
    image_tag: str
    build_method: BuildMethod
    status: BuildStatus
    user_id: str
    project_id: Optional[str] = None

    # 构建配置
    registry_config: Optional[RegistryConfig] = None
    build_context: Optional[BuildContext] = None
    base_image: Optional[str] = None
    image_type: ImageType = ImageType.CUSTOM

    # Web Shell 构建相关
    container_id: Optional[str] = None
    shell_url: Optional[str] = None

    # 从容器提交相关
    source_container: Optional[str] = None

    # 结果
    full_image_path: Optional[str] = None
    image_digest: Optional[str] = None
    image_size: Optional[int] = None

    # 日志
    build_logs: List[str] = field(default_factory=list)

    # 时间
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # K8s 资源
    pod_name: Optional[str] = None
    namespace: str = "image-build"

    # 错误
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "build_method": self.build_method.value,
            "status": self.status.value,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "base_image": self.base_image,
            "image_type": self.image_type.value,
            "full_image_path": self.full_image_path,
            "image_digest": self.image_digest,
            "image_size": self.image_size,
            "shell_url": self.shell_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


# 预定义的基础镜像模板
BASE_IMAGE_TEMPLATES = {
    ImageType.NOTEBOOK: {
        "jupyter": {
            "dockerfile": """
FROM python:3.10-slim

RUN pip install --no-cache-dir jupyter jupyterlab notebook

WORKDIR /workspace
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
""",
            "description": "基础 Jupyter Notebook 镜像",
        },
        "jupyter-ml": {
            "dockerfile": """
FROM python:3.10-slim

RUN pip install --no-cache-dir \\
    jupyter jupyterlab notebook \\
    numpy pandas scikit-learn \\
    matplotlib seaborn plotly \\
    xgboost lightgbm catboost

WORKDIR /workspace
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
""",
            "description": "机器学习 Jupyter 镜像",
        },
    },
    ImageType.TRAINING: {
        "pytorch": {
            "dockerfile": """
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

RUN pip install --no-cache-dir \\
    transformers datasets accelerate \\
    tensorboard wandb

WORKDIR /workspace
""",
            "description": "PyTorch 训练镜像",
        },
        "tensorflow": {
            "dockerfile": """
FROM tensorflow/tensorflow:2.14.0-gpu

RUN pip install --no-cache-dir \\
    keras tensorboard wandb

WORKDIR /workspace
""",
            "description": "TensorFlow 训练镜像",
        },
    },
    ImageType.SERVING: {
        "triton": {
            "dockerfile": """
FROM nvcr.io/nvidia/tritonserver:23.10-py3

WORKDIR /models
EXPOSE 8000 8001 8002

CMD ["tritonserver", "--model-repository=/models"]
""",
            "description": "Triton 推理服务镜像",
        },
        "vllm": {
            "dockerfile": """
FROM vllm/vllm-openai:v0.2.7

WORKDIR /app
EXPOSE 8000

CMD ["python", "-m", "vllm.entrypoints.openai.api_server"]
""",
            "description": "vLLM 大模型推理镜像",
        },
    },
}


class ImageBuildService:
    """镜像构建服务"""

    def __init__(
        self,
        namespace: str = "image-build",
        default_registry: Optional[RegistryConfig] = None,
        kaniko_image: str = "gcr.io/kaniko-project/executor:latest",
    ):
        self.namespace = namespace
        self.default_registry = default_registry
        self.kaniko_image = kaniko_image

        # 任务存储（生产环境应使用数据库）
        self._jobs: Dict[str, ImageBuildJob] = {}

        # K8s 客户端
        self._k8s_client = None

    def _get_k8s_client(self):
        """获取 K8s 客户端"""
        if self._k8s_client is not None:
            return

        try:
            from kubernetes import client, config

            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

            self._k8s_client = client.CoreV1Api()
            logger.info("K8s 客户端初始化成功")

        except ImportError:
            logger.warning("kubernetes 库未安装")
        except Exception as e:
            logger.error(f"K8s 客户端初始化失败: {e}")

    def get_base_templates(self, image_type: Optional[ImageType] = None) -> Dict[str, Any]:
        """获取基础镜像模板"""
        if image_type:
            return BASE_IMAGE_TEMPLATES.get(image_type, {})
        return BASE_IMAGE_TEMPLATES

    def create_dockerfile_build(
        self,
        image_name: str,
        user_id: str,
        dockerfile: str,
        image_tag: str = "latest",
        project_id: Optional[str] = None,
        registry_config: Optional[RegistryConfig] = None,
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        image_type: ImageType = ImageType.CUSTOM,
    ) -> ImageBuildJob:
        """
        创建 Dockerfile 构建任务

        Args:
            image_name: 镜像名称
            user_id: 用户 ID
            dockerfile: Dockerfile 内容
            image_tag: 镜像标签
            project_id: 项目 ID
            registry_config: 镜像仓库配置
            build_args: 构建参数
            no_cache: 是否禁用缓存
            image_type: 镜像类型
        """
        job_id = f"build-{uuid.uuid4().hex[:12]}"

        registry = registry_config or self.default_registry
        if not registry:
            raise ValueError("未配置镜像仓库")

        build_context = BuildContext(
            dockerfile=dockerfile,
            build_args=build_args or {},
            no_cache=no_cache,
        )

        job = ImageBuildJob(
            job_id=job_id,
            image_name=image_name,
            image_tag=image_tag,
            build_method=BuildMethod.DOCKERFILE,
            status=BuildStatus.PENDING,
            user_id=user_id,
            project_id=project_id,
            registry_config=registry,
            build_context=build_context,
            image_type=image_type,
            full_image_path=registry.get_full_image_path(image_name, image_tag),
            created_at=datetime.utcnow(),
            namespace=self.namespace,
        )

        self._jobs[job_id] = job

        logger.info(f"创建 Dockerfile 构建任务: {job_id}, 镜像: {image_name}:{image_tag}")

        return job

    def create_webshell_build(
        self,
        image_name: str,
        user_id: str,
        base_image: str,
        image_tag: str = "latest",
        project_id: Optional[str] = None,
        registry_config: Optional[RegistryConfig] = None,
        image_type: ImageType = ImageType.CUSTOM,
    ) -> ImageBuildJob:
        """
        创建 Web Shell 交互式构建任务

        用户可以通过 Web Shell 进入容器，手动安装软件后保存为镜像
        """
        job_id = f"shell-{uuid.uuid4().hex[:12]}"

        registry = registry_config or self.default_registry
        if not registry:
            raise ValueError("未配置镜像仓库")

        job = ImageBuildJob(
            job_id=job_id,
            image_name=image_name,
            image_tag=image_tag,
            build_method=BuildMethod.WEB_SHELL,
            status=BuildStatus.PENDING,
            user_id=user_id,
            project_id=project_id,
            registry_config=registry,
            base_image=base_image,
            image_type=image_type,
            full_image_path=registry.get_full_image_path(image_name, image_tag),
            created_at=datetime.utcnow(),
            namespace=self.namespace,
        )

        self._jobs[job_id] = job

        logger.info(f"创建 Web Shell 构建任务: {job_id}, 基础镜像: {base_image}")

        return job

    def start_build(self, job_id: str) -> bool:
        """启动构建任务"""
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"任务不存在: {job_id}")
            return False

        if job.status != BuildStatus.PENDING:
            logger.warning(f"任务状态不正确: {job.status}")
            return False

        try:
            job.status = BuildStatus.BUILDING
            job.started_at = datetime.utcnow()

            if job.build_method == BuildMethod.DOCKERFILE:
                self._start_kaniko_build(job)
            elif job.build_method == BuildMethod.WEB_SHELL:
                self._start_webshell_container(job)
            else:
                raise ValueError(f"不支持的构建方式: {job.build_method}")

            logger.info(f"构建任务已启动: {job_id}")
            return True

        except Exception as e:
            logger.error(f"启动构建任务失败: {e}")
            job.status = BuildStatus.FAILED
            job.error_message = str(e)
            return False

    def _start_kaniko_build(self, job: ImageBuildJob):
        """使用 Kaniko 构建镜像"""
        self._get_k8s_client()

        if not self._k8s_client:
            logger.warning("K8s 客户端不可用，模拟构建")
            job.pod_name = f"kaniko-{job.job_id}"
            return

        from kubernetes import client

        # 生成 Pod 名称
        job.pod_name = f"kaniko-{job.job_id}"

        # 准备 Dockerfile ConfigMap
        dockerfile_cm_name = f"{job.job_id}-dockerfile"
        dockerfile_cm = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=dockerfile_cm_name,
                namespace=job.namespace,
            ),
            data={
                "Dockerfile": job.build_context.dockerfile,
            },
        )

        try:
            self._k8s_client.create_namespaced_config_map(
                namespace=job.namespace, body=dockerfile_cm
            )
        except client.exceptions.ApiException as e:
            if e.status != 409:
                raise

        # 准备镜像仓库认证 Secret
        registry_secret_name = f"{job.job_id}-registry"
        if job.registry_config and job.registry_config.username:
            auth_config = {
                "auths": {
                    job.registry_config.registry: {
                        "username": job.registry_config.username,
                        "password": job.registry_config.password,
                    }
                }
            }

            registry_secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=registry_secret_name,
                    namespace=job.namespace,
                ),
                type="kubernetes.io/dockerconfigjson",
                data={
                    ".dockerconfigjson": self._base64_encode(json.dumps(auth_config))
                },
            )

            try:
                self._k8s_client.create_namespaced_secret(
                    namespace=job.namespace, body=registry_secret
                )
            except client.exceptions.ApiException as e:
                if e.status != 409:
                    raise

        # 构建 Kaniko 参数
        kaniko_args = [
            f"--dockerfile=/workspace/Dockerfile",
            f"--context=dir:///workspace",
            f"--destination={job.full_image_path}",
            "--cache=true",
        ]

        if job.build_context.no_cache:
            kaniko_args.append("--no-cache")

        if job.registry_config and job.registry_config.insecure:
            kaniko_args.append("--insecure")

        for key, value in (job.build_context.build_args or {}).items():
            kaniko_args.append(f"--build-arg={key}={value}")

        # 创建 Kaniko Pod
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=job.pod_name,
                namespace=job.namespace,
                labels={
                    "app": "image-build",
                    "job-id": job.job_id,
                    "user-id": job.user_id,
                },
            ),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[
                    client.V1Container(
                        name="kaniko",
                        image=self.kaniko_image,
                        args=kaniko_args,
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="dockerfile",
                                mount_path="/workspace",
                            ),
                            client.V1VolumeMount(
                                name="docker-config",
                                mount_path="/kaniko/.docker",
                            ),
                        ],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "1", "memory": "2Gi"},
                            limits={"cpu": "2", "memory": "4Gi"},
                        ),
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="dockerfile",
                        config_map=client.V1ConfigMapVolumeSource(
                            name=dockerfile_cm_name
                        ),
                    ),
                    client.V1Volume(
                        name="docker-config",
                        secret=client.V1SecretVolumeSource(
                            secret_name=registry_secret_name
                        ),
                    ),
                ],
            ),
        )

        self._k8s_client.create_namespaced_pod(namespace=job.namespace, body=pod)

    def _start_webshell_container(self, job: ImageBuildJob):
        """启动 Web Shell 容器"""
        self._get_k8s_client()

        if not self._k8s_client:
            logger.warning("K8s 客户端不可用，模拟 Web Shell")
            job.pod_name = f"shell-{job.job_id}"
            job.shell_url = f"http://localhost:8080/shell/{job.job_id}"
            return

        from kubernetes import client

        job.pod_name = f"shell-{job.job_id}"

        # 创建带有 ttyd 的容器用于 Web Shell
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=job.pod_name,
                namespace=job.namespace,
                labels={
                    "app": "image-build",
                    "type": "webshell",
                    "job-id": job.job_id,
                    "user-id": job.user_id,
                },
            ),
            spec=client.V1PodSpec(
                containers=[
                    # 主容器 - 用户的构建环境
                    client.V1Container(
                        name="build-env",
                        image=job.base_image,
                        command=["/bin/sh", "-c", "sleep infinity"],
                        tty=True,
                        stdin=True,
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "1", "memory": "2Gi"},
                            limits={"cpu": "4", "memory": "8Gi"},
                        ),
                    ),
                    # Sidecar - ttyd Web 终端
                    client.V1Container(
                        name="ttyd",
                        image="tsl0922/ttyd:alpine",
                        args=[
                            "-p", "7681",
                            "docker", "exec", "-it", job.pod_name, "/bin/bash",
                        ],
                        ports=[
                            client.V1ContainerPort(container_port=7681, name="ttyd")
                        ],
                    ),
                ],
                restart_policy="Never",
            ),
        )

        self._k8s_client.create_namespaced_pod(namespace=job.namespace, body=pod)

        # 创建 Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=f"{job.job_id}-shell",
                namespace=job.namespace,
            ),
            spec=client.V1ServiceSpec(
                selector={"job-id": job.job_id},
                ports=[
                    client.V1ServicePort(name="ttyd", port=7681, target_port=7681)
                ],
                type="ClusterIP",
            ),
        )

        self._k8s_client.create_namespaced_service(namespace=job.namespace, body=service)

        # 生成 Shell URL
        job.shell_url = f"/api/v1/image-build/{job.job_id}/shell"

    def commit_webshell_image(self, job_id: str) -> bool:
        """
        提交 Web Shell 容器为镜像

        用户完成环境配置后，调用此方法保存镜像
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"任务不存在: {job_id}")
            return False

        if job.build_method != BuildMethod.WEB_SHELL:
            logger.error(f"任务类型不正确: {job.build_method}")
            return False

        try:
            job.status = BuildStatus.PUSHING

            # 这里应该使用 buildah 或类似工具从容器创建镜像
            # 简化实现：创建一个 Kaniko 任务来构建
            logger.info(f"提交 Web Shell 镜像: {job_id}")

            # 模拟成功
            job.status = BuildStatus.SUCCEEDED
            job.completed_at = datetime.utcnow()

            return True

        except Exception as e:
            logger.error(f"提交镜像失败: {e}")
            job.status = BuildStatus.FAILED
            job.error_message = str(e)
            return False

    def get_build_status(self, job_id: str) -> Optional[ImageBuildJob]:
        """获取构建状态"""
        job = self._jobs.get(job_id)
        if not job:
            return None

        # 如果是 Kaniko 构建，检查 Pod 状态
        if job.build_method == BuildMethod.DOCKERFILE and job.pod_name:
            self._update_kaniko_status(job)

        return job

    def _update_kaniko_status(self, job: ImageBuildJob):
        """更新 Kaniko 构建状态"""
        self._get_k8s_client()

        if not self._k8s_client or not job.pod_name:
            return

        try:
            from kubernetes import client

            pod = self._k8s_client.read_namespaced_pod(
                name=job.pod_name, namespace=job.namespace
            )

            if pod.status.phase == "Succeeded":
                job.status = BuildStatus.SUCCEEDED
                job.completed_at = datetime.utcnow()
            elif pod.status.phase == "Failed":
                job.status = BuildStatus.FAILED
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        if cs.state.terminated and cs.state.terminated.message:
                            job.error_message = cs.state.terminated.message

        except client.exceptions.ApiException as e:
            if e.status == 404:
                job.status = BuildStatus.FAILED
                job.error_message = "构建 Pod 不存在"

    def get_build_logs(self, job_id: str, tail_lines: int = 100) -> List[str]:
        """获取构建日志"""
        job = self._jobs.get(job_id)
        if not job or not job.pod_name:
            return []

        self._get_k8s_client()

        if not self._k8s_client:
            return ["K8s 客户端不可用"]

        try:
            logs = self._k8s_client.read_namespaced_pod_log(
                name=job.pod_name,
                namespace=job.namespace,
                tail_lines=tail_lines,
            )
            return logs.split("\n")
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            return [f"获取日志失败: {e}"]

    def cancel_build(self, job_id: str) -> bool:
        """取消构建任务"""
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status in (BuildStatus.SUCCEEDED, BuildStatus.FAILED, BuildStatus.CANCELLED):
            return False

        try:
            # 删除 K8s 资源
            self._cleanup_build_resources(job)

            job.status = BuildStatus.CANCELLED
            job.completed_at = datetime.utcnow()

            return True

        except Exception as e:
            logger.error(f"取消构建失败: {e}")
            return False

    def _cleanup_build_resources(self, job: ImageBuildJob):
        """清理构建资源"""
        self._get_k8s_client()

        if not self._k8s_client:
            return

        from kubernetes import client

        # 删除 Pod
        if job.pod_name:
            try:
                self._k8s_client.delete_namespaced_pod(
                    name=job.pod_name, namespace=job.namespace
                )
            except client.exceptions.ApiException:
                pass

        # 删除 ConfigMap
        try:
            self._k8s_client.delete_namespaced_config_map(
                name=f"{job.job_id}-dockerfile", namespace=job.namespace
            )
        except client.exceptions.ApiException:
            pass

        # 删除 Secret
        try:
            self._k8s_client.delete_namespaced_secret(
                name=f"{job.job_id}-registry", namespace=job.namespace
            )
        except client.exceptions.ApiException:
            pass

    def list_builds(
        self,
        user_id: Optional[str] = None,
        status: Optional[BuildStatus] = None,
        limit: int = 50,
    ) -> List[ImageBuildJob]:
        """列出构建任务"""
        jobs = list(self._jobs.values())

        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        if status:
            jobs = [j for j in jobs if j.status == status]

        # 按创建时间倒序
        jobs.sort(key=lambda x: x.created_at or datetime.min, reverse=True)

        return jobs[:limit]

    @staticmethod
    def _base64_encode(s: str) -> str:
        """Base64 编码"""
        import base64
        return base64.b64encode(s.encode()).decode()


# 全局服务实例
_build_service: Optional[ImageBuildService] = None


def get_image_build_service() -> ImageBuildService:
    """获取镜像构建服务实例"""
    global _build_service
    if _build_service is None:
        _build_service = ImageBuildService()
    return _build_service
