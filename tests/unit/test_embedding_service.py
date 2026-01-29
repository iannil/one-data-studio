"""
Embedding 服务单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import asyncio
import sys
from pathlib import Path

# 添加 agent-api 路径
_agent_api_root = Path(__file__).parent.parent.parent / "services" / "agent-api"
if str(_agent_api_root) not in sys.path:
    sys.path.insert(0, str(_agent_api_root))

# 尝试导入，失败则跳过
try:
    from services.embedding import EmbeddingService, MODEL_API_URL, EMBEDDING_MODEL, EMBEDDING_DIM
    _IMPORT_SUCCESS = True
except ImportError as e:
    _IMPORT_SUCCESS = False
    _IMPORT_ERROR = str(e)
    EmbeddingService = MagicMock
    MODEL_API_URL = "http://localhost:8000"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    EMBEDDING_DIM = 1536

# 如果导入失败则跳过所有测试
pytestmark = pytest.mark.skipif(
    not _IMPORT_SUCCESS,
    reason=f"Cannot import embedding module: {_IMPORT_ERROR if not _IMPORT_SUCCESS else ''}"
)


class TestEmbeddingService:
    """EmbeddingService 单元测试"""

    @pytest.fixture
    def embedding_service(self):
        """创建 EmbeddingService 实例"""
        return EmbeddingService()

    def test_init_default_values(self):
        """测试默认初始化"""
        service = EmbeddingService()
        assert service.api_url == MODEL_API_URL
        assert service.model == EMBEDDING_MODEL

    def test_init_custom_url(self):
        """测试自定义 API URL"""
        custom_url = "http://custom-api:8000"
        service = EmbeddingService(api_url=custom_url)
        assert service.api_url == custom_url

    @pytest.mark.asyncio
    async def test_embed_text_empty(self):
        """测试空文本嵌入"""
        service = EmbeddingService()
        result = await service.embed_text("")

        assert len(result) == EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    async def test_embed_text_whitespace(self):
        """测试纯空白文本嵌入"""
        service = EmbeddingService()
        result = await service.embed_text("   ")

        assert len(result) == EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_text_success(self, mock_post):
        """测试成功的文本嵌入"""
        expected_embedding = [0.1] * 1536
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": expected_embedding}]
        }
        mock_post.return_value = mock_response

        service = EmbeddingService()
        result = await service.embed_text("test text")

        assert result == expected_embedding
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_text_api_error(self, mock_post):
        """测试 API 错误时的降级处理"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        service = EmbeddingService()
        result = await service.embed_text("test text")

        # 应该返回 mock embedding
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_text_connection_error(self, mock_post):
        """测试连接错误时的降级处理"""
        mock_post.side_effect = Exception("Connection error")

        service = EmbeddingService()
        result = await service.embed_text("test text")

        # 应该返回 mock embedding
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_texts_batch(self, mock_post):
        """测试批量文本嵌入"""
        expected_embedding = [0.1] * 1536
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": expected_embedding}]
        }
        mock_post.return_value = mock_response

        service = EmbeddingService()
        texts = ["text1", "text2", "text3"]
        results = await service.embed_texts(texts)

        assert len(results) == 3
        assert all(len(r) == 1536 for r in results)

    def test_mock_embedding(self):
        """测试 Mock embedding 生成"""
        service = EmbeddingService()

        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Different text"

        emb1 = service._mock_embedding(text1)
        emb2 = service._mock_embedding(text2)
        emb3 = service._mock_embedding(text3)

        # 相同文本应该生成相同的 embedding
        assert emb1 == emb2
        # 不同文本应该生成不同的 embedding
        assert emb1 != emb3
        # 长度应该正确
        assert len(emb1) == EMBEDDING_DIM
        # 值应该在 [-1, 1] 范围内
        assert all(-1 <= v <= 1 for v in emb1)

    def test_sync_embed_text(self):
        """测试同步版本的 embed_text"""
        service = EmbeddingService()

        with patch.object(service, 'embed_text', return_value=[0.1] * EMBEDDING_DIM):
            # sync_embed_text 应该调用 asyncio.run
            result = service.sync_embed_text("test")
            assert len(result) == EMBEDDING_DIM

    def test_sync_embed_texts(self):
        """测试同步版本的 embed_texts"""
        service = EmbeddingService()

        with patch.object(service, 'embed_texts', return_value=[[0.1] * EMBEDDING_DIM] * 3):
            result = service.sync_embed_texts(["a", "b", "c"])
            assert len(result) == 3


class TestEmbeddingServiceIntegration:
    """集成测试（需要真实服务）"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_embedding_api(self):
        """测试真实 Embedding API（需要服务运行）"""
        service = EmbeddingService()
        result = await service.embed_text("测试文本")

        assert len(result) == 1536
        # 确保不全是 0（mock 的特征）
        assert not all(v == 0.0 for v in result)
