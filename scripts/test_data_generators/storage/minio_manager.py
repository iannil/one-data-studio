"""
MinIO存储管理器

提供：
1. 对象存储连接管理
2. 文件上传功能
3. 文件清理功能
"""

import os
import logging
from typing import Any, Dict, List, Optional, BinaryIO
from io import BytesIO
from datetime import datetime

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = None

from ..config import MinIOConfig


logger = logging.getLogger(__name__)


class MinIOManager:
    """
    MinIO对象存储管理器

    提供：
    - Bucket管理
    - 文件上传/下载
    - 文件清理
    """

    def __init__(self, config: MinIOConfig = None):
        """
        初始化MinIO管理器

        Args:
            config: MinIO配置
        """
        self.config = config or MinIOConfig.from_env()
        self._client = None
        self._connected = False

    @property
    def is_available(self) -> bool:
        """检查minio是否可用"""
        return Minio is not None

    def connect(self) -> bool:
        """
        建立MinIO连接

        Returns:
            连接是否成功
        """
        if not self.is_available:
            logger.warning("MinIO library not available, using mock mode")
            self._connected = True
            return True

        if self._connected and self._client:
            return True

        try:
            self._client = Minio(
                self.config.endpoint,
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                secure=self.config.secure
            )
            self._connected = True
            logger.info(f"Connected to MinIO at {self.config.endpoint}")

            # 确保bucket存在
            self._ensure_bucket()

            return True
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")
            self._connected = True  # 设置为True以避免重复尝试
            return False

    def disconnect(self):
        """断开MinIO连接"""
        self._client = None
        self._connected = False
        logger.info("Disconnected from MinIO")

    def _ensure_bucket(self):
        """确保bucket存在"""
        if not self._client:
            return

        try:
            if not self._client.bucket_exists(self.config.bucket):
                self._client.make_bucket(self.config.bucket)
                logger.info(f"Created bucket: {self.config.bucket}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")

    def put_object(
        self,
        object_name: str,
        data: bytes,
        length: int = None,
        content_type: str = "application/octet-stream"
    ) -> bool:
        """
        上传对象

        Args:
            object_name: 对象名称
            data: 数据字节
            length: 数据长度
            content_type: 内容类型

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                self._client.put_object(
                    self.config.bucket,
                    object_name,
                    BytesIO(data),
                    length=len(data) if length is None else length,
                    content_type=content_type
                )
            logger.debug(f"Uploaded object: {object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload object {object_name}: {e}")
            return False

    def put_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = None
    ) -> bool:
        """
        上传文件

        Args:
            object_name: 对象名称
            file_path: 文件路径
            content_type: 内容类型

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        try:
            if self._client:
                self._client.fput_object(
                    self.config.bucket,
                    object_name,
                    file_path,
                    content_type=content_type
                )
            logger.debug(f"Uploaded file: {file_path} -> {object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            return False

    def get_object(self, object_name: str) -> Optional[bytes]:
        """
        获取对象

        Args:
            object_name: 对象名称

        Returns:
            对象数据
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                response = self._client.get_object(self.config.bucket, object_name)
                return response.read()
        except Exception as e:
            logger.error(f"Failed to get object {object_name}: {e}")

        return None

    def remove_object(self, object_name: str) -> bool:
        """
        删除对象

        Args:
            object_name: 对象名称

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                self._client.remove_object(self.config.bucket, object_name)
            logger.debug(f"Removed object: {object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove object {object_name}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> List[str]:
        """
        列出对象

        Args:
            prefix: 对象名前缀

        Returns:
            对象名称列表
        """
        if not self._connected:
            self.connect()

        objects = []
        try:
            if self._client:
                for obj in self._client.list_objects(self.config.bucket, prefix=prefix):
                    if obj.object_name:
                        objects.append(obj.object_name)
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")

        return objects

    def remove_objects(self, prefix: str = "") -> int:
        """
        批量删除对象

        Args:
            prefix: 对象名前缀

        Returns:
            删除的数量
        """
        objects = self.list_objects(prefix)
        count = 0
        for obj in objects:
            if self.remove_object(obj):
                count += 1
        return count

    # ==================== 便捷方法 ====================

    def upload_document(
        self,
        doc_id: str,
        content: str,
        title: str = "",
        file_type: str = "txt"
    ) -> str:
        """
        上传文档内容

        Args:
            doc_id: 文档ID
            content: 文档内容
            title: 文档标题
            file_type: 文件类型

        Returns:
            对象名称
        """
        object_name = f"documents/{doc_id}.{file_type}"
        data = content.encode('utf-8')
        self.put_object(object_name, data, content_type="text/plain; charset=utf-8")
        return object_name

    def upload_model(
        self,
        model_id: str,
        version: str,
        model_data: bytes
    ) -> str:
        """
        上传模型文件

        Args:
            model_id: 模型ID
            version: 版本号
            model_data: 模型数据

        Returns:
            对象名称
        """
        object_name = f"models/{model_id}/{version}/model.pkl"
        self.put_object(object_name, model_data, content_type="application/octet-stream")
        return object_name

    def upload_chunk(
        self,
        doc_id: str,
        chunk_index: int,
        content: str
    ) -> str:
        """
        上传文档分块

        Args:
            doc_id: 文档ID
            chunk_index: 分块索引
            content: 分块内容

        Returns:
            对象名称
        """
        object_name = f"chunks/{doc_id}/{chunk_index}.txt"
        data = content.encode('utf-8')
        self.put_object(object_name, data, content_type="text/plain; charset=utf-8")
        return object_name

    def get_object_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """
        获取对象的预签名URL

        Args:
            object_name: 对象名称
            expires: 过期时间（秒）

        Returns:
            预签名URL
        """
        if not self._connected:
            self.connect()

        try:
            if self._client:
                from datetime import timedelta
                return self._client.presigned_get_object(
                    self.config.bucket,
                    object_name,
                    expires=timedelta(seconds=expires)
                )
        except Exception as e:
            logger.error(f"Failed to get presigned URL: {e}")

        return None


class MockMinIOManager:
    """
    MinIO管理器的Mock实现（用于测试）
    """

    def __init__(self, config: MinIOConfig = None):
        self.config = config or MinIOConfig()
        self._objects: Dict[str, bytes] = {}
        self._connected = False

    def connect(self) -> bool:
        """模拟连接"""
        self._connected = True
        return True

    def disconnect(self):
        """模拟断开"""
        self._connected = False

    def put_object(self, object_name: str, data: bytes, **kwargs) -> bool:
        """模拟上传"""
        self._objects[object_name] = data
        return True

    def put_file(self, object_name: str, file_path: str, **kwargs) -> bool:
        """模拟上传文件"""
        try:
            with open(file_path, 'rb') as f:
                self._objects[object_name] = f.read()
            return True
        except Exception:
            return False

    def get_object(self, object_name: str) -> Optional[bytes]:
        """模拟获取"""
        return self._objects.get(object_name)

    def remove_object(self, object_name: str) -> bool:
        """模拟删除"""
        self._objects.pop(object_name, None)
        return True

    def list_objects(self, prefix: str = "") -> List[str]:
        """模拟列表"""
        return [obj for obj in self._objects.keys() if obj.startswith(prefix)]

    def remove_objects(self, prefix: str = "") -> int:
        """模拟批量删除"""
        to_remove = [obj for obj in self._objects.keys() if obj.startswith(prefix)]
        for obj in to_remove:
            del self._objects[obj]
        return len(to_remove)

    def upload_document(self, doc_id: str, content: str, title: str = "", file_type: str = "txt") -> str:
        """模拟上传文档"""
        object_name = f"documents/{doc_id}.{file_type}"
        self._objects[object_name] = content.encode('utf-8')
        return object_name

    def upload_model(self, model_id: str, version: str, model_data: bytes) -> str:
        """模拟上传模型"""
        object_name = f"models/{model_id}/{version}/model.pkl"
        self._objects[object_name] = model_data
        return object_name

    def upload_chunk(self, doc_id: str, chunk_index: int, content: str) -> str:
        """模拟上传分块"""
        object_name = f"chunks/{doc_id}/{chunk_index}.txt"
        self._objects[object_name] = content.encode('utf-8')
        return object_name

    def get_object_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """模拟获取URL"""
        return f"http://mock-minio/{self.config.bucket}/{object_name}"

    def get_all_objects(self) -> Dict[str, bytes]:
        """获取所有对象（用于测试验证）"""
        return self._objects.copy()


def get_minio_manager(config: MinIOConfig = None, mock: bool = False) -> MinIOManager:
    """
    获取MinIO管理器实例

    Args:
        config: MinIO配置
        mock: 是否使用Mock实现

    Returns:
        MinIO管理器实例
    """
    if mock or Minio is None:
        return MockMinIOManager(config)
    return MinIOManager(config)
