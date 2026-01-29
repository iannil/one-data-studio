"""
MinIO 存储客户端
管理 MinIO 对象存储操作
"""

import os
import uuid
from datetime import timedelta
from typing import Optional, Dict, Any
import logging

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    Minio = None
    S3Error = None

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO 客户端封装"""

    def __init__(self):
        self._client = None
        self._initialized = False

        # 配置 - 生产环境必须设置环境变量
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'minio.one-data-infra.svc.cluster.local:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY')
        self.secret_key = os.getenv('MINIO_SECRET_KEY')
        self.default_bucket = os.getenv('MINIO_DEFAULT_BUCKET', 'alldata')
        self.use_ssl = os.getenv('MINIO_USE_SSL', 'false').lower() == 'true'

        # 检查必需的凭据
        if not self.access_key or not self.secret_key:
            logger.warning(
                "MINIO_ACCESS_KEY and MINIO_SECRET_KEY not set. "
                "MinIO will run in mock mode. Set these environment variables for production use."
            )

    def init_client(self):
        """初始化 MinIO 客户端"""
        if not MINIO_AVAILABLE:
            logger.warning("MinIO client not available, using mock storage")
            self._initialized = True
            return

        # 检查凭据是否已设置
        if not self.access_key or not self.secret_key:
            logger.warning("MinIO credentials not configured, using mock storage")
            self._initialized = True
            return

        try:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.use_ssl
            )

            # 确保默认桶存在
            self._ensure_bucket(self.default_bucket)

            self._initialized = True
            logger.info(f"MinIO client initialized: {self.endpoint}")

        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            # Mock 模式下仍然继续
            self._initialized = True

    def _ensure_bucket(self, bucket_name: str):
        """确保桶存在"""
        if not MINIO_AVAILABLE or not self._client:
            return

        try:
            if not self._client.bucket_exists(bucket_name):
                self._client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket {bucket_name}: {e}")

    def generate_presigned_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: int = 3600,
        method: str = 'PUT'
    ) -> Dict[str, Any]:
        """
        生成预签名 URL

        Args:
            object_name: 对象名称
            bucket_name: 桶名称（默认使用 default_bucket）
            expires: 过期时间（秒）
            method: HTTP 方法 (PUT, GET)

        Returns:
            包含预签名 URL 的字典
        """
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            # Mock 模式
            return {
                'url': f'mock://{bucket}/{object_name}',
                'method': method,
                'expires_in': expires,
                'mock': True
            }

        try:
            url = self._client.presigned_url(
                method=method.upper(),
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )

            return {
                'url': url,
                'method': method,
                'bucket': bucket,
                'object_name': object_name,
                'expires_in': expires
            }
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def get_object_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: int = 3600
    ) -> str:
        """获取对象访问 URL"""
        result = self.generate_presigned_url(object_name, bucket_name, expires, 'GET')
        return result['url']

    def put_object(
        self,
        object_name: str,
        data: bytes,
        bucket_name: Optional[str] = None,
        content_type: str = 'application/octet-stream'
    ) -> bool:
        """
        上传对象

        Args:
            object_name: 对象名称
            data: 数据
            bucket_name: 桶名称
            content_type: 内容类型

        Returns:
            是否成功
        """
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            logger.warning(f"Mock upload: {bucket}/{object_name}")
            return True

        try:
            from io import BytesIO
            self._client.put_object(
                bucket,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            logger.info(f"Uploaded: {bucket}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload object: {e}")
            return False

    def get_object(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> Optional[bytes]:
        """获取对象数据"""
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            logger.warning(f"Mock get: {bucket}/{object_name}")
            return b''

        try:
            response = self._client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to get object: {e}")
            return None

    def delete_object(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """删除对象"""
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            logger.warning(f"Mock delete: {bucket}/{object_name}")
            return True

        try:
            self._client.remove_object(bucket, object_name)
            logger.info(f"Deleted: {bucket}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete object: {e}")
            return False

    def object_exists(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """检查对象是否存在"""
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            return False

        try:
            self._client.stat_object(bucket, object_name)
            return True
        except S3Error as e:
            logger.debug(f"Object '{object_name}' not found in bucket '{bucket}': {e}")
            return False

    def list_objects(
        self,
        prefix: str = '',
        bucket_name: Optional[str] = None,
        recursive: bool = False
    ) -> list:
        """列出对象"""
        bucket = bucket_name or self.default_bucket

        if not self._initialized:
            self.init_client()

        if not MINIO_AVAILABLE or not self._client:
            return []

        try:
            objects = self._client.list_objects(bucket, prefix=prefix, recursive=recursive)
            return [
                {
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    def generate_upload_id(self) -> str:
        """生成唯一上传 ID"""
        return f"upload-{uuid.uuid4().hex[:16]}"

    def parse_storage_path(self, storage_path: str) -> tuple:
        """
        解析存储路径

        Args:
            storage_path: 如 s3://bucket/path/to/file.csv

        Returns:
            (bucket_name, object_name) 元组
        """
        if storage_path.startswith('s3://'):
            path = storage_path[5:]
            parts = path.split('/', 1)
            bucket = parts[0]
            object_name = parts[1] if len(parts) > 1 else ''
            return bucket, object_name
        else:
            # 默认使用 default bucket
            return self.default_bucket, storage_path

    def build_storage_path(self, bucket: str, object_name: str) -> str:
        """构建存储路径"""
        return f"s3://{bucket}/{object_name}"


# 全局 MinIO 客户端实例
minio_client = MinIOClient()


def init_storage():
    """初始化存储客户端"""
    minio_client.init_client()


def get_storage_client() -> MinIOClient:
    """获取存储客户端"""
    if not minio_client._initialized:
        minio_client.init_client()
    return minio_client
