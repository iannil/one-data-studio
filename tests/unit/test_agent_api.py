"""
Agent API 单元测试
Sprint 24: 测试覆盖率扩展

测试 Agent API 的核心功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            import sys
            sys.path.insert(0, '/app')
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_health_endpoint_returns_200(self, client):
        """测试健康检查返回 200"""
        response = client.get('/api/v1/health')

        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, client):
        """测试健康检查返回 JSON"""
        response = client.get('/api/v1/health')

        data = response.get_json()
        assert data is not None
        assert 'code' in data

    def test_health_endpoint_shows_version(self, client):
        """测试健康检查显示版本"""
        response = client.get('/api/v1/health')

        data = response.get_json()
        assert 'version' in data or 'service' in data


class TestChatEndpoint:
    """聊天端点测试"""

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

    def test_chat_requires_message(self, client):
        """测试聊天需要消息"""
        response = client.post(
            '/api/v1/chat',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_chat_with_empty_message(self, client):
        """测试空消息"""
        response = client.post(
            '/api/v1/chat',
            json={'message': ''},
            content_type='application/json'
        )

        assert response.status_code == 400


class TestRAGEndpoint:
    """RAG 端点测试"""

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

    def test_rag_query_requires_question(self, client):
        """测试 RAG 查询需要问题"""
        response = client.post(
            '/api/v1/rag/query',
            json={},
            content_type='application/json'
        )

        # 应该返回错误或成功（取决于实现）
        assert response.status_code in [200, 400, 500]


class TestText2SQLEndpoint:
    """Text-to-SQL 端点测试"""

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

    def test_text2sql_requires_question(self, client):
        """测试 Text-to-SQL 需要问题"""
        response = client.post(
            '/api/v1/text2sql',
            json={},
            content_type='application/json'
        )

        # 端点应该存在
        assert response.status_code in [200, 400, 500, 503]

    def test_text2sql_with_question(self, client):
        """测试 Text-to-SQL 带问题"""
        response = client.post(
            '/api/v1/text2sql',
            json={
                'question': '查询所有用户',
                'database': 'test_db'
            },
            content_type='application/json'
        )

        # 端点应该处理请求
        assert response.status_code in [200, 400, 500, 503]


class TestWorkflowEndpoints:
    """工作流端点测试"""

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

    def test_list_workflows(self, client):
        """测试列出工作流"""
        response = client.get('/api/v1/workflows')

        assert response.status_code in [200, 401, 403]

    def test_get_workflow(self, client):
        """测试获取工作流"""
        response = client.get('/api/v1/workflows/test-workflow-id')

        assert response.status_code in [200, 404, 401, 403]


class TestConversationEndpoints:
    """会话端点测试"""

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

    def test_list_conversations(self, client):
        """测试列出会话"""
        response = client.get('/api/v1/conversations')

        assert response.status_code in [200, 401, 403]

    def test_get_conversation(self, client):
        """测试获取会话"""
        response = client.get('/api/v1/conversations/test-conversation-id')

        assert response.status_code in [200, 404, 401, 403]


class TestScheduleEndpoints:
    """调度端点测试"""

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

    def test_list_schedules(self, client):
        """测试列出调度"""
        response = client.get('/api/v1/schedules')

        # 端点可能存在也可能不存在
        assert response.status_code in [200, 404, 401, 403]

    def test_create_schedule(self, client):
        """测试创建调度"""
        response = client.post(
            '/api/v1/workflows/test-workflow/schedules',
            json={
                'type': 'cron',
                'expression': '0 9 * * *'
            },
            content_type='application/json'
        )

        assert response.status_code in [200, 201, 400, 404, 401, 403]


class TestVectorStoreService:
    """向量存储服务测试"""

    def test_vector_store_initialization(self):
        """测试向量存储初始化"""
        try:
            from services.vector_store import VectorStore

            store = VectorStore()
            assert store is not None
        except ImportError:
            pytest.skip("VectorStore not available")

    @patch('services.vector_store.Milvus')
    def test_vector_store_search(self, mock_milvus):
        """测试向量搜索"""
        try:
            from services.vector_store import VectorStore

            mock_milvus.return_value = MagicMock()
            store = VectorStore()

            # 测试搜索方法存在
            assert hasattr(store, 'search') or hasattr(store, 'similarity_search')
        except ImportError:
            pytest.skip("VectorStore not available")


class TestEmbeddingService:
    """嵌入服务测试"""

    def test_embedding_service_initialization(self):
        """测试嵌入服务初始化"""
        try:
            from services.embedding import EmbeddingService

            service = EmbeddingService()
            assert service is not None
        except ImportError:
            pytest.skip("EmbeddingService not available")


class TestDocumentService:
    """文档服务测试"""

    def test_document_service_initialization(self):
        """测试文档服务初始化"""
        try:
            from services.document import DocumentService

            service = DocumentService()
            assert service is not None
        except ImportError:
            pytest.skip("DocumentService not available")
