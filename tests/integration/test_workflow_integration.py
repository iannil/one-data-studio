"""
工作流编排集成测试
测试用例编号: AD-WF-I-001 ~ AD-WF-I-010

工作流编排是 AI 开发者角色的核心功能，用于创建和管理复杂的 AI 处理流程。
集成测试覆盖：
- 工作流创建与编辑
- 工作流节点编排
- 工作流执行与监控
- 工作流调度
"""

import pytest
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Dict, List, Any

import sys
import os

_project_root = os.path.join(os.path.dirname(__file__), "../..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ==================== Fixtures ====================

@pytest.fixture
def workflow_integration_service():
    """工作流集成服务"""

    class WorkflowIntegrationService:
        """工作流集成测试服务"""

        def __init__(self):
            self._workflows = {}
            self._executions = {}
            self._schedules = {}
            self._node_types = self._init_node_types()

        def _init_node_types(self):
            """初始化支持的节点类型"""
            return {
                'input': {'category': 'io', 'async': False},
                'output': {'category': 'io', 'async': False},
                'llm': {'category': 'ai', 'async': True},
                'vector_retrieval': {'category': 'retrieval', 'async': True},
                'sql_generation': {'category': 'sql', 'async': True},
                'sql_execute': {'category': 'sql', 'async': True},
                'schema_fetch': {'category': 'sql', 'async': False},
                'knowledge_search': {'category': 'retrieval', 'async': True},
                'api_call': {'category': 'external', 'async': True},
                'conditional': {'category': 'control', 'async': False},
                'validation': {'category': 'control', 'async': False}
            }

        def create_workflow(self, workflow_data: Dict) -> Dict:
            """创建工作流"""
            name = workflow_data.get('name')
            workflow_type = workflow_data.get('type', 'rag')
            definition = workflow_data.get('definition', {})

            workflow_id = f"wf_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            workflow = {
                'workflow_id': workflow_id,
                'name': name,
                'description': workflow_data.get('description', ''),
                'type': workflow_type,
                'status': 'stopped',
                'definition': json.dumps(definition),
                'created_by': workflow_data.get('created_by', 'test_user'),
                'created_at': now,
                'updated_at': now
            }

            self._workflows[workflow_id] = workflow
            return {'success': True, 'workflow_id': workflow_id, 'workflow': workflow}

        def validate_workflow_definition(self, definition: Dict) -> Dict:
            """验证工作流定义"""
            nodes = definition.get('nodes', [])
            edges = definition.get('edges', [])

            # 检查是否有输入和输出节点
            node_types = {n.get('type') for n in nodes}
            if 'input' not in node_types:
                return {'valid': False, 'errors': ['缺少输入节点']}
            if 'output' not in node_types:
                return {'valid': False, 'errors': ['缺少输出节点']}

            # 检查节点类型是否有效
            for node in nodes:
                node_type = node.get('type')
                if node_type not in self._node_types:
                    return {'valid': False, 'errors': [f'无效的节点类型: {node_type}']}

            # 检查边的连接是否有效
            node_ids = {n.get('id') for n in nodes}
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                if source not in node_ids:
                    return {'valid': False, 'errors': [f'边引用了不存在的源节点: {source}']}
                if target not in node_ids:
                    return {'valid': False, 'errors': [f'边引用了不存在的目标节点: {target}']}

            # 检查孤立节点
            connected_nodes = set()
            for edge in edges:
                connected_nodes.add(edge['source'])
                connected_nodes.add(edge['target'])

            orphan_nodes = []
            for node in nodes:
                if node['id'] not in connected_nodes and node['type'] not in ['input', 'output']:
                    orphan_nodes.append(node['id'])

            if orphan_nodes:
                return {'valid': False, 'errors': [f'存在孤立节点: {", ".join(orphan_nodes)}']}

            return {'valid': True, 'errors': []}

        def execute_workflow(self, workflow_id: str, input_data: Dict) -> Dict:
            """执行工作流"""
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return {'success': False, 'error': '工作流不存在'}

            if workflow['status'] == 'running':
                return {'success': False, 'error': '工作流正在运行中'}

            execution_id = f"exec_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            execution = {
                'execution_id': execution_id,
                'workflow_id': workflow_id,
                'status': 'running',
                'input_data': input_data,
                'current_node': 'input',
                'started_at': now,
                'completed_at': None,
                'logs': []
            }

            self._executions[execution_id] = execution

            # 更新工作流状态
            workflow['status'] = 'running'

            return {'success': True, 'execution_id': execution_id, 'execution': execution}

        async def simulate_workflow_execution(self, execution_id: str) -> Dict:
            """模拟工作流执行过程"""
            execution = self._executions.get(execution_id)
            if not execution:
                return {'success': False, 'error': '执行不存在'}

            workflow = self._workflows.get(execution['workflow_id'])
            definition = json.loads(workflow['definition'])

            # 模拟节点执行
            nodes = definition.get('nodes', [])
            edges = definition.get('edges', [])

            # 构建执行路径
            path = ['input']
            current = 'input'
            while current != 'output':
                for edge in edges:
                    if edge['source'] == current:
                        current = edge['target']
                        path.append(current)
                        break

            # 模拟执行每个节点
            for node in path:
                execution['current_node'] = node
                execution['logs'].append({
                    'node': node,
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': f'执行节点: {node}',
                    'level': 'info'
                })
                await asyncio.sleep(0.01)  # 模拟处理时间

            execution['status'] = 'completed'
            execution['current_node'] = 'output'
            execution['completed_at'] = datetime.utcnow().isoformat()
            execution['result'] = {'message': '工作流执行完成', 'nodes_executed': len(path)}

            workflow['status'] = 'stopped'

            return {'success': True, 'execution': execution}

        def get_execution_status(self, execution_id: str) -> Dict:
            """获取执行状态"""
            execution = self._executions.get(execution_id)
            if not execution:
                return {'success': False, 'error': '执行不存在'}

            nodes_count = len(execution.get('logs', []))
            total_nodes = 5  # 假设典型工作流有5个节点

            return {
                'success': True,
                'execution_id': execution_id,
                'status': execution['status'],
                'current_node': execution.get('current_node'),
                'progress': int(nodes_count / total_nodes * 100) if total_nodes > 0 else 0,
                'started_at': execution['started_at'],
                'completed_at': execution.get('completed_at')
            }

        def stop_execution(self, execution_id: str) -> Dict:
            """停止执行"""
            execution = self._executions.get(execution_id)
            if not execution:
                return {'success': False, 'error': '执行不存在'}

            if execution['status'] == 'completed':
                return {'success': False, 'error': '执行已完成，无法停止'}

            execution['status'] = 'stopped'
            execution['completed_at'] = datetime.utcnow().isoformat()

            workflow_id = execution['workflow_id']
            self._workflows[workflow_id]['status'] = 'stopped'

            return {'success': True, 'execution_id': execution_id, 'status': 'stopped'}

        def create_schedule(self, workflow_id: str, schedule_config: Dict) -> Dict:
            """创建调度"""
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return {'success': False, 'error': '工作流不存在'}

            schedule_id = f"sched_{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            schedule = {
                'schedule_id': schedule_id,
                'workflow_id': workflow_id,
                'cron': schedule_config.get('cron', '0 * * * *'),
                'timezone': schedule_config.get('timezone', 'Asia/Shanghai'),
                'input_data': schedule_config.get('input_data', {}),
                'is_active': True,
                'created_at': now
            }

            self._schedules[schedule_id] = schedule
            return {'success': True, 'schedule_id': schedule_id, 'schedule': schedule}

        def update_schedule(self, schedule_id: str, update_config: Dict) -> Dict:
            """更新调度"""
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return {'success': False, 'error': '调度不存在'}

            for key, value in update_config.items():
                if key in schedule:
                    schedule[key] = value

            return {'success': True, 'schedule_id': schedule_id, 'schedule': schedule}

        def delete_schedule(self, schedule_id: str) -> Dict:
            """删除调度"""
            if schedule_id not in self._schedules:
                return {'success': False, 'error': '调度不存在'}

            del self._schedules[schedule_id]
            return {'success': True, 'schedule_id': schedule_id}

        def get_workflow(self, workflow_id: str) -> Dict:
            """获取工作流"""
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return {'success': False, 'error': '工作流不存在'}
            return {'success': True, 'workflow': workflow}

        def update_workflow(self, workflow_id: str, update_data: Dict) -> Dict:
            """更新工作流"""
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return {'success': False, 'error': '工作流不存在'}

            for key, value in update_data.items():
                if key == 'definition':
                    workflow[key] = json.dumps(value)
                elif key in workflow:
                    workflow[key] = value

            workflow['updated_at'] = datetime.utcnow().isoformat()
            return {'success': True, 'workflow_id': workflow_id, 'workflow': workflow}

        def delete_workflow(self, workflow_id: str) -> Dict:
            """删除工作流"""
            if workflow_id not in self._workflows:
                return {'success': False, 'error': '工作流不存在'}

            workflow = self._workflows[workflow_id]
            if workflow['status'] == 'running':
                return {'success': False, 'error': '运行中的工作流无法删除'}

            del self._workflows[workflow_id]
            return {'success': True, 'workflow_id': workflow_id}

    return WorkflowIntegrationService()


# ==================== 测试类 ====================

@pytest.mark.integration
class TestWorkflowCreationAndValidation:
    """工作流创建与验证测试 (AD-WF-I-001 ~ AD-WF-I-003)"""

    def test_create_rag_workflow(self, workflow_integration_service):
        """AD-WF-I-001: 创建 RAG 类型工作流"""
        workflow_data = {
            'name': '知识库问答工作流',
            'type': 'rag',
            'description': '基于向量检索的问答流程',
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

        result = workflow_integration_service.create_workflow(workflow_data)

        assert result['success'] is True
        assert 'workflow_id' in result
        assert result['workflow']['type'] == 'rag'

    def test_create_sql_workflow(self, workflow_integration_service):
        """AD-WF-I-002: 创建 SQL 生成类型工作流"""
        workflow_data = {
            'name': 'Text-to-SQL 工作流',
            'type': 'sql',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'schema', 'type': 'schema_fetch'},
                    {'id': 'sql_gen', 'type': 'sql_generation'},
                    {'id': 'execute', 'type': 'sql_execute'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'schema'},
                    {'source': 'schema', 'target': 'sql_gen'},
                    {'source': 'sql_gen', 'target': 'execute'},
                    {'source': 'execute', 'target': 'output'}
                ]
            }
        }

        result = workflow_integration_service.create_workflow(workflow_data)

        assert result['success'] is True
        assert result['workflow']['type'] == 'sql'

    def test_validate_valid_workflow(self, workflow_integration_service):
        """AD-WF-I-003: 验证有效的工作流定义"""
        definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'process', 'type': 'llm'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'process'},
                {'source': 'process', 'target': 'output'}
            ]
        }

        result = workflow_integration_service.validate_workflow_definition(definition)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_invalid_workflow_missing_nodes(self, workflow_integration_service):
        """验证缺少必要节点的工作流"""
        definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'}
                # 缺少 output 节点
            ],
            'edges': []
        }

        result = workflow_integration_service.validate_workflow_definition(definition)

        assert result['valid'] is False
        assert '缺少输出节点' in result['errors']

    def test_validate_invalid_workflow_orphan_nodes(self, workflow_integration_service):
        """验证有孤立节点的工作流"""
        definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'orphan', 'type': 'llm'},  # 孤立节点
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'output'}
            ]
        }

        result = workflow_integration_service.validate_workflow_definition(definition)

        assert result['valid'] is False
        assert any('孤立节点' in err for err in result['errors'])


@pytest.mark.integration
class TestWorkflowExecution:
    """工作流执行测试 (AD-WF-I-004 ~ AD-WF-I-007)"""

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, workflow_integration_service):
        """AD-WF-I-004: 成功执行工作流"""
        # 创建工作流
        workflow_data = {
            'name': '测试工作流',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'process', 'type': 'llm'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'process'},
                    {'source': 'process', 'target': 'output'}
                ]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        # 执行工作流
        input_data = {'query': '测试问题'}
        exec_result = workflow_integration_service.execute_workflow(workflow_id, input_data)

        assert exec_result['success'] is True
        assert 'execution_id' in exec_result
        assert exec_result['execution']['status'] == 'running'

        # 模拟执行完成
        execution_id = exec_result['execution_id']
        await workflow_integration_service.simulate_workflow_execution(execution_id)

        # 验证执行完成
        status_result = workflow_integration_service.get_execution_status(execution_id)
        assert status_result['status'] == 'completed'

    def test_execute_workflow_not_found(self, workflow_integration_service):
        """AD-WF-I-005: 执行不存在的工作流"""
        result = workflow_integration_service.execute_workflow('invalid_wf_id', {})

        assert result['success'] is False
        assert '不存在' in result['error']

    def test_execute_running_workflow(self, workflow_integration_service):
        """AD-WF-I-006: 执行正在运行的工作流"""
        workflow_data = {
            'name': '运行测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        # 第一次执行
        workflow_integration_service.execute_workflow(workflow_id, {})

        # 第二次执行应该失败
        result = workflow_integration_service.execute_workflow(workflow_id, {})

        assert result['success'] is False
        assert '运行中' in result['error']

    def test_stop_workflow_execution(self, workflow_integration_service):
        """AD-WF-I-007: 停止工作流执行"""
        workflow_data = {
            'name': '停止测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'process', 'type': 'llm'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'process'},
                    {'source': 'process', 'target': 'output'}
                ]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        # 执行工作流
        exec_result = workflow_integration_service.execute_workflow(workflow_id, {})
        execution_id = exec_result['execution_id']

        # 停止执行
        stop_result = workflow_integration_service.stop_execution(execution_id)

        assert stop_result['success'] is True
        assert stop_result['status'] == 'stopped'


@pytest.mark.integration
class TestWorkflowScheduling:
    """工作流调度测试 (AD-WF-I-008 ~ AD-WF-I-010)"""

    def test_create_workflow_schedule(self, workflow_integration_service):
        """AD-WF-I-008: 创建工作流调度"""
        workflow_data = {
            'name': '调度测试工作流',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        schedule_config = {
            'cron': '0 9 * * *',
            'timezone': 'Asia/Shanghai',
            'input_data': {'query': '日报生成'}
        }

        result = workflow_integration_service.create_schedule(workflow_id, schedule_config)

        assert result['success'] is True
        assert 'schedule_id' in result
        assert result['schedule']['cron'] == '0 9 * * *'

    def test_update_workflow_schedule(self, workflow_integration_service):
        """AD-WF-I-009: 更新工作流调度"""
        workflow_data = {
            'name': '调度更新测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        schedule_result = workflow_integration_service.create_schedule(workflow_id, {'cron': '0 9 * * *'})
        schedule_id = schedule_result['schedule_id']

        # 更新调度
        update_config = {'cron': '0 18 * * *'}  # 改为18点
        result = workflow_integration_service.update_schedule(schedule_id, update_config)

        assert result['success'] is True
        assert result['schedule']['cron'] == '0 18 * * *'

    def test_delete_workflow_schedule(self, workflow_integration_service):
        """AD-WF-I-010: 删除工作流调度"""
        workflow_data = {
            'name': '调度删除测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        schedule_result = workflow_integration_service.create_schedule(workflow_id, {'cron': '0 9 * * *'})
        schedule_id = schedule_result['schedule_id']

        # 删除调度
        result = workflow_integration_service.delete_schedule(schedule_id)

        assert result['success'] is True
        assert result['schedule_id'] == schedule_id


@pytest.mark.integration
class TestWorkflowManagement:
    """工作流管理测试 (AD-WF-I-011 ~ AD-WF-I-013)"""

    def test_update_workflow_definition(self, workflow_integration_service):
        """AD-WF-I-011: 更新工作流定义"""
        workflow_data = {
            'name': '更新测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        # 更新定义
        new_definition = {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'process', 'type': 'llm'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'process'},
                {'source': 'process', 'target': 'output'}
            ]
        }

        result = workflow_integration_service.update_workflow(workflow_id, {'definition': new_definition})

        assert result['success'] is True

        # 验证更新
        get_result = workflow_integration_service.get_workflow(workflow_id)
        updated_definition = json.loads(get_result['workflow']['definition'])
        assert len(updated_definition['nodes']) == 3

    def test_delete_workflow(self, workflow_integration_service):
        """AD-WF-I-012: 删除工作流"""
        workflow_data = {
            'name': '删除测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [{'source': 'input', 'target': 'output'}]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        result = workflow_integration_service.delete_workflow(workflow_id)

        assert result['success'] is True

        # 验证删除
        get_result = workflow_integration_service.get_workflow(workflow_id)
        assert get_result['success'] is False

    def test_delete_running_workflow_blocked(self, workflow_integration_service):
        """AD-WF-I-013: 删除正在运行的工作流被阻止"""
        workflow_data = {
            'name': '运行中删除测试',
            'definition': {
                'nodes': [
                    {'id': 'input', 'type': 'input'},
                    {'id': 'process', 'type': 'llm'},
                    {'id': 'output', 'type': 'output'}
                ],
                'edges': [
                    {'source': 'input', 'target': 'process'},
                    {'source': 'process', 'target': 'output'}
                ]
            }
        }

        create_result = workflow_integration_service.create_workflow(workflow_data)
        workflow_id = create_result['workflow_id']

        # 执行工作流
        workflow_integration_service.execute_workflow(workflow_id, {})

        # 尝试删除
        result = workflow_integration_service.delete_workflow(workflow_id)

        assert result['success'] is False
        assert '运行中' in result['error']
