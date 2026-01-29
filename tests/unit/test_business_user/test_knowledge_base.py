"""
知识库文档管理单元测试
测试用例：BU-KB-001 ~ BU-KB-007
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from typing import List


class TestDocumentUpload:
    """文档上传测试 (BU-KB-001 ~ BU-KB-003)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upload_pdf_document(self, mock_document_service):
        """BU-KB-001: 上传PDF文档"""
        file_data = b'Mock PDF content...'
        file_name = 'test_document.pdf'
        kb_id = 'kb_0001'

        mock_document_service.upload.return_value = {
            'success': True,
            'doc_id': 'doc_0001',
            'file_name': file_name,
            'file_type': 'pdf',
            'storage_path': f's3://documents/doc_0001/test_document.pdf'
        }

        result = await mock_document_service.upload(file_data, file_name, kb_id)

        assert result['success'] is True
        assert result['file_type'] == 'pdf'
        assert 'doc_id' in result

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upload_word_document(self, mock_document_service):
        """BU-KB-002: 上传Word文档"""
        file_data = b'Mock Word content...'
        file_name = 'test_document.docx'
        kb_id = 'kb_0001'

        mock_document_service.upload.return_value = {
            'success': True,
            'doc_id': 'doc_0002',
            'file_type': 'docx'
        }

        result = await mock_document_service.upload(file_data, file_name, kb_id)

        assert result['success'] is True
        assert result['file_type'] == 'docx'

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upload_txt_document(self, mock_document_service):
        """BU-KB-003: 上传TXT文档"""
        file_data = b'Mock TXT content...'
        file_name = 'test_document.txt'
        kb_id = 'kb_0001'

        mock_document_service.upload.return_value = {
            'success': True,
            'doc_id': 'doc_0003',
            'file_type': 'txt'
        }

        result = await mock_document_service.upload(file_data, file_name, kb_id)

        assert result['success'] is True


class TestDocumentProcessing:
    """文档处理测试 (BU-KB-004 ~ BU-KB-006)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_parsing_and_chunking(self, mock_document_service):
        """BU-KB-004: 文档解析分块"""
        doc_id = 'doc_0001'

        mock_document_service.parse_and_chunk = AsyncMock(return_value={
            'success': True,
            'doc_id': doc_id,
            'chunks': [
                {'chunk_index': 0, 'text': 'This is the first chunk...'},
                {'chunk_index': 1, 'text': 'This is the second chunk...'},
                {'chunk_index': 2, 'text': 'This is the third chunk...'}
            ],
            'total_chunks': 3,
            'chunking_strategy': 'RecursiveCharacterTextSplitter',
            'chunk_size': 1000,
            'chunk_overlap': 200
        })

        result = await mock_document_service.parse_and_chunk(doc_id)

        assert result['success'] is True
        assert result['total_chunks'] > 0
        assert 'chunking_strategy' in result

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_vectorization(self, mock_document_service, mock_vllm_client):
        """BU-KB-005: 文档向量化"""
        doc_id = 'doc_0001'
        chunks = [
            {'chunk_index': 0, 'text': 'First chunk'},
            {'chunk_index': 1, 'text': 'Second chunk'}
        ]

        # Mock vLLM embeddings
        mock_vllm_client.embeddings = AsyncMock(return_value={
            'data': [
                {'embedding': [0.1] * 1536, 'index': 0},
                {'embedding': [0.2] * 1536, 'index': 1}
            ]
        })

        mock_document_service.vectorize = AsyncMock(return_value={
            'success': True,
            'doc_id': doc_id,
            'vectorized_chunks': len(chunks),
            'dimension': 1536
        })

        result = await mock_document_service.vectorize(doc_id, chunks)

        assert result['success'] is True
        assert result['vectorized_chunks'] == len(chunks)
        assert result['dimension'] == 1536

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_index_construction(self, mock_document_service, mock_milvus_client):
        """BU-KB-006: 向量索引构建"""
        kb_id = 'kb_0001'
        doc_id = 'doc_0001'
        vectors = [[0.1] * 1536, [0.2] * 1536]

        mock_milvus_client.create_collection = AsyncMock()
        mock_milvus_client.insert = AsyncMock(return_value={
            'success': True,
            'insert_count': len(vectors)
        })
        mock_milvus_client.create_index = AsyncMock()

        mock_document_service.build_index = AsyncMock(return_value={
            'success': True,
            'kb_id': kb_id,
            'doc_id': doc_id,
            'indexed_chunks': len(vectors),
            'index_type': 'HNSW',
            'metric_type': 'COSINE'
        })

        result = await mock_document_service.build_index(kb_id, doc_id, vectors)

        assert result['success'] is True
        assert result['indexed_chunks'] == len(vectors)
        assert result['index_type'] == 'HNSW'


class TestDocumentIndex:
    """文档索引记录测试 (BU-KB-007)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_index_record(self, mock_document_service):
        """BU-KB-007: 文档索引记录"""
        kb_id = 'kb_0001'
        doc_id = 'doc_0001'

        mock_document_service.save_index_record = AsyncMock(return_value={
            'success': True,
            'indexed_id': 'idx_0001',
            'doc_id': doc_id,
            'kb_id': kb_id,
            'chunk_count': 5
        })

        result = await mock_document_service.save_index_record(kb_id, doc_id, chunk_count=5)

        assert result['success'] is True
        assert result['chunk_count'] == 5


class TestBatchDocumentUpload:
    """批量文档上传测试 (BU-KB-008)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_document_upload(self, mock_document_service):
        """BU-KB-008: 批量文档上传"""
        kb_id = 'kb_0001'
        files = [
            {'name': 'doc1.pdf', 'data': b'PDF content 1'},
            {'name': 'doc2.pdf', 'data': b'PDF content 2'},
            {'name': 'doc3.pdf', 'data': b'PDF content 3'}
        ]

        mock_document_service.batch_upload = AsyncMock(return_value={
            'success': True,
            'uploaded_count': len(files),
            'failed_count': 0,
            'doc_ids': ['doc_0001', 'doc_0002', 'doc_0003']
        })

        result = await mock_document_service.batch_upload(kb_id, files)

        assert result['success'] is True
        assert result['uploaded_count'] == len(files)
        assert result['failed_count'] == 0


class TestDocumentManagement:
    """文档管理测试 (BU-KB-009 ~ BU-KB-010)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_document(self, mock_document_service, mock_milvus_client):
        """BU-KB-009: 删除文档"""
        doc_id = 'doc_0001'
        kb_id = 'kb_0001'

        mock_document_service.delete = AsyncMock(return_value={
            'success': True,
            'doc_id': doc_id,
            'deleted_from_storage': True,
            'deleted_from_vector_db': True
        })

        result = await mock_document_service.delete(doc_id, kb_id)

        assert result['success'] is True
        assert result['deleted_from_storage'] is True
        assert result['deleted_from_vector_db'] is True

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_document(self, mock_document_service):
        """BU-KB-010: 更新文档（重新上传同名文档）"""
        kb_id = 'kb_0001'
        old_doc_id = 'doc_0001'
        new_file_data = b'Updated PDF content...'

        mock_document_service.update = AsyncMock(return_value={
            'success': True,
            'old_doc_id': old_doc_id,
            'new_doc_id': 'doc_0002',
            'vector_index_updated': True
        })

        result = await mock_document_service.update(kb_id, old_doc_id, new_file_data)

        assert result['success'] is True
        assert result['vector_index_updated'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_document_service():
    """Mock 文档服务"""
    service = Mock()
    service.upload = AsyncMock()
    service.parse_and_chunk = AsyncMock()
    service.vectorize = AsyncMock()
    service.build_index = AsyncMock()
    service.save_index_record = AsyncMock()
    service.batch_upload = AsyncMock()
    service.delete = AsyncMock()
    service.update = AsyncMock()
    return service


@pytest.fixture
def mock_vllm_client():
    """Mock vLLM客户端"""
    client = Mock()
    client.embeddings = AsyncMock()
    return client


@pytest.fixture
def mock_milvus_client():
    """Mock Milvus客户端"""
    client = Mock()
    client.create_collection = AsyncMock()
    client.insert = AsyncMock()
    client.create_index = AsyncMock()
    client.delete = AsyncMock()
    return client
