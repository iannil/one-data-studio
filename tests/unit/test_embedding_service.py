"""
Embedding 服务单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import asyncio


class TestEmbeddingService:
    """EmbeddingService 单元测试"""

    @pytest.fixture
    def embedding_service(self):
        """创建 EmbeddingService 实例"""
        from services.embedding import EmbeddingService
        return EmbeddingService()

    def test_init_default_values(self):
        """测试默认初始化"""
        from services.embedding import EmbeddingService, CUBE_API_URL, EMBEDDING_MODEL

        service = EmbeddingService()
        assert service.api_url == CUBE_API_URL
        assert service.model == EMBEDDING_MODEL

    def test_init_custom_url(self):
        """测试自定义 API URL"""
        from services.embedding import EmbeddingService

        custom_url = "http://custom-api:8000"
        service = EmbeddingService(api_url=custom_url)
        assert service.api_url == custom_url

    @pytest.mark.asyncio
    async def test_embed_text_empty(self):
        """测试空文本嵌入"""
        from services.embedding import EmbeddingService, EMBEDDING_DIM

        service = EmbeddingService()
        result = await service.embed_text("")

        assert len(result) == EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    async def test_embed_text_whitespace(self):
        """测试纯空白文本嵌入"""
        from services.embedding import EmbeddingService, EMBEDDING_DIM

        service = EmbeddingService()
        result = await service.embed_text("   ")

        assert len(result) == EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_text_success(self, mock_post):
        """测试成功的文本嵌入"""
        from services.embedding import EmbeddingService

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
        from services.embedding import EmbeddingService, EMBEDDING_DIM

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
        from services.embedding import EmbeddingService, EMBEDDING_DIM

        mock_post.side_effect = Exception("Connection error")

        service = EmbeddingService()
        result = await service.embed_text("test text")

        # 应该返回 mock embedding
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    @patch('services.embedding.requests.post')
    async def test_embed_texts_batch(self, mock_post):
        """测试批量文本嵌入"""
        from services.embedding import EmbeddingService

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
        from services.embedding import EmbeddingService, EMBEDDING_DIM

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
        from services.embedding import EmbeddingService, EMBEDDING_DIM

        service = EmbeddingService()

        with patch.object(service, 'embed_text', return_value=[0.1] * EMBEDDING_DIM):
            # sync_embed_text 应该调用 asyncio.run
            result = service.sync_embed_text("test")
            assert len(result) == EMBEDDING_DIM

    def test_sync_embed_texts(self):
        """测试同步版本的 embed_texts"""
        from services.embedding import EmbeddingService, EMBEDDING_DIM

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
        from services.embedding import EmbeddingService

        service = EmbeddingService()
        result = await service.embed_text("测试文本")

        assert len(result) == 1536
        # 确保不全是 0（mock 的特征）
        assert not all(v == 0.0 for v in result)
