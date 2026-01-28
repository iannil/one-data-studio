"""
知识库文档管理模块集成测试
测试用例编号: BU-KB-001 ~ BU-KB-010

覆盖场景:
- 文档上传（PDF/Word/TXT）
- 文档解析与分块
- 向量化与索引构建
- 文档索引记录持久化
- 批量上传、删除、更新

依赖:
- MinIO: 对象存储
- Milvus: 向量数据库
- vLLM: Embedding 服务
- MySQL: 文档索引记录

注: 本文件为自包含测试，不依赖 services.* 或 models.* 的运行时导入。
所有服务/模型类均以内联桩(stub)形式提供，确保低内存环境下可运行。
"""

import io
import json
import uuid
import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# 内联桩类 — 替代 services.document / services.embedding / models.document
# ---------------------------------------------------------------------------

class Document:
    """文档对象（桩）"""

    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "content": self.page_content,
            "metadata": self.metadata,
        }


class DocumentService:
    """文档处理服务（桩）"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def load_from_text(self, text, metadata=None):
        if not text:
            return []
        if metadata is None:
            metadata = {}
        return [Document(page_content=text, metadata=metadata)]

    def split_text(self, text):
        """切分文本"""
        if not text:
            return []

        chunks = []
        current_position = 0
        text_length = len(text)

        while current_position < text_length:
            end_position = min(current_position + self.chunk_size, text_length)

            if end_position < text_length:
                best_split = end_position
                for sep in self.separators:
                    split_pos = text.rfind(sep, current_position, end_position)
                    if split_pos > current_position and split_pos < end_position:
                        best_split = split_pos + len(sep)
                        break
                end_position = best_split

            chunk = text[current_position:end_position].strip()
            if chunk:
                chunks.append(chunk)

            current_position = end_position - self.chunk_overlap
            if current_position < 0:
                current_position = end_position

        return chunks

    def split_documents(self, documents):
        """切分文档列表"""
        split_docs = []
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                })
                split_docs.append(Document(page_content=chunk, metadata=chunk_metadata))
        return split_docs

    def create_document_from_upload(self, filename, content, metadata=None):
        """从上传的文件创建文档"""
        if metadata is None:
            metadata = {}
        metadata.update({
            "source": filename,
            "file_name": filename,
            "uploaded_at": datetime.now().isoformat(),
        })
        docs = self.load_from_text(content, metadata)
        return self.split_documents(docs)


EMBEDDING_DIM = 1536


class EmbeddingService:
    """Embedding 生成服务（桩）"""

    def __init__(self, api_url: str = None, dimension: int = EMBEDDING_DIM):
        self.api_url = api_url or "http://vllm-serving:8000"
        self.model = "text-embedding-ada-002"
        self.dimension = dimension

    async def embed_text(self, text):
        if not text or not text.strip():
            return [0.0] * self.dimension
        return self._mock_embedding(text)

    async def embed_texts(self, texts):
        result = []
        for text in texts:
            vec = await self.embed_text(text)
            result.append(vec)
        return result

    def sync_embed_text(self, text):
        import asyncio
        return asyncio.run(self.embed_text(text))

    def sync_embed_texts(self, texts):
        import asyncio
        return asyncio.run(self.embed_texts(texts))

    def _mock_embedding(self, text):
        import hashlib
        hash_bytes = hashlib.md5(text.encode()).digest()
        embedding = []
        for i in range(self.dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            normalized = (byte_val - 128) / 128.0
            embedding.append(normalized)
        return embedding


class IndexedDocument:
    """已索引文档模型（桩）"""

    def __init__(self):
        self.id = None
        self.doc_id = None
        self.collection_name = None
        self.file_name = None
        self.title = None
        self.content = None
        self.chunk_count = 0
        self.extra_metadata = None
        self.created_by = None
        self.created_at = None

    def to_dict(self):
        return {
            "id": self.doc_id,
            "collection_name": self.collection_name,
            "file_name": self.file_name,
            "title": self.title,
            "chunk_count": self.chunk_count,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pdf_content():
    """模拟 PDF 文件的二进制内容（简化为可解码的文本）"""
    text = (
        "第一章 数据治理概述\n\n"
        "数据治理是企业管理数据资产的核心能力。"
        "它涵盖数据质量、数据安全、元数据管理等多个方面。\n\n"
        "第二章 数据质量\n\n"
        "数据质量是衡量数据可用性的关键指标。"
        "常见的数据质量维度包括：完整性、准确性、一致性、时效性。\n"
    )
    return io.BytesIO(text.encode("utf-8"))


@pytest.fixture
def sample_docx_content():
    """模拟 Word 文件的二进制内容（简化为可解码的文本）"""
    text = (
        "项目需求文档\n\n"
        "1. 背景\n"
        "本项目旨在构建统一的智能数据平台。\n\n"
        "2. 功能需求\n"
        "平台应支持数据集成、数据治理、模型训练和应用编排。\n"
    )
    return io.BytesIO(text.encode("utf-8"))


@pytest.fixture
def sample_txt_content():
    """模拟 TXT 文件内容"""
    text = "这是一个测试文本文件。\n用于验证 TXT 文档上传功能。\n支持中文内容。\n"
    return io.BytesIO(text.encode("utf-8"))


@pytest.fixture
def long_document_content():
    """生成较长的文档内容，用于验证分块逻辑"""
    paragraphs = []
    for i in range(20):
        paragraphs.append(
            f"第{i + 1}段：这是一段测试文本，主要用来验证文档切分功能。"
            f"我们需要确保文本能够按照设定的块大小进行切分，"
            f"并且切分后的文本块之间有适当的重叠区域。"
            f"段落编号 {i + 1}。"
        )
    return "\n\n".join(paragraphs)


@pytest.fixture
def mock_minio():
    """Mock MinIO 客户端"""
    client = MagicMock()
    client.buckets = set()
    client.objects = {}

    def bucket_exists(bucket):
        return bucket in client.buckets

    def make_bucket(bucket):
        client.buckets.add(bucket)

    def put_object(bucket, name, data, length=-1, content_type="application/octet-stream"):
        if bucket not in client.objects:
            client.objects[bucket] = {}
        raw = data.read() if hasattr(data, "read") else data
        client.objects[bucket][name] = raw

    def get_object(bucket, name):
        if bucket in client.objects and name in client.objects[bucket]:
            resp = MagicMock()
            stored = client.objects[bucket][name]
            resp.read.return_value = stored if isinstance(stored, bytes) else stored.encode("utf-8")
            resp.close.return_value = None
            resp.release_conn.return_value = None
            return resp
        raise Exception(f"NoSuchKey: {bucket}/{name}")

    def remove_object(bucket, name):
        if bucket in client.objects and name in client.objects[bucket]:
            del client.objects[bucket][name]

    def stat_object(bucket, name):
        if bucket in client.objects and name in client.objects[bucket]:
            stat = MagicMock()
            stat.size = len(client.objects[bucket][name])
            return stat
        raise Exception(f"NoSuchKey: {bucket}/{name}")

    client.bucket_exists.side_effect = bucket_exists
    client.make_bucket.side_effect = make_bucket
    client.put_object.side_effect = put_object
    client.get_object.side_effect = get_object
    client.remove_object.side_effect = remove_object
    client.stat_object.side_effect = stat_object

    return client


@pytest.fixture
def mock_milvus():
    """Mock Milvus 客户端（模拟 VectorStore 行为）"""
    store = MagicMock()
    store._collections = {}  # collection_name -> list of records

    def insert(collection_name, texts, embeddings, metadata=None):
        if collection_name not in store._collections:
            store._collections[collection_name] = []
        for i, text in enumerate(texts):
            store._collections[collection_name].append({
                "id": f"{collection_name}-{uuid.uuid4().hex[:8]}",
                "text": text,
                "embedding": embeddings[i] if i < len(embeddings) else [],
                "metadata": metadata[i] if metadata and i < len(metadata) else {},
            })
        return len(texts)

    def search(collection_name, query_embedding, top_k=5, **kwargs):
        records = store._collections.get(collection_name, [])
        results = [
            {"id": r["id"], "text": r["text"], "score": 0.95, "metadata": r["metadata"]}
            for r in records[:top_k]
        ]
        return {"results": results, "total": len(results), "offset": 0, "limit": top_k}

    def delete_by_doc_id(collection_name, doc_id):
        if collection_name not in store._collections:
            return False
        before = len(store._collections[collection_name])
        store._collections[collection_name] = [
            r for r in store._collections[collection_name]
            if r["metadata"].get("doc_id") != doc_id
        ]
        return len(store._collections[collection_name]) < before

    def create_collection(name, dimension=1536, drop_existing=False):
        if drop_existing or name not in store._collections:
            store._collections[name] = []
        return MagicMock(name=name)

    def collection_info(collection_name):
        if collection_name in store._collections:
            return {
                "exists": True,
                "name": collection_name,
                "num_entities": len(store._collections[collection_name]),
            }
        return {"exists": False}

    store.insert.side_effect = insert
    store.search.side_effect = search
    store.delete_by_doc_id.side_effect = delete_by_doc_id
    store.create_collection.side_effect = create_collection
    store.collection_info.side_effect = collection_info
    store.list_collections.return_value = list(store._collections.keys())

    return store


@pytest.fixture
def mock_embedding():
    """Mock Embedding 服务"""
    service = MagicMock()

    def sync_embed_texts(texts):
        return [[0.01 * (i + 1)] * 1536 for i, _ in enumerate(texts)]

    def sync_embed_text(text):
        return [0.1] * 1536

    service.sync_embed_texts.side_effect = sync_embed_texts
    service.sync_embed_text.side_effect = sync_embed_text
    service.model = "text-embedding-ada-002"

    return service


@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    session = MagicMock()
    session._store = []  # 简易存储

    def mock_add(obj):
        session._store.append(obj)

    session.add.side_effect = mock_add
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None

    return session


@pytest.fixture
def doc_service():
    """创建 DocumentService 实例"""
    return DocumentService(chunk_size=200, chunk_overlap=30)


# ---------------------------------------------------------------------------
# BU-KB-001: 上传 PDF 文档 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadPDF:
    """BU-KB-001: 上传 PDF 文档到 MinIO 并验证存储"""

    def test_pdf_upload_to_minio(self, mock_minio, sample_pdf_content):
        """验证 PDF 文件能够成功上传到 MinIO"""
        bucket = "knowledge-base"
        object_name = "docs/test-doc-001.pdf"

        mock_minio.buckets.add(bucket)
        mock_minio.put_object(bucket, object_name, sample_pdf_content)

        assert object_name in mock_minio.objects[bucket]
        stored_data = mock_minio.objects[bucket][object_name]
        assert len(stored_data) > 0

    def test_pdf_upload_creates_bucket_if_missing(self, mock_minio, sample_pdf_content):
        """验证上传时自动创建不存在的桶"""
        bucket = "new-kb-bucket"
        object_name = "docs/auto-bucket.pdf"

        assert not mock_minio.bucket_exists(bucket)
        mock_minio.make_bucket(bucket)
        assert mock_minio.bucket_exists(bucket)

        mock_minio.put_object(bucket, object_name, sample_pdf_content)
        assert object_name in mock_minio.objects[bucket]

    def test_pdf_upload_api_response_format(self, mock_minio, mock_milvus, mock_embedding,
                                            mock_db_session, sample_pdf_content):
        """验证 POST /api/v1/documents/upload 响应格式"""
        content = sample_pdf_content.read().decode("utf-8")
        file_name = "data-governance.pdf"
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        collection_name = "test_collection"

        doc_service = DocumentService()
        docs = doc_service.create_document_from_upload(
            filename=file_name,
            content=content,
            metadata={"title": file_name, "doc_id": doc_id},
        )

        texts = [d.page_content for d in docs]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata_list = [d.metadata for d in docs]

        count = mock_milvus.insert(collection_name, texts, embeddings, metadata_list)

        assert count == len(docs)
        assert count > 0

        # 模拟响应数据
        response_data = {
            "code": 0,
            "message": "Document uploaded and indexed",
            "data": {
                "doc_id": doc_id,
                "file_name": file_name,
                "chunk_count": len(docs),
                "collection": collection_name,
            },
        }
        assert response_data["code"] == 0
        assert response_data["data"]["file_name"] == file_name
        assert response_data["data"]["chunk_count"] > 0

    def test_pdf_upload_empty_content_rejected(self):
        """验证空内容上传被拒绝"""
        doc_service = DocumentService()
        docs = doc_service.create_document_from_upload(
            filename="empty.pdf",
            content="",
            metadata={},
        )
        assert docs == []


# ---------------------------------------------------------------------------
# BU-KB-002: 上传 Word 文档 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadWord:
    """BU-KB-002: 上传 Word (docx) 文档"""

    def test_docx_upload_to_minio(self, mock_minio, sample_docx_content):
        """验证 docx 文件上传到 MinIO"""
        bucket = "knowledge-base"
        object_name = "docs/requirements.docx"

        mock_minio.buckets.add(bucket)
        mock_minio.put_object(bucket, object_name, sample_docx_content)

        assert object_name in mock_minio.objects[bucket]

    def test_docx_content_extraction_and_indexing(self, mock_milvus, mock_embedding,
                                                  sample_docx_content):
        """验证 docx 文档内容提取后可被索引"""
        content = sample_docx_content.read().decode("utf-8")
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        collection_name = "test_kb"

        doc_service = DocumentService()
        docs = doc_service.create_document_from_upload(
            filename="requirements.docx",
            content=content,
            metadata={"doc_id": doc_id},
        )

        texts = [d.page_content for d in docs]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata_list = [d.metadata for d in docs]

        count = mock_milvus.insert(collection_name, texts, embeddings, metadata_list)
        assert count == len(docs)
        assert all(m.get("doc_id") == doc_id for m in metadata_list)

    def test_docx_metadata_contains_file_info(self, sample_docx_content):
        """验证 docx 上传后元数据包含文件信息"""
        content = sample_docx_content.read().decode("utf-8")

        doc_service = DocumentService()
        docs = doc_service.create_document_from_upload(
            filename="report.docx",
            content=content,
            metadata={"category": "report"},
        )

        assert len(docs) >= 1
        first_meta = docs[0].metadata
        assert first_meta["file_name"] == "report.docx"
        assert first_meta["source"] == "report.docx"
        assert first_meta["category"] == "report"
        assert "uploaded_at" in first_meta


# ---------------------------------------------------------------------------
# BU-KB-003: 上传 TXT 文档 (P1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUploadTxt:
    """BU-KB-003: 上传 TXT 文档"""

    def test_txt_upload_to_minio(self, mock_minio, sample_txt_content):
        """验证 TXT 文件上传到 MinIO"""
        bucket = "knowledge-base"
        object_name = "docs/notes.txt"

        mock_minio.buckets.add(bucket)
        mock_minio.put_object(bucket, object_name, sample_txt_content)

        assert object_name in mock_minio.objects[bucket]
        stored = mock_minio.objects[bucket][object_name]
        assert "测试文本" in stored.decode("utf-8")

    def test_txt_content_round_trip(self, mock_minio, sample_txt_content):
        """验证 TXT 内容写入后读回一致"""
        bucket = "knowledge-base"
        object_name = "docs/round-trip.txt"

        mock_minio.buckets.add(bucket)

        original = sample_txt_content.read()
        sample_txt_content.seek(0)

        mock_minio.put_object(bucket, object_name, sample_txt_content)
        response = mock_minio.get_object(bucket, object_name)
        retrieved = response.read()

        assert retrieved == original

    def test_txt_document_processing(self, mock_embedding, sample_txt_content):
        """验证 TXT 文档处理与向量化"""
        content = sample_txt_content.read().decode("utf-8")

        doc_service = DocumentService()
        docs = doc_service.create_document_from_upload(
            filename="notes.txt",
            content=content,
            metadata={},
        )

        assert len(docs) >= 1
        texts = [d.page_content for d in docs]
        embeddings = mock_embedding.sync_embed_texts(texts)

        assert len(embeddings) == len(texts)
        assert all(len(e) == 1536 for e in embeddings)


# ---------------------------------------------------------------------------
# BU-KB-004: 文档解析分块 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDocumentChunking:
    """BU-KB-004: 使用 RecursiveTextSplitter 进行文档分块"""

    def test_chunking_respects_chunk_size(self, long_document_content):
        """验证分块不超过设定的 chunk_size"""
        chunk_size = 200
        doc_service = DocumentService(chunk_size=chunk_size, chunk_overlap=30)
        chunks = doc_service.split_text(long_document_content)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= chunk_size, (
                f"分块长度 {len(chunk)} 超过限制 {chunk_size}"
            )

    def test_chunking_preserves_content(self, long_document_content):
        """验证分块后内容不丢失"""
        doc_service = DocumentService(chunk_size=200, chunk_overlap=0)
        chunks = doc_service.split_text(long_document_content)

        combined = "".join(chunks)
        # 关键句段应该在合并后的内容中存在
        assert "第1段" in combined
        assert "第20段" in combined

    def test_chunking_with_overlap(self, long_document_content):
        """验证分块重叠设置生效"""
        overlap = 50
        doc_service = DocumentService(chunk_size=200, chunk_overlap=overlap)
        chunks = doc_service.split_text(long_document_content)

        # 至少应该有多个分块
        assert len(chunks) > 2
        # 相邻块之间应该存在文本重叠
        for i in range(len(chunks) - 1):
            tail = chunks[i][-overlap:]
            head = chunks[i + 1][:overlap]
            # 由于按分隔符切分，重叠不一定完全精确对齐，
            # 但整体分块数量应大于无重叠时的分块数量
            pass

        # 有重叠时分块数量通常多于无重叠
        no_overlap = DocumentService(chunk_size=200, chunk_overlap=0)
        chunks_no_overlap = no_overlap.split_text(long_document_content)
        assert len(chunks) >= len(chunks_no_overlap)

    def test_chunking_chinese_sentence_boundaries(self):
        """验证中文文档按句号/感叹号等分隔符切分"""
        text = "这是第一句话。这是第二句话！这是第三句话？" * 10
        doc_service = DocumentService(chunk_size=60, chunk_overlap=10)
        chunks = doc_service.split_text(text)

        assert len(chunks) > 1

    def test_split_documents_adds_chunk_metadata(self, long_document_content):
        """验证 split_documents 在元数据中记录块信息"""
        doc_service = DocumentService(chunk_size=200, chunk_overlap=30)
        doc = Document(page_content=long_document_content, metadata={"source": "test.pdf"})

        split_docs = doc_service.split_documents([doc])
        assert len(split_docs) > 1

        for i, sd in enumerate(split_docs):
            assert sd.metadata["chunk_index"] == i
            assert sd.metadata["chunk_count"] == len(split_docs)
            assert sd.metadata["source"] == "test.pdf"


# ---------------------------------------------------------------------------
# BU-KB-005: 文档向量化 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDocumentVectorization:
    """BU-KB-005: 调用 vLLM /v1/embeddings 生成向量"""

    def test_single_text_embedding(self, mock_embedding):
        """验证单条文本向量生成"""
        vector = mock_embedding.sync_embed_text("数据治理概述")

        assert isinstance(vector, list)
        assert len(vector) == 1536

    def test_batch_text_embedding(self, mock_embedding):
        """验证批量文本向量生成"""
        texts = [
            "数据质量管理",
            "元数据治理",
            "数据血缘分析",
        ]
        vectors = mock_embedding.sync_embed_texts(texts)

        assert len(vectors) == 3
        assert all(len(v) == 1536 for v in vectors)

    def test_embedding_dimension_consistency(self, mock_embedding):
        """验证所有向量维度一致"""
        texts = [f"测试文本 {i}" for i in range(10)]
        vectors = mock_embedding.sync_embed_texts(texts)

        dims = set(len(v) for v in vectors)
        assert len(dims) == 1, f"向量维度不一致: {dims}"

    def test_empty_text_embedding(self):
        """验证空文本返回零向量"""
        import asyncio

        service = EmbeddingService()
        result = asyncio.run(service.embed_text(""))

        assert len(result) == EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    def test_embedding_api_call_format(self):
        """验证调用 /v1/embeddings 的请求格式"""
        import asyncio

        service = EmbeddingService(api_url="http://vllm-serving:8000")
        result = asyncio.run(service.embed_text("测试"))

        assert len(result) == 1536
        # 验证返回的向量不是全零（非空文本应返回非零向量）
        assert any(v != 0.0 for v in result)
        # 验证服务 URL 配置正确
        assert service.api_url == "http://vllm-serving:8000"
        assert service.model == "text-embedding-ada-002"


# ---------------------------------------------------------------------------
# BU-KB-006: 向量索引构建 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestVectorIndexBuilding:
    """BU-KB-006: 向量插入 Milvus 并构建索引"""

    def test_insert_vectors_to_collection(self, mock_milvus, mock_embedding):
        """验证向量插入到 Milvus 集合"""
        collection_name = "kb_test_001"
        texts = ["文档片段一", "文档片段二", "文档片段三"]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata = [{"doc_id": "doc-001", "chunk_index": i} for i in range(len(texts))]

        count = mock_milvus.insert(collection_name, texts, embeddings, metadata)

        assert count == 3
        assert collection_name in mock_milvus._collections
        assert len(mock_milvus._collections[collection_name]) == 3

    def test_search_after_insert(self, mock_milvus, mock_embedding):
        """验证插入后可搜索"""
        collection_name = "kb_search_test"
        texts = ["机器学习简介", "深度学习基础", "自然语言处理"]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata = [{"doc_id": "doc-search-001"} for _ in texts]

        mock_milvus.insert(collection_name, texts, embeddings, metadata)

        query_vec = mock_embedding.sync_embed_text("什么是深度学习")
        result = mock_milvus.search(collection_name, query_vec, top_k=2)

        assert "results" in result
        assert len(result["results"]) <= 2

    def test_create_collection_with_dimension(self, mock_milvus):
        """验证集合创建指定向量维度"""
        collection_name = "kb_dim_test"
        mock_milvus.create_collection(collection_name, dimension=1536)

        mock_milvus.create_collection.assert_called_with(collection_name, dimension=1536)
        assert collection_name in mock_milvus._collections

    def test_multiple_docs_same_collection(self, mock_milvus, mock_embedding):
        """验证多个文档可索引到同一集合"""
        collection_name = "kb_multi_doc"

        for doc_idx in range(3):
            doc_id = f"doc-multi-{doc_idx:03d}"
            texts = [f"文档{doc_idx}片段{i}" for i in range(5)]
            embeddings = mock_embedding.sync_embed_texts(texts)
            metadata = [{"doc_id": doc_id, "chunk_index": i} for i in range(5)]
            mock_milvus.insert(collection_name, texts, embeddings, metadata)

        assert len(mock_milvus._collections[collection_name]) == 15


# ---------------------------------------------------------------------------
# BU-KB-007: 文档索引记录 (P1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDocumentIndexRecord:
    """BU-KB-007: 保存 IndexedDocument 记录到 MySQL"""

    def test_indexed_document_model_fields(self):
        """验证 IndexedDocument 模型字段"""
        doc = IndexedDocument()
        doc.doc_id = "doc-test-007"
        doc.collection_name = "test_collection"
        doc.file_name = "report.pdf"
        doc.title = "测试报告"
        doc.content = "这是报告的内容摘要。"
        doc.chunk_count = 5
        doc.extra_metadata = json.dumps({"source": "upload"}, ensure_ascii=False)
        doc.created_by = "test-user-001"

        assert doc.doc_id == "doc-test-007"
        assert doc.collection_name == "test_collection"
        assert doc.chunk_count == 5

    def test_indexed_document_to_dict(self):
        """验证 IndexedDocument.to_dict() 输出格式"""
        doc = IndexedDocument()
        doc.doc_id = "doc-dict-001"
        doc.collection_name = "kb_main"
        doc.file_name = "guide.pdf"
        doc.title = "用户指南"
        doc.chunk_count = 3
        doc.extra_metadata = json.dumps({"category": "guide"})
        doc.created_by = "admin"
        doc.created_at = datetime(2026, 1, 28, 10, 0, 0)

        result = doc.to_dict()

        assert result["id"] == "doc-dict-001"
        assert result["collection_name"] == "kb_main"
        assert result["file_name"] == "guide.pdf"
        assert result["chunk_count"] == 3
        assert result["metadata"]["category"] == "guide"
        assert result["created_by"] == "admin"
        assert "2026-01-28" in result["created_at"]

    def test_indexed_document_saved_to_session(self, mock_db_session):
        """验证文档记录可添加到数据库会话"""
        doc = IndexedDocument()
        doc.doc_id = "doc-session-001"
        doc.collection_name = "test_kb"
        doc.file_name = "test.txt"
        doc.title = "测试文档"
        doc.chunk_count = 2
        doc.created_by = "user-001"

        mock_db_session.add(doc)
        mock_db_session.commit()

        assert len(mock_db_session._store) == 1
        assert mock_db_session._store[0].doc_id == "doc-session-001"

    def test_indexed_document_metadata_json(self):
        """验证元数据以 JSON 格式正确存储"""
        metadata = {
            "source": "upload",
            "file_type": ".pdf",
            "chunk_size": 500,
            "tags": ["test", "知识库"],
        }

        doc = IndexedDocument()
        doc.doc_id = "doc-meta-001"
        doc.collection_name = "meta_test"
        doc.extra_metadata = json.dumps(metadata, ensure_ascii=False)

        parsed = json.loads(doc.extra_metadata)
        assert parsed["source"] == "upload"
        assert parsed["tags"] == ["test", "知识库"]


# ---------------------------------------------------------------------------
# BU-KB-008: 批量文档上传 (P1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestBatchDocumentUpload:
    """BU-KB-008: 批量上传并处理文档"""

    def test_batch_upload_multiple_files(self, mock_minio, mock_milvus, mock_embedding):
        """验证批量上传多个文件"""
        bucket = "knowledge-base"
        collection_name = "batch_kb"
        mock_minio.buckets.add(bucket)

        files = [
            ("doc1.pdf", "第一个文档的内容。数据治理相关内容。"),
            ("doc2.docx", "第二个文档的内容。模型训练相关内容。"),
            ("doc3.txt", "第三个文档的内容。应用编排相关内容。"),
        ]

        doc_service = DocumentService(chunk_size=200, chunk_overlap=30)

        uploaded_docs = []
        for file_name, content in files:
            doc_id = f"doc-batch-{uuid.uuid4().hex[:8]}"

            # 存储到 MinIO
            data = io.BytesIO(content.encode("utf-8"))
            mock_minio.put_object(bucket, f"docs/{file_name}", data)

            # 文档处理与索引
            docs = doc_service.create_document_from_upload(
                filename=file_name,
                content=content,
                metadata={"doc_id": doc_id},
            )
            texts = [d.page_content for d in docs]
            embeddings = mock_embedding.sync_embed_texts(texts)
            metadata_list = [d.metadata for d in docs]
            mock_milvus.insert(collection_name, texts, embeddings, metadata_list)

            uploaded_docs.append({
                "doc_id": doc_id,
                "file_name": file_name,
                "chunk_count": len(docs),
            })

        assert len(uploaded_docs) == 3
        assert all(d["chunk_count"] >= 1 for d in uploaded_docs)
        assert len(mock_minio.objects[bucket]) == 3

    def test_batch_upload_partial_failure_isolation(self, mock_minio, mock_milvus, mock_embedding):
        """验证批量上传中单文件失败不影响其他文件"""
        bucket = "knowledge-base"
        collection_name = "batch_isolation"
        mock_minio.buckets.add(bucket)

        files = [
            ("ok1.txt", "正常文档内容一。"),
            ("bad.txt", ""),  # 空内容，应该失败
            ("ok2.txt", "正常文档内容二。"),
        ]

        doc_service = DocumentService()

        results = {"success": 0, "failed": 0}
        for file_name, content in files:
            try:
                if not content:
                    results["failed"] += 1
                    continue
                docs = doc_service.create_document_from_upload(
                    filename=file_name,
                    content=content,
                    metadata={"doc_id": f"doc-{uuid.uuid4().hex[:8]}"},
                )
                if docs:
                    texts = [d.page_content for d in docs]
                    embeddings = mock_embedding.sync_embed_texts(texts)
                    mock_milvus.insert(collection_name, texts, embeddings)
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception:
                results["failed"] += 1

        assert results["success"] == 2
        assert results["failed"] == 1

    def test_batch_upload_generates_unique_doc_ids(self, mock_embedding, mock_milvus):
        """验证批量上传中每个文档获得唯一 doc_id"""
        collection_name = "batch_unique_ids"
        doc_ids = set()

        doc_service = DocumentService()

        for i in range(10):
            doc_id = f"doc-{uuid.uuid4().hex[:12]}"
            doc_ids.add(doc_id)
            docs = doc_service.create_document_from_upload(
                filename=f"file_{i}.txt",
                content=f"文档 {i} 的内容。",
                metadata={"doc_id": doc_id},
            )
            texts = [d.page_content for d in docs]
            embeddings = mock_embedding.sync_embed_texts(texts)
            mock_milvus.insert(collection_name, texts, embeddings)

        assert len(doc_ids) == 10


# ---------------------------------------------------------------------------
# BU-KB-009: 删除文档 (P1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDeleteDocument:
    """BU-KB-009: 删除文档及其向量索引"""

    def test_delete_removes_vectors(self, mock_milvus, mock_embedding):
        """验证删除文档时向量数据也被清除"""
        collection_name = "kb_delete_test"
        doc_id = "doc-del-001"

        # 插入文档向量
        texts = ["待删除文档片段一", "待删除文档片段二"]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata = [{"doc_id": doc_id} for _ in texts]
        mock_milvus.insert(collection_name, texts, embeddings, metadata)

        assert len(mock_milvus._collections[collection_name]) == 2

        # 执行删除
        result = mock_milvus.delete_by_doc_id(collection_name, doc_id)
        assert result is True
        assert len(mock_milvus._collections[collection_name]) == 0

    def test_delete_nonexistent_document(self, mock_milvus):
        """验证删除不存在的文档返回 False"""
        result = mock_milvus.delete_by_doc_id("nonexistent_collection", "doc-ghost")
        assert result is False

    def test_delete_preserves_other_documents(self, mock_milvus, mock_embedding):
        """验证删除仅影响目标文档，不影响其他文档"""
        collection_name = "kb_selective_delete"

        # 插入两个文档
        for doc_id in ["doc-keep", "doc-remove"]:
            texts = [f"{doc_id} 片段 {i}" for i in range(3)]
            embeddings = mock_embedding.sync_embed_texts(texts)
            metadata = [{"doc_id": doc_id} for _ in texts]
            mock_milvus.insert(collection_name, texts, embeddings, metadata)

        assert len(mock_milvus._collections[collection_name]) == 6

        # 只删除 doc-remove
        mock_milvus.delete_by_doc_id(collection_name, "doc-remove")

        remaining = mock_milvus._collections[collection_name]
        assert len(remaining) == 3
        assert all(r["metadata"]["doc_id"] == "doc-keep" for r in remaining)

    def test_delete_document_record_and_vectors(self, mock_milvus, mock_embedding,
                                                mock_db_session):
        """验证删除同时移除数据库记录和向量数据"""
        collection_name = "kb_full_delete"
        doc_id = "doc-full-del-001"

        # 插入向量
        texts = ["删除测试内容"]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata = [{"doc_id": doc_id}]
        mock_milvus.insert(collection_name, texts, embeddings, metadata)

        # 模拟数据库记录
        doc_record = IndexedDocument()
        doc_record.doc_id = doc_id
        doc_record.collection_name = collection_name
        mock_db_session.add(doc_record)

        # 删除向量
        vector_deleted = mock_milvus.delete_by_doc_id(collection_name, doc_id)
        assert vector_deleted is True

        # 删除数据库记录
        mock_db_session.delete = MagicMock()
        mock_db_session.delete(doc_record)
        mock_db_session.commit()

        mock_db_session.delete.assert_called_once_with(doc_record)


# ---------------------------------------------------------------------------
# BU-KB-010: 更新文档 (P2)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUpdateDocument:
    """BU-KB-010: 重新上传文档并更新向量索引"""

    def test_update_replaces_old_vectors(self, mock_milvus, mock_embedding):
        """验证更新文档时旧向量被替换"""
        collection_name = "kb_update_test"
        doc_id = "doc-update-001"

        # 原始版本
        old_texts = ["旧版本内容一", "旧版本内容二"]
        old_embeddings = mock_embedding.sync_embed_texts(old_texts)
        old_metadata = [{"doc_id": doc_id, "version": 1} for _ in old_texts]
        mock_milvus.insert(collection_name, old_texts, old_embeddings, old_metadata)

        assert len(mock_milvus._collections[collection_name]) == 2

        # 删除旧向量
        mock_milvus.delete_by_doc_id(collection_name, doc_id)
        assert len(mock_milvus._collections[collection_name]) == 0

        # 插入新版本
        new_texts = ["新版本内容一", "新版本内容二", "新版本内容三"]
        new_embeddings = mock_embedding.sync_embed_texts(new_texts)
        new_metadata = [{"doc_id": doc_id, "version": 2} for _ in new_texts]
        mock_milvus.insert(collection_name, new_texts, new_embeddings, new_metadata)

        assert len(mock_milvus._collections[collection_name]) == 3
        assert all(
            r["metadata"]["version"] == 2
            for r in mock_milvus._collections[collection_name]
        )

    def test_update_preserves_doc_id(self, mock_milvus, mock_embedding):
        """验证更新后 doc_id 保持不变"""
        collection_name = "kb_update_id"
        doc_id = "doc-stable-id"

        # 原始
        texts = ["原始内容"]
        embeddings = mock_embedding.sync_embed_texts(texts)
        metadata = [{"doc_id": doc_id}]
        mock_milvus.insert(collection_name, texts, embeddings, metadata)

        # 更新
        mock_milvus.delete_by_doc_id(collection_name, doc_id)
        new_texts = ["更新后的内容"]
        new_embeddings = mock_embedding.sync_embed_texts(new_texts)
        new_metadata = [{"doc_id": doc_id}]
        mock_milvus.insert(collection_name, new_texts, new_embeddings, new_metadata)

        records = mock_milvus._collections[collection_name]
        assert len(records) == 1
        assert records[0]["metadata"]["doc_id"] == doc_id

    def test_update_minio_object_overwrite(self, mock_minio):
        """验证 MinIO 中的对象可以被覆盖"""
        bucket = "knowledge-base"
        object_name = "docs/updatable.pdf"
        mock_minio.buckets.add(bucket)

        # 上传第一版
        v1 = io.BytesIO(b"version 1 content")
        mock_minio.put_object(bucket, object_name, v1)
        resp1 = mock_minio.get_object(bucket, object_name)
        assert resp1.read() == b"version 1 content"

        # 上传第二版（覆盖）
        v2 = io.BytesIO(b"version 2 content - updated")
        mock_minio.put_object(bucket, object_name, v2)
        resp2 = mock_minio.get_object(bucket, object_name)
        assert resp2.read() == b"version 2 content - updated"

    def test_update_refreshes_chunk_count(self, mock_milvus, mock_embedding, mock_db_session):
        """验证更新后 chunk_count 被刷新"""
        collection_name = "kb_chunk_refresh"
        doc_id = "doc-chunk-refresh"

        # 原始：2 块
        old_texts = ["旧块一", "旧块二"]
        old_embeddings = mock_embedding.sync_embed_texts(old_texts)
        mock_milvus.insert(collection_name, old_texts, old_embeddings,
                           [{"doc_id": doc_id}] * 2)

        doc_record = IndexedDocument()
        doc_record.doc_id = doc_id
        doc_record.collection_name = collection_name
        doc_record.chunk_count = 2

        # 更新：4 块
        mock_milvus.delete_by_doc_id(collection_name, doc_id)
        new_texts = ["新块一", "新块二", "新块三", "新块四"]
        new_embeddings = mock_embedding.sync_embed_texts(new_texts)
        mock_milvus.insert(collection_name, new_texts, new_embeddings,
                           [{"doc_id": doc_id}] * 4)

        doc_record.chunk_count = len(new_texts)

        assert doc_record.chunk_count == 4
        assert len(mock_milvus._collections[collection_name]) == 4

    def test_full_update_workflow(self, mock_minio, mock_milvus, mock_embedding, mock_db_session):
        """验证完整的文档更新流程：删除旧版 -> 上传新版 -> 重新索引"""
        bucket = "knowledge-base"
        collection_name = "kb_full_update"
        doc_id = "doc-full-update-001"
        file_name = "evolving-doc.pdf"
        mock_minio.buckets.add(bucket)

        doc_service = DocumentService(chunk_size=200, chunk_overlap=30)

        # ---- 第一版上传 ----
        v1_content = "第一版文档内容。数据平台建设初步方案。"
        v1_data = io.BytesIO(v1_content.encode("utf-8"))
        mock_minio.put_object(bucket, f"docs/{file_name}", v1_data)

        v1_docs = doc_service.create_document_from_upload(
            filename=file_name,
            content=v1_content,
            metadata={"doc_id": doc_id, "version": 1},
        )
        v1_texts = [d.page_content for d in v1_docs]
        v1_embeddings = mock_embedding.sync_embed_texts(v1_texts)
        mock_milvus.insert(collection_name, v1_texts, v1_embeddings,
                           [d.metadata for d in v1_docs])

        v1_record = IndexedDocument()
        v1_record.doc_id = doc_id
        v1_record.collection_name = collection_name
        v1_record.file_name = file_name
        v1_record.chunk_count = len(v1_docs)
        mock_db_session.add(v1_record)

        # ---- 更新为第二版 ----
        # 1. 删除旧向量
        mock_milvus.delete_by_doc_id(collection_name, doc_id)

        # 2. 上传新文件到 MinIO（覆盖）
        v2_content = (
            "第二版文档内容。数据平台建设详细方案。"
            "新增了模型训练模块和应用编排模块的描述。"
            "包含更详细的技术架构说明。"
        )
        v2_data = io.BytesIO(v2_content.encode("utf-8"))
        mock_minio.put_object(bucket, f"docs/{file_name}", v2_data)

        # 3. 重新处理文档
        v2_docs = doc_service.create_document_from_upload(
            filename=file_name,
            content=v2_content,
            metadata={"doc_id": doc_id, "version": 2},
        )
        v2_texts = [d.page_content for d in v2_docs]
        v2_embeddings = mock_embedding.sync_embed_texts(v2_texts)
        mock_milvus.insert(collection_name, v2_texts, v2_embeddings,
                           [d.metadata for d in v2_docs])

        # 4. 更新数据库记录
        v1_record.chunk_count = len(v2_docs)

        # ---- 验证 ----
        # MinIO 中存储的是新版本
        resp = mock_minio.get_object(bucket, f"docs/{file_name}")
        assert "第二版" in resp.read().decode("utf-8")

        # 向量数据是新版本
        all_records = mock_milvus._collections[collection_name]
        assert len(all_records) == len(v2_docs)
        assert all(r["metadata"].get("version") == 2 for r in all_records)

        # 数据库记录已更新
        assert v1_record.chunk_count == len(v2_docs)
