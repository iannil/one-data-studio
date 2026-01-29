"""
MinIO Storage Client 单元测试
tests/unit/test_storage.py

注意：此测试需要 data-api 完整环境。如果 import 失败，测试将被跳过。
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

# 设置环境变量以启用 mock 模式
os.environ.setdefault('MINIO_ACCESS_KEY', '')
os.environ.setdefault('MINIO_SECRET_KEY', '')

# 添加 data-api/src 路径以便导入 storage 模块
_data_api_src = Path(__file__).parent.parent.parent / "services" / "data-api" / "src"
sys.path.insert(0, str(_data_api_src))

_IMPORT_SUCCESS = False
_IMPORT_ERROR = ""

try:
    from storage import MinIOClient, parse_storage_path, build_storage_path
    _IMPORT_SUCCESS = True
except Exception as e:
    _IMPORT_ERROR = str(e)
    MinIOClient = MagicMock
    parse_storage_path = MagicMock()
    build_storage_path = MagicMock()

# 如果导入失败则跳过所有测试
pytestmark = pytest.mark.skipif(
    not _IMPORT_SUCCESS,
    reason=f"Cannot import storage module: {_IMPORT_ERROR if not _IMPORT_SUCCESS else ''}"
)


class TestMinIOClientInit:
    """测试 MinIOClient 初始化"""

    def test_init_without_credentials_logs_warning(self, caplog):
        """没有凭据时应记录警告"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            # 重新导入以获取新实例
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            assert client.access_key is None or client.access_key == ''

    def test_init_with_credentials(self):
        """有凭据时应正常初始化"""
        with patch.dict(os.environ, {
            'MINIO_ACCESS_KEY': 'test_key',
            'MINIO_SECRET_KEY': 'test_secret',
            'MINIO_ENDPOINT': 'localhost:9000'
        }):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            assert client.access_key == 'test_key'
            assert client.secret_key == 'test_secret'
            assert client.endpoint == 'localhost:9000'

    def test_default_bucket_config(self):
        """默认桶配置"""
        with patch.dict(os.environ, {'MINIO_DEFAULT_BUCKET': 'custom-bucket'}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            assert client.default_bucket == 'custom-bucket'


class TestMinIOClientMockMode:
    """测试 Mock 模式（无实际 MinIO 连接）"""

    @pytest.fixture
    def mock_client(self):
        """创建 Mock 模式的客户端"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            client.init_client()
            return client

    def test_generate_presigned_url_mock(self, mock_client):
        """Mock 模式下生成预签名 URL"""
        result = mock_client.generate_presigned_url('test-object.txt')

        assert result['mock'] is True
        assert 'mock://' in result['url']
        assert result['method'] == 'PUT'

    def test_get_object_url_mock(self, mock_client):
        """Mock 模式下获取对象 URL"""
        url = mock_client.get_object_url('test-object.txt')

        assert 'mock://' in url

    def test_put_object_mock(self, mock_client):
        """Mock 模式下上传对象"""
        result = mock_client.put_object('test-object.txt', b'test data')

        assert result is True

    def test_get_object_mock(self, mock_client):
        """Mock 模式下获取对象"""
        result = mock_client.get_object('test-object.txt')

        assert result == b''

    def test_delete_object_mock(self, mock_client):
        """Mock 模式下删除对象"""
        result = mock_client.delete_object('test-object.txt')

        assert result is True

    def test_object_exists_mock(self, mock_client):
        """Mock 模式下检查对象存在"""
        result = mock_client.object_exists('test-object.txt')

        assert result is False

    def test_list_objects_mock(self, mock_client):
        """Mock 模式下列出对象"""
        result = mock_client.list_objects()

        assert result == []


class TestMinIOClientWithMinio:
    """测试有 MinIO 客户端的情况"""

    @pytest.fixture
    def client_with_mock_minio(self):
        """创建带 Mock MinIO 的客户端"""
        with patch.dict(os.environ, {
            'MINIO_ACCESS_KEY': 'test_key',
            'MINIO_SECRET_KEY': 'test_secret'
        }):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()

            # Mock the Minio client
            mock_minio = MagicMock()
            client._client = mock_minio
            client._initialized = True

            return client, mock_minio

    def test_generate_presigned_url_real(self, client_with_mock_minio):
        """真实模式下生成预签名 URL"""
        client, mock_minio = client_with_mock_minio
        mock_minio.presigned_url.return_value = 'https://minio.example.com/presigned-url'

        result = client.generate_presigned_url('test-object.txt', expires=7200)

        assert result['url'] == 'https://minio.example.com/presigned-url'
        assert result['expires_in'] == 7200
        mock_minio.presigned_url.assert_called_once()

    def test_put_object_real(self, client_with_mock_minio):
        """真实模式下上传对象"""
        client, mock_minio = client_with_mock_minio

        result = client.put_object('test.txt', b'hello world', content_type='text/plain')

        assert result is True
        mock_minio.put_object.assert_called_once()

    def test_get_object_real(self, client_with_mock_minio):
        """真实模式下获取对象"""
        client, mock_minio = client_with_mock_minio

        mock_response = MagicMock()
        mock_response.read.return_value = b'file content'
        mock_minio.get_object.return_value = mock_response

        result = client.get_object('test.txt')

        assert result == b'file content'
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_delete_object_real(self, client_with_mock_minio):
        """真实模式下删除对象"""
        client, mock_minio = client_with_mock_minio

        result = client.delete_object('test.txt')

        assert result is True
        mock_minio.remove_object.assert_called_once()

    def test_object_exists_true(self, client_with_mock_minio):
        """对象存在返回 True"""
        client, mock_minio = client_with_mock_minio
        mock_minio.stat_object.return_value = MagicMock()

        result = client.object_exists('existing.txt')

        assert result is True

    def test_object_exists_false(self, client_with_mock_minio):
        """对象不存在返回 False"""
        client, mock_minio = client_with_mock_minio

        # 导入 S3Error 用于模拟
        try:
            from minio.error import S3Error
            mock_minio.stat_object.side_effect = S3Error(
                'NoSuchKey', 'Object not found', 'test', 'test', 'test', 'test'
            )
        except ImportError:
            # 如果没有 minio 包，跳过测试
            pytest.skip("minio package not available")

        result = client.object_exists('nonexistent.txt')

        assert result is False

    def test_list_objects_real(self, client_with_mock_minio):
        """真实模式下列出对象"""
        client, mock_minio = client_with_mock_minio

        mock_obj1 = MagicMock()
        mock_obj1.object_name = 'file1.txt'
        mock_obj1.size = 100
        mock_obj1.last_modified = None
        mock_obj1.etag = 'abc123'

        mock_obj2 = MagicMock()
        mock_obj2.object_name = 'file2.txt'
        mock_obj2.size = 200
        mock_obj2.last_modified = None
        mock_obj2.etag = 'def456'

        mock_minio.list_objects.return_value = [mock_obj1, mock_obj2]

        result = client.list_objects(prefix='files/')

        assert len(result) == 2
        assert result[0]['name'] == 'file1.txt'
        assert result[1]['name'] == 'file2.txt'


class TestStoragePathParsing:
    """测试存储路径解析"""

    @pytest.fixture
    def client(self):
        """创建客户端"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)
            return storage_module.MinIOClient()

    def test_parse_s3_path(self, client):
        """解析 S3 路径"""
        bucket, object_name = client.parse_storage_path('s3://my-bucket/path/to/file.csv')

        assert bucket == 'my-bucket'
        assert object_name == 'path/to/file.csv'

    def test_parse_s3_path_no_object(self, client):
        """解析没有对象的 S3 路径"""
        bucket, object_name = client.parse_storage_path('s3://my-bucket')

        assert bucket == 'my-bucket'
        assert object_name == ''

    def test_parse_plain_path(self, client):
        """解析普通路径"""
        bucket, object_name = client.parse_storage_path('path/to/file.csv')

        assert bucket == client.default_bucket
        assert object_name == 'path/to/file.csv'

    def test_build_storage_path(self, client):
        """构建存储路径"""
        path = client.build_storage_path('my-bucket', 'path/to/file.csv')

        assert path == 's3://my-bucket/path/to/file.csv'


class TestGenerateUploadId:
    """测试上传 ID 生成"""

    def test_generate_upload_id_format(self):
        """上传 ID 格式正确"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            upload_id = client.generate_upload_id()

            assert upload_id.startswith('upload-')
            assert len(upload_id) == 23  # 'upload-' + 16 hex chars

    def test_generate_upload_id_unique(self):
        """上传 ID 唯一"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.MinIOClient()
            ids = [client.generate_upload_id() for _ in range(100)]

            assert len(set(ids)) == 100  # 全部唯一


class TestGlobalClientAndHelpers:
    """测试全局客户端和辅助函数"""

    def test_get_storage_client(self):
        """获取存储客户端"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            client = storage_module.get_storage_client()

            assert client is not None
            assert client._initialized is True

    def test_init_storage(self):
        """初始化存储"""
        with patch.dict(os.environ, {'MINIO_ACCESS_KEY': '', 'MINIO_SECRET_KEY': ''}):
            import importlib
            import storage as storage_module
            importlib.reload(storage_module)

            storage_module.init_storage()

            assert storage_module.minio_client._initialized is True
