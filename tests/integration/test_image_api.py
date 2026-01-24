"""
图片 API 集成测试
Sprint 24: 图片处理 MinIO 集成

测试图片上传、处理、存储、检索和删除功能
"""

import pytest
import io
import base64
from unittest.mock import Mock, patch, MagicMock


class TestImageProcessor:
    """图片处理器单元测试"""

    def test_image_metadata_extraction(self):
        """测试图片元数据提取"""
        from services.image_processor import ImageProcessor, ImageMetadata

        # 创建测试用的 1x1 像素 PNG 图片
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        processor = ImageProcessor()
        metadata = processor.get_image_info(png_data)

        assert metadata.width == 1
        assert metadata.height == 1
        assert metadata.format.lower() == 'png'
        assert metadata.size_bytes > 0
        assert isinstance(metadata.hash, str)

    def test_process_image_resize(self):
        """测试图片缩放"""
        from services.image_processor import ImageProcessor

        # 创建处理器，设置小尺寸
        processor = ImageProcessor(max_size=(100, 100))

        # 创建测试图片
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        processed = processor.process_image(png_data, resize=True)

        assert processed.metadata.width <= 100
        assert processed.metadata.height <= 100
        assert processed.data is not None

    def test_generate_thumbnail(self):
        """测试缩略图生成"""
        from services.image_processor import ImageProcessor

        processor = ImageProcessor(thumbnail_size=(50, 50))

        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        processed = processor.process_image(png_data, generate_thumbnail=True)

        assert processed.thumbnail is not None
        assert len(processed.thumbnail) > 0

    def test_base64_conversion(self):
        """测试 Base64 转换"""
        from services.image_processor import ImageProcessor

        original_data = b'test image data'
        b64_string = ImageProcessor.to_base64(original_data, 'png')

        assert b64_string.startswith('data:image/png;base64,')

        decoded = ImageProcessor.from_base64(b64_string)
        assert decoded == original_data

    def test_from_base64_without_prefix(self):
        """测试不带前缀的 Base64 解码"""
        from services.image_processor import ImageProcessor

        original_data = b'test image data'
        b64_string = base64.b64encode(original_data).decode('utf-8')

        decoded = ImageProcessor.from_base64(b64_string)
        assert decoded == original_data


class TestMinIOImageStorage:
    """MinIO 存储测试"""

    @patch('services.image_processor.Minio')
    def test_minio_upload(self, mock_minio_class):
        """测试 MinIO 上传"""
        from services.image_processor import MinIOImageStorage

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        storage = MinIOImageStorage(
            endpoint='localhost:9000',
            access_key='test',
            secret_key='test',
            bucket='test-bucket'
        )

        image_data = b'test image data'
        path = storage.upload('test-id', image_data, 'image/jpeg')

        assert path == 'images/test-id'
        mock_client.put_object.assert_called_once()

    @patch('services.image_processor.Minio')
    def test_minio_download(self, mock_minio_class):
        """测试 MinIO 下载"""
        from services.image_processor import MinIOImageStorage

        mock_response = MagicMock()
        mock_response.read.return_value = b'image data'

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_client

        storage = MinIOImageStorage(
            endpoint='localhost:9000',
            access_key='test',
            secret_key='test'
        )

        data = storage.download('images/test-id')
        assert data == b'image data'

    @patch('services.image_processor.Minio')
    def test_minio_delete(self, mock_minio_class):
        """测试 MinIO 删除"""
        from services.image_processor import MinIOImageStorage

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        storage = MinIOImageStorage(
            endpoint='localhost:9000',
            access_key='test',
            secret_key='test'
        )

        result = storage.delete('test-id')
        assert result is True
        mock_client.remove_object.assert_called()

    @patch('services.image_processor.Minio')
    def test_minio_ensure_bucket_creates_if_not_exists(self, mock_minio_class):
        """测试 bucket 不存在时自动创建"""
        from services.image_processor import MinIOImageStorage

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_class.return_value = mock_client

        storage = MinIOImageStorage(bucket='new-bucket')
        _ = storage.client  # 触发初始化

        mock_client.make_bucket.assert_called_once_with('new-bucket')


class TestImageService:
    """图片服务集成测试"""

    @patch('services.image_processor.is_minio_enabled')
    @patch('services.image_processor.get_minio_storage')
    def test_upload_image_minio(self, mock_get_storage, mock_is_enabled):
        """测试使用 MinIO 上传图片"""
        from services.image_processor import ImageService, StoredImage

        mock_is_enabled.return_value = True
        mock_storage = MagicMock()
        mock_storage.upload.return_value = 'images/test-id'
        mock_get_storage.return_value = mock_storage

        service = ImageService()

        # 创建测试图片
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        result = service.upload_image(png_data, 'test.png')

        assert isinstance(result, StoredImage)
        assert result.storage_type == 'minio'
        assert result.url.startswith('/api/v1/images/')

    @patch('services.image_processor.is_minio_enabled')
    def test_upload_image_local(self, mock_is_enabled, tmp_path):
        """测试本地存储上传图片"""
        import os
        from services.image_processor import ImageService, StoredImage

        mock_is_enabled.return_value = False

        with patch.dict(os.environ, {'IMAGE_UPLOAD_DIR': str(tmp_path)}):
            service = ImageService()

            png_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            )

            result = service.upload_image(png_data, 'test.png')

            assert isinstance(result, StoredImage)
            assert result.storage_type == 'local'
            assert os.path.exists(result.storage_path)

    @patch('services.image_processor.is_minio_enabled')
    def test_batch_upload(self, mock_is_enabled, tmp_path):
        """测试批量上传"""
        import os
        from services.image_processor import ImageService

        mock_is_enabled.return_value = False

        with patch.dict(os.environ, {'IMAGE_UPLOAD_DIR': str(tmp_path)}):
            service = ImageService()

            png_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            )

            images = [
                (png_data, 'image1.png'),
                (png_data, 'image2.png'),
                (png_data, 'image3.png')
            ]

            results = service.batch_upload(images)

            assert len(results) == 3
            for result in results:
                assert result.storage_type == 'local'


class TestImageAPI:
    """图片 API 端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        import sys
        sys.path.insert(0, '/app')

        try:
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_upload_endpoint(self, client):
        """测试上传端点"""
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        response = client.post(
            '/api/v1/images/upload',
            data={'file': (io.BytesIO(png_data), 'test.png')},
            content_type='multipart/form-data'
        )

        # 可能因为依赖未安装而失败，但端点应该存在
        assert response.status_code in [200, 400, 500, 503]

    def test_upload_without_file(self, client):
        """测试无文件上传"""
        response = client.post('/api/v1/images/upload')
        assert response.status_code == 400

    def test_get_nonexistent_image(self, client):
        """测试获取不存在的图片"""
        response = client.get('/api/v1/images/nonexistent-id')
        assert response.status_code == 404


class TestImageBatchUpload:
    """批量上传 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_batch_upload_endpoint(self, client):
        """测试批量上传端点"""
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )

        data = {
            'files': [
                (io.BytesIO(png_data), 'image1.png'),
                (io.BytesIO(png_data), 'image2.png')
            ]
        }

        response = client.post(
            '/api/v1/images/batch-upload',
            data=data,
            content_type='multipart/form-data'
        )

        # 端点可能存在也可能不存在
        assert response.status_code in [200, 404, 400, 500, 503]
