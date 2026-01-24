"""
工作流执行器单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock
import asyncio
import json


class TestWorkflowExecutor:
    """WorkflowExecutor 单元测试"""

    @pytest.fixture
    def simple_workflow_definition(self):
        """简单工作流定义"""
        return {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input", "config": {"key": "query"}},
                {"id": "output", "type": "output", "config": {"input_from": "input"}}
            ],
            "edges": [
                {"source": "input", "target": "output"}
            ]
        }

    @pytest.fixture
    def rag_workflow_definition(self):
        """RAG 工作流定义"""
        return {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input", "config": {"key": "query"}},
                {"id": "retriever", "type": "retriever", "config": {"collection": "default", "top_k": 5}},
                {"id": "llm", "type": "llm", "config": {"model": "gpt-4o-mini"}},
                {"id": "output", "type": "output", "config": {"input_from": "llm"}}
            ],
            "edges": [
                {"source": "input", "target": "retriever"},
                {"source": "retriever", "target": "llm"},
                {"source": "llm", "target": "output"}
            ]
        }

    def test_init(self, simple_workflow_definition):
        """测试初始化"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", simple_workflow_definition)

        assert executor.workflow_id == "wf-001"
        assert executor.status == "pending"
        assert len(executor.nodes) == 2
        assert len(executor.edges) == 1
        assert executor.execution_id.startswith("exec-")

    def test_build_graph(self, simple_workflow_definition):
        """测试图构建"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", simple_workflow_definition)

        # 验证邻接表
        assert "input" in executor.adjacency
        assert "output" in executor.adjacency["input"]

        # 验证反向邻接表
        assert "output" in executor.reverse_adjacency
        assert "input" in executor.reverse_adjacency["output"]

    def test_validate_valid_workflow(self, simple_workflow_definition):
        """测试验证有效工作流"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", simple_workflow_definition)
        is_valid, errors = executor.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_version(self):
        """测试验证无效版本"""
        from engine.executor import WorkflowExecutor

        definition = {
            "version": "2.0",  # 不支持的版本
            "nodes": [{"id": "input", "type": "input"}],
            "edges": []
        }

        executor = WorkflowExecutor("wf-001", definition)
        is_valid, errors = executor.validate()

        assert is_valid is False
        assert any("版本" in e for e in errors)

    def test_validate_no_nodes(self):
        """测试验证无节点"""
        from engine.executor import WorkflowExecutor

        definition = {
            "version": "1.0",
            "nodes": [],
            "edges": []
        }

        executor = WorkflowExecutor("wf-001", definition)
        is_valid, errors = executor.validate()

        assert is_valid is False
        assert any("节点" in e for e in errors)

    def test_validate_no_input_node(self):
        """测试验证无输入节点"""
        from engine.executor import WorkflowExecutor

        definition = {
            "version": "1.0",
            "nodes": [
                {"id": "output", "type": "output"}
            ],
            "edges": []
        }

        executor = WorkflowExecutor("wf-001", definition)
        is_valid, errors = executor.validate()

        assert is_valid is False
        assert any("输入节点" in e for e in errors)

    def test_validate_invalid_edge_source(self):
        """测试验证无效边源"""
        from engine.executor import WorkflowExecutor

        definition = {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input"}
            ],
            "edges": [
                {"source": "nonexistent", "target": "input"}
            ]
        }

        executor = WorkflowExecutor("wf-001", definition)
        is_valid, errors = executor.validate()

        assert is_valid is False
        assert any("源节点不存在" in e for e in errors)

    def test_topological_sort(self, rag_workflow_definition):
        """测试拓扑排序"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", rag_workflow_definition)
        order = executor._topological_sort()

        # 验证顺序正确
        assert order.index("input") < order.index("retriever")
        assert order.index("retriever") < order.index("llm")
        assert order.index("llm") < order.index("output")

    def test_topological_sort_cycle_detection(self):
        """测试拓扑排序循环检测"""
        from engine.executor import WorkflowExecutor

        # 创建有循环的工作流
        definition = {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input"},
                {"id": "a", "type": "transform"},
                {"id": "b", "type": "transform"}
            ],
            "edges": [
                {"source": "input", "target": "a"},
                {"source": "a", "target": "b"},
                {"source": "b", "target": "a"}  # 循环
            ]
        }

        executor = WorkflowExecutor("wf-001", definition)

        with pytest.raises(ValueError, match="循环"):
            executor._topological_sort()

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self, simple_workflow_definition):
        """测试执行简单工作流"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", simple_workflow_definition)

        result = await executor.execute({"query": "test input"})

        assert result["status"] == "completed"
        assert "execution_id" in result
        assert executor.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_invalid_workflow(self):
        """测试执行无效工作流"""
        from engine.executor import WorkflowExecutor

        definition = {
            "version": "2.0",  # 无效版本
            "nodes": [],
            "edges": []
        }

        executor = WorkflowExecutor("wf-001", definition)
        result = await executor.execute({})

        assert result["status"] == "failed"
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_execute_with_node_error(self):
        """测试执行时节点错误"""
        from engine.executor import WorkflowExecutor
        from engine.nodes import register_node_type, BaseNode

        # 创建一个会失败的节点类型
        class FailingNode(BaseNode):
            async def execute(self, context):
                raise Exception("Node execution failed")

        register_node_type("failing", FailingNode)

        definition = {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input"},
                {"id": "fail", "type": "failing"},
                {"id": "output", "type": "output", "config": {"input_from": "fail"}}
            ],
            "edges": [
                {"source": "input", "target": "fail"},
                {"source": "fail", "target": "output"}
            ]
        }

        executor = WorkflowExecutor("wf-001", definition)
        result = await executor.execute({})

        assert result["status"] == "failed"
        assert "fail" in result.get("node_results", {})
        assert result["node_results"]["fail"]["status"] == "error"

    def test_get_status(self, simple_workflow_definition):
        """测试获取状态"""
        from engine.executor import WorkflowExecutor

        executor = WorkflowExecutor("wf-001", simple_workflow_definition)
        status = executor.get_status()

        assert status["workflow_id"] == "wf-001"
        assert status["status"] == "pending"
        assert status["started_at"] is None
        assert status["completed_at"] is None

    def test_parse_definition_valid(self):
        """测试解析有效定义"""
        from engine.executor import WorkflowExecutor

        json_str = '{"version": "1.0", "nodes": [], "edges": []}'
        result = WorkflowExecutor.parse_definition(json_str)

        assert result["version"] == "1.0"

    def test_parse_definition_invalid(self):
        """测试解析无效定义"""
        from engine.executor import WorkflowExecutor

        with pytest.raises(ValueError, match="无效的工作流定义"):
            WorkflowExecutor.parse_definition("invalid json")


class TestExecutionManagement:
    """执行管理函数测试"""

    def test_register_and_get_execution(self):
        """测试注册和获取执行"""
        from engine.executor import (
            WorkflowExecutor,
            register_execution,
            get_execution,
            unregister_execution
        )

        definition = {"version": "1.0", "nodes": [{"id": "input", "type": "input"}], "edges": []}
        executor = WorkflowExecutor("wf-001", definition)

        register_execution(executor)

        retrieved = get_execution(executor.execution_id)
        assert retrieved is executor

        unregister_execution(executor.execution_id)

        assert get_execution(executor.execution_id) is None

    def test_stop_execution(self):
        """测试停止执行"""
        from engine.executor import (
            WorkflowExecutor,
            register_execution,
            stop_execution,
            get_execution
        )

        definition = {"version": "1.0", "nodes": [{"id": "input", "type": "input"}], "edges": []}
        executor = WorkflowExecutor("wf-001", definition)

        register_execution(executor)

        result = stop_execution(executor.execution_id)

        assert result is True
        assert executor.status == "stopped"
        assert get_execution(executor.execution_id) is None

    def test_stop_nonexistent_execution(self):
        """测试停止不存在的执行"""
        from engine.executor import stop_execution

        result = stop_execution("nonexistent-id")
        assert result is False
