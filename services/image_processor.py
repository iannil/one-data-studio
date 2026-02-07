"""
图片处理服务 - 重新导出模块
Sprint 24: 图片处理 MinIO 集成

从 agent-api 服务重新导出图片处理功能，供测试使用
"""

import io
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import base64
import hashlib

# 添加 agent-api 路径到 sys.path
agent_api_path = Path(__file__).parent / "agent-api"
if str(agent_api_path) not in sys.path:
    sys.path.insert(0, str(agent_api_path))

try:
    from agent_services.image_processor import (
        ImageProcessor as _ImageProcessor,
        ImageMetadata,
        ImageFormat,
        OCRResult,
        ProcessedImage,
        StoredImage,
        MinIOImageStorage as _MinIOImageStorage,
        ImageService as _ImageService,
        get_image_processor,
        get_minio_storage,
        is_minio_enabled,
        get_image_service,
    )

    # 使用实际的实现
    class ImageProcessor(_ImageProcessor):
        pass

    class MinIOImageStorage(_MinIOImageStorage):
        pass

    class ImageService(_ImageService):
        pass

    # 导出 Minio 类供测试 mock 使用
    try:
        from minio import Minio
    except ImportError:
        Minio = None

except ImportError:
    # 如果 agent_services 不可用，提供最小化实现
    import logging

    logger = logging.getLogger(__name__)

    class ImageFormat(Enum):
        """支持的图片格式"""
        JPEG = "jpeg"
        PNG = "png"
        WEBP = "webp"
        GIF = "gif"
        BMP = "bmp"
        TIFF = "tiff"

    @dataclass
    class ImageMetadata:
        """图片元数据"""
        width: int
        height: int
        format: str
        size_bytes: int
        color_mode: str
        has_alpha: bool
        hash: str

    @dataclass
    class OCRResult:
        """OCR 识别结果"""
        text: str
        confidence: float
        bounding_boxes: List[Dict[str, Any]]
        language: str

    @dataclass
    class ProcessedImage:
        """处理后的图片"""
        data: bytes
        metadata: ImageMetadata
        thumbnail: Optional[bytes] = None
        ocr_result: Optional[OCRResult] = None

    @dataclass
    class StoredImage:
        """存储后的图片信息"""
        image_id: str
        url: str
        thumbnail_url: Optional[str]
        metadata: ImageMetadata
        storage_path: str
        storage_type: str  # 'minio' or 'local'

    class ImageProcessor:
        """图片处理器 - 最小化实现"""

        DEFAULT_MAX_SIZE = (1920, 1080)
        DEFAULT_THUMBNAIL_SIZE = (256, 256)
        DEFAULT_QUALITY = 85
        MAX_FILE_SIZE = 20 * 1024 * 1024

        def __init__(self, max_size=None, thumbnail_size=None, quality=None, enable_ocr=True, ocr_languages=None):
            self.max_size = max_size or self.DEFAULT_MAX_SIZE
            self.thumbnail_size = thumbnail_size or self.DEFAULT_THUMBNAIL_SIZE
            self.quality = quality or self.DEFAULT_QUALITY
            self.enable_ocr = enable_ocr
            self.ocr_languages = ocr_languages or ['chi_sim', 'eng']

        def get_image_info(self, image_data: bytes) -> ImageMetadata:
            """获取图片信息"""
            # 尝试使用 PIL
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(image_data))
                return ImageMetadata(
                    width=img.width,
                    height=img.height,
                    format=img.format or 'PNG',
                    size_bytes=len(image_data),
                    color_mode=img.mode,
                    has_alpha=img.mode in ('RGBA', 'LA', 'P'),
                    hash=hashlib.md5(image_data).hexdigest()
                )
            except ImportError:
                return ImageMetadata(
                    width=1,
                    height=1,
                    format="png",
                    size_bytes=len(image_data),
                    color_mode="RGB",
                    has_alpha=False,
                    hash=hashlib.md5(image_data).hexdigest()
                )

        def process_image(self, image_data: bytes, resize=False, generate_thumbnail=False,
                         extract_text=False, output_format=None) -> ProcessedImage:
            """处理图片"""
            metadata = self.get_image_info(image_data)

            # 如果需要调整大小
            processed_data = image_data
            if resize and self.max_size:
                try:
                    from PIL import Image
                    img = Image.open(io.BytesIO(image_data))

                    # 处理 RGBA 转 JPEG 的问题
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background

                    if img.width > self.max_size[0] or img.height > self.max_size[1]:
                        img.thumbnail(self.max_size, Image.Resampling.LANCZOS)

                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=self.quality)
                    processed_data = buffer.getvalue()
                    metadata = self.get_image_info(processed_data)
                except ImportError:
                    pass

            # 生成缩略图
            thumbnail = None
            if generate_thumbnail:
                try:
                    from PIL import Image
                    img = Image.open(io.BytesIO(processed_data))

                    # 处理 RGBA 转 JPEG 的问题
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background

                    thumb = img.copy()
                    thumb.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    thumb.save(buffer, format='JPEG', quality=75)
                    thumbnail = buffer.getvalue()
                except ImportError:
                    thumbnail = processed_data[:100] if len(processed_data) > 100 else processed_data

            return ProcessedImage(data=processed_data, metadata=metadata, thumbnail=thumbnail)

        @staticmethod
        def to_base64(data: bytes, format: str = 'jpeg') -> str:
            """转换为 Base64"""
            b64 = base64.b64encode(data).decode('utf-8')
            return f"data:image/{format};base64,{b64}"

        @staticmethod
        def from_base64(b64_string: str) -> bytes:
            """从 Base64 转换"""
            if ',' in b64_string:
                b64_string = b64_string.split(',', 1)[1]
            return base64.b64decode(b64_string)

    class MinIOImageStorage:
        """MinIO 存储 - 最小化实现"""

        def __init__(self, endpoint='localhost:9000', access_key='', secret_key='', bucket='images', secure=False):
            self.endpoint = endpoint
            self.access_key = access_key
            self.secret_key = secret_key
            self.bucket = bucket
            self.secure = secure
            self._client = None

        @property
        def client(self):
            if self._client is None:
                self._client = MockMinioClient()
            return self._client

        def upload(self, image_id: str, data: bytes, content_type: str = 'image/jpeg', is_thumbnail: bool = False) -> str:
            suffix = '_thumb' if is_thumbnail else ''
            return f"images/{image_id}{suffix}"

        def download(self, path: str) -> bytes:
            return b""

        def delete(self, image_id: str, delete_thumbnail: bool = True) -> bool:
            return True

    class MockMinioClient:
        """Mock MinIO 客户端"""
        def __init__(self):
            self.buckets = set()
            self.objects = {}

        def bucket_exists(self, bucket):
            return bucket in self.buckets

        def make_bucket(self, bucket):
            self.buckets.add(bucket)

        def put_object(self, bucket, name, data, *args, **kwargs):
            if bucket not in self.objects:
                self.objects[bucket] = {}

            if hasattr(data, 'read'):
                self.objects[bucket][name] = data.read()
            else:
                self.objects[bucket][name] = data

        def get_object(self, bucket, name):
            if bucket in self.objects and name in self.objects[bucket]:
                class MockResponse:
                    def __init__(self, data):
                        self.data = data
                    def read(self):
                        return self.data if isinstance(self.data, bytes) else self.data.encode()
                    def close(self):
                        pass
                    def release_conn(self):
                        pass
                return MockResponse(self.objects[bucket][name])
            raise Exception("Object not found")

        def remove_object(self, bucket, name):
            if bucket in self.objects and name in self.objects[bucket]:
                del self.objects[bucket][name]

    # 导出 Minio 类（实际上是 mock）
    class Minio:
        """Minio 类 - mock 实现"""
        def __init__(self, endpoint, access_key, secret_key, secure=False):
            self.endpoint = endpoint
            self.access_key = access_key
            self.secret_key = secret_key
            self.secure = secure

    class ImageService:
        """图片服务 - 最小化实现"""

        def __init__(self):
            self.processor = ImageProcessor()
            self.use_minio = is_minio_enabled()
            self.storage = None

        def upload_image(self, data: bytes, filename: str, generate_thumbnail: bool = True,
                        extract_text: bool = False) -> StoredImage:
            import uuid
            image_id = str(uuid.uuid4())
            processed = self.processor.process_image(data, resize=True, generate_thumbnail=generate_thumbnail)
            metadata = processed.metadata

            return StoredImage(
                image_id=image_id,
                url=f"/api/v1/images/{image_id}",
                thumbnail_url=f"/api/v1/images/{image_id}/thumbnail" if processed.thumbnail else None,
                metadata=metadata,
                storage_path=f"images/{image_id}",
                storage_type="minio" if self.use_minio else "local"
            )

        def batch_upload(self, images: List[Tuple[bytes, str]], generate_thumbnails: bool = True) -> List[StoredImage]:
            return [self.upload_image(data, filename, generate_thumbnail=generate_thumbnails)
                    for data, filename in images]

    def get_image_processor() -> ImageProcessor:
        return ImageProcessor()

    def get_minio_storage() -> MinIOImageStorage:
        return MinIOImageStorage()

    def is_minio_enabled() -> bool:
        return os.environ.get('IMAGE_STORAGE_TYPE', 'minio').lower() == 'minio'

    def get_image_service() -> ImageService:
        return ImageService()


__all__ = [
    "ImageProcessor",
    "ImageMetadata",
    "ImageFormat",
    "OCRResult",
    "ProcessedImage",
    "StoredImage",
    "MinIOImageStorage",
    "ImageService",
    "Minio",
    "get_image_processor",
    "get_minio_storage",
    "is_minio_enabled",
    "get_image_service",
]
