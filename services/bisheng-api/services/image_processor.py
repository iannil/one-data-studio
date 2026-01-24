"""
图片处理服务
Sprint 15: 多模态支持 - 图片预处理（OCR、缩放、格式转换）
Sprint 24: MinIO 集成 - 云存储支持

提供图片上传、预处理和 OCR 文字识别功能
"""

import io
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import base64
import hashlib

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


class MinIOImageStorage:
    """
    MinIO 图片存储服务
    Sprint 24: 云存储集成
    """

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket: str = None,
        secure: bool = False
    ):
        """
        初始化 MinIO 存储

        Args:
            endpoint: MinIO 服务地址
            access_key: 访问密钥
            secret_key: 密钥
            bucket: 存储桶名称
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint or os.environ.get('MINIO_ENDPOINT', 'minio.one-data-infra.svc.cluster.local:9000')
        self.access_key = access_key or os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = secret_key or os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
        self.bucket = bucket or os.environ.get('MINIO_IMAGES_BUCKET', 'images')
        self.secure = secure or os.environ.get('MINIO_USE_SSL', 'false').lower() == 'true'

        self._client = None

    @property
    def client(self):
        """延迟加载 MinIO 客户端"""
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure
                )
                # 确保 bucket 存在
                self._ensure_bucket()
            except ImportError:
                raise ImportError("minio is required for MinIO storage. Install with: pip install minio")
        return self._client

    def _ensure_bucket(self):
        """确保存储桶存在"""
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket: {e}")
            raise

    def upload(
        self,
        image_id: str,
        image_data: bytes,
        content_type: str = 'image/jpeg',
        is_thumbnail: bool = False
    ) -> str:
        """
        上传图片到 MinIO

        Args:
            image_id: 图片 ID
            image_data: 图片数据
            content_type: 内容类型
            is_thumbnail: 是否为缩略图

        Returns:
            存储路径
        """
        suffix = '_thumb' if is_thumbnail else ''
        object_name = f"images/{image_id}{suffix}"

        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(image_data),
                length=len(image_data),
                content_type=content_type
            )
            logger.debug(f"Uploaded to MinIO: {object_name}")
            return object_name
        except Exception as e:
            logger.error(f"Failed to upload to MinIO: {e}")
            raise

    def download(self, object_name: str) -> bytes:
        """
        从 MinIO 下载图片

        Args:
            object_name: 对象名称

        Returns:
            图片数据
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"Failed to download from MinIO: {e}")
            raise

    def delete(self, image_id: str, delete_thumbnail: bool = True) -> bool:
        """
        从 MinIO 删除图片

        Args:
            image_id: 图片 ID
            delete_thumbnail: 是否删除缩略图

        Returns:
            是否成功
        """
        try:
            self.client.remove_object(self.bucket, f"images/{image_id}")
            if delete_thumbnail:
                try:
                    self.client.remove_object(self.bucket, f"images/{image_id}_thumb")
                except Exception:
                    pass  # 缩略图可能不存在
            logger.debug(f"Deleted from MinIO: {image_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from MinIO: {e}")
            return False

    def get_url(self, object_name: str, expires: int = 3600) -> str:
        """
        获取图片的预签名 URL

        Args:
            object_name: 对象名称
            expires: 过期时间（秒）

        Returns:
            预签名 URL
        """
        from datetime import timedelta
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except Exception as e:
            logger.error(f"Failed to get presigned URL: {e}")
            raise

    def list_images(self, prefix: str = "images/", limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出存储的图片

        Args:
            prefix: 前缀
            limit: 最大数量

        Returns:
            图片列表
        """
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            images = []
            count = 0
            for obj in objects:
                if count >= limit:
                    break
                if not obj.object_name.endswith('_thumb'):
                    images.append({
                        'name': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified,
                        'etag': obj.etag
                    })
                    count += 1
            return images
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []


class ImageProcessor:
    """
    图片处理器

    Sprint 15: 多模态支持

    功能:
    - 图片格式转换
    - 图片缩放
    - 缩略图生成
    - OCR 文字识别
    - 图片元数据提取
    """

    # 默认配置
    DEFAULT_MAX_SIZE = (1920, 1080)  # 最大尺寸
    DEFAULT_THUMBNAIL_SIZE = (256, 256)  # 缩略图尺寸
    DEFAULT_QUALITY = 85  # JPEG 质量
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(
        self,
        max_size: Tuple[int, int] = None,
        thumbnail_size: Tuple[int, int] = None,
        quality: int = None,
        enable_ocr: bool = True,
        ocr_languages: List[str] = None
    ):
        """
        初始化图片处理器

        Args:
            max_size: 最大尺寸 (width, height)
            thumbnail_size: 缩略图尺寸
            quality: JPEG 压缩质量
            enable_ocr: 是否启用 OCR
            ocr_languages: OCR 语言列表
        """
        self.max_size = max_size or self.DEFAULT_MAX_SIZE
        self.thumbnail_size = thumbnail_size or self.DEFAULT_THUMBNAIL_SIZE
        self.quality = quality or self.DEFAULT_QUALITY
        self.enable_ocr = enable_ocr
        self.ocr_languages = ocr_languages or ['chi_sim', 'eng']  # 简体中文 + 英文

        # 延迟导入，避免启动时加载大型库
        self._pil = None
        self._tesseract = None

    @property
    def pil(self):
        """延迟加载 PIL"""
        if self._pil is None:
            try:
                from PIL import Image, ImageOps, ExifTags
                self._pil = {
                    'Image': Image,
                    'ImageOps': ImageOps,
                    'ExifTags': ExifTags
                }
            except ImportError:
                raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")
        return self._pil

    @property
    def tesseract(self):
        """延迟加载 Tesseract OCR"""
        if self._tesseract is None and self.enable_ocr:
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                logger.warning("pytesseract not available. OCR will be disabled.")
                self.enable_ocr = False
        return self._tesseract

    def process_image(
        self,
        image_data: bytes,
        resize: bool = True,
        generate_thumbnail: bool = True,
        extract_text: bool = False,
        output_format: ImageFormat = None
    ) -> ProcessedImage:
        """
        处理图片

        Args:
            image_data: 原始图片数据
            resize: 是否调整尺寸
            generate_thumbnail: 是否生成缩略图
            extract_text: 是否进行 OCR
            output_format: 输出格式

        Returns:
            ProcessedImage 对象
        """
        if len(image_data) > self.MAX_FILE_SIZE:
            raise ValueError(f"Image size exceeds maximum allowed size ({self.MAX_FILE_SIZE / 1024 / 1024}MB)")

        Image = self.pil['Image']
        ImageOps = self.pil['ImageOps']

        # 打开图片
        img = Image.open(io.BytesIO(image_data))

        # 自动旋转（根据 EXIF）
        img = ImageOps.exif_transpose(img)

        # 获取原始元数据
        original_format = img.format or 'UNKNOWN'
        original_mode = img.mode

        # 转换为 RGB（如果需要）
        if img.mode in ('RGBA', 'LA', 'P'):
            has_alpha = True
            if output_format == ImageFormat.JPEG:
                # JPEG 不支持透明度，转换为 RGB
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
        else:
            has_alpha = False
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

        # 调整尺寸
        if resize and (img.width > self.max_size[0] or img.height > self.max_size[1]):
            img.thumbnail(self.max_size, Image.Resampling.LANCZOS)
            logger.debug(f"Image resized to {img.width}x{img.height}")

        # 确定输出格式
        if output_format is None:
            output_format = ImageFormat(original_format.lower()) if original_format.lower() in [f.value for f in ImageFormat] else ImageFormat.JPEG

        # 保存处理后的图片
        output_buffer = io.BytesIO()
        save_kwargs = {'format': output_format.value.upper()}
        if output_format == ImageFormat.JPEG:
            save_kwargs['quality'] = self.quality
            save_kwargs['optimize'] = True
        elif output_format == ImageFormat.PNG:
            save_kwargs['optimize'] = True
        elif output_format == ImageFormat.WEBP:
            save_kwargs['quality'] = self.quality

        img.save(output_buffer, **save_kwargs)
        processed_data = output_buffer.getvalue()

        # 计算哈希
        image_hash = hashlib.md5(processed_data).hexdigest()

        # 创建元数据
        metadata = ImageMetadata(
            width=img.width,
            height=img.height,
            format=output_format.value,
            size_bytes=len(processed_data),
            color_mode=img.mode,
            has_alpha=has_alpha,
            hash=image_hash
        )

        # 生成缩略图
        thumbnail_data = None
        if generate_thumbnail:
            thumbnail_data = self._generate_thumbnail(img)

        # OCR 文字提取
        ocr_result = None
        if extract_text and self.enable_ocr:
            ocr_result = self._extract_text(img)

        return ProcessedImage(
            data=processed_data,
            metadata=metadata,
            thumbnail=thumbnail_data,
            ocr_result=ocr_result
        )

    def _generate_thumbnail(self, img) -> bytes:
        """生成缩略图"""
        Image = self.pil['Image']

        # 复制图片避免修改原图
        thumb = img.copy()
        thumb.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

        # 保存为 JPEG
        buffer = io.BytesIO()
        if thumb.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', thumb.size, (255, 255, 255))
            if thumb.mode == 'P':
                thumb = thumb.convert('RGBA')
            background.paste(thumb, mask=thumb.split()[-1] if thumb.mode in ('RGBA', 'LA') else None)
            thumb = background

        thumb.save(buffer, format='JPEG', quality=75, optimize=True)
        return buffer.getvalue()

    def _extract_text(self, img) -> Optional[OCRResult]:
        """使用 OCR 提取文字"""
        if not self.tesseract:
            return None

        try:
            # 使用 pytesseract 进行 OCR
            lang = '+'.join(self.ocr_languages)

            # 获取详细结果
            data = self.tesseract.image_to_data(
                img,
                lang=lang,
                output_type=self.tesseract.Output.DICT
            )

            # 解析结果
            text_parts = []
            bounding_boxes = []
            confidences = []

            for i, word in enumerate(data['text']):
                if word.strip():
                    conf = int(data['conf'][i])
                    if conf > 0:  # 过滤无效结果
                        text_parts.append(word)
                        confidences.append(conf)
                        bounding_boxes.append({
                            'text': word,
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'confidence': conf
                        })

            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return OCRResult(
                text=' '.join(text_parts),
                confidence=avg_confidence / 100,  # 转换为 0-1 范围
                bounding_boxes=bounding_boxes,
                language=lang
            )

        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return None

    def extract_from_pdf(self, pdf_data: bytes, page_numbers: List[int] = None) -> List[ProcessedImage]:
        """
        从 PDF 提取图片

        Args:
            pdf_data: PDF 文件数据
            page_numbers: 要提取的页码列表（从 0 开始）

        Returns:
            ProcessedImage 列表
        """
        try:
            from pdf2image import convert_from_bytes
        except ImportError:
            raise ImportError("pdf2image is required for PDF processing. Install with: pip install pdf2image")

        images = convert_from_bytes(
            pdf_data,
            dpi=150,  # 适中的分辨率
            fmt='png'
        )

        if page_numbers:
            images = [images[i] for i in page_numbers if 0 <= i < len(images)]

        results = []
        for i, img in enumerate(images):
            # 转换为 bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_data = buffer.getvalue()

            # 处理图片
            processed = self.process_image(
                img_data,
                resize=True,
                generate_thumbnail=True,
                extract_text=True,
                output_format=ImageFormat.PNG
            )
            results.append(processed)
            logger.debug(f"Processed PDF page {i + 1}")

        return results

    @staticmethod
    def to_base64(image_data: bytes, format: str = 'jpeg') -> str:
        """将图片数据转换为 base64 字符串"""
        b64 = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/{format};base64,{b64}"

    @staticmethod
    def from_base64(b64_string: str) -> bytes:
        """从 base64 字符串解码图片数据"""
        if ',' in b64_string:
            b64_string = b64_string.split(',', 1)[1]
        return base64.b64decode(b64_string)

    def get_image_info(self, image_data: bytes) -> ImageMetadata:
        """获取图片基本信息（不进行处理）"""
        Image = self.pil['Image']

        img = Image.open(io.BytesIO(image_data))

        return ImageMetadata(
            width=img.width,
            height=img.height,
            format=img.format or 'UNKNOWN',
            size_bytes=len(image_data),
            color_mode=img.mode,
            has_alpha=img.mode in ('RGBA', 'LA', 'P'),
            hash=hashlib.md5(image_data).hexdigest()
        )


# 全局实例
_processor: Optional[ImageProcessor] = None
_minio_storage: Optional[MinIOImageStorage] = None


def get_image_processor() -> ImageProcessor:
    """获取全局图片处理器实例"""
    global _processor
    if _processor is None:
        _processor = ImageProcessor()
    return _processor


def get_minio_storage() -> MinIOImageStorage:
    """获取全局 MinIO 存储实例"""
    global _minio_storage
    if _minio_storage is None:
        _minio_storage = MinIOImageStorage()
    return _minio_storage


def is_minio_enabled() -> bool:
    """检查是否启用 MinIO 存储"""
    return os.environ.get('IMAGE_STORAGE_TYPE', 'minio').lower() == 'minio'


class ImageService:
    """
    图片服务 - 统一的图片处理和存储接口
    Sprint 24: 整合处理器和存储
    """

    def __init__(self):
        self.processor = get_image_processor()
        self.use_minio = is_minio_enabled()
        if self.use_minio:
            try:
                self.storage = get_minio_storage()
            except Exception as e:
                logger.warning(f"MinIO not available, falling back to local storage: {e}")
                self.use_minio = False
                self.storage = None
        else:
            self.storage = None

    def upload_image(
        self,
        image_data: bytes,
        filename: str,
        generate_thumbnail: bool = True,
        extract_text: bool = False
    ) -> StoredImage:
        """
        上传并处理图片

        Args:
            image_data: 原始图片数据
            filename: 文件名
            generate_thumbnail: 是否生成缩略图
            extract_text: 是否进行 OCR

        Returns:
            StoredImage 对象
        """
        import uuid

        # 处理图片
        processed = self.processor.process_image(
            image_data,
            resize=True,
            generate_thumbnail=generate_thumbnail,
            extract_text=extract_text
        )

        # 生成 ID
        image_id = str(uuid.uuid4())
        content_type = f'image/{processed.metadata.format}'

        if self.use_minio and self.storage:
            # 上传到 MinIO
            storage_path = self.storage.upload(
                image_id,
                processed.data,
                content_type=content_type
            )

            thumbnail_path = None
            if processed.thumbnail:
                thumbnail_path = self.storage.upload(
                    image_id,
                    processed.thumbnail,
                    content_type='image/jpeg',
                    is_thumbnail=True
                )

            return StoredImage(
                image_id=image_id,
                url=f"/api/v1/images/{image_id}",
                thumbnail_url=f"/api/v1/images/{image_id}/thumbnail" if thumbnail_path else None,
                metadata=processed.metadata,
                storage_path=storage_path,
                storage_type='minio'
            )
        else:
            # 本地存储
            upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
            os.makedirs(upload_dir, exist_ok=True)

            image_path = os.path.join(upload_dir, f"{image_id}.{processed.metadata.format}")
            with open(image_path, 'wb') as f:
                f.write(processed.data)

            thumbnail_path = None
            if processed.thumbnail:
                thumbnail_path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")
                with open(thumbnail_path, 'wb') as f:
                    f.write(processed.thumbnail)

            return StoredImage(
                image_id=image_id,
                url=f"/api/v1/images/{image_id}",
                thumbnail_url=f"/api/v1/images/{image_id}/thumbnail" if thumbnail_path else None,
                metadata=processed.metadata,
                storage_path=image_path,
                storage_type='local'
            )

    def batch_upload(
        self,
        images: List[Tuple[bytes, str]],
        generate_thumbnails: bool = True
    ) -> List[StoredImage]:
        """
        批量上传图片

        Args:
            images: (图片数据, 文件名) 列表
            generate_thumbnails: 是否生成缩略图

        Returns:
            StoredImage 列表
        """
        results = []
        for image_data, filename in images:
            try:
                result = self.upload_image(
                    image_data,
                    filename,
                    generate_thumbnail=generate_thumbnails
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                # 继续处理其他图片
        return results

    def get_image(self, image_id: str) -> Optional[bytes]:
        """
        获取图片数据

        Args:
            image_id: 图片 ID

        Returns:
            图片数据
        """
        if self.use_minio and self.storage:
            try:
                return self.storage.download(f"images/{image_id}")
            except Exception:
                return None
        else:
            upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
            for ext in ['jpeg', 'jpg', 'png', 'webp', 'gif']:
                path = os.path.join(upload_dir, f"{image_id}.{ext}")
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        return f.read()
            return None

    def get_thumbnail(self, image_id: str) -> Optional[bytes]:
        """
        获取缩略图数据

        Args:
            image_id: 图片 ID

        Returns:
            缩略图数据
        """
        if self.use_minio and self.storage:
            try:
                return self.storage.download(f"images/{image_id}_thumb")
            except Exception:
                return None
        else:
            upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
            path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return f.read()
            return None

    def delete_image(self, image_id: str) -> bool:
        """
        删除图片

        Args:
            image_id: 图片 ID

        Returns:
            是否成功
        """
        if self.use_minio and self.storage:
            return self.storage.delete(image_id)
        else:
            upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
            deleted = False
            for ext in ['jpeg', 'jpg', 'png', 'webp', 'gif']:
                path = os.path.join(upload_dir, f"{image_id}.{ext}")
                if os.path.exists(path):
                    os.remove(path)
                    deleted = True
                    break
            thumb_path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            return deleted


# 全局图片服务实例
_image_service: Optional[ImageService] = None


def get_image_service() -> ImageService:
    """获取全局图片服务实例"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service

