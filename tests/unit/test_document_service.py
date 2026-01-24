"""
文档处理服务单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import os
import tempfile


class TestDocumentService:
    """DocumentService 单元测试"""

    @pytest.fixture
    def doc_service(self):
        """创建 DocumentService 实例"""
        from services.document import DocumentService
        return DocumentService()

    @pytest.fixture
    def doc_service_custom(self):
        """创建自定义配置的 DocumentService"""
        from services.document import DocumentService
        return DocumentService(chunk_size=100, chunk_overlap=20)

    def test_init_default_values(self):
        """测试默认初始化"""
        from services.document import DocumentService

        service = DocumentService()
        assert service.chunk_size == 500
        assert service.chunk_overlap == 50

    def test_init_custom_values(self):
        """测试自定义初始化"""
        from services.document import DocumentService

        service = DocumentService(chunk_size=1000, chunk_overlap=100)
        assert service.chunk_size == 1000
        assert service.chunk_overlap == 100

    def test_load_from_text_empty(self, doc_service):
        """测试加载空文本"""
        result = doc_service.load_from_text("")
        assert result == []

    def test_load_from_text_with_content(self, doc_service):
        """测试加载有内容的文本"""
        text = "This is a test document."
        result = doc_service.load_from_text(text)

        assert len(result) == 1
        assert result[0].page_content == text

    def test_load_from_text_with_metadata(self, doc_service):
        """测试加载带元数据的文本"""
        text = "Test content"
        metadata = {"source": "test", "author": "tester"}

        result = doc_service.load_from_text(text, metadata)

        assert len(result) == 1
        assert result[0].metadata == metadata

    def test_load_from_file_not_exists(self, doc_service):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            doc_service.load_from_file("/nonexistent/path/file.txt")

    def test_load_from_file_exists(self, doc_service):
        """测试加载存在的文件"""
        content = "Test file content"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = doc_service.load_from_file(temp_path)

            assert len(result) == 1
            assert result[0].page_content == content
            assert result[0].metadata["source"] == temp_path
            assert result[0].metadata["file_name"] == os.path.basename(temp_path)
            assert result[0].metadata["file_type"] == ".txt"
            assert "loaded_at" in result[0].metadata
        finally:
            os.unlink(temp_path)

    def test_split_text_empty(self, doc_service):
        """测试切分空文本"""
        result = doc_service.split_text("")
        assert result == []

    def test_split_text_short(self, doc_service):
        """测试切分短文本（不需要切分）"""
        text = "Short text"
        result = doc_service.split_text(text)

        assert len(result) == 1
        assert result[0] == text

    def test_split_text_long(self, doc_service_custom):
        """测试切分长文本"""
        # 创建一个长于 chunk_size 的文本
        text = "This is a test. " * 20  # 约 320 字符
        result = doc_service_custom.split_text(text)

        # 应该被切分成多个块
        assert len(result) > 1
        # 每个块都不应该超过 chunk_size
        for chunk in result:
            assert len(chunk) <= doc_service_custom.chunk_size

    def test_split_text_at_separator(self, doc_service_custom):
        """测试在分隔符处切分"""
        # 创建在句号处可以切分的文本
        text = "First sentence. Second sentence. " * 10
        result = doc_service_custom.split_text(text)

        # 验证切分发生在句号后
        for chunk in result[:-1]:  # 最后一块可能不以句号结尾
            assert chunk.endswith('.') or chunk.endswith(' ')

    def test_split_text_chinese(self, doc_service_custom):
        """测试切分中文文本"""
        text = "这是第一句话。这是第二句话！这是第三句话？" * 5
        result = doc_service_custom.split_text(text)

        # 应该能正常切分中文
        assert len(result) >= 1
        # 重组后应该包含所有内容
        combined = "".join(result)
        assert "这是第一句话" in combined

    def test_split_documents(self, doc_service_custom):
        """测试切分文档列表"""
        from services.document import Document

        doc = Document(
            page_content="Content. " * 50,
            metadata={"source": "test"}
        )

        result = doc_service_custom.split_documents([doc])

        assert len(result) > 1
        # 每个块都应该有元数据
        for i, chunk in enumerate(result):
            assert chunk.metadata["source"] == "test"
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["chunk_count"] == len(result)

    def test_create_document_from_upload(self, doc_service_custom):
        """测试从上传创建文档"""
        filename = "upload.txt"
        content = "Uploaded content. " * 20
        metadata = {"category": "test"}

        result = doc_service_custom.create_document_from_upload(
            filename, content, metadata
        )

        assert len(result) >= 1
        # 验证元数据
        assert result[0].metadata["source"] == filename
        assert result[0].metadata["file_name"] == filename
        assert result[0].metadata["category"] == "test"
        assert "uploaded_at" in result[0].metadata

    def test_estimate_tokens_english(self, doc_service):
        """测试英文 token 估算"""
        text = "Hello world"  # 11 字符，约 2-3 token
        tokens = doc_service.estimate_tokens(text)

        # 英文约 4 字符 = 1 token
        assert tokens == 11 // 4  # 2

    def test_estimate_tokens_chinese(self, doc_service):
        """测试中文 token 估算"""
        text = "你好世界"  # 4 个中文字符
        tokens = doc_service.estimate_tokens(text)

        # 中文约 1 字符 = 1 token
        assert tokens == 4

    def test_estimate_tokens_mixed(self, doc_service):
        """测试混合语言 token 估算"""
        text = "Hello 你好 World 世界"
        tokens = doc_service.estimate_tokens(text)

        # 4 个中文字符 + 约 4 个英文 token (包括空格)
        chinese_tokens = 4
        other_chars = len(text) - chinese_tokens
        expected = chinese_tokens + (other_chars // 4)
        assert tokens == expected

    def test_get_document_stats_empty(self, doc_service):
        """测试空文档列表统计"""
        stats = doc_service.get_document_stats([])

        assert stats["document_count"] == 0
        assert stats["total_characters"] == 0
        assert stats["total_tokens"] == 0
        assert stats["avg_characters_per_doc"] == 0
        assert stats["avg_tokens_per_doc"] == 0

    def test_get_document_stats(self, doc_service):
        """测试文档统计"""
        from services.document import Document

        docs = [
            Document("Hello world", {}),  # 11 chars
            Document("Test document content", {}),  # 21 chars
        ]

        stats = doc_service.get_document_stats(docs)

        assert stats["document_count"] == 2
        assert stats["total_characters"] == 32
        assert stats["avg_characters_per_doc"] == 16


class TestDocument:
    """Document 类测试"""

    def test_document_creation(self):
        """测试 Document 创建"""
        from services.document import Document

        doc = Document("content", {"key": "value"})

        assert doc.page_content == "content"
        assert doc.metadata == {"key": "value"}

    def test_document_default_metadata(self):
        """测试 Document 默认元数据"""
        from services.document import Document

        doc = Document("content")

        assert doc.metadata == {}

    def test_document_to_dict(self):
        """测试 Document 转字典"""
        from services.document import Document

        doc = Document("content", {"key": "value"})
        result = doc.to_dict()

        assert result == {
            "content": "content",
            "metadata": {"key": "value"}
        }
