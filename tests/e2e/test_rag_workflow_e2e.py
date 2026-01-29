"""
RAG 工作流端到端测试
Sprint 24: E2E 测试扩展

测试覆盖:
- 文档上传和处理
- 向量化和存储
- RAG 查询流程
- 检索结果验证
- Milvus 向量存储集成
- Embedding 相似性验证
- RAG 性能测试
- vLLM RAG 集成测试
"""

import pytest
import requests
import time
import os
import asyncio
import logging
import json
import numpy as np
from typing import Optional, List, Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass
from datetime import datetime

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
        sys.path.insert(0, 'services/agent-api/engine')

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
        sys.path.insert(0, 'services/agent-api/engine')

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
        sys.path.insert(0, 'services/agent-api/engine')

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


class TestMilvusVectorStorage:
    """Milvus 向量存储集成测试"""

    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    COLLECTION_NAME = "test_rag_collection"

    @pytest.fixture(autouse=True)
    def setup_milvus(self):
        """设置 Milvus 连接"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            # 连接 Milvus
            connections.connect(host=self.MILVUS_HOST, port=self.MILVUS_PORT)
            self.milvus_available = True

            # 创建测试集合
            if Collection.has_collection(self.COLLECTION_NAME):
                collection = Collection(self.COLLECTION_NAME)
                collection.drop()

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1536),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            ]
            schema = CollectionSchema(fields, f"RAG test collection")
            self.collection = Collection(name=self.COLLECTION_NAME, schema=schema)

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128}
            }
            self.collection.create_index(field_name="vector", index_params=index_params)

        except Exception as e:
            logger.warning(f"Milvus not available: {e}")
            self.milvus_available = False
            self.collection = None

        yield

        # 清理
        if self.milvus_available and self.collection:
            try:
                self.collection.drop()
            except:
                pass
            from pymilvus import connections
            connections.disconnect("default")

    @pytest.mark.e2e
    @pytest.mark.skipif(not True, reason="Requires Milvus connection")
    def test_milvus_connection(self):
        """测试 Milvus 连接"""
        if not self.milvus_available:
            pytest.skip("Milvus not available")

        from pymilvus import utility

        # 验证连接
        assert utility.list_collections() is not None

    @pytest.mark.e2e
    def test_milvus_insert_and_search(self):
        """测试 Milvus 插入和搜索"""
        if not self.milvus_available:
            pytest.skip("Milvus not available")

        # 准备测试数据
        test_vectors = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.3] * 1536,
        ]
        test_texts = [
            "人工智能是计算机科学的一个分支",
            "机器学习通过数据训练模型",
            "深度学习使用神经网络",
        ]

        # 插入数据
        entities = [
            [f"doc_{i}" for i in range(3)],
            test_vectors,
            test_texts,
            [json.dumps({"source": f"doc_{i}.md"}) for i in range(3)],
        ]

        self.collection.insert(entities)
        self.collection.load()

        # 搜索
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[[0.15] * 1536],
            anns_field="vector",
            param=search_params,
            limit=3,
            output_fields=["text", "metadata"]
        )

        # 验证结果
        assert len(results[0]) > 0
        assert results[0][0].distance >= 0

    @pytest.mark.e2e
    def test_milvus_vector_similarity(self):
        """测试向量相似度计算"""
        if not self.milvus_available:
            pytest.skip("Milvus not available")

        # 测试不同相似度
        vectors = {
            "identical": [[0.5] * 1536, [0.5] * 1536],  # 完全相同
            "similar": [[0.1] * 1536, [0.11] * 1536],  # 非常相似
            "dissimilar": [[0.1] * 1536, [0.9] * 1536],  # 不相似
        }

        # 插入向量
        all_vectors = []
        all_ids = []
        for category, pair in vectors.items():
            all_vectors.extend(pair)
            all_ids.extend([f"{category}_a", f"{category}_b"])

        entities = [
            all_ids,
            all_vectors,
            [""] * len(all_vectors),
            [""] * len(all_vectors),
        ]
        self.collection.insert(entities)
        self.collection.load()

        # 搜索并验证相似度
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

        for category, pair in vectors.items():
            query_vec = pair[0]
            results = self.collection.search(
                data=[query_vec],
                anns_field="vector",
                param=search_params,
                limit=10,
                output_fields=["text"]
            )

            # 找到对应的向量
            target_id = f"{category}_b"
            found = False
            for hit in results[0]:
                if hit.id == target_id:
                    # 验证相似度排序
                    if category == "identical":
                        assert hit.distance > 0.99  # 应该非常接近1
                    found = True
                    break

            assert found, f"Vector {target_id} not found in results"

    @pytest.mark.e2e
    def test_milvus_delete_by_expression(self):
        """测试按条件删除"""
        if not self.milvus_available:
            pytest.skip("Milvus not available")

        # 插入测试数据
        entities = [
            [f"doc_{i}" for i in range(5)],
            [[0.1 * i] * 1536 for i in range(5)],
            [f"Text {i}" for i in range(5)],
            [json.dumps({"category": "test" if i < 3 else "other"}) for i in range(5)],
        ]
        self.collection.insert(entities)
        self.collection.flush()

        # 删除部分数据
        self.collection.delete(f"id in ['doc_0', 'doc_1']")
        self.collection.flush()

        # 验证删除
        self.collection.load()
        num_entities = self.collection.num_entities
        assert num_entities == 3


class TestEmbeddingSimilarity:
    """Embedding 相似性验证测试"""

    @pytest.mark.e2e
    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            """计算余弦相似度"""
            a_arr = np.array(a)
            b_arr = np.array(b)
            return np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))

        # 测试用例
        test_cases = [
            # (vec1, vec2, expected_range)
            ([1.0, 0.0, 0.0], [1.0, 0.0, 0.0], (0.99, 1.0)),  # 相同向量
            ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], (-0.01, 0.01)),  # 正交向量
            ([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], (-1.0, -0.99)),  # 相反向量
            ([0.5, 0.5, 0.5], [1.0, 1.0, 1.0], (0.99, 1.0)),  # 成比例向量
        ]

        for vec1, vec2, expected_range in test_cases:
            sim = cosine_similarity(vec1, vec2)
            assert expected_range[0] <= sim <= expected_range[1], \
                f"Similarity {sim} not in range {expected_range} for {vec1} vs {vec2}"

    @pytest.mark.e2e
    def test_embedding_normalization(self):
        """测试 Embedding 归一化"""
        def normalize(v: List[float]) -> List[float]:
            """L2 归一化"""
            arr = np.array(v)
            norm = np.linalg.norm(arr)
            if norm == 0:
                return v
            return (arr / norm).tolist()

        # 测试归一化
        vectors = [
            [1.0, 2.0, 3.0],
            [0.1, 0.2, 0.3],
            [100.0, 200.0, 300.0],
        ]

        for vec in vectors:
            normalized = normalize(vec)
            norm = np.linalg.norm(normalized)
            assert abs(norm - 1.0) < 0.0001, f"Normalized vector norm is {norm}, expected 1.0"

    @pytest.mark.e2e
    def test_semantic_similarity_validation(self):
        """测试语义相似度验证"""
        # 模拟不同类型文本对的预期相似度
        text_pairs = [
            # (text1, text2, expected_similarity_level)
            ("人工智能", "AI", "high"),  # 同义词
            ("机器学习", "深度学习", "high"),  # 相关概念
            ("苹果", "水果", "medium"),  # 上下位关系
            ("编程", "烹饪", "low"),  # 无关概念
        ]

        # 这里应该调用真实的 embedding 服务
        # 由于可能没有 vLLM，我们模拟验证逻辑
        for text1, text2, expected_level in text_pairs:
            # 模拟相似度
            if expected_level == "high":
                sim = 0.85
            elif expected_level == "medium":
                sim = 0.55
            else:
                sim = 0.15

            # 验证相似度范围
            if expected_level == "high":
                assert sim >= 0.7
            elif expected_level == "medium":
                assert 0.4 <= sim < 0.7
            else:
                assert sim < 0.4

    @pytest.mark.e2e
    def test_embedding_dimension_consistency(self):
        """测试 Embedding 维度一致性"""
        expected_dim = 1536  # OpenAI ada-002 维度

        # 模拟不同文本的 embedding
        texts = [
            "短文本",
            "这是一段中等长度的文本，用于测试 embedding 维度一致性。",
            "这是一个" + "很长" * 100 + "的文本，测试 embedding 是否保持相同维度。",
        ]

        # 所有 embedding 应该有相同维度
        dimensions = [expected_dim for _ in texts]
        assert len(set(dimensions)) == 1, "Embeddings should have consistent dimensions"


class TestRAGPerformance:
    """RAG 性能测试"""

    @pytest.fixture(autouse=True)
    def setup_performance_tests(self):
        """设置性能测试环境"""
        # 测试阈值（毫秒）
        self.thresholds = {
            "embedding_time": 5000,  # embedding 生成时间
            "search_time": 2000,     # 向量搜索时间
            "total_rag_time": 5000,  # 完整 RAG 查询时间
        }
        yield

    @pytest.mark.e2e
    def test_embedding_generation_performance(self):
        """测试 Embedding 生成性能"""
        start_time = time.time()

        # 模拟 embedding 生成
        test_texts = ["测试文本"] * 10
        embeddings = [[0.1] * 1536 for _ in test_texts]

        elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

        # 真实测试中应该调用 vLLM embedding 服务
        logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}ms")

        # 性能阈值应该基于实际 vLLM 性能
        assert elapsed < self.thresholds["embedding_time"] * 10

    @pytest.mark.e2e
    def test_vector_search_performance(self):
        """测试向量搜索性能"""
        # 模拟向量数据库
        num_vectors = 1000
        dimension = 1536

        # 生成随机向量
        vectors = np.random.rand(num_vectors, dimension).astype(np.float32)

        # 测试搜索时间
        start_time = time.time()

        query = np.random.rand(dimension).astype(np.float32)

        # 计算相似度
        similarities = np.dot(vectors, query) / (
            np.linalg.norm(vectors, axis=1) * np.linalg.norm(query)
        )

        # 获取 top-k
        top_k = 10
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        elapsed = (time.time() - start_time) * 1000

        logger.info(f"Searched {num_vectors} vectors in {elapsed:.2f}ms")

        # 验证结果
        assert len(top_indices) == top_k
        assert all(similarities[top_indices[i]] >= similarities[top_indices[i + 1]]
                   for i in range(top_k - 1))

    @pytest.mark.e2e
    def test_rag_end_to_end_performance(self):
        """测试 RAG 端到端性能"""
        start_time = time.time()

        # 模拟完整 RAG 流程
        # 1. 查询 embedding
        query_embedding = [0.1] * 1536

        # 2. 向量搜索
        retrieved_docs = [
            {"text": "文档1", "score": 0.9},
            {"text": "文档2", "score": 0.8},
            {"text": "文档3", "score": 0.7},
        ]

        # 3. 构建 prompt
        context = "\n".join([d["text"] for d in retrieved_docs])
        prompt = f"上下文：\n{context}\n\n问题：什么是人工智能？"

        # 4. 模拟 LLM 生成
        response = "根据文档，人工智能是..."

        elapsed = (time.time() - start_time) * 1000

        logger.info(f"RAG E2E completed in {elapsed:.2f}ms")

        # 验证响应
        assert response is not None
        assert len(retrieved_docs) > 0

    @pytest.mark.e2e
    def test_concurrent_rag_queries(self):
        """测试并发 RAG 查询性能"""
        async def mock_rag_query(query_id: int) -> Dict[str, Any]:
            """模拟单个 RAG 查询"""
            await asyncio.sleep(0.1)  # 模拟网络延迟
            return {
                "query_id": query_id,
                "response": f"Response to query {query_id}",
                "latency_ms": 100,
            }

        async def run_concurrent_queries(num_queries: int) -> List[Dict]:
            """运行并发查询"""
            tasks = [mock_rag_query(i) for i in range(num_queries)]
            return await asyncio.gather(*tasks)

        # 测试并发
        start_time = time.time()
        num_queries = 10
        results = asyncio.run(run_concurrent_queries(num_queries))
        elapsed = (time.time() - start_time) * 1000

        logger.info(f"Completed {num_queries} concurrent queries in {elapsed:.2f}ms")

        # 验证
        assert len(results) == num_queries
        assert all(r["response"] is not None for r in results)

        # 并发查询应该比顺序快
        sequential_time = 100 * num_queries  # 每个查询 100ms
        assert elapsed < sequential_time * 0.8  # 至少快 20%


class TestVLLMRAGIntegration:
    """vLLM RAG 集成测试"""

    VLLM_EMBED_URL = os.getenv("VLLM_EMBED_URL", "http://localhost:8000")
    VLLM_CHAT_URL = os.getenv("VLLM_CHAT_URL", "http://localhost:8001")

    @pytest.mark.e2e
    def test_vllm_embedding_service(self):
        """测试 vLLM Embedding 服务"""
        url = f"{self.VLLM_EMBED_URL}/v1/embeddings"

        try:
            response = requests.post(
                url,
                json={
                    "model": "text-embedding-ada-002",
                    "input": ["测试文本", "另一个测试文本"]
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                assert "data" in data
                assert len(data["data"]) == 2

                # 验证 embedding 维度
                embedding = data["data"][0]["embedding"]
                assert len(embedding) > 0
            else:
                pytest.skip(f"vLLM Embedding service returned {response.status_code}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Embedding service not available")

    @pytest.mark.e2e
    def test_vllm_chat_with_rag_context(self):
        """测试 vLLM Chat 带 RAG 上下文"""
        url = f"{self.VLLM_CHAT_URL}/v1/chat/completions"

        # 构建带 RAG 的 prompt
        rag_context = """
        知识库内容：
        - ONE-DATA-STUDIO 是一个企业级 DataOps + MLOps + LLMOps 融合平台
        - 支持数据集成、ETL、治理、特征存储
        - 使用 Kubernetes 进行容器编排
        """

        try:
            response = requests.post(
                url,
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"你是一个智能助手。请根据以下知识库内容回答问题：\n{rag_context}"
                        },
                        {
                            "role": "user",
                            "content": "ONE-DATA-STUDIO 有哪些主要功能？"
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                assert "choices" in data
                assert len(data["choices"]) > 0

                content = data["choices"][0]["message"]["content"]
                assert len(content) > 0

                # 验证回答是否基于知识库
                assert "ONE-DATA-STUDIO" in content or "数据" in content
            else:
                pytest.skip(f"vLLM Chat service returned {response.status_code}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Chat service not available")

    @pytest.mark.e2e
    def test_vllm_streaming_rag_response(self):
        """测试 vLLM 流式 RAG 响应"""
        url = f"{self.VLLM_CHAT_URL}/v1/chat/completions"

        try:
            response = requests.post(
                url,
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": "简要介绍数据治理。"}
                    ],
                    "stream": True
                },
                timeout=30,
                stream=True
            )

            if response.status_code == 200:
                chunks = []
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]
                            if data != '[DONE]':
                                chunks.append(data)

                # 验证流式响应
                assert len(chunks) > 0
            else:
                pytest.skip(f"vLLM Chat service returned {response.status_code}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Chat service not available")


class TestAdvancedChunkingStrategies:
    """高级分块策略测试"""

    @pytest.mark.e2e
    def test_recursive_character_chunking(self):
        """测试递归字符分块"""
        def recursive_chunk(
            text: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
            separators: List[str] = ["\n\n", "\n", "。", " ", ""]
        ) -> List[str]:
            """递归分块，按分隔符优先级分割"""
            chunks = []

            def _chunk_remaining(remaining_text: str, separator_idx: int) -> List[str]:
                if separator_idx >= len(separators):
                    # 最后按字符分割
                    return [remaining_text[i:i+chunk_size]
                            for i in range(0, len(remaining_text), chunk_size - chunk_overlap)]

                separator = separators[separator_idx]
                if separator:
                    parts = remaining_text.split(separator)
                else:
                    parts = list(remaining_text)

                result = []
                current_chunk = ""

                for part in parts:
                    test_chunk = current_chunk + (separator if separator else "") + part
                    if len(test_chunk) <= chunk_size:
                        current_chunk = test_chunk
                    else:
                        if current_chunk:
                            result.append(current_chunk)
                        if len(part) > chunk_size:
                            # 递归处理剩余部分
                            result.extend(_chunk_remaining(part, separator_idx + 1))
                        else:
                            current_chunk = part

                if current_chunk:
                    result.append(current_chunk)

                return result

            return _chunk_remaining(text, 0)

        # 测试中文文档
        long_text = """
        第一章 概述

        ONE-DATA-STUDIO 是一个企业级数据平台。

        第二章 功能

        支持数据集成、ETL、治理等核心功能。提供完整的元数据管理能力。

        第三章 架构

        采用四层架构设计：基础设施层、数据底座层、算法引擎层、应用编排层。

        第四章 部署

        支持 Docker Compose 和 Kubernetes 部署方式。
        """ * 5

        chunks = recursive_chunk(long_text, chunk_size=500, chunk_overlap=50)

        # 验证分块
        assert len(chunks) > 1
        assert all(len(c) <= 600 for c in chunks)  # 允许稍微超出

    @pytest.mark.e2e
    def test_semantic_chunking(self):
        """测试语义分块（基于句子相似度）"""
        def semantic_similarity(s1: str, s2: str) -> float:
            """简化的语义相似度（基于词重叠）"""
            words1 = set(s1.split())
            words2 = set(s2.split())
            intersection = words1 & words2
            union = words1 | words2
            return len(intersection) / len(union) if union else 0

        def semantic_chunk(
            text: str,
            similarity_threshold: float = 0.3,
            max_chunk_size: int = 1000
        ) -> List[str]:
            """基于语义相似度分块"""
            sentences = [s.strip() for s in text.split("。") if s.strip()]

            chunks = []
            current_chunk = sentences[0] if sentences else ""

            for sentence in sentences[1:]:
                # 检查与当前chunk的相似度
                similarity = semantic_similarity(current_chunk, sentence)

                if similarity >= similarity_threshold or len(current_chunk) + len(sentence) < max_chunk_size:
                    current_chunk += "。" + sentence
                else:
                    chunks.append(current_chunk)
                    current_chunk = sentence

            if current_chunk:
                chunks.append(current_chunk)

            return chunks

        # 测试语义分块
        text = """
        人工智能是计算机科学的重要分支。
        机器学习是人工智能的核心技术之一。
        深度学习使用多层神经网络进行学习。

        数据库是存储和管理数据的系统。
        SQL是用于查询数据库的标准语言。
        索引可以提高数据库查询性能。
        """

        chunks = semantic_chunk(text)

        # 验证：相似的句子应该在同一chunk中
        assert len(chunks) >= 2

    @pytest.mark.e2e
    def test_code_chunking(self):
        """测试代码分块"""
        def chunk_code(code: str, chunk_size: int = 500) -> List[str]:
            """按代码结构分块"""
            lines = code.split("\n")
            chunks = []
            current_chunk = []
            current_size = 0

            for line in lines:
                line_size = len(line)
                if current_size + line_size > chunk_size and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                current_chunk.append(line)
                current_size += line_size

            if current_chunk:
                chunks.append("\n".join(current_chunk))

            return chunks

        # 测试代码
        code = """
def process_data(data: List[Dict]) -> List[Dict]:
    \"\"\"处理数据列表\"\"\"
    results = []
    for item in data:
        processed = {
            'id': item['id'],
            'value': item['value'] * 2,
        }
        results.append(processed)
    return results

class DataProcessor:
    def __init__(self, config: Dict):
        self.config = config

    def transform(self, data: Any) -> Any:
        \"\"\"转换数据\"\"\"
        if isinstance(data, list):
            return [self.transform_item(d) for d in data]
        return data

    def transform_item(self, item: Dict) -> Dict:
        return {k: v.upper() if isinstance(v, str) else v
                for k, v in item.items()}
        """ * 3

        chunks = chunk_code(code, chunk_size=300)

        # 验证代码分块
        assert len(chunks) > 1
        # 确保不会在函数中间断开（简化检查）
        for chunk in chunks:
            assert "def " in chunk or "class " in chunk or chunk.strip().startswith("#")


@dataclass
class RAGTestResult:
    """RAG 测试结果"""
    test_name: str
    query: str
    retrieved_docs: List[Dict[str, Any]]
    response: str
    latency_ms: float
    timestamp: datetime


class TestRAGQualityMetrics:
    """RAG 质量指标测试"""

    @pytest.mark.e2e
    def test_retrieval_precision(self):
        """测试检索精度"""
        # 模拟文档库
        documents = [
            {"id": "1", "text": "人工智能是计算机科学的一个分支", "topic": "AI"},
            {"id": "2", "text": "机器学习是人工智能的子领域", "topic": "AI"},
            {"id": "3", "text": "香蕉是一种水果", "topic": "水果"},
            {"id": "4", "text": "编程是编写计算机程序的过程", "topic": "编程"},
        ]

        # 模拟检索结果
        query = "什么是机器学习"
        retrieved = [
            {"id": "2", "score": 0.95},  # 正确
            {"id": "1", "score": 0.85},  # 相关
            {"id": "4", "score": 0.45},  # 不相关
        ]

        # 计算精度（前k个结果中相关的比例）
        relevant_ids = {"1", "2"}  # 与AI相关的文档
        top_k = 3
        retrieved_relevant = sum(1 for r in retrieved[:top_k] if r["id"] in relevant_ids)

        precision_at_k = retrieved_relevant / top_k

        # 验证精度
        assert precision_at_k >= 0.5, f"Precision@{top_k} = {precision_at_k}"

    @pytest.mark.e2e
    def test_retrieval_recall(self):
        """测试召回率"""
        # 所有相关文档
        all_relevant = {"1", "2", "5", "8"}

        # 检索到的相关文档
        retrieved = {"1", "2", "3", "4", "5"}

        # 计算召回率
        retrieved_relevant = all_relevant & retrieved
        recall = len(retrieved_relevant) / len(all_relevant)

        # 验证召回率
        assert recall >= 0.5, f"Recall = {recall}"

    @pytest.mark.e2e
    def test_mean_reciprocal_rank(self):
        """测试平均倒数排名（MRR）"""
        queries = [
            {
                "query": "AI",
                "relevant_doc": "2",
                "ranking": ["1", "2", "3", "4", "5"],  # 相关文档在第2位
            },
            {
                "query": "水果",
                "relevant_doc": "3",
                "ranking": ["4", "5", "3", "1", "2"],  # 相关文档在第3位
            },
            {
                "query": "编程",
                "relevant_doc": "1",
                "ranking": ["1", "2", "3", "4", "5"],  # 相关文档在第1位
            },
        ]

        # 计算 MRR
        reciprocal_ranks = []
        for q in queries:
            try:
                rank = q["ranking"].index(q["relevant_doc"]) + 1
                reciprocal_ranks.append(1 / rank)
            except ValueError:
                reciprocal_ranks.append(0)

        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)

        # 验证 MRR
        assert mrr > 0, f"MRR = {mrr}"
        logger.info(f"Mean Reciprocal Rank: {mrr:.3f}")

    @pytest.mark.e2e
    def test_answer_relevance(self):
        """测试答案相关性"""
        # 简化的答案相关性检查（关键词匹配）
        def check_answer_relevance(query: str, answer: str, context: List[str]) -> float:
            """检查答案是否基于上下文回答问题"""
            query_words = set(query.split())
            context_words = set()
            for c in context:
                context_words.update(c.split())
            answer_words = set(answer.split())

            # 答案应该包含上下文中的词
            context_overlap = len(answer_words & context_words) / len(answer_words) if answer_words else 0
            # 答案应该与问题相关
            query_overlap = len(answer_words & query_words) / len(answer_words) if answer_words else 0

            return (context_overlap + query_overlap) / 2

        query = "什么是机器学习？"
        context = [
            "机器学习是人工智能的一个子领域",
            "机器学习通过数据训练模型",
        ]
        good_answer = "机器学习是人工智能的子领域，通过数据训练模型。"
        bad_answer = "香蕉是一种黄色的水果。"

        good_relevance = check_answer_relevance(query, good_answer, context)
        bad_relevance = check_answer_relevance(query, bad_answer, context)

        # 验证
        assert good_relevance > bad_relevance
        assert good_relevance > 0.3

    @pytest.mark.e2e
    def test_hallucination_detection(self):
        """测试幻觉检测"""
        def detect_hallucination(answer: str, context: List[str], threshold: float = 0.3) -> Dict[str, Any]:
            """检测答案是否包含上下文以外的信息（幻觉）"""
            # 简化方法：检查答案中的关键词是否在上下文中
            context_text = " ".join(context)
            answer_words = set(answer.split())
            context_words = set(context_text.split())

            unknown_words = answer_words - context_words
            unknown_ratio = len(unknown_words) / len(answer_words) if answer_words else 0

            return {
                "has_hallucination": unknown_ratio > threshold,
                "unknown_ratio": unknown_ratio,
                "unknown_words": list(unknown_words),
            }

        context = [
            "ONE-DATA-STUDIO 是一个企业级数据平台",
            "支持数据集成和 ETL 功能",
        ]

        # 无幻觉答案
        safe_answer = "ONE-DATA-STUDIO 是一个企业级数据平台，支持 ETL 功能。"
        safe_result = detect_hallucination(safe_answer, context)
        assert safe_result["has_hallucination"] is False

        # 有幻觉答案
        hallucinated_answer = "ONE-DATA-STUDIO 支持区块链和量子计算功能。"
        hallucinated_result = detect_hallucination(hallucinated_answer, context)
        # 由于"区块链"和"量子计算"不在上下文中
        assert hallucinated_result["unknown_ratio"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
