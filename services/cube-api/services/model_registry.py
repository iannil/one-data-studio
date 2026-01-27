"""
模型版本管理服务

提供模型版本管理功能：
- 模型元数据注册
- MinIO 模型存储
- 模型版本回滚
- 模型评估和比较
"""

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, BinaryIO
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelStage(Enum):
    """模型阶段"""
    DEVELOPMENT = "development"  # 开发中
    STAGING = "staging"          # 预发布
    PRODUCTION = "production"    # 生产环境
    ARCHIVED = "archived"        # 已归档


class ModelFormat(Enum):
    """模型格式"""
    PYTORCH = "pytorch"          # .pt, .pth
    TENSORFLOW = "tensorflow"    # SavedModel, .h5
    ONNX = "onnx"                # .onnx
    TRANSFORMERS = "transformers"  # HuggingFace format
    SKLEARN = "sklearn"          # .pkl, .joblib
    XGBOOST = "xgboost"          # .json, .ubj


@dataclass
class ModelMetrics:
    """模型评估指标"""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    loss: Optional[float] = None
    # 自定义指标
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "auc_roc": self.auc_roc,
            "loss": self.loss,
        }
        # 只包含非 None 的值
        result = {k: v for k, v in result.items() if v is not None}
        result.update(self.custom_metrics)
        return result


@dataclass
class ModelArtifact:
    """模型文件工件"""
    name: str
    path: str
    size: int
    checksum: str
    format: ModelFormat
    is_main: bool = True  # 是否是主模型文件


@dataclass
class ModelVersionInfo:
    """模型版本信息"""
    version_id: str
    version: str
    model_id: str
    artifacts: List[ModelArtifact]
    metrics: Optional[ModelMetrics] = None
    stage: ModelStage = ModelStage.DEVELOPMENT
    framework: Optional[str] = None
    training_job_id: Optional[str] = None
    base_model: Optional[str] = None
    created_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelRegistryService:
    """
    模型注册服务

    管理模型版本、存储和元数据。
    """

    def __init__(
        self,
        storage_backend: str = "minio",
        storage_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化模型注册服务

        Args:
            storage_backend: 存储后端 (minio, local, s3)
            storage_config: 存储配置
        """
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        self._storage_client = None

    def _ensure_storage_client(self):
        """确保存储客户端已初始化"""
        if self._storage_client is None:
            if self.storage_backend == "minio":
                self._storage_client = MinIOStorageClient(self.storage_config)
            elif self.storage_backend == "local":
                self._storage_client = LocalStorageClient(self.storage_config)
            else:
                raise ValueError(f"Unsupported storage backend: {self.storage_backend}")

    def register_model(
        self,
        model_id: str,
        version: str,
        model_files: Dict[str, BinaryIO],
        framework: str,
        metrics: Optional[ModelMetrics] = None,
        training_job_id: Optional[str] = None,
        base_model: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelVersionInfo:
        """
        注册新模型版本

        Args:
            model_id: 模型ID
            version: 版本号 (如 "1.0.0")
            model_files: 模型文件 {filename: file_object}
            framework: 框架名称
            metrics: 评估指标
            training_job_id: 关联的训练任务ID
            base_model: 基础模型ID
            tags: 标签列表
            metadata: 额外元数据

        Returns:
            模型版本信息
        """
        self._ensure_storage_client()

        version_id = f"{model_id}-{version}-{uuid.uuid4().hex[:8]}"
        storage_path = f"models/{model_id}/{version}"

        # 上传模型文件
        artifacts = []
        total_size = 0

        for filename, file_obj in model_files.items():
            file_path = f"{storage_path}/{filename}"

            # 计算校验和
            checksum = self._calculate_checksum(file_obj)

            # 上传文件
            file_size = self._storage_client.upload_file(
                file_path, file_obj, metadata=metadata
            )

            # 检测模型格式
            model_format = self._detect_model_format(filename)

            artifacts.append(ModelArtifact(
                name=filename,
                path=file_path,
                size=file_size,
                checksum=checksum,
                format=model_format,
                is_main=filename in ("model.pt", "model.pth", "pytorch_model.bin",
                                   "model.onnx", "model.joblib"),
            ))

            total_size += file_size

        logger.info(
            f"Registered model {model_id} v{version}: "
            f"{len(model_files)} files, {total_size} bytes"
        )

        return ModelVersionInfo(
            version_id=version_id,
            version=version,
            model_id=model_id,
            artifacts=artifacts,
            metrics=metrics,
            stage=ModelStage.DEVELOPMENT,
            framework=framework,
            training_job_id=training_job_id,
            base_model=base_model,
            created_at=datetime.now(),
            tags=tags or [],
            metadata=metadata or {},
        )

    def download_model(
        self,
        model_id: str,
        version: str,
        destination: str,
    ) -> List[str]:
        """
        下载模型文件

        Args:
            model_id: 模型ID
            version: 版本号
            destination: 目标目录

        Returns:
            下载的文件路径列表
        """
        self._ensure_storage_client()

        storage_path = f"models/{model_id}/{version}"
        destination_path = Path(destination)
        destination_path.mkdir(parents=True, exist_ok=True)

        downloaded_files = []

        try:
            files = self._storage_client.list_files(storage_path)
            for file_info in files:
                file_path = file_info["path"]
                local_path = destination_path / Path(file_path).name

                self._storage_client.download_file(
                    file_path, str(local_path)
                )
                downloaded_files.append(str(local_path))

            logger.info(f"Downloaded {len(downloaded_files)} files to {destination}")

        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

        return downloaded_files

    def list_model_versions(self, model_id: str) -> List[str]:
        """
        列出模型的所有版本

        Args:
            model_id: 模型ID

        Returns:
            版本号列表
        """
        self._ensure_storage_client()

        storage_prefix = f"models/{model_id}/"
        versions = set()

        try:
            files = self._storage_client.list_files(storage_prefix)
            for file_info in files:
                path = file_info["path"]
                # 提取版本号 (models/{model_id}/{version}/...)
                parts = path.split("/")
                if len(parts) > 2:
                    versions.add(parts[2])

        except Exception as e:
            logger.error(f"Failed to list model versions: {e}")

        return sorted(versions, reverse=True)

    def delete_model_version(self, model_id: str, version: str) -> bool:
        """
        删除模型版本

        Args:
            model_id: 模型ID
            version: 版本号

        Returns:
            是否成功删除
        """
        self._ensure_storage_client()

        storage_path = f"models/{model_id}/{version}"

        try:
            self._storage_client.delete_files(storage_path)
            logger.info(f"Deleted model {model_id} v{version}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model version: {e}")
            return False

    def compare_versions(
        self,
        model_id: str,
        version_a: str,
        version_b: str,
    ) -> Dict[str, Any]:
        """
        比较两个模型版本的指标

        Args:
            model_id: 模型ID
            version_a: 版本A
            version_b: 版本B

        Returns:
            比较结果
        """
        # 这里需要从元数据库读取指标
        # 简化实现，返回占位符
        return {
            "model_id": model_id,
            "version_a": version_a,
            "version_b": version_b,
            "metrics_diff": {},
            "recommendation": "none",
        }

    def set_model_stage(
        self,
        model_id: str,
        version: str,
        stage: ModelStage,
    ) -> bool:
        """
        设置模型阶段

        Args:
            model_id: 模型ID
            version: 版本号
            stage: 目标阶段

        Returns:
            是否成功
        """
        # 这里需要更新元数据库
        # 简化实现
        logger.info(f"Set {model_id} v{version} stage to {stage.value}")
        return True

    def get_model_uri(self, model_id: str, version: str) -> str:
        """
        获取模型的访问 URI

        Args:
            model_id: 模型ID
            version: 版本号

        Returns:
            模型URI
        """
        if self.storage_backend == "minio":
            endpoint = self.storage_config.get("endpoint", "localhost:9000")
            bucket = self.storage_config.get("bucket", "models")
            return f"s3://{bucket}/models/{model_id}/{version}"
        else:
            return f"file:///models/{model_id}/{version}"

    def _calculate_checksum(self, file_obj: BinaryIO) -> str:
        """计算文件校验和"""
        md5_hash = hashlib.md5()
        # 读取文件
        for chunk in iter(lambda: file_obj.read(4096), b""):
            md5_hash.update(chunk)
        # 重置文件指针
        file_obj.seek(0)
        return md5_hash.hexdigest()

    def _detect_model_format(self, filename: str) -> ModelFormat:
        """从文件名检测模型格式"""
        ext = Path(filename).suffix.lower()

        if ext in (".pt", ".pth"):
            return ModelFormat.PYTORCH
        elif ext in (".h5", ".keras"):
            return ModelFormat.TENSORFLOW
        elif ext == ".onnx":
            return ModelFormat.ONNX
        elif ext in (".bin", ".safetensors"):
            return ModelFormat.TRANSFORMERS
        elif ext in (".pkl", ".joblib"):
            return ModelFormat.SKLEARN
        elif ext == ".json":
            # 可能是 XGBoost 或其他格式
            return ModelFormat.XGBOOST
        else:
            return ModelFormat.TRANSFORMERS  # 默认


class MinIOStorageClient:
    """MinIO 存储客户端"""

    def __init__(self, config: Dict[str, Any]):
        self.endpoint = config.get("endpoint", "localhost:9000")
        self.access_key = config.get("access_key", "minioadmin")
        self.secret_key = config.get("secret_key", "minioadmin")
        self.bucket = config.get("bucket", "models")
        self.secure = config.get("secure", False)
        self._client = None

    def _ensure_client(self):
        """确保 MinIO 客户端已初始化"""
        if self._client is None:
            try:
                from minio import Minio

                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )

                # 确保存储桶存在
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
                    logger.info(f"Created MinIO bucket: {self.bucket}")

            except ImportError:
                raise ImportError("Please install minio package: pip install minio")

    def upload_file(
        self,
        path: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """上传文件到 MinIO"""
        self._ensure_client()

        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)

        self._client.put_object(
            self.bucket,
            path,
            file_obj,
            length=size,
            metadata=metadata or {},
        )

        return size

    def download_file(self, path: str, local_path: str) -> None:
        """从 MinIO 下载文件"""
        self._ensure_client()

        self._client.fget_object(self.bucket, path, local_path)

    def list_files(self, prefix: str) -> List[Dict[str, Any]]:
        """列出 MinIO 中的文件"""
        self._ensure_client()

        objects = self._client.list_objects(self.bucket, prefix=prefix, recursive=True)
        return [
            {"path": obj.object_name, "size": obj.size, "last_modified": obj.last_modified}
            for obj in objects
        ]

    def delete_files(self, prefix: str) -> None:
        """删除 MinIO 中的文件"""
        self._ensure_client()

        objects = self._client.list_objects(self.bucket, prefix=prefix, recursive=True)
        for obj in objects:
            self._client.remove_object(self.bucket, obj.object_name)


class LocalStorageClient:
    """本地存储客户端"""

    def __init__(self, config: Dict[str, Any]):
        self.base_path = Path(config.get("base_path", "/tmp/models"))
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self,
        path: str,
        file_obj: BinaryIO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """保存文件到本地"""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            size = 0
            for chunk in iter(lambda: file_obj.read(4096), b""):
                f.write(chunk)
                size += len(chunk)

        # 保存元数据
        if metadata:
            meta_path = file_path.with_suffix(".meta.json")
            with open(meta_path, "w") as f:
                json.dump(metadata, f)

        return size

    def download_file(self, path: str, local_path: str) -> None:
        """从本地复制文件"""
        import shutil

        src_path = self.base_path / path
        shutil.copy(src_path, local_path)

    def list_files(self, prefix: str) -> List[Dict[str, Any]]:
        """列出本地文件"""
        base_dir = self.base_path / prefix

        if not base_dir.exists():
            return []

        files = []
        for file_path in base_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".meta.json"):
                stat = file_path.stat()
                files.append({
                    "path": str(file_path.relative_to(self.base_path)),
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime),
                })

        return files

    def delete_files(self, prefix: str) -> None:
        """删除本地文件"""
        import shutil

        base_dir = self.base_path / prefix
        if base_dir.exists():
            shutil.rmtree(base_dir)


# 全局实例
_model_registry: Optional[ModelRegistryService] = None


def get_model_registry(
    storage_backend: str = "minio",
    storage_config: Optional[Dict[str, Any]] = None,
) -> ModelRegistryService:
    """获取模型注册服务单例"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistryService(
            storage_backend=storage_backend,
            storage_config=storage_config,
        )
    return _model_registry
