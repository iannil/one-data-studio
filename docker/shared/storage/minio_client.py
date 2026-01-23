"""
MinIO 存储客户端
Sprint 4.3: MinIO 对象存储封装
"""

import os
from datetime import timedelta
from typing import Optional, List
from minio import Minio
from minio.error import S3Error


class MinIOStorage:
    """
    MinIO 存储封装类
    提供文件上传、下载、删除、列表等操作
    """

    # 默认 buckets
    DEFAULT_BUCKETS = ["datasets", "uploads", "models", "workflows"]

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False,
    ):
        """
        初始化 MinIO 客户端

        Args:
            endpoint: MinIO 服务地址，默认从环境变量读取
            access_key: 访问密钥，默认从环境变量读取
            secret_key: 秘密密钥，默认从环境变量读取
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint or os.getenv(
            "MINIO_ENDPOINT",
            "minio.one-data-infra.svc.cluster.local:9000"
        )
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = secure

        # 初始化客户端
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        # 确保默认 buckets 存在
        self._ensure_buckets()

    def _ensure_buckets(self):
        """确保默认 buckets 存在"""
        for bucket in self.DEFAULT_BUCKETS:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                print(f"创建 bucket: {bucket}")

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: Optional[str] = None,
        data: Optional[bytes] = None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        上传文件

        Args:
            bucket: Bucket 名称
            object_name: 对象名称（路径）
            file_path: 本地文件路径（与 data 二选一）
            data: 文件数据（与 file_path 二选一）
            content_type: 内容类型

        Returns:
            是否成功
        """
        try:
            if file_path:
                self.client.fput_object(
                    bucket, object_name, file_path, content_type=content_type
                )
            elif data:
                from io import BytesIO
                self.client.put_object(
                    bucket,
                    object_name,
                    BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
            else:
                raise ValueError("必须提供 file_path 或 data")
            return True
        except S3Error as e:
            print(f"上传文件失败: {e}")
            return False

    def download_file(
        self,
        bucket: str,
        object_name: str,
        file_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        下载文件

        Args:
            bucket: Bucket 名称
            object_name: 对象名称
            file_path: 本地保存路径（如果为 None，返回文件内容）

        Returns:
            文件内容（如果 file_path 为 None）
        """
        try:
            if file_path:
                self.client.fget_object(bucket, object_name, file_path)
                return None
            else:
                response = self.client.get_object(bucket, object_name)
                return response.read()
        except S3Error as e:
            print(f"下载文件失败: {e}")
            return None

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        获取临时访问 URL

        Args:
            bucket: Bucket 名称
            object_name: 对象名称
            expires: 过期时间（秒）

        Returns:
            临时 URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            print(f"生成临时 URL 失败: {e}")
            return None

    def delete_file(self, bucket: str, object_name: str) -> bool:
        """
        删除文件

        Args:
            bucket: Bucket 名称
            object_name: 对象名称

        Returns:
            是否成功
        """
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except S3Error as e:
            print(f"删除文件失败: {e}")
            return False

    def list_files(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = False,
    ) -> List[str]:
        """
        列出文件

        Args:
            bucket: Bucket 名称
            prefix: 前缀过滤
            recursive: 是否递归

        Returns:
            文件列表
        """
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=recursive)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"列出文件失败: {e}")
            return []

    def file_exists(self, bucket: str, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            bucket: Bucket 名称
            object_name: 对象名称

        Returns:
            是否存在
        """
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False

    def get_file_size(self, bucket: str, object_name: str) -> Optional[int]:
        """
        获取文件大小

        Args:
            bucket: Bucket 名称
            object_name: 对象名称

        Returns:
            文件大小（字节）
        """
        try:
            stat = self.client.stat_object(bucket, object_name)
            return stat.size
        except S3Error:
            return None


# 全局实例
_storage_instance: Optional[MinIOStorage] = None


def get_storage() -> MinIOStorage:
    """
    获取 MinIO 存储实例（单例）
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MinIOStorage()
    return _storage_instance
