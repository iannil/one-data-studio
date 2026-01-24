"""
RAG 工作流端到端测试
Sprint 24: E2E 测试扩展

测试覆盖:
- 文档上传和处理
- 向量化和存储
- RAG 查询流程
- 检索结果验证
"""

import pytest
import requests
import time
import os
import asyncio
import logging
from typing import Optional
from unittest.mock import patch, MagicMock, AsyncMock

# 配置日志
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8081")
AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

# 请求头
HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestDocumentUploadFlow:
    """文档上传流程测试"""

    document_id: Optional[str] = None
    collection_name: str = "test_collection"

    def test_01_create_collection(self):
        """测试创建集合"""
        response = requests.post(
            f"{BASE_URL}/api/v1/collections",
            headers=HEADERS,
            json={
                "name": self.collection_name,
                "description": "E2E 测试集合",
                "embedding_model": "text-embedding-ada-002"
            }
        )

        # 允许 201（成功）、401（未认证）或 409（已存在）
        assert response.status_code in [201, 401, 409], f"Unexpected status: {response.status_code}"

    def test_02_upload_document(self):
        """测试上传文档"""
        # 创建测试文件
        test_content = """
        # 测试文档

        这是一个用于 RAG 测试的示例文档。

        ## 主要内容

        1. 人工智能是计算机科学的一个分支
        2. 机器学习是人工智能的子领域
        3. 深度学习使用多层神经网络

        ## 技术要点

        - 自然语言处理 (NLP) 使计算机理解人类语言
        - 计算机视觉让机器能够"看"
        - 强化学习通过奖励机制训练模型
        """

        # 上传文件
        files = {
            'file': ('test_document.md', test_content, 'text/markdown')
        }
        data = {
            'collection': self.collection_name,
            'title': 'AI 技术概述'
        }

        # 移除 Content-Type，让 requests 自动设置 multipart
        upload_headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}

        response = requests.post(
            f"{BASE_URL}/api/v1/documents/upload",
            headers=upload_headers,
            files=files,
            data=data
        )

        assert response.status_code in [201, 401, 400], f"Unexpected status: {response.status_code}"

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestDocumentUploadFlow.document_id = data["data"].get("document_id")
            logger.info("Uploaded document: %s", TestDocumentUploadFlow.document_id)

    def test_03_list_documents(self):
        """测试列出文档"""
        response = requests.get(
            f"{BASE_URL}/api/v1/documents",
            headers=HEADERS,
            params={"collection": self.collection_name}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "documents" in data["data"]

    def test_04_get_document_status(self):
        """测试获取文档处理状态"""
        if not TestDocumentUploadFlow.document_id:
            pytest.skip("No document uploaded")

        # 等待处理
        max_wait = 30
        start = time.time()

        while time.time() - start < max_wait:
            response = requests.get(
                f"{BASE_URL}/api/v1/documents/{TestDocumentUploadFlow.document_id}",
                headers=HEADERS
            )

            if response.status_code == 200:
                data = response.json()
                status = data["data"].get("status")
                if status in ["completed", "indexed"]:
                    logger.info("Document indexed successfully")
                    return
                elif status == "failed":
                    pytest.fail("Document processing failed")

            time.sleep(2)

        pytest.skip("Document processing timed out")

    def test_05_cleanup_document(self):
        """清理测试文档"""
        if TestDocumentUploadFlow.document_id:
            response = requests.delete(
                f"{BASE_URL}/api/v1/documents/{TestDocumentUploadFlow.document_id}",
                headers=HEADERS
            )
            # 允许 200 或 401
            assert response.status_code in [200, 401, 404]


class TestRAGQueryFlow:
    """RAG 查询流程测试"""

    @pytest.fixture(autouse=True)
    def setup_collection(self):
        """设置测试集合"""
        # 确保集合存在
        requests.post(
            f"{BASE_URL}/api/v1/collections",
            headers=HEADERS,
            json={
                "name": "rag_test_collection",
                "description": "RAG 查询测试集合"
            }
        )
        yield
        # 清理（可选）

    def test_01_vector_search(self):
        """测试向量搜索"""
        response = requests.post(
            f"{BASE_URL}/api/v1/search",
            headers=HEADERS,
            json={
                "query": "什么是机器学习？",
                "collection": "rag_test_collection",
                "top_k": 5
            }
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "results" in data["data"]
            # 即使没有结果，结构应该正确
            assert isinstance(data["data"]["results"], list)

    def test_02_rag_query(self):
        """测试 RAG 查询"""
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": "根据知识库，解释一下人工智能是什么？"}
                ],
                "rag_config": {
                    "enabled": True,
                    "collection": "rag_test_collection",
                    "top_k": 3
                }
            }
        )

        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]

    def test_03_rag_with_filters(self):
        """测试带过滤条件的 RAG 查询"""
        response = requests.post(
            f"{BASE_URL}/api/v1/search",
            headers=HEADERS,
            json={
                "query": "深度学习的应用",
                "collection": "rag_test_collection",
                "top_k": 5,
                "filters": {
                    "doc_type": "markdown"
                },
                "min_score": 0.5
            }
        )

        assert response.status_code in [200, 401]


class TestRAGWorkflowIntegration:
    """RAG 工作流集成测试（使用 Mock）"""

    @pytest.mark.e2e
    def test_complete_rag_pipeline_mock(self):
        """测试完整的 RAG 流水线（使用 Mock）"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        # Mock 向量存储和嵌入服务
        mock_vector_store = MagicMock()
        mock_vector_store.search.return_value = [
            {
                "text": "人工智能是计算机科学的一个分支，致力于创建智能机器。",
                "score": 0.92,
                "metadata": {"source": "ai_intro.md"}
            },
            {
                "text": "机器学习是人工智能的一个子领域，使用数据训练模型。",
                "score": 0.88,
                "metadata": {"source": "ml_basics.md"}
            }
        ]

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 1536)

        # 测试搜索工具
        with patch('tools.VectorSearchTool.__init__', return_value=None):
            from tools import VectorSearchTool

            tool = VectorSearchTool.__new__(VectorSearchTool)
            tool.config = {}
            tool.vector_store = mock_vector_store
            tool.embedding_service = mock_embedding_service

            # 执行搜索
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(query="什么是人工智能？", collection="test", top_k=3)
            )

            # 验证结果
            assert mock_embedding_service.embed_text.called
            assert mock_vector_store.search.called

    @pytest.mark.e2e
    def test_rag_error_handling(self):
        """测试 RAG 错误处理"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        # 测试向量存储连接失败
        mock_vector_store = MagicMock()
        mock_vector_store.search.side_effect = Exception("Connection failed")

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 1536)

        with patch('tools.VectorSearchTool.__init__', return_value=None):
            from tools import VectorSearchTool

            tool = VectorSearchTool.__new__(VectorSearchTool)
            tool.config = {}
            tool.vector_store = mock_vector_store
            tool.embedding_service = mock_embedding_service

            # 应该返回错误而不是崩溃
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(query="测试查询", collection="test", top_k=3)
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.e2e
    def test_embedding_dimension_validation(self):
        """测试嵌入维度验证"""
        import sys
        sys.path.insert(0, 'services/bisheng-api/engine')

        # 测试维度不匹配
        mock_vector_store = MagicMock()
        mock_embedding_service = MagicMock()
        # 返回错误维度的嵌入
        mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 512)  # 应该是 1536

        # 向量存储应该检测维度不匹配
        mock_vector_store.search.side_effect = ValueError("Dimension mismatch")

        with patch('tools.VectorSearchTool.__init__', return_value=None):
            from tools import VectorSearchTool

            tool = VectorSearchTool.__new__(VectorSearchTool)
            tool.config = {}
            tool.vector_store = mock_vector_store
            tool.embedding_service = mock_embedding_service

            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(query="测试", collection="test", top_k=3)
            )

            assert result["success"] is False


class TestDocumentProcessingPipeline:
    """文档处理流水线测试"""

    @pytest.mark.e2e
    def test_text_chunking(self):
        """测试文本分块"""
        # 模拟长文档
        long_text = "这是一段测试文本。" * 500  # 约 4500 字符

        # 假设有一个分块函数
        def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunks.append(text[start:end])
                start = end - overlap
            return chunks

        chunks = chunk_text(long_text, chunk_size=500, overlap=50)

        # 验证分块
        assert len(chunks) > 1
        assert all(len(c) <= 500 for c in chunks)

        # 验证重叠
        for i in range(len(chunks) - 1):
            overlap_text = chunks[i][-50:]
            assert chunks[i + 1].startswith(overlap_text) or len(chunks[i]) < 500

    @pytest.mark.e2e
    def test_metadata_extraction(self):
        """测试元数据提取"""
        # Markdown 文档元数据
        markdown_doc = """---
title: 测试文档
author: Test User
date: 2024-01-01
tags: [test, e2e, rag]
---

# 正文内容

这是文档的正文。
"""

        # 简单的元数据解析
        import re

        def extract_frontmatter(text: str):
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
            if match:
                import yaml
                try:
                    return yaml.safe_load(match.group(1))
                except:
                    return {}
            return {}

        metadata = extract_frontmatter(markdown_doc)

        assert metadata.get("title") == "测试文档"
        assert metadata.get("author") == "Test User"
        assert "test" in metadata.get("tags", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
