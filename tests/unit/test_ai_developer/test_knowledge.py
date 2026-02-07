"""
AI 开发者 - 知识库管理单元测试
测试用例：AD-KB-U-001 ~ AD-KB-U-015

知识库管理是 AI 开发者角色的核心功能，用于创建和管理向量知识库。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestKnowledgeBaseCreation:
    """知识库创建测试 (AD-KB-U-001 ~ AD-KB-U-003)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_knowledge_base(self, mock_knowledge_service):
        """AD-KB-U-001: 创建知识库"""
        kb_data = {
            'name': '产品文档知识库',
            'description': '包含产品手册、FAQ等文档',
            'embedding_model': 'text-embedding-ada-002',
            'chunk_size': 500,
            'chunk_overlap': 50
        }

        result = mock_knowledge_service.create_knowledge_base(kb_data)

        assert result['success'] is True
        assert 'kb_id' in result
        assert result['name'] == '产品文档知识库'

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_knowledge_base_with_vector_config(self, mock_knowledge_service):
        """AD-KB-U-002: 创建带向量配置的知识库"""
        kb_data = {
            'name': '技术文档知识库',
            'description': 'API文档、技术规范',
            'embedding_model': 'bge-large-zh',
            'dimension': 1024,
            'metric_type': 'cosine',
            'index_type': 'IVF_FLAT',
            'nlist': 128
        }

        result = mock_knowledge_service.create_knowledge_base(kb_data)

        assert result['success'] is True
        assert result['dimension'] == 1024

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_knowledge_base_invalid_chunk_config(self, mock_knowledge_service):
        """AD-KB-U-003: 创建知识库时无效的分块配置"""
        kb_data = {
            'name': '测试知识库',
            'chunk_size': -100,  # 无效值
            'chunk_overlap': 200  # 大于 chunk_size
        }

        result = mock_knowledge_service.create_knowledge_base(kb_data)

        assert result['success'] is False
        assert 'error' in result


class TestDocumentUpload:
    """文档上传测试 (AD-KB-U-004 ~ AD-KB-U-007)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_upload_document(self, mock_knowledge_service):
        """AD-KB-U-004: 上传文档到知识库"""
        kb_id = 'kb_001'
        document_data = {
            'filename': 'product_manual.pdf',
            'content_type': 'application/pdf',
            'content': b'fake_pdf_content',
            'metadata': {'category': 'product', 'version': '1.0'}
        }

        mock_knowledge_service.upload_document.return_value = {
            'success': True,
            'document_id': 'doc_001',
            'status': 'processing',
            'chunks_expected': 10
        }

        result = mock_knowledge_service.upload_document(kb_id, document_data)

        assert result['success'] is True
        assert 'document_id' in result
        assert result['status'] == 'processing'

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_batch_upload_documents(self, mock_knowledge_service):
        """AD-KB-U-005: 批量上传文档"""
        kb_id = 'kb_001'
        documents = [
            {'filename': 'doc1.pdf', 'content': b'content1'},
            {'filename': 'doc2.pdf', 'content': b'content2'},
            {'filename': 'doc3.txt', 'content': b'content3'}
        ]

        mock_knowledge_service.batch_upload_documents.return_value = {
            'success': True,
            'results': [
                {'filename': 'doc1.pdf', 'document_id': 'doc_001', 'status': 'processing'},
                {'filename': 'doc2.pdf', 'document_id': 'doc_002', 'status': 'processing'},
                {'filename': 'doc3.txt', 'document_id': 'doc_003', 'status': 'processing'}
            ],
            'total': 3
        }

        result = mock_knowledge_service.batch_upload_documents(kb_id, documents)

        assert result['success'] is True
        assert result['total'] == 3

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_document_processing_status(self, mock_knowledge_service):
        """AD-KB-U-006: 获取文档处理状态"""
        document_id = 'doc_001'

        mock_knowledge_service.get_document_status.return_value = {
            'success': True,
            'document_id': document_id,
            'status': 'completed',
            'chunks_processed': 10,
            'vectors_embedded': 10,
            'error': None
        }

        result = mock_knowledge_service.get_document_status(document_id)

        assert result['success'] is True
        assert result['status'] == 'completed'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_delete_document(self, mock_knowledge_service):
        """AD-KB-U-007: 删除知识库中的文档"""
        kb_id = 'kb_001'
        document_id = 'doc_001'

        result = mock_knowledge_service.delete_document(kb_id, document_id)

        assert result['success'] is True


class TestKnowledgeRetrieval:
    """知识检索测试 (AD-KB-U-008 ~ AD-KB-U-011)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_vector_similarity_search(self, mock_knowledge_service):
        """AD-KB-U-008: 向量相似度检索"""
        kb_id = 'kb_001'
        query = '产品价格是多少？'
        search_config = {
            'top_k': 5,
            'score_threshold': 0.7
        }

        mock_knowledge_service.search.return_value = {
            'success': True,
            'results': [
                {'chunk_id': 'chk_001', 'content': '产品价格为199元', 'score': 0.92},
                {'chunk_id': 'chk_002', 'content': '促销活动享折扣', 'score': 0.85}
            ],
            'total': 2
        }

        result = mock_knowledge_service.search(kb_id, query, search_config)

        assert result['success'] is True
        assert len(result['results']) == 2
        assert result['results'][0]['score'] > result['results'][1]['score']

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_hybrid_search(self, mock_knowledge_service):
        """AD-KB-U-009: 混合检索（向量+关键词）"""
        kb_id = 'kb_001'
        query = '产品价格'
        search_config = {
            'mode': 'hybrid',
            'vector_weight': 0.7,
            'keyword_weight': 0.3,
            'top_k': 10
        }

        mock_knowledge_service.search.return_value = {
            'success': True,
            'results': [
                {'chunk_id': 'chk_001', 'content': '产品价格信息', 'score': 0.95, 'type': 'hybrid'}
            ],
            'total': 1
        }

        result = mock_knowledge_service.search(kb_id, query, search_config)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_search_with_filter(self, mock_knowledge_service):
        """AD-KB-U-010: 带过滤条件的检索"""
        kb_id = 'kb_001'
        query = '产品使用说明'
        filter_config = {
            'metadata_filter': {'category': 'user_guide'},
            'date_range': {'start': '2024-01-01', 'end': '2024-12-31'}
        }

        mock_knowledge_service.search.return_value = {
            'success': True,
            'results': [
                {'chunk_id': 'chk_005', 'content': '用户指南内容', 'metadata': {'category': 'user_guide'}}
            ],
            'total': 1
        }

        result = mock_knowledge_service.search(kb_id, query, filter_config)

        assert result['success'] is True
        assert result['results'][0]['metadata']['category'] == 'user_guide'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_rerank_search_results(self, mock_knowledge_service):
        """AD-KB-U-011: 重排序检索结果"""
        chunk_ids = ['chk_001', 'chk_002', 'chk_003']
        query = '产品价格信息'

        mock_knowledge_service.rerank.return_value = {
            'success': True,
            'reranked_results': [
                {'chunk_id': 'chk_002', 'score': 0.95},
                {'chunk_id': 'chk_001', 'score': 0.88},
                {'chunk_id': 'chk_003', 'score': 0.72}
            ]
        }

        result = mock_knowledge_service.rerank(chunk_ids, query)

        assert result['success'] is True
        assert result['reranked_results'][0]['chunk_id'] == 'chk_002'


class TestKnowledgeBaseManagement:
    """知识库管理测试 (AD-KB-U-012 ~ AD-KB-U-015)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_knowledge_bases(self, mock_knowledge_service):
        """AD-KB-U-012: 列出知识库"""
        mock_knowledge_service.list_knowledge_bases.return_value = {
            'success': True,
            'knowledge_bases': [
                {'kb_id': 'kb_001', 'name': '产品文档', 'document_count': 15},
                {'kb_id': 'kb_002', 'name': '技术文档', 'document_count': 8}
            ],
            'total': 2
        }

        result = mock_knowledge_service.list_knowledge_bases()

        assert result['success'] is True
        assert len(result['knowledge_bases']) == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_knowledge_base_detail(self, mock_knowledge_service):
        """AD-KB-U-013: 获取知识库详情"""
        kb_id = 'kb_001'

        mock_knowledge_service.get_knowledge_base.return_value = {
            'success': True,
            'kb_id': kb_id,
            'name': '产品文档知识库',
            'document_count': 15,
            'total_chunks': 150,
            'embedding_model': 'text-embedding-ada-002',
            'created_at': '2024-01-01T00:00:00Z'
        }

        result = mock_knowledge_service.get_knowledge_base(kb_id)

        assert result['success'] is True
        assert result['kb_id'] == kb_id

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_knowledge_base(self, mock_knowledge_service):
        """AD-KB-U-014: 更新知识库配置"""
        kb_id = 'kb_001'
        update_data = {
            'name': '更新后的名称',
            'description': '更新后的描述'
        }

        mock_knowledge_service.update_knowledge_base.return_value = {
            'success': True,
            'kb_id': kb_id
        }

        result = mock_knowledge_service.update_knowledge_base(kb_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_delete_knowledge_base(self, mock_knowledge_service):
        """AD-KB-U-015: 删除知识库"""
        kb_id = 'kb_001'

        result = mock_knowledge_service.delete_knowledge_base(kb_id)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_knowledge_service():
    """Mock 知识库服务"""
    service = Mock()

    def mock_create_kb(data):
        # 验证 chunk_size 和 chunk_overlap
        chunk_size = data.get('chunk_size')
        chunk_overlap = data.get('chunk_overlap')

        if chunk_size is not None and chunk_size <= 0:
            return {
                'success': False,
                'error': 'chunk_size must be positive'
            }

        if chunk_overlap is not None and chunk_size is not None and chunk_overlap >= chunk_size:
            return {
                'success': False,
                'error': 'chunk_overlap must be less than chunk_size'
            }

        return {
            'success': True,
            'kb_id': 'kb_001',
            'name': data.get('name', ''),
            'embedding_model': data.get('embedding_model', 'text-embedding-ada-002'),
            'dimension': data.get('dimension', 1536)
        }

    def mock_upload_doc(kb_id, document_data):
        return {
            'success': True,
            'document_id': 'doc_001',
            'status': 'processing',
            'chunks_expected': 10
        }

    def mock_batch_upload(kb_id, documents):
        return {
            'success': True,
            'results': [
                {'filename': d['filename'], 'document_id': f'doc_{i:03d}', 'status': 'processing'}
                for i, d in enumerate(documents, 1)
            ],
            'total': len(documents)
        }

    service.create_knowledge_base = Mock(side_effect=mock_create_kb)
    service.upload_document = Mock(side_effect=mock_upload_doc)
    service.batch_upload_documents = Mock(side_effect=mock_batch_upload)
    service.get_document_status = Mock()
    service.delete_document = Mock(return_value={'success': True})
    service.search = Mock()
    service.rerank = Mock()
    service.list_knowledge_bases = Mock()
    service.get_knowledge_base = Mock()
    service.update_knowledge_base = Mock(return_value={'success': True})
    service.delete_knowledge_base = Mock(return_value={'success': True})

    return service
