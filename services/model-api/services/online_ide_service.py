"""
在线 IDE 服务

支持多种在线开发环境：
- Jupyter Notebook/JupyterLab
- VSCode/Theia (code-server)
- RStudio
- Matlab (需授权)
- 大数据 Jupyter (Spark/Flink 环境)
- 机器学习/深度学习 Jupyter
"""

import logging
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class IDEType(str, Enum):
    """IDE 类型"""
    JUPYTER = "jupyter"
    JUPYTERLAB = "jupyterlab"
    VSCODE = "vscode"  # code-server
    THEIA = "theia"
    RSTUDIO = "rstudio"
    MATLAB = "matlab"
    # 专业版本
    JUPYTER_ML = "jupyter-ml"  # 机器学习版
    JUPYTER_DL = "jupyter-dl"  # 深度学习版
    JUPYTER_BIGDATA = "jupyter-bigdata"  # 大数据版


class IDEStatus(str, Enum):
    """IDE 状态"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class GPUShareMode(str, Enum):
    """GPU 共享模式"""
    EXCLUSIVE = "exclusive"  # 独占
    SHARED = "shared"  # 共享 (nvidia MPS)
    VGPU = "vgpu"  # 虚拟 GPU


@dataclass
class IDEImage:
    """IDE 镜像配置"""
    ide_type: IDEType
    image: str
    display_name: str
    description: str = ""
    python_version: Optional[str] = None
    cuda_version: Optional[str] = None
    default_port: int = 8888
    health_check_path: str = "/api/status"
    supported_features: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ide_type": self.ide_type.value,
            "image": self.image,
            "display_name": self.display_name,
            "description": self.description,
            "python_version": self.python_version,
            "cuda_version": self.cuda_version,
            "default_port": self.default_port,
            "supported_features": self.supported_features,
        }


# 预定义镜像配置
PREDEFINED_IMAGES: Dict[IDEType, List[IDEImage]] = {
    IDEType.JUPYTER: [
        IDEImage(
            ide_type=IDEType.JUPYTER,
            image="jupyter/minimal-notebook:python-3.10",
            display_name="Jupyter Notebook (Python 3.10)",
            description="基础 Jupyter Notebook 环境",
            python_version="3.10",
            default_port=8888,
            health_check_path="/api/status",
            supported_features=["notebook", "terminal", "file_browser"],
        ),
        IDEImage(
            ide_type=IDEType.JUPYTER,
            image="jupyter/minimal-notebook:python-3.11",
            display_name="Jupyter Notebook (Python 3.11)",
            python_version="3.11",
            default_port=8888,
        ),
    ],
    IDEType.JUPYTERLAB: [
        IDEImage(
            ide_type=IDEType.JUPYTERLAB,
            image="jupyter/scipy-notebook:python-3.10",
            display_name="JupyterLab (SciPy)",
            description="包含 SciPy、Pandas、Matplotlib 等科学计算库",
            python_version="3.10",
            default_port=8888,
            supported_features=["notebook", "terminal", "file_browser", "git"],
        ),
    ],
    IDEType.VSCODE: [
        IDEImage(
            ide_type=IDEType.VSCODE,
            image="codercom/code-server:4.19.0",
            display_name="VS Code (code-server)",
            description="基于 code-server 的在线 VS Code",
            python_version="3.10",
            default_port=8080,
            health_check_path="/healthz",
            supported_features=["editor", "terminal", "git", "extensions", "debug"],
        ),
        IDEImage(
            ide_type=IDEType.VSCODE,
            image="codercom/code-server:4.19.0-python",
            display_name="VS Code + Python",
            description="预装 Python 扩展的 VS Code",
            python_version="3.10",
            default_port=8080,
        ),
    ],
    IDEType.THEIA: [
        IDEImage(
            ide_type=IDEType.THEIA,
            image="theiaide/theia-python:1.35.0",
            display_name="Eclipse Theia (Python)",
            description="Eclipse Theia 在线 IDE",
            python_version="3.10",
            default_port=3000,
            health_check_path="/",
            supported_features=["editor", "terminal", "git", "extensions"],
        ),
    ],
    IDEType.RSTUDIO: [
        IDEImage(
            ide_type=IDEType.RSTUDIO,
            image="rocker/rstudio:4.3.1",
            display_name="RStudio Server",
            description="R 语言集成开发环境",
            default_port=8787,
            health_check_path="/",
            supported_features=["editor", "console", "plots", "packages"],
        ),
    ],
    IDEType.MATLAB: [
        IDEImage(
            ide_type=IDEType.MATLAB,
            image="mathworks/matlab:r2023b",
            display_name="MATLAB Online",
            description="MATLAB 在线版（需授权）",
            default_port=8888,
            supported_features=["editor", "command_window", "plots", "apps"],
        ),
    ],
    IDEType.JUPYTER_ML: [
        IDEImage(
            ide_type=IDEType.JUPYTER_ML,
            image="jupyter/scipy-notebook:python-3.10",
            display_name="机器学习版 Jupyter",
            description="包含 scikit-learn、XGBoost、LightGBM 等机器学习库",
            python_version="3.10",
            default_port=8888,
            supported_features=["notebook", "sklearn", "xgboost", "lightgbm"],
        ),
    ],
    IDEType.JUPYTER_DL: [
        IDEImage(
            ide_type=IDEType.JUPYTER_DL,
            image="jupyter/tensorflow-notebook:python-3.10",
            display_name="深度学习版 Jupyter (TensorFlow)",
            description="包含 TensorFlow、Keras 深度学习框架",
            python_version="3.10",
            cuda_version="11.8",
            default_port=8888,
            supported_features=["notebook", "tensorflow", "keras", "tensorboard"],
        ),
        IDEImage(
            ide_type=IDEType.JUPYTER_DL,
            image="jupyter/pytorch-notebook:python-3.10",
            display_name="深度学习版 Jupyter (PyTorch)",
            description="包含 PyTorch 深度学习框架",
            python_version="3.10",
            cuda_version="11.8",
            default_port=8888,
            supported_features=["notebook", "pytorch", "transformers"],
        ),
    ],
    IDEType.JUPYTER_BIGDATA: [
        IDEImage(
            ide_type=IDEType.JUPYTER_BIGDATA,
            image="jupyter/pyspark-notebook:python-3.10",
            display_name="大数据版 Jupyter (Spark)",
            description="包含 Apache Spark、PySpark 大数据处理框架",
            python_version="3.10",
            default_port=8888,
            supported_features=["notebook", "spark", "hadoop", "hive"],
        ),
    ],
}


@dataclass
class IDEResourceConfig:
    """IDE 资源配置"""
    cpu: str = "2"
    memory: str = "4Gi"
    gpu_count: int = 0
    gpu_type: Optional[str] = None  # nvidia-tesla-v100, nvidia-a100 等
    gpu_share_mode: GPUShareMode = GPUShareMode.EXCLUSIVE
    storage: str = "10Gi"

    def to_k8s_resources(self) -> Dict[str, Any]:
        """转换为 K8s 资源格式"""
        resources = {
            "requests": {
                "cpu": self.cpu,
                "memory": self.memory,
            },
            "limits": {
                "cpu": self.cpu,
                "memory": self.memory,
            },
        }

        if self.gpu_count > 0:
            if self.gpu_share_mode == GPUShareMode.VGPU:
                resources["limits"]["nvidia.com/vgpu"] = str(self.gpu_count)
            else:
                resources["limits"]["nvidia.com/gpu"] = str(self.gpu_count)

        return resources


@dataclass
class IDEInstance:
    """IDE 实例"""
    instance_id: str
    name: str
    ide_type: IDEType
    image: str
    status: IDEStatus
    user_id: str
    project_id: Optional[str] = None
    workspace: str = "/home/workspace"
    resources: IDEResourceConfig = field(default_factory=IDEResourceConfig)

    # 网络配置
    url: Optional[str] = None
    internal_url: Optional[str] = None
    port: int = 8888
    ssh_port: Optional[int] = None

    # 安全配置
    password_protected: bool = False
    password_hash: Optional[str] = None
    token: Optional[str] = None

    # 环境配置
    env_vars: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    init_script: Optional[str] = None

    # 时间
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # K8s 资源信息
    pod_name: Optional[str] = None
    service_name: Optional[str] = None
    ingress_name: Optional[str] = None
    namespace: str = "notebook"

    # 错误信息
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "name": self.name,
            "ide_type": self.ide_type.value,
            "image": self.image,
            "status": self.status.value,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "workspace": self.workspace,
            "resources": {
                "cpu": self.resources.cpu,
                "memory": self.resources.memory,
                "gpu_count": self.resources.gpu_count,
                "gpu_type": self.resources.gpu_type,
            },
            "url": self.url,
            "ssh_port": self.ssh_port,
            "password_protected": self.password_protected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "error_message": self.error_message,
        }


class OnlineIDEService:
    """在线 IDE 服务"""

    def __init__(
        self,
        namespace: str = "notebook",
        base_domain: Optional[str] = None,
        storage_class: str = "standard",
        default_expiry_days: int = 3,
    ):
        self.namespace = namespace
        self.base_domain = base_domain or "notebook.local"
        self.storage_class = storage_class
        self.default_expiry_days = default_expiry_days

        # 实例存储（生产环境应使用数据库）
        self._instances: Dict[str, IDEInstance] = {}

        # K8s 客户端
        self._k8s_client = None
        self._k8s_apps_client = None
        self._k8s_networking_client = None

    def _get_k8s_clients(self):
        """获取 K8s 客户端"""
        if self._k8s_client is not None:
            return

        try:
            from kubernetes import client, config

            # 尝试加载集群内配置，失败则使用 kubeconfig
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

            self._k8s_client = client.CoreV1Api()
            self._k8s_apps_client = client.AppsV1Api()
            self._k8s_networking_client = client.NetworkingV1Api()

            logger.info("K8s 客户端初始化成功")

        except ImportError:
            logger.warning("kubernetes 库未安装，K8s 功能不可用")
        except Exception as e:
            logger.error(f"K8s 客户端初始化失败: {e}")

    def get_available_images(self, ide_type: Optional[IDEType] = None) -> List[Dict[str, Any]]:
        """获取可用的 IDE 镜像列表"""
        images = []

        if ide_type:
            type_images = PREDEFINED_IMAGES.get(ide_type, [])
            images.extend([img.to_dict() for img in type_images])
        else:
            for ide_images in PREDEFINED_IMAGES.values():
                images.extend([img.to_dict() for img in ide_images])

        return images

    def create_instance(
        self,
        name: str,
        ide_type: IDEType,
        user_id: str,
        image: Optional[str] = None,
        project_id: Optional[str] = None,
        workspace: str = "/home/workspace",
        cpu: str = "2",
        memory: str = "4Gi",
        gpu_count: int = 0,
        gpu_type: Optional[str] = None,
        gpu_share_mode: GPUShareMode = GPUShareMode.EXCLUSIVE,
        storage: str = "10Gi",
        password_protected: bool = False,
        password: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        init_script: Optional[str] = None,
        expiry_days: Optional[int] = None,
    ) -> IDEInstance:
        """
        创建 IDE 实例

        Args:
            name: 实例名称
            ide_type: IDE 类型
            user_id: 用户 ID
            image: 镜像（可选，默认使用预定义镜像）
            project_id: 项目 ID
            workspace: 工作空间路径
            cpu: CPU 配额
            memory: 内存配额
            gpu_count: GPU 数量
            gpu_type: GPU 类型
            gpu_share_mode: GPU 共享模式
            storage: 存储大小
            password_protected: 是否启用密码保护
            password: 密码
            env_vars: 环境变量
            init_script: 初始化脚本
            expiry_days: 过期天数
        """
        instance_id = f"ide-{uuid.uuid4().hex[:12]}"

        # 选择镜像
        if not image:
            default_images = PREDEFINED_IMAGES.get(ide_type, [])
            if default_images:
                image = default_images[0].image
            else:
                raise ValueError(f"未找到 IDE 类型 {ide_type} 的默认镜像")

        # 获取默认端口
        default_port = 8888
        for img_list in PREDEFINED_IMAGES.values():
            for img in img_list:
                if img.image == image:
                    default_port = img.default_port
                    break

        # 计算过期时间
        expiry = expiry_days or self.default_expiry_days
        expires_at = datetime.utcnow() + timedelta(days=expiry)

        # 生成 token
        token = uuid.uuid4().hex

        # 创建资源配置
        resources = IDEResourceConfig(
            cpu=cpu,
            memory=memory,
            gpu_count=gpu_count,
            gpu_type=gpu_type,
            gpu_share_mode=gpu_share_mode,
            storage=storage,
        )

        # 创建实例
        instance = IDEInstance(
            instance_id=instance_id,
            name=name,
            ide_type=ide_type,
            image=image,
            status=IDEStatus.PENDING,
            user_id=user_id,
            project_id=project_id,
            workspace=workspace,
            resources=resources,
            port=default_port,
            password_protected=password_protected,
            token=token,
            env_vars=env_vars or {},
            init_script=init_script,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            namespace=self.namespace,
        )

        # 设置密码（如果启用）
        if password_protected and password:
            import hashlib
            instance.password_hash = hashlib.sha256(password.encode()).hexdigest()

        # 存储实例
        self._instances[instance_id] = instance

        logger.info(f"创建 IDE 实例: {instance_id}, 类型: {ide_type.value}, 用户: {user_id}")

        return instance

    def start_instance(self, instance_id: str) -> bool:
        """启动 IDE 实例"""
        instance = self._instances.get(instance_id)
        if not instance:
            logger.error(f"实例不存在: {instance_id}")
            return False

        if instance.status == IDEStatus.RUNNING:
            logger.info(f"实例已运行: {instance_id}")
            return True

        try:
            instance.status = IDEStatus.STARTING

            # 创建 K8s 资源
            self._create_k8s_resources(instance)

            instance.status = IDEStatus.RUNNING
            instance.started_at = datetime.utcnow()
            instance.last_active_at = datetime.utcnow()

            # 生成访问 URL
            instance.url = self._generate_url(instance)

            logger.info(f"IDE 实例启动成功: {instance_id}, URL: {instance.url}")
            return True

        except Exception as e:
            logger.error(f"启动 IDE 实例失败: {e}")
            instance.status = IDEStatus.ERROR
            instance.error_message = str(e)
            return False

    def stop_instance(self, instance_id: str) -> bool:
        """停止 IDE 实例"""
        instance = self._instances.get(instance_id)
        if not instance:
            logger.error(f"实例不存在: {instance_id}")
            return False

        if instance.status == IDEStatus.STOPPED:
            return True

        try:
            instance.status = IDEStatus.STOPPING

            # 删除 K8s 资源（保留 PVC）
            self._delete_k8s_resources(instance, keep_pvc=True)

            instance.status = IDEStatus.STOPPED
            instance.url = None

            logger.info(f"IDE 实例已停止: {instance_id}")
            return True

        except Exception as e:
            logger.error(f"停止 IDE 实例失败: {e}")
            instance.status = IDEStatus.ERROR
            instance.error_message = str(e)
            return False

    def delete_instance(self, instance_id: str, keep_data: bool = False) -> bool:
        """删除 IDE 实例"""
        instance = self._instances.get(instance_id)
        if not instance:
            logger.error(f"实例不存在: {instance_id}")
            return False

        try:
            # 删除 K8s 资源
            self._delete_k8s_resources(instance, keep_pvc=keep_data)

            # 从存储中移除
            del self._instances[instance_id]

            logger.info(f"IDE 实例已删除: {instance_id}")
            return True

        except Exception as e:
            logger.error(f"删除 IDE 实例失败: {e}")
            return False

    def get_instance(self, instance_id: str) -> Optional[IDEInstance]:
        """获取 IDE 实例"""
        return self._instances.get(instance_id)

    def list_instances(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[IDEStatus] = None,
        ide_type: Optional[IDEType] = None,
    ) -> List[IDEInstance]:
        """列出 IDE 实例"""
        instances = list(self._instances.values())

        if user_id:
            instances = [i for i in instances if i.user_id == user_id]
        if project_id:
            instances = [i for i in instances if i.project_id == project_id]
        if status:
            instances = [i for i in instances if i.status == status]
        if ide_type:
            instances = [i for i in instances if i.ide_type == ide_type]

        return instances

    def save_as_image(
        self,
        instance_id: str,
        image_name: str,
        image_tag: str = "latest",
        registry: Optional[str] = None,
    ) -> Optional[str]:
        """
        将实例环境保存为镜像

        Args:
            instance_id: 实例 ID
            image_name: 镜像名称
            image_tag: 镜像标签
            registry: 镜像仓库地址

        Returns:
            完整的镜像地址，失败返回 None
        """
        instance = self._instances.get(instance_id)
        if not instance:
            logger.error(f"实例不存在: {instance_id}")
            return None

        if instance.status != IDEStatus.RUNNING:
            logger.error(f"实例未运行，无法保存: {instance_id}")
            return None

        try:
            # 生成完整镜像地址
            if registry:
                full_image = f"{registry}/{image_name}:{image_tag}"
            else:
                full_image = f"{image_name}:{image_tag}"

            # 这里应该调用实际的镜像构建服务
            # 例如使用 Kaniko 或提交到镜像构建 Pipeline
            logger.info(f"镜像保存任务已提交: {full_image}")

            return full_image

        except Exception as e:
            logger.error(f"保存镜像失败: {e}")
            return None

    def _create_k8s_resources(self, instance: IDEInstance):
        """创建 K8s 资源"""
        self._get_k8s_clients()

        if not self._k8s_client:
            logger.warning("K8s 客户端不可用，跳过资源创建")
            # 模拟 URL 生成（开发环境）
            instance.pod_name = f"{instance.instance_id}-pod"
            instance.service_name = f"{instance.instance_id}-svc"
            return

        from kubernetes import client

        # 生成资源名称
        instance.pod_name = f"{instance.instance_id}"
        instance.service_name = f"{instance.instance_id}-svc"
        pvc_name = f"{instance.instance_id}-pvc"

        # 1. 创建 PVC（持久化存储）
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=pvc_name,
                namespace=instance.namespace,
                labels={
                    "app": "online-ide",
                    "instance-id": instance.instance_id,
                    "user-id": instance.user_id,
                },
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name=self.storage_class,
                resources=client.V1ResourceRequirements(
                    requests={"storage": instance.resources.storage}
                ),
            ),
        )

        try:
            self._k8s_client.create_namespaced_persistent_volume_claim(
                namespace=instance.namespace, body=pvc
            )
        except client.exceptions.ApiException as e:
            if e.status != 409:  # 忽略已存在
                raise

        # 2. 构建环境变量
        env_vars = [
            client.V1EnvVar(name="INSTANCE_ID", value=instance.instance_id),
            client.V1EnvVar(name="USER_ID", value=instance.user_id),
        ]

        if instance.password_protected and instance.password_hash:
            env_vars.append(client.V1EnvVar(name="IDE_PASSWORD", value=instance.password_hash))

        if instance.token:
            env_vars.append(client.V1EnvVar(name="IDE_TOKEN", value=instance.token))

        # 添加自定义环境变量
        for key, value in instance.env_vars.items():
            env_vars.append(client.V1EnvVar(name=key, value=value))

        # IDE 特定配置
        if instance.ide_type == IDEType.VSCODE:
            env_vars.extend([
                client.V1EnvVar(name="PASSWORD", value=instance.token or ""),
                client.V1EnvVar(name="SUDO_PASSWORD", value=instance.token or ""),
            ])
        elif instance.ide_type == IDEType.RSTUDIO:
            env_vars.extend([
                client.V1EnvVar(name="USER", value="rstudio"),
                client.V1EnvVar(name="PASSWORD", value=instance.token or "rstudio"),
            ])

        # 3. 创建 Pod
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=instance.pod_name,
                namespace=instance.namespace,
                labels={
                    "app": "online-ide",
                    "instance-id": instance.instance_id,
                    "ide-type": instance.ide_type.value,
                    "user-id": instance.user_id,
                },
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="ide",
                        image=instance.image,
                        ports=[
                            client.V1ContainerPort(container_port=instance.port, name="http")
                        ],
                        env=env_vars,
                        resources=client.V1ResourceRequirements(
                            **instance.resources.to_k8s_resources()
                        ),
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="workspace",
                                mount_path=instance.workspace,
                            )
                        ],
                        readiness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(
                                path="/",
                                port=instance.port,
                            ),
                            initial_delay_seconds=10,
                            period_seconds=5,
                        ),
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="workspace",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        ),
                    )
                ],
                restart_policy="Always",
            ),
        )

        # 添加 GPU 节点选择器
        if instance.resources.gpu_count > 0 and instance.resources.gpu_type:
            pod.spec.node_selector = {
                "nvidia.com/gpu.product": instance.resources.gpu_type
            }

        self._k8s_client.create_namespaced_pod(namespace=instance.namespace, body=pod)

        # 4. 创建 Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=instance.service_name,
                namespace=instance.namespace,
                labels={
                    "app": "online-ide",
                    "instance-id": instance.instance_id,
                },
            ),
            spec=client.V1ServiceSpec(
                selector={
                    "instance-id": instance.instance_id,
                },
                ports=[
                    client.V1ServicePort(
                        name="http",
                        port=instance.port,
                        target_port=instance.port,
                    )
                ],
                type="ClusterIP",
            ),
        )

        self._k8s_client.create_namespaced_service(namespace=instance.namespace, body=service)

        # 5. 创建 Ingress（可选）
        if self.base_domain:
            instance.ingress_name = f"{instance.instance_id}-ingress"
            self._create_ingress(instance)

    def _create_ingress(self, instance: IDEInstance):
        """创建 Ingress"""
        if not self._k8s_networking_client:
            return

        from kubernetes import client

        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=instance.ingress_name,
                namespace=instance.namespace,
                annotations={
                    "nginx.ingress.kubernetes.io/proxy-body-size": "0",
                    "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
                    "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
                    # WebSocket 支持
                    "nginx.ingress.kubernetes.io/proxy-http-version": "1.1",
                    "nginx.ingress.kubernetes.io/configuration-snippet": "proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection 'upgrade';",
                },
            ),
            spec=client.V1IngressSpec(
                rules=[
                    client.V1IngressRule(
                        host=f"{instance.instance_id}.{self.base_domain}",
                        http=client.V1HTTPIngressRuleValue(
                            paths=[
                                client.V1HTTPIngressPath(
                                    path="/",
                                    path_type="Prefix",
                                    backend=client.V1IngressBackend(
                                        service=client.V1IngressServiceBackend(
                                            name=instance.service_name,
                                            port=client.V1ServiceBackendPort(
                                                number=instance.port
                                            ),
                                        )
                                    ),
                                )
                            ]
                        ),
                    )
                ]
            ),
        )

        try:
            self._k8s_networking_client.create_namespaced_ingress(
                namespace=instance.namespace, body=ingress
            )
        except Exception as e:
            logger.warning(f"创建 Ingress 失败: {e}")

    def _delete_k8s_resources(self, instance: IDEInstance, keep_pvc: bool = False):
        """删除 K8s 资源"""
        self._get_k8s_clients()

        if not self._k8s_client:
            return

        from kubernetes import client

        # 删除 Pod
        if instance.pod_name:
            try:
                self._k8s_client.delete_namespaced_pod(
                    name=instance.pod_name, namespace=instance.namespace
                )
            except client.exceptions.ApiException:
                pass

        # 删除 Service
        if instance.service_name:
            try:
                self._k8s_client.delete_namespaced_service(
                    name=instance.service_name, namespace=instance.namespace
                )
            except client.exceptions.ApiException:
                pass

        # 删除 Ingress
        if instance.ingress_name and self._k8s_networking_client:
            try:
                self._k8s_networking_client.delete_namespaced_ingress(
                    name=instance.ingress_name, namespace=instance.namespace
                )
            except client.exceptions.ApiException:
                pass

        # 删除 PVC（可选）
        if not keep_pvc:
            pvc_name = f"{instance.instance_id}-pvc"
            try:
                self._k8s_client.delete_namespaced_persistent_volume_claim(
                    name=pvc_name, namespace=instance.namespace
                )
            except client.exceptions.ApiException:
                pass

    def _generate_url(self, instance: IDEInstance) -> str:
        """生成访问 URL"""
        if self.base_domain:
            return f"https://{instance.instance_id}.{self.base_domain}"
        else:
            # 开发环境使用 NodePort 或 Port-Forward
            return f"http://localhost:{instance.port}"


# 全局服务实例
_ide_service: Optional[OnlineIDEService] = None


def get_ide_service() -> OnlineIDEService:
    """获取 IDE 服务实例"""
    global _ide_service
    if _ide_service is None:
        _ide_service = OnlineIDEService()
    return _ide_service
