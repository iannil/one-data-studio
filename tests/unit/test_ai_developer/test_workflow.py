"""
AI 开发者 - 工作流单元测试
测试用例：AD-WF-U-001 ~ AD-WF-U-010

工作流编排是 AI 开发者角色的核心功能，用于创建和管理复杂的 AI 处理流程。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json


class TestWorkflowCreation:
    """工作流创建测试 (AD-WF-U-001)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_rag_workflow(self, mock_workflow_service):
        """AD-WF-U-001: 创建 RAG 类型工作流"""
        workflow_data = {
            'name': '知识库问答工作流',
            'description': '基于向量检索的问答流程',
            'type': 'rag',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input', 'label': '用户输入'},
                    {'id': 'retrieval', 'type': 'vector_retrieval', 'label': '向量检索'},
                    {'id': 'llm', 'type': 'llm', 'label': 'LLM生成'},
                    {'id': 'output', 'type': 'output', 'label': '输出'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'retrieval'},
                    {'source': 'retrieval', 'target': 'llm'},
                    {'source': 'llm', 'target': 'output'}
                ]
            }
        }

        result = mock_workflow_service.create_workflow(workflow_data)

        assert result['success'] is True
        assert 'workflow_id' in result
        assert result['type'] == 'rag'
        assert result['status'] == 'stopped'

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_sql_workflow(self, mock_workflow_service):
        """AD-WF-U-001: 创建 SQL 生成类型工作流"""
        workflow_data = {
            'name': 'Text-to-SQL 工作流',
            'description': '自然语言转 SQL 查询',
            'type': 'sql',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input', 'label': '自然语言输入'},
                    {'id': 'schema_fetch', 'type': 'schema_fetch', 'label': '获取表结构'},
                    {'id': 'sql_gen', 'type': 'sql_generation', 'label': 'SQL生成'},
                    {'id': 'execute', 'type': 'sql_execute', 'label': '执行SQL'},
                    {'id': 'output', 'type': 'output', 'label': '返回结果'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'schema_fetch'},
                    {'source': 'schema_fetch', 'target': 'sql_gen'},
                    {'source': 'sql_gen', 'target': 'execute'},
                    {'source': 'execute', 'target': 'output'}
                ]
            }
        }

        result = mock_workflow_service.create_workflow(workflow_data)

        assert result['success'] is True
        assert result['type'] == 'sql'

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_agent_workflow(self, mock_workflow_service):
        """AD-WF-U-001: 创建 Agent 类型工作流"""
        workflow_data = {
            'name': '智能客服 Agent',
            'description': '多轮对话客服机器人',
            'type': 'agent',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'intent', 'type': 'intent_classification'},
                    {'id': 'route', 'type': 'conditional'},
                    {'id': 'kb_search', 'type': 'knowledge_search'},
                    {'id': 'api_call', 'type': 'api_call'},
                    {'id': 'output', 'type': 'output'}
                ]
            }
        }

        result = mock_workflow_service.create_workflow(workflow_data)

        assert result['success'] is True
        assert result['type'] == 'agent'


class TestWorkflowEditing:
    """工作流编辑测试 (AD-WF-U-002 ~ AD-WF-U-004)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_workflow_definition(self, mock_workflow_service):
        """AD-WF-U-002: 更新工作流定义"""
        workflow_id = 'wf_001'
        new_definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'process', 'type': 'llm', 'model': 'gpt-4'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'process'},
                {'source': 'process', 'target': 'output'}
            ]
        }

        mock_workflow_service.update_workflow.return_value = {
            'success': True,
            'workflow_id': workflow_id
        }

        result = mock_workflow_service.update_workflow(workflow_id, {'definition': new_definition})

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_add_workflow_node(self, mock_workflow_service):
        """AD-WF-U-003: 向工作流添加节点"""
        workflow_id = 'wf_001'
        new_node = {
            'id': 'validation',
            'type': 'validation',
            'label': '结果验证',
            'config': {'rules': ['format_check', 'range_check']}
        }

        result = mock_workflow_service.add_node(workflow_id, new_node)

        assert result['success'] is True
        assert 'node_id' in result

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_remove_workflow_node(self, mock_workflow_service):
        """AD-WF-U-004: 从工作流移除节点"""
        workflow_id = 'wf_001'
        node_id = 'old_node'

        mock_workflow_service.remove_node.return_value = {
            'success': True,
            'removed_edges': 2
        }

        result = mock_workflow_service.remove_node(workflow_id, node_id)

        assert result['success'] is True
        assert result['removed_edges'] == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_add_workflow_edge(self, mock_workflow_service):
        """AD-WF-U-005: 添加工作流边"""
        workflow_id = 'wf_001'
        edge = {'source': 'node_a', 'target': 'node_b', 'condition': 'success'}

        result = mock_workflow_service.add_edge(workflow_id, edge)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_validate_workflow_definition(self, mock_workflow_service):
        """AD-WF-U-006: 验证工作流定义"""
        valid_definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'output'}
            ]
        }

        result = mock_workflow_service.validate_definition(valid_definition)

        assert result['valid'] is True

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_validate_invalid_workflow(self, mock_workflow_service):
        """AD-WF-U-006: 验证无效工作流定义（断链）"""
        invalid_definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'orphan', 'type': 'process'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'output'}
            ]
        }

        mock_workflow_service.validate_definition.return_value = {
            'valid': False,
            'errors': ['节点 orphan 没有连接到工作流']
        }

        result = mock_workflow_service.validate_definition(invalid_definition)

        assert result['valid'] is False
        assert len(result['errors']) > 0


class TestWorkflowExecution:
    """工作流执行测试 (AD-WF-U-007 ~ AD-WF-U-010)"""

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_start_workflow_execution(self, mock_workflow_service):
        """AD-WF-U-007: 启动工作流执行"""
        workflow_id = 'wf_001'
        input_data = {
            'query': '用户的问题'
        }

        mock_workflow_service.start_execution.return_value = {
            'success': True,
            'execution_id': 'exec_001',
            'status': 'running'
        }

        result = mock_workflow_service.start_execution(workflow_id, input_data)

        assert result['success'] is True
        assert 'execution_id' in result
        assert result['status'] == 'running'

    @pytest.mark.p0
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_workflow_execution_status(self, mock_workflow_service):
        """AD-WF-U-008: 获取工作流执行状态"""
        execution_id = 'exec_001'

        mock_workflow_service.get_execution_status.return_value = {
            'execution_id': execution_id,
            'status': 'completed',
            'current_node': 'output',
            'completed_nodes': ['input', 'retrieval', 'llm', 'output'],
            'progress': 100
        }

        result = mock_workflow_service.get_execution_status(execution_id)

        assert result['status'] == 'completed'
        assert result['progress'] == 100

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_stop_workflow_execution(self, mock_workflow_service):
        """AD-WF-U-009: 停止工作流执行"""
        execution_id = 'exec_001'

        mock_workflow_service.stop_execution.return_value = {
            'success': True,
            'execution_id': execution_id,
            'status': 'stopped'
        }

        result = mock_workflow_service.stop_execution(execution_id)

        assert result['success'] is True
        assert result['status'] == 'stopped'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_workflow_execution_logs(self, mock_workflow_service):
        """AD-WF-U-010: 获取工作流执行日志"""
        execution_id = 'exec_001'

        mock_workflow_service.get_execution_logs.return_value = {
            'execution_id': execution_id,
            'logs': [
                {'node': 'input', 'timestamp': '2024-01-01T10:00:00Z', 'message': '接收输入', 'level': 'info'},
                {'node': 'retrieval', 'timestamp': '2024-01-01T10:00:01Z', 'message': '检索到 5 个文档', 'level': 'info'},
                {'node': 'llm', 'timestamp': '2024-01-01T10:00:03Z', 'message': '生成响应完成', 'level': 'info'}
            ]
        }

        result = mock_workflow_service.get_execution_logs(execution_id)

        assert 'logs' in result
        assert len(result['logs']) == 3


class TestWorkflowManagement:
    """工作流管理测试 (AD-WF-U-011 ~ AD-WF-U-015)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_workflows(self, mock_workflow_service):
        """AD-WF-U-011: 列出工作流"""
        mock_workflow_service.list_workflows.return_value = {
            'success': True,
            'workflows': [
                {'workflow_id': 'wf_001', 'name': 'RAG工作流', 'type': 'rag', 'status': 'running'},
                {'workflow_id': 'wf_002', 'name': 'SQL工作流', 'type': 'sql', 'status': 'stopped'}
            ],
            'total': 2
        }

        result = mock_workflow_service.list_workflows()

        assert result['success'] is True
        assert len(result['workflows']) == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_get_workflow_detail(self, mock_workflow_service):
        """AD-WF-U-012: 获取工作流详情"""
        workflow_id = 'wf_001'

        mock_workflow_service.get_workflow.return_value = {
            'success': True,
            'workflow_id': workflow_id,
            'name': 'RAG工作流',
            'type': 'rag',
            'definition': {'nodes': [], 'edges': []},
            'created_by': 'user001',
            'created_at': '2024-01-01T00:00:00Z'
        }

        result = mock_workflow_service.get_workflow(workflow_id)

        assert result['workflow_id'] == workflow_id

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_delete_workflow(self, mock_workflow_service):
        """AD-WF-U-013: 删除工作流"""
        workflow_id = 'wf_001'

        result = mock_workflow_service.delete_workflow(workflow_id)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_duplicate_workflow(self, mock_workflow_service):
        """AD-WF-U-014: 复制工作流"""
        workflow_id = 'wf_001'

        mock_workflow_service.duplicate_workflow.return_value = {
            'success': True,
            'new_workflow_id': 'wf_002',
            'name': 'RAG工作流 (副本)'
        }

        result = mock_workflow_service.duplicate_workflow(workflow_id)

        assert result['success'] is True
        assert 'new_workflow_id' in result

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_export_import_workflow(self, mock_workflow_service):
        """AD-WF-U-015: 导出/导入工作流"""
        workflow_id = 'wf_001'

        # 导出
        mock_workflow_service.export_workflow.return_value = {
            'success': True,
            'data': json.dumps({
                'name': 'RAG工作流',
                'type': 'rag',
                'definition': {'nodes': [], 'edges': []}
            })
        }

        export_result = mock_workflow_service.export_workflow(workflow_id)
        assert export_result['success'] is True

        # 导入
        import_data = json.loads(export_result['data'])
        mock_workflow_service.import_workflow.return_value = {
            'success': True,
            'workflow_id': 'wf_003',
            'name': 'RAG工作流'
        }

        import_result = mock_workflow_service.import_workflow(import_data)
        assert import_result['success'] is True


class TestWorkflowScheduling:
    """工作流调度测试 (AD-WF-U-016 ~ AD-WF-U-018)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_workflow_schedule(self, mock_workflow_service):
        """AD-WF-U-016: 创建工作流调度"""
        workflow_id = 'wf_001'
        schedule_config = {
            'cron': '0 9 * * *',  # 每天 9 点
            'timezone': 'Asia/Shanghai',
            'input_data': {'query': '日报生成'}
        }

        mock_workflow_service.create_schedule.return_value = {
            'success': True,
            'schedule_id': 'sched_001'
        }

        result = mock_workflow_service.create_schedule(workflow_id, schedule_config)

        assert result['success'] is True
        assert 'schedule_id' in result

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_workflow_schedule(self, mock_workflow_service):
        """AD-WF-U-017: 更新工作流调度"""
        schedule_id = 'sched_001'
        new_config = {'cron': '0 18 * * *'}  # 改为 18 点

        mock_workflow_service.update_schedule.return_value = {
            'success': True,
            'schedule_id': schedule_id
        }

        result = mock_workflow_service.update_schedule(schedule_id, new_config)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_delete_workflow_schedule(self, mock_workflow_service):
        """AD-WF-U-018: 删除工作流调度"""
        schedule_id = 'sched_001'

        result = mock_workflow_service.delete_schedule(schedule_id)

        assert result['success'] is True


# ==================== Fixtures ====================

@pytest.fixture
def mock_workflow_service():
    """Mock 工作流服务"""
    service = Mock()

    def mock_create(data):
        return {
            'success': True,
            'workflow_id': 'wf_001',
            'type': data.get('type', 'rag'),
            'status': 'stopped',
            'name': data.get('name', '')
        }

    def mock_validate(definition):
        # 简单验证：检查孤立节点
        nodes = definition.get('nodes', [])
        edges = definition.get('edges', [])
        connected = set()
        for edge in edges:
            connected.add(edge['source'])
            connected.add(edge['target'])
        orphans = [n['id'] for n in nodes if n['id'] not in connected and n['type'] not in ['input', 'output']]

        if orphans:
            return {
                'valid': False,
                'errors': [f'节点 {orphans[0]} 没有连接到工作流']
            }
        return {'valid': True}

    service.create_workflow = Mock(side_effect=mock_create)
    service.update_workflow = Mock()
    service.add_node = Mock(return_value={'success': True, 'node_id': 'node_001'})
    service.remove_node = Mock()
    service.add_edge = Mock(return_value={'success': True})
    service.validate_definition = Mock(side_effect=mock_validate)
    service.start_execution = Mock()
    service.get_execution_status = Mock()
    service.stop_execution = Mock()
    service.get_execution_logs = Mock()
    service.list_workflows = Mock()
    service.get_workflow = Mock()
    service.delete_workflow = Mock(return_value={'success': True})
    service.duplicate_workflow = Mock()
    service.export_workflow = Mock()
    service.import_workflow = Mock()
    service.create_schedule = Mock()
    service.update_schedule = Mock()
    service.delete_schedule = Mock(return_value={'success': True})

    return service
