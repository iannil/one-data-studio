"""
共享存储模块
Sprint 4.3: MinIO 存储封装
"""

from .minio_client import MinIOStorage, get_storage

__all__ = [
    "MinIOStorage",
    "get_storage",
]
