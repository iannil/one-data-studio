"""
AI 开发者 - Agent 应用管理单元测试
测试用例：AD-AG-U-001 ~ AD-AG-U-012

Agent 应用管理是 AI 开发者角色发布和管理 AI 应用的核心功能。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestAgentAppPublish:
    """Agent 应用发布测试 (AD-AG-U-001 ~ AD-AG-U-003)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_publish_workflow_as_app(self, mock_agent_app_service):
        """AD-AG-U-001: 发布工作流为 Agent 应用"""
        publish_data = {
            'workflow_id': 'wf_001',
            'app_name': '智能客服助手',
            'description': '基于知识库的智能客服问答应用',
            'version': '1.0.0',
            'is_public': True
        }

        result = mock_agent_app_service.publish_app(publish_data)

        assert result['success'] is True
        assert 'app_id' in result
        assert result['status'] == 'published'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_publish_app_with_api_config(self, mock_agent_app_service):
        """AD-AG-U-002: 发布应用并配置 API"""
        publish_data = {
            'workflow_id': 'wf_001',
            'app_name': 'SQL生成助手',
            'description': '自然语言转SQL查询',
            'version': '1.0.0',
            'api_config': {
                'rate_limit': 100,
                'timeout': 30,
                'auth_required': True
            }
        }

        result = mock_agent_app_service.publish_app(publish_data)

        assert result['success'] is True
        assert 'api_endpoint' in result
        assert 'api_key' in result

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_publish_app_invalid_workflow(self, mock_agent_app_service):
        """AD-AG-U-003: 发布无效工作流为应用"""
        publish_data = {
            'workflow_id': 'invalid_wf_id',
            'app_name': '测试应用'
        }

        result = mock_agent_app_service.publish_app(publish_data)

        assert result['success'] is False
        assert 'error' in result


class TestAgentAppManagement:
    """Agent 应用管理测试 (AD-AG-U-004 ~ AD-AG-U-008)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_agent_apps(self, mock_agent_app_service):
        """AD-AG-U-004: 列出 Agent 应用"""
        mock_agent_app_service.list_apps.return_value = {
            'success': True,
            'apps': [
                {'app_id': 'app_001', 'name': '智能客服', 'status': 'published', 'version': '1.0.0'},
                {'app_id': 'app_002', 'name': 'SQL助手', 'status': 'published', 'version': '2.0.0'}
            ],
            'total': 2
        }

        result = mock_agent_app_service.list_apps()

        assert result['success'] is True
        assert len(result['apps']) == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_agent_app_detail(self, mock_agent_app_service):
        """AD-AG-U-005: 获取 Agent 应用详情"""
        app_id = 'app_001'

        mock_agent_app_service.get_app.return_value = {
            'success': True,
            'app_id': app_id,
            'name': '智能客服助手',
            'description': '基于知识库的智能客服',
            'workflow_id': 'wf_001',
            'status': 'published',
            'version': '1.0.0',
            'api_endpoint': f'/api/v1/agent/apps/{app_id}',
            'created_by': 'user001',
            'created_at': '2024-01-01T00:00:00Z'
        }

        result = mock_agent_app_service.get_app(app_id)

        assert result['success'] is True
        assert result['app_id'] == app_id

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_agent_app(self, mock_agent_app_service):
        """AD-AG-U-006: 更新 Agent 应用"""
        app_id = 'app_001'
        update_data = {
            'name': '更新后的应用名称',
            'description': '更新后的描述'
        }

        mock_agent_app_service.update_app.return_value = {
            'success': True,
            'app_id': app_id
        }

        result = mock_agent_app_service.update_app(app_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_app_version(self, mock_agent_app_service):
        """AD-AG-U-007: 更新应用版本"""
        app_id = 'app_001'
        version_data = {
            'workflow_id': 'wf_002',  # 新版本工作流
            'version': '2.0.0',
            'change_log': '优化检索逻辑，提升准确率'
        }

        mock_agent_app_service.create_version.return_value = {
            'success': True,
            'app_id': app_id,
            'new_version': '2.0.0',
            'previous_version': '1.0.0'
        }

        result = mock_agent_app_service.create_version(app_id, version_data)

        assert result['success'] is True
        assert result['new_version'] == '2.0.0'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_deprecate_agent_app(self, mock_agent_app_service):
        """AD-AG-U-008: 弃用 Agent 应用"""
        app_id = 'app_001'

        mock_agent_app_service.deprecate_app.return_value = {
            'success': True,
            'app_id': app_id,
            'status': 'deprecated'
        }

        result = mock_agent_app_service.deprecate_app(app_id)

        assert result['success'] is True
        assert result['status'] == 'deprecated'


class TestAgentAppExecution:
    """Agent 应用执行测试 (AD-AG-U-009 ~ AD-AG-U-011)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_execute_agent_app(self, mock_agent_app_service):
        """AD-AG-U-009: 执行 Agent 应用"""
        app_id = 'app_001'
        input_data = {
            'query': '产品价格是多少？'
        }

        mock_agent_app_service.execute_app.return_value = {
            'success': True,
            'execution_id': 'exec_001',
            'result': '根据知识库，产品价格为199元',
            'tokens_used': 250,
            'duration_ms': 1500
        }

        result = mock_agent_app_service.execute_app(app_id, input_data)

        assert result['success'] is True
        assert 'result' in result
        assert 'execution_id' in result

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_execute_app_with_streaming(self, mock_agent_app_service):
        """AD-AG-U-010: 流式执行 Agent 应用"""
        app_id = 'app_001'
        input_data = {
            'query': '写一段产品介绍',
            'stream': True
        }

        mock_agent_app_service.execute_app_stream.return_value = {
            'success': True,
            'execution_id': 'exec_002',
            'stream_url': '/api/v1/agent/apps/app_001/stream/exec_002'
        }

        result = mock_agent_app_service.execute_app_stream(app_id, input_data)

        assert result['success'] is True
        assert 'stream_url' in result

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_app_execution_history(self, mock_agent_app_service):
        """AD-AG-U-011: 获取应用执行历史"""
        app_id = 'app_001'

        mock_agent_app_service.get_execution_history.return_value = {
            'success': True,
            'executions': [
                {'execution_id': 'exec_001', 'status': 'completed', 'created_at': '2024-01-01T10:00:00Z'},
                {'execution_id': 'exec_002', 'status': 'completed', 'created_at': '2024-01-01T11:00:00Z'}
            ],
            'total': 2
        }

        result = mock_agent_app_service.get_execution_history(app_id)

        assert result['success'] is True
        assert len(result['executions']) == 2


class TestAgentAppApiKey:
    """Agent 应用 API Key 测试 (AD-AG-U-012 ~ AD-AG-U-014)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_api_key(self, mock_agent_app_service):
        """AD-AG-U-012: 创建应用 API Key"""
        app_id = 'app_001'
        key_config = {
            'name': '生产环境Key',
            'rate_limit': 1000,
            'expires_at': '2025-01-01T00:00:00Z'
        }

        mock_agent_app_service.create_api_key.return_value = {
            'success': True,
            'api_key': 'sk_live_xxxxx',
            'key_id': 'key_001'
        }

        result = mock_agent_app_service.create_api_key(app_id, key_config)

        assert result['success'] is True
        assert 'api_key' in result
        assert result['api_key'].startswith('sk_live_')

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_api_keys(self, mock_agent_app_service):
        """AD-AG-U-013: 列出应用 API Key"""
        app_id = 'app_001'

        mock_agent_app_service.list_api_keys.return_value = {
            'success': True,
            'api_keys': [
                {'key_id': 'key_001', 'name': '生产环境Key', 'last_used': '2024-01-01T10:00:00Z'},
                {'key_id': 'key_002', 'name': '测试环境Key', 'last_used': None}
            ],
            'total': 2
        }

        result = mock_agent_app_service.list_api_keys(app_id)

        assert result['success'] is True
        assert len(result['api_keys']) == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_revoke_api_key(self, mock_agent_app_service):
        """AD-AG-U-014: 撤销应用 API Key"""
        app_id = 'app_001'
        key_id = 'key_001'

        result = mock_agent_app_service.revoke_api_key(app_id, key_id)

        assert result['success'] is True


class TestAgentAppAnalytics:
    """Agent 应用分析测试 (AD-AG-U-015 ~ AD-AG-U-016)"""

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_app_statistics(self, mock_agent_app_service):
        """AD-AG-U-015: 获取应用统计数据"""
        app_id = 'app_001'

        mock_agent_app_service.get_statistics.return_value = {
            'success': True,
            'app_id': app_id,
            'total_executions': 1000,
            'successful_executions': 950,
            'failed_executions': 50,
            'avg_duration_ms': 1200,
            'total_tokens_used': 250000,
            'total_cost': 5.0,
            'date_range': {'start': '2024-01-01', 'end': '2024-01-31'}
        }

        result = mock_agent_app_service.get_statistics(app_id)

        assert result['success'] is True
        assert result['total_executions'] == 1000
        assert result['successful_executions'] == 950

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_app_daily_usage(self, mock_agent_app_service):
        """AD-AG-U-016: 获取应用每日使用情况"""
        app_id = 'app_001'

        mock_agent_app_service.get_daily_usage.return_value = {
            'success': True,
            'app_id': app_id,
            'daily_data': [
                {'date': '2024-01-01', 'executions': 100, 'tokens': 25000},
                {'date': '2024-01-02', 'executions': 120, 'tokens': 30000},
                {'date': '2024-01-03', 'executions': 80, 'tokens': 20000}
            ]
        }

        result = mock_agent_app_service.get_daily_usage(app_id)

        assert result['success'] is True
        assert len(result['daily_data']) == 3


# ==================== Fixtures ====================

@pytest.fixture
def mock_agent_app_service():
    """Mock Agent 应用服务"""
    service = Mock()

    def mock_publish(data):
        # 检查是否为无效工作流
        if data.get('workflow_id') == 'invalid_wf_id':
            return {
                'success': False,
                'error': 'Workflow not found or not in valid state'
            }

        result = {
            'success': True,
            'app_id': 'app_001',
            'name': data.get('app_name', ''),
            'status': 'published',
            'version': data.get('version', '1.0.0')
        }

        # 如果有 api_config，返回 API 相关字段
        if 'api_config' in data:
            result['api_endpoint'] = '/api/v1/agent/apps/app_001'
            result['api_key'] = 'sk_test_xxxxx'

        return result

    service.publish_app = Mock(side_effect=mock_publish)
    service.list_apps = Mock()
    service.get_app = Mock()
    service.update_app = Mock(return_value={'success': True})
    service.create_version = Mock()
    service.deprecate_app = Mock()
    service.execute_app = Mock()
    service.execute_app_stream = Mock()
    service.get_execution_history = Mock()
    service.create_api_key = Mock()
    service.list_api_keys = Mock()
    service.revoke_api_key = Mock(return_value={'success': True})
    service.get_statistics = Mock()
    service.get_daily_usage = Mock()

    return service
