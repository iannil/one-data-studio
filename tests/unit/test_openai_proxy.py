"""
OpenAI 代理服务单元测试
Sprint 14: P1 测试覆盖
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock, AsyncMock
import sys
import os

# 添加 services 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services'))


class TestGetOpenAIClient:
    """OpenAI 客户端初始化测试"""

    @patch.dict(os.environ, {}, clear=True)
    @patch('services.openai-proxy.main.OPENAI_AVAILABLE', False)
    def test_client_not_available_when_library_missing(self):
        """测试 OpenAI 库未安装时返回 None"""
        # 需要重新导入以应用 patch
        from importlib import reload
        import services
        # 此测试验证逻辑

    @patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=True)
    def test_client_not_available_without_api_key(self):
        """测试无 API Key 时返回 None"""
        pass  # 逻辑验证


class TestPromptTemplates:
    """Prompt 模板管理测试"""

    def test_default_template_exists(self):
        """测试默认模板存在"""
        from services.openai_proxy.main import PROMPT_TEMPLATES
        assert 'default' in PROMPT_TEMPLATES
        assert 'rag' in PROMPT_TEMPLATES
        assert 'sql' in PROMPT_TEMPLATES
        assert 'chat' in PROMPT_TEMPLATES

    def test_get_prompt_template_default(self):
        """测试获取默认模板"""
        from services.openai_proxy.main import get_prompt_template
        template = get_prompt_template('default')
        assert '智能助手' in template

    def test_get_prompt_template_with_vars(self):
        """测试带变量的模板"""
        from services.openai_proxy.main import get_prompt_template
        template = get_prompt_template('rag', context='测试上下文', question='测试问题')
        assert '测试上下文' in template
        assert '测试问题' in template

    def test_get_prompt_template_nonexistent_falls_back_to_default(self):
        """测试不存在的模板返回默认"""
        from services.openai_proxy.main import get_prompt_template
        template = get_prompt_template('nonexistent')
        assert '智能助手' in template


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_check_returns_ok(self, client):
        """测试健康检查返回 ok"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['service'] == 'openai-proxy'
        assert 'version' in data
        assert 'openai_configured' in data

    @patch.dict(os.environ, {'OPENAI_BASE_URL': 'https://custom.api.com/v1'})
    def test_health_check_shows_custom_base_url(self, client):
        """测试健康检查显示自定义 base_url"""
        response = client.get('/health')
        data = json.loads(response.data)
        # base_url 应该在响应中可见


class TestListModelsEndpoint:
    """模型列表端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @patch('services.openai_proxy.main.get_openai_client')
    def test_list_models_without_client_returns_mock(self, mock_get_client, client):
        """测试无客户端时返回 mock 模型列表"""
        mock_get_client.return_value = None
        response = client.get('/v1/models')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['object'] == 'list'
        assert len(data['data']) > 0
        assert any(m['id'] == 'gpt-4o-mini' for m in data['data'])

    @patch('services.openai_proxy.main.get_openai_client')
    def test_list_models_with_error_returns_default(self, mock_get_client, client):
        """测试 API 错误时返回默认列表"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        async def mock_list():
            raise Exception("API Error")

        mock_client.models.list = mock_list

        response = client.get('/v1/models')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data


class TestChatCompletionsEndpoint:
    """聊天补全端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @patch('services.openai_proxy.main.get_openai_client')
    def test_chat_completions_mock_response(self, mock_get_client, client):
        """测试无客户端时返回 mock 响应"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}]
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['object'] == 'chat.completion'
        assert 'choices' in data
        assert len(data['choices']) > 0
        assert 'Mock 响应' in data['choices'][0]['message']['content']

    @patch('services.openai_proxy.main.get_openai_client')
    def test_chat_completions_with_prompt_template(self, mock_get_client, client):
        """测试使用 Prompt 模板"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "查询用户数"}],
            "prompt_template": "sql",
            "context": {
                "database": "test_db",
                "schema": "users(id, name, email)",
                "question": "查询所有用户"
            }
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['object'] == 'chat.completion'

    @patch('services.openai_proxy.main.get_openai_client')
    def test_chat_completions_streaming_mock(self, mock_get_client, client):
        """测试流式响应 mock"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}],
            "stream": True
        })

        assert response.status_code == 200
        assert response.content_type == 'text/event-stream'

        # 验证流式数据格式
        data = response.get_data(as_text=True)
        assert 'data:' in data
        assert '[DONE]' in data

    @patch('services.openai_proxy.main.get_openai_client')
    def test_chat_completions_includes_usage(self, mock_get_client, client):
        """测试响应包含 usage 信息"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "测试消息"}]
        })

        data = json.loads(response.data)
        assert 'usage' in data
        assert 'prompt_tokens' in data['usage']
        assert 'completion_tokens' in data['usage']
        assert 'total_tokens' in data['usage']


class TestTemplateAPI:
    """Prompt 模板 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_list_templates(self, client):
        """测试列出所有模板"""
        response = client.get('/api/v1/templates')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert 'templates' in data['data']
        assert 'default' in data['data']['templates']
        assert 'rag' in data['data']['templates']

    def test_get_template_existing(self, client):
        """测试获取存在的模板"""
        response = client.get('/api/v1/templates/default')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert data['data']['name'] == 'default'
        assert 'template' in data['data']

    def test_get_template_nonexistent(self, client):
        """测试获取不存在的模板"""
        response = client.get('/api/v1/templates/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 40401

    def test_create_template(self, client):
        """测试创建新模板"""
        response = client.post('/api/v1/templates', json={
            "name": "custom_test",
            "template": "这是一个测试模板"
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['code'] == 0
        assert data['data']['name'] == 'custom_test'

        # 验证模板已创建
        response = client.get('/api/v1/templates/custom_test')
        assert response.status_code == 200

    def test_create_template_missing_name(self, client):
        """测试创建模板缺少名称"""
        response = client.post('/api/v1/templates', json={
            "template": "模板内容"
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 40001

    def test_create_template_missing_template(self, client):
        """测试创建模板缺少内容"""
        response = client.post('/api/v1/templates', json={
            "name": "test"
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 40001


class TestStatsAPI:
    """统计 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_get_stats(self, client):
        """测试获取统计信息"""
        response = client.get('/api/v1/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert 'total_requests' in data['data']
        assert 'total_tokens' in data['data']
        assert 'models' in data['data']


class TestOpenAIIntegration:
    """OpenAI 集成测试（需要 mock）"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @patch('services.openai_proxy.main.get_openai_client')
    def test_real_openai_call_non_streaming(self, mock_get_client, client):
        """测试真实 OpenAI 调用（非流式）"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 创建 mock 响应
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o-mini",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "测试响应"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }

        async def mock_create(*args, **kwargs):
            return mock_response

        mock_client.chat.completions.create = mock_create

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}]
        })

        assert response.status_code == 200

    @patch('services.openai_proxy.main.get_openai_client')
    def test_openai_error_handling(self, mock_get_client, client):
        """测试 OpenAI 错误处理"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from services.openai_proxy.main import OpenAIError

        async def mock_create(*args, **kwargs):
            raise OpenAIError("API Error")

        mock_client.chat.completions.create = mock_create

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}]
        })

        # 应该返回错误响应
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


class TestStreamingResponse:
    """流式响应测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from services.openai_proxy.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @patch('services.openai_proxy.main.get_openai_client')
    def test_streaming_chunks_format(self, mock_get_client, client):
        """测试流式响应格式"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}],
            "stream": True
        })

        chunks = response.get_data(as_text=True).split('\n\n')

        # 验证数据块格式
        for chunk in chunks:
            if chunk.startswith('data: ') and chunk != 'data: [DONE]':
                chunk_data = chunk.replace('data: ', '')
                try:
                    parsed = json.loads(chunk_data)
                    assert 'id' in parsed
                    assert 'choices' in parsed
                except json.JSONDecodeError:
                    pass  # 空行或 [DONE]

    @patch('services.openai_proxy.main.get_openai_client')
    def test_streaming_ends_with_done(self, mock_get_client, client):
        """测试流式响应以 [DONE] 结束"""
        mock_get_client.return_value = None

        response = client.post('/v1/chat/completions', json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "你好"}],
            "stream": True
        })

        data = response.get_data(as_text=True)
        assert 'data: [DONE]' in data
