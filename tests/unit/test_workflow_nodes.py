"""
工作流节点单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock
import asyncio


class TestInputNode:
    """InputNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import InputNode

        node = InputNode("input-1", {"key": "query"})

        assert node.node_id == "input-1"
        assert node.node_type == "input"
        assert node.input_key == "query"

    def test_init_default_key(self):
        """测试默认 key"""
        from engine.nodes import InputNode

        node = InputNode("input-1", {})
        assert node.input_key == "input"

    @pytest.mark.asyncio
    async def test_execute(self):
        """测试执行"""
        from engine.nodes import InputNode

        node = InputNode("input-1", {"key": "query"})
        context = {"_initial_input": {"query": "test question"}}

        result = await node.execute(context)

        assert "input-1" in result
        assert result["input-1"]["value"] == "test question"

    @pytest.mark.asyncio
    async def test_execute_fallback_to_query(self):
        """测试回退到 query 字段"""
        from engine.nodes import InputNode

        node = InputNode("input-1", {"key": "nonexistent"})
        context = {"_initial_input": {"query": "fallback value"}}

        result = await node.execute(context)

        assert result["input-1"]["value"] == "fallback value"


class TestOutputNode:
    """OutputNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import OutputNode

        node = OutputNode("output-1", {"input_from": "llm"})

        assert node.node_id == "output-1"
        assert node.input_from == "llm"

    @pytest.mark.asyncio
    async def test_execute(self):
        """测试执行"""
        from engine.nodes import OutputNode

        node = OutputNode("output-1", {"input_from": "llm"})
        context = {
            "llm": {"output": "Generated response"}
        }

        result = await node.execute(context)

        assert result["output-1"]["output"] == "Generated response"
        assert result["output-1"]["final_result"] == "Generated response"

    @pytest.mark.asyncio
    async def test_execute_with_path(self):
        """测试使用路径的执行"""
        from engine.nodes import OutputNode

        node = OutputNode("output-1", {"input_from": "node.value"})
        context = {
            "node": {"value": "path value", "other": "other value"}
        }

        result = await node.execute(context)

        assert result["output-1"]["output"] == "path value"


class TestTransformNode:
    """TransformNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import TransformNode

        node = TransformNode("transform-1", {"type": "extract_documents"})

        assert node.transform_type == "extract_documents"

    @pytest.mark.asyncio
    async def test_execute_pass_through(self):
        """测试透传转换"""
        from engine.nodes import TransformNode

        node = TransformNode("transform-1", {"type": "pass_through", "input_from": "input"})
        context = {"input": {"value": "test data"}}

        result = await node.execute(context)

        assert result["transform-1"] == {"value": "test data"}

    @pytest.mark.asyncio
    async def test_execute_extract_documents(self):
        """测试提取文档转换"""
        from engine.nodes import TransformNode

        node = TransformNode("transform-1", {"type": "extract_documents", "input_from": "retriever"})
        context = {
            "retriever": {
                "documents": [
                    {"text": "doc1"},
                    {"text": "doc2"}
                ]
            }
        }

        result = await node.execute(context)

        assert result["transform-1"]["texts"] == ["doc1", "doc2"]


class TestRetrieverNode:
    """RetrieverNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import RetrieverNode

        node = RetrieverNode("retriever-1", {
            "collection": "my_collection",
            "top_k": 10
        })

        assert node.collection_name == "my_collection"
        assert node.top_k == 10

    @pytest.mark.asyncio
    async def test_execute_fallback(self):
        """测试无向量服务时的降级"""
        from engine.nodes import RetrieverNode

        node = RetrieverNode("retriever-1", {})
        node.vector_store = None
        node.embedding_service = None

        context = {"_initial_input": {"query": "test query"}}
        result = await node.execute(context)

        assert result["retriever-1"]["fallback"] is True
        assert len(result["retriever-1"]["documents"]) > 0

    def test_get_query_from_context(self):
        """测试从上下文获取查询"""
        from engine.nodes import RetrieverNode

        node = RetrieverNode("retriever-1", {"query_from": "input.value"})

        context = {"input": {"value": "query from input"}}
        query = node._get_query(context)

        assert query == "query from input"

    def test_mock_results(self):
        """测试模拟结果"""
        from engine.nodes import RetrieverNode

        node = RetrieverNode("retriever-1", {"top_k": 2})
        results = node._mock_results("test query")

        assert len(results) == 2
        assert all("text" in r for r in results)
        assert all("score" in r for r in results)


class TestLLMNode:
    """LLMNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import LLMNode

        node = LLMNode("llm-1", {
            "model": "gpt-4",
            "temperature": 0.5
        })

        assert node.model == "gpt-4"
        assert node.temperature == 0.5

    @pytest.mark.asyncio
    @patch('engine.nodes.requests.post')
    async def test_execute_success(self, mock_post):
        """测试成功执行"""
        from engine.nodes import LLMNode

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "AI response"}}],
            "usage": {"total_tokens": 100}
        }
        mock_post.return_value = mock_response

        node = LLMNode("llm-1", {"input_from": "input"})
        context = {"input": "User question"}

        result = await node.execute(context)

        assert result["llm-1"]["output"] == "AI response"
        assert result["llm-1"]["tokens"] == 100

    @pytest.mark.asyncio
    @patch('engine.nodes.requests.post')
    async def test_execute_with_documents(self, mock_post):
        """测试使用文档上下文执行"""
        from engine.nodes import LLMNode

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response with context"}}],
            "usage": {"total_tokens": 150}
        }
        mock_post.return_value = mock_response

        node = LLMNode("llm-1", {"input_from": "retriever.documents"})
        context = {
            "retriever": {
                "documents": [
                    {"text": "Context 1"},
                    {"text": "Context 2"}
                ]
            }
        }

        result = await node.execute(context)

        assert result["llm-1"]["output"] == "Response with context"
        # 验证调用包含了文档上下文
        call_args = mock_post.call_args
        assert "Context 1" in str(call_args)

    @pytest.mark.asyncio
    @patch('engine.nodes.requests.post')
    async def test_execute_api_error(self, mock_post):
        """测试 API 错误"""
        from engine.nodes import LLMNode

        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        node = LLMNode("llm-1", {})
        context = {"_initial_input": {"query": "test"}}

        result = await node.execute(context)

        assert "error" in result["llm-1"]
        assert result["llm-1"]["output"] is None


class TestThinkNode:
    """ThinkNode 单元测试"""

    def test_init(self):
        """测试初始化"""
        from engine.nodes import ThinkNode

        node = ThinkNode("think-1", {
            "prompt": "Analyze: {{ input }}",
            "model": "gpt-4"
        })

        assert "{{ input }}" in node.prompt_template
        assert node.model == "gpt-4"

    @pytest.mark.asyncio
    @patch('engine.nodes.requests.post')
    async def test_execute(self, mock_post):
        """测试执行"""
        from engine.nodes import ThinkNode

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Thought: This is interesting"}}]
        }
        mock_post.return_value = mock_response

        node = ThinkNode("think-1", {"input_from": "input"})
        context = {"input": {"output": "Some data to analyze"}}

        result = await node.execute(context)

        assert "thought" in result["think-1"]


class TestNodeFactory:
    """节点工厂测试"""

    def test_get_node_executor_input(self):
        """测试获取输入节点执行器"""
        from engine.nodes import get_node_executor, InputNode

        node_def = {"id": "input-1", "type": "input", "config": {}}
        executor = get_node_executor(node_def)

        assert isinstance(executor, InputNode)

    def test_get_node_executor_output(self):
        """测试获取输出节点执行器"""
        from engine.nodes import get_node_executor, OutputNode

        node_def = {"id": "output-1", "type": "output", "config": {}}
        executor = get_node_executor(node_def)

        assert isinstance(executor, OutputNode)

    def test_get_node_executor_unknown(self):
        """测试获取未知节点执行器"""
        from engine.nodes import get_node_executor

        node_def = {"id": "unknown-1", "type": "unknown_type", "config": {}}

        with pytest.raises(ValueError, match="Unknown node type"):
            get_node_executor(node_def)

    def test_register_custom_node(self):
        """测试注册自定义节点"""
        from engine.nodes import register_node_type, get_node_executor, BaseNode

        class CustomNode(BaseNode):
            async def execute(self, context):
                return {self.node_id: {"custom": True}}

        register_node_type("custom", CustomNode)

        node_def = {"id": "custom-1", "type": "custom", "config": {}}
        executor = get_node_executor(node_def)

        assert isinstance(executor, CustomNode)
