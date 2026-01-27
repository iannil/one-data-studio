"""
Agent 执行单元测试
Sprint 12: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock
import json


class TestAgentStep:
    """AgentStep 单元测试"""

    def test_init(self):
        """测试 AgentStep 初始化"""
        from engine.agents import AgentStep

        step = AgentStep("thought", "thinking about something", {"key": "value"})

        assert step.step_type == "thought"
        assert step.content == "thinking about something"
        assert step.tool_output == {"key": "value"}
        assert step.timestamp is not None

    def test_to_dict(self):
        """测试 AgentStep 转换为字典"""
        from engine.agents import AgentStep

        step = AgentStep("action", "running tool", {"result": 42})
        result = step.to_dict()

        assert result["type"] == "action"
        assert result["content"] == "running tool"
        assert result["tool_output"] == {"result": 42}
        assert "timestamp" in result


class TestStreamingCallback:
    """StreamingCallback 单元测试"""

    def test_emit(self):
        """测试 emit 方法"""
        from engine.agents import StreamingCallback

        callback = StreamingCallback()
        step = callback.emit("thought", "test content", {"data": 123})

        assert step.step_type == "thought"
        assert step.content == "test content"
        assert len(callback.queue) == 1

    def test_get_and_clear(self):
        """测试 get_and_clear 方法"""
        from engine.agents import StreamingCallback

        callback = StreamingCallback()
        callback.emit("step1", "content1")
        callback.emit("step2", "content2")

        items = callback.get_and_clear()

        assert len(items) == 2
        assert len(callback.queue) == 0


class TestReActAgent:
    """ReActAgent 单元测试"""

    @pytest.fixture
    def mock_tool_registry(self):
        """创建 mock tool registry"""
        registry = MagicMock()
        registry.list_tools.return_value = [
            {
                "name": "calculator",
                "description": "执行数学计算",
                "parameters": [{"name": "expression", "type": "string"}]
            }
        ]
        registry.get_function_schemas.return_value = []
        return registry

    def test_build_tools_description(self, mock_tool_registry):
        """测试工具描述构建"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)
        description = agent._build_tools_description()

        assert "calculator" in description
        assert "执行数学计算" in description

    def test_get_tool_names(self, mock_tool_registry):
        """测试获取工具名称"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)
        names = agent._get_tool_names()

        assert "calculator" in names

    def test_parse_action_valid(self, mock_tool_registry):
        """测试解析有效的 Action"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)

        text = """Thought: I need to calculate something
Action: calculator
Action Input: {"expression": "1 + 1"}"""

        tool_name, params = agent._parse_action(text)

        assert tool_name == "calculator"
        assert params == {"expression": "1 + 1"}

    def test_parse_action_no_action(self, mock_tool_registry):
        """测试解析无 Action 的文本"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)

        text = "Thought: I'm just thinking"

        tool_name, params = agent._parse_action(text)

        assert tool_name is None
        assert params is None

    def test_check_final_answer_found(self, mock_tool_registry):
        """测试检测最终答案"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)

        text = """Thought: I have the answer now
Final Answer: The result is 42"""

        answer = agent._check_final_answer(text)

        assert answer == "The result is 42"

    def test_check_final_answer_not_found(self, mock_tool_registry):
        """测试未找到最终答案"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)

        text = "Thought: Still thinking..."

        answer = agent._check_final_answer(text)

        assert answer is None

    def test_format_history_empty(self, mock_tool_registry):
        """测试格式化空历史"""
        from engine.agents import ReActAgent

        agent = ReActAgent(tool_registry=mock_tool_registry)
        history = agent._format_history()

        assert history == ""

    def test_format_history_with_steps(self, mock_tool_registry):
        """测试格式化带步骤的历史"""
        from engine.agents import ReActAgent, AgentStep

        agent = ReActAgent(tool_registry=mock_tool_registry)
        agent.steps = [
            AgentStep("thought", "thinking"),
            AgentStep("action", "calculator({})"),
            AgentStep("observation", "result: 2")
        ]

        history = agent._format_history()

        assert "Thought: thinking" in history
        assert "Action: calculator" in history
        assert "Observation: result" in history


class TestFunctionCallingAgent:
    """FunctionCallingAgent 单元测试"""

    @pytest.fixture
    def mock_tool_registry(self):
        """创建 mock tool registry"""
        registry = MagicMock()
        registry.list_tools.return_value = []
        registry.get_function_schemas.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "执行计算",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        }
                    }
                }
            }
        ]
        return registry

    @pytest.mark.asyncio
    @patch('engine.agents.requests.post')
    async def test_run_no_tool_calls(self, mock_post, mock_tool_registry):
        """测试无工具调用的执行"""
        from engine.agents import FunctionCallingAgent

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "The answer is 42",
                    "tool_calls": None
                }
            }]
        }
        mock_post.return_value = mock_response

        agent = FunctionCallingAgent(tool_registry=mock_tool_registry)
        result = await agent.run("What is 40 + 2?")

        assert result["success"] is True
        assert result["answer"] == "The answer is 42"

    @pytest.mark.asyncio
    @patch('engine.agents.requests.post')
    async def test_run_api_error(self, mock_post, mock_tool_registry):
        """测试 API 错误处理"""
        from engine.agents import FunctionCallingAgent

        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        agent = FunctionCallingAgent(tool_registry=mock_tool_registry)
        result = await agent.run("Test query")

        assert result["success"] is False
        assert "error" in result


class TestPlanExecuteAgent:
    """PlanExecuteAgent 单元测试"""

    @pytest.fixture
    def mock_tool_registry(self):
        """创建 mock tool registry"""
        registry = MagicMock()
        registry.list_tools.return_value = []
        registry.get_function_schemas.return_value = []
        return registry

    @pytest.mark.asyncio
    @patch('engine.agents.requests.post')
    async def test_make_plan_success(self, mock_post, mock_tool_registry):
        """测试计划生成成功"""
        from engine.agents import PlanExecuteAgent

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '["Step 1", "Step 2", "Step 3"]'
                }
            }]
        }
        mock_post.return_value = mock_response

        agent = PlanExecuteAgent(tool_registry=mock_tool_registry)
        plan = await agent._make_plan("Test task")

        assert len(plan) == 3
        assert plan[0] == "Step 1"

    @pytest.mark.asyncio
    @patch('engine.agents.requests.post')
    async def test_make_plan_fallback(self, mock_post, mock_tool_registry):
        """测试计划生成失败时的回退"""
        from engine.agents import PlanExecuteAgent

        mock_post.side_effect = Exception("Connection error")

        agent = PlanExecuteAgent(tool_registry=mock_tool_registry)
        plan = await agent._make_plan("Test task")

        # 应该返回默认计划
        assert len(plan) >= 1


class TestCreateAgent:
    """Agent 工厂测试"""

    @pytest.fixture
    def mock_tool_registry(self):
        """创建 mock tool registry"""
        registry = MagicMock()
        registry.list_tools.return_value = []
        registry.get_function_schemas.return_value = []
        return registry

    def test_create_react_agent(self, mock_tool_registry):
        """测试创建 ReAct Agent"""
        from engine.agents import create_agent, ReActAgent

        agent = create_agent("react", tool_registry=mock_tool_registry)
        assert isinstance(agent, ReActAgent)

    def test_create_function_calling_agent(self, mock_tool_registry):
        """测试创建 Function Calling Agent"""
        from engine.agents import create_agent, FunctionCallingAgent

        agent = create_agent("function_calling", tool_registry=mock_tool_registry)
        assert isinstance(agent, FunctionCallingAgent)

    def test_create_plan_execute_agent(self, mock_tool_registry):
        """测试创建 Plan Execute Agent"""
        from engine.agents import create_agent, PlanExecuteAgent

        agent = create_agent("plan_execute", tool_registry=mock_tool_registry)
        assert isinstance(agent, PlanExecuteAgent)

    def test_create_unknown_agent(self):
        """测试创建未知类型 Agent"""
        from engine.agents import create_agent

        with pytest.raises(ValueError) as exc_info:
            create_agent("unknown_type")

        assert "Unknown agent type" in str(exc_info.value)
