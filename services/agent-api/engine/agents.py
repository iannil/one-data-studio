"""
ReAct Agent 实现
Phase 7: Sprint 7.1

基于推理-行动循环的 Agent 编排
ReAct: Reasoning + Acting
"""

import json
import logging
import os
import re
import requests
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .base_tools import get_tool_registry, ToolRegistry

logger = logging.getLogger(__name__)

# 配置
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://vllm-serving:8000")

# ReAct Prompt 模板
REACT_PROMPT_TEMPLATE = """你是一个智能助手，可以使用工具来帮助用户完成任务。

请按照以下格式思考和行动：

Thought: 思考当前需要做什么
Action: 工具名称（可选工具：{tool_names}）
Action Input: 工具参数（JSON 格式）

当你获得足够信息时，使用以下格式返回最终答案：

Thought: 我已经获得了足够的信息
Final Answer: 最终答案

可用工具：
{tools_description}

用户问题：{query}

{history}

Thought:"""


class AgentStep:
    """Agent 执行步骤"""

    def __init__(self, step_type: str, content: str, tool_output: Any = None):
        self.step_type = step_type  # thought, action, observation, final, plan, error
        self.content = content
        self.tool_output = tool_output
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.step_type,
            "content": self.content,
            "tool_output": self.tool_output,
            "timestamp": self.timestamp.isoformat()
        }


class StreamingCallback:
    """流式回调类，用于实时发送步骤"""

    def __init__(self):
        self.queue = []

    def emit(self, step_type: str, content: str, tool_output: Any = None):
        """发送一个步骤"""
        step = AgentStep(step_type, content, tool_output)
        self.queue.append(step.to_dict())
        return step

    def get_and_clear(self) -> List[Dict[str, Any]]:
        """获取并清空队列"""
        items = self.queue.copy()
        self.queue.clear()
        return items


class ReActAgent:
    """ReAct 模式 Agent

    实现 Reasoning + Acting 循环：
    1. Thought: 思考当前状态和下一步行动
    2. Action: 选择并执行工具
    3. Observation: 观察工具执行结果
    4. 重复直到可以给出最终答案
    """

    def __init__(
        self,
        llm_api_url: str = None,
        model: str = "gpt-4o-mini",
        max_iterations: int = 10,
        tool_registry: ToolRegistry = None,
        verbose: bool = True
    ):
        self.llm_api_url = llm_api_url or CUBE_API_URL
        self.model = model
        self.max_iterations = max_iterations
        self.tool_registry = tool_registry or get_tool_registry()
        self.verbose = verbose

        # 执行历史
        self.steps: List[AgentStep] = []

    def _build_tools_description(self) -> str:
        """构建工具描述"""
        descriptions = []
        for tool_info in self.tool_registry.list_tools():
            params = ", ".join([f"{p['name']} ({p['type']})" for p in tool_info['parameters']])
            descriptions.append(
                f"- {tool_info['name']}: {tool_info['description']}\n  参数: {params}"
            )
        return "\n".join(descriptions)

    def _get_tool_names(self) -> List[str]:
        """获取可用工具名称列表"""
        return [t['name'] for t in self.tool_registry.list_tools()]

    def _parse_action(self, text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """解析 LLM 输出的 Action

        Returns:
            (tool_name, parameters) 元组
        """
        # 匹配 Action: tool_name
        action_match = re.search(r'Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)', text, re.IGNORECASE)
        if not action_match:
            return None, None

        tool_name = action_match.group(1)

        # 匹配 Action Input: {...}
        input_match = re.search(r'Action Input:\s*(\{.*?\})(?=\n\s*(Thought|Action|Final Answer)|$)', text, re.DOTALL | re.IGNORECASE)
        parameters = {}
        if input_match:
            try:
                parameters = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                # 尝试更宽松的解析
                input_text = input_match.group(1).strip()
                # 移除可能的换行和空格
                input_text = re.sub(r'\s+', ' ', input_text)
                try:
                    parameters = json.loads(input_text)
                except (json.JSONDecodeError, TypeError, ValueError):
                    parameters = {}

        return tool_name, parameters

    def _check_final_answer(self, text: str) -> Optional[str]:
        """检查是否有最终答案"""
        match = re.search(r'Final Answer:\s*(.*?)(?=\n\s*(Thought|Action)|$)', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    async def _call_llm(self, prompt: str, retries: int = 2) -> str:
        """调用 LLM API（异步 + 重试）"""
        last_error = None

        for attempt in range(retries + 1):
            try:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self.llm_api_url}/v1/chat/completions",
                            json={
                                "model": self.model,
                                "messages": [
                                    {"role": "system", "content": "你是一个有帮助的 AI 助手，可以思考和使用工具来解决问题。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "temperature": 0.1,
                                "max_tokens": 1000
                            },
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
                            else:
                                last_error = f"LLM API returned {resp.status}"
                except ImportError:
                    # aiohttp 不可用时回退到同步 requests
                    import asyncio
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, lambda: requests.post(
                        f"{self.llm_api_url}/v1/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "你是一个有帮助的 AI 助手，可以思考和使用工具来解决问题。"},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 1000
                        },
                        timeout=30
                    ))

                    if response.status_code == 200:
                        result = response.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        last_error = f"LLM API returned {response.status_code}"

            except Exception as e:
                last_error = str(e)
                if attempt < retries:
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))  # 递增延迟
                    logger.warning(f"LLM 调用失败 (attempt {attempt + 1}/{retries + 1}): {e}")

        return f"Error: {last_error}"

    def _format_history(self) -> str:
        """格式化执行历史"""
        if not self.steps:
            return ""

        lines = []
        for step in self.steps:
            if step.step_type == "thought":
                lines.append(f"Thought: {step.content}")
            elif step.step_type == "action":
                lines.append(f"Action: {step.content}")
            elif step.step_type == "observation":
                lines.append(f"Observation: {step.content}")

        return "\n".join(lines)

    async def run(self, query: str) -> Dict[str, Any]:
        """执行 ReAct 循环

        Args:
            query: 用户问题

        Returns:
            执行结果字典
        """
        self.steps = []

        tools_description = self._build_tools_description()
        tool_names = ", ".join(self._get_tool_names())

        consecutive_no_action = 0  # 连续无动作计数

        for iteration in range(self.max_iterations):
            # 构建提示
            history = self._format_history()
            prompt = REACT_PROMPT_TEMPLATE.format(
                tool_names=tool_names,
                tools_description=tools_description,
                query=query,
                history=history
            )

            # 调用 LLM
            llm_output = await self._call_llm(prompt)

            if self.verbose:
                logger.debug(f"\n=== Iteration {iteration + 1} ===")
                logger.debug(f"LLM Output:\n{llm_output}")

            # 检查 LLM 是否返回了错误
            if llm_output.startswith("Error:"):
                self.steps.append(AgentStep("error", llm_output))
                return {
                    "success": False,
                    "error": llm_output,
                    "iterations": iteration + 1,
                    "steps": [s.to_dict() for s in self.steps]
                }

            # 检查是否有最终答案
            final_answer = self._check_final_answer(llm_output)
            if final_answer:
                self.steps.append(AgentStep("final", final_answer))

                return {
                    "success": True,
                    "answer": final_answer,
                    "iterations": iteration + 1,
                    "steps": [s.to_dict() for s in self.steps]
                }

            # 解析 Action
            thought_match = re.search(r'Thought:\s*(.*?)(?=\n\s*Action:|Final Answer:|$)', llm_output, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
                self.steps.append(AgentStep("thought", thought))

            tool_name, parameters = self._parse_action(llm_output)

            if tool_name:
                consecutive_no_action = 0
                self.steps.append(AgentStep("action", f"{tool_name}({json.dumps(parameters, ensure_ascii=False)})"))

                # 执行工具
                try:
                    tool_result = await self.tool_registry.execute(tool_name, **parameters)
                except Exception as e:
                    tool_result = {"success": False, "error": f"工具执行异常: {str(e)}"}

                # 格式化观察结果
                if isinstance(tool_result, dict):
                    if tool_result.get("success"):
                        observation = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        observation = f"Error: {tool_result.get('error', 'Unknown error')}"
                else:
                    observation = str(tool_result)

                # 截断过长的观察结果
                if len(observation) > 2000:
                    observation = observation[:2000] + "...(结果已截断)"

                self.steps.append(AgentStep("observation", observation, tool_result))

                if self.verbose:
                    logger.debug(f"Action: {tool_name}")
                    logger.debug(f"Parameters: {parameters}")
                    logger.debug(f"Observation: {observation[:200]}")
            else:
                # LLM 没有给出 Action 也没有给出 Final Answer
                consecutive_no_action += 1
                if consecutive_no_action >= 2:
                    # 如果连续两次无法解析出动作，将 LLM 原始输出作为最终答案
                    clean_output = llm_output.strip()
                    if thought_match:
                        clean_output = thought_match.group(1).strip()
                    self.steps.append(AgentStep("final", clean_output))
                    return {
                        "success": True,
                        "answer": clean_output,
                        "iterations": iteration + 1,
                        "steps": [s.to_dict() for s in self.steps],
                        "note": "LLM 未使用工具，直接返回思考结果"
                    }

        # 达到最大迭代次数
        # 尝试从最后的步骤中提取有用信息
        last_thoughts = [s.content for s in self.steps if s.step_type in ("thought", "observation")]
        fallback_answer = last_thoughts[-1] if last_thoughts else "未能在最大迭代次数内得出结论"

        return {
            "success": False,
            "error": "Max iterations reached",
            "answer": fallback_answer,
            "iterations": self.max_iterations,
            "steps": [s.to_dict() for s in self.steps]
        }

    async def run_stream(self, query: str):
        """流式执行 ReAct 循环，实时 yield 步骤

        Args:
            query: 用户问题

        Yields:
            Agent 执行步骤字典
        """
        self.steps = []

        tools_description = self._build_tools_description()
        tool_names = ", ".join(self._get_tool_names())

        # 发送开始事件
        yield {"type": "start", "message": "开始执行 Agent", "agent_type": "react"}

        consecutive_no_action = 0

        for iteration in range(self.max_iterations):
            # 构建提示
            history = self._format_history()
            prompt = REACT_PROMPT_TEMPLATE.format(
                tool_names=tool_names,
                tools_description=tools_description,
                query=query,
                history=history
            )

            # 发送思考前状态
            yield {"type": "iteration", "iteration": iteration + 1, "max_iterations": self.max_iterations}

            # 调用 LLM
            llm_output = await self._call_llm(prompt)

            # 检查 LLM 错误
            if llm_output.startswith("Error:"):
                self.steps.append(AgentStep("error", llm_output))
                yield {"type": "step", "data": AgentStep("error", llm_output).to_dict()}
                yield {"type": "end", "success": False, "error": llm_output, "iterations": iteration + 1}
                return

            # 检查是否有最终答案
            final_answer = self._check_final_answer(llm_output)
            if final_answer:
                self.steps.append(AgentStep("final", final_answer))
                yield {"type": "step", "data": AgentStep("final", final_answer).to_dict()}
                yield {"type": "end", "success": True, "answer": final_answer, "iterations": iteration + 1}
                return

            # 解析 Thought
            thought_match = re.search(r'Thought:\s*(.*?)(?=\n\s*Action:|Final Answer:|$)', llm_output, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
                self.steps.append(AgentStep("thought", thought))
                yield {"type": "step", "data": AgentStep("thought", thought).to_dict()}

            # 解析 Action
            tool_name, parameters = self._parse_action(llm_output)

            if tool_name:
                consecutive_no_action = 0
                action_str = f"{tool_name}({json.dumps(parameters, ensure_ascii=False)})"
                self.steps.append(AgentStep("action", action_str))
                yield {"type": "step", "data": AgentStep("action", action_str).to_dict()}

                # 执行工具
                yield {"type": "tool_start", "tool": tool_name}

                try:
                    tool_result = await self.tool_registry.execute(tool_name, **parameters)
                except Exception as e:
                    tool_result = {"success": False, "error": f"工具执行异常: {str(e)}"}

                # 格式化观察结果
                if isinstance(tool_result, dict):
                    if tool_result.get("success"):
                        observation = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        observation = f"Error: {tool_result.get('error', 'Unknown error')}"
                else:
                    observation = str(tool_result)

                if len(observation) > 2000:
                    observation = observation[:2000] + "...(结果已截断)"

                self.steps.append(AgentStep("observation", observation, tool_result))
                yield {"type": "step", "data": AgentStep("observation", observation, tool_result).to_dict()}
                yield {"type": "tool_end", "tool": tool_name}
            else:
                consecutive_no_action += 1
                if consecutive_no_action >= 2:
                    clean_output = llm_output.strip()
                    if thought_match:
                        clean_output = thought_match.group(1).strip()
                    self.steps.append(AgentStep("final", clean_output))
                    yield {"type": "step", "data": AgentStep("final", clean_output).to_dict()}
                    yield {"type": "end", "success": True, "answer": clean_output, "iterations": iteration + 1}
                    return

        # 达到最大迭代次数
        yield {"type": "end", "success": False, "error": "Max iterations reached", "iterations": self.max_iterations}


class FunctionCallingAgent:
    """基于 Function Calling 的 Agent

    使用 OpenAI Function Calling API 进行工具调用
    """

    def __init__(
        self,
        llm_api_url: str = None,
        model: str = "gpt-4o-mini",
        max_iterations: int = 10,
        tool_registry: ToolRegistry = None,
        verbose: bool = True
    ):
        self.llm_api_url = llm_api_url or CUBE_API_URL
        self.model = model
        self.max_iterations = max_iterations
        self.tool_registry = tool_registry or get_tool_registry()
        self.verbose = verbose

        self.steps: List[AgentStep] = []

    async def run(self, query: str) -> Dict[str, Any]:
        """执行 Function Calling 循环"""
        self.steps = []

        messages = [
            {"role": "system", "content": "你是一个有帮助的 AI 助手，可以使用工具来帮助用户解决问题。"},
            {"role": "user", "content": query}
        ]

        for iteration in range(self.max_iterations):
            # 调用 LLM
            try:
                response = requests.post(
                    f"{self.llm_api_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": self.tool_registry.get_function_schemas(),
                        "tool_choice": "auto",
                        "temperature": 0.1,
                        "max_tokens": 1000
                    },
                    timeout=30
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"LLM API error: {response.status_code}",
                        "steps": [s.to_dict() for s in self.steps]
                    }

                result = response.json()
                message = result.get("choices", [{}])[0].get("message", {})

                # 记录助手回复
                assistant_message = {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": message.get("tool_calls")
                }
                messages.append(assistant_message)

                tool_calls = message.get("tool_calls")

                # 如果没有工具调用，说明已经有最终答案
                if not tool_calls:
                    final_answer = message.get("content", "")
                    self.steps.append(AgentStep("final", final_answer))

                    return {
                        "success": True,
                        "answer": final_answer,
                        "iterations": iteration + 1,
                        "steps": [s.to_dict() for s in self.steps]
                    }

                # 执行工具调用
                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    function_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

                    self.steps.append(AgentStep("action", f"{function_name}({json.dumps(function_args, ensure_ascii=False)})"))

                    # 执行工具
                    tool_result = await self.tool_registry.execute(function_name, **function_args)

                    # 格式化结果
                    if isinstance(tool_result, dict):
                        observation = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        observation = str(tool_result)

                    self.steps.append(AgentStep("observation", observation, tool_result))

                    # 添加工具响应消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": observation
                    })

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "steps": [s.to_dict() for s in self.steps]
                }

        # 达到最大迭代次数
        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": self.max_iterations,
            "steps": [s.to_dict() for s in self.steps]
        }

    async def run_stream(self, query: str):
        """流式执行 Function Calling 循环，实时 yield 步骤

        Args:
            query: 用户问题

        Yields:
            Agent 执行步骤字典
        """
        self.steps = []

        messages = [
            {"role": "system", "content": "你是一个有帮助的 AI 助手，可以使用工具来帮助用户解决问题。"},
            {"role": "user", "content": query}
        ]

        # 发送开始事件
        yield {"type": "start", "message": "开始执行 Agent", "agent_type": "function_calling"}

        for iteration in range(self.max_iterations):
            # 发送迭代状态
            yield {"type": "iteration", "iteration": iteration + 1, "max_iterations": self.max_iterations}

            # 调用 LLM
            try:
                response = requests.post(
                    f"{self.llm_api_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": self.tool_registry.get_function_schemas(),
                        "tool_choice": "auto",
                        "temperature": 0.1,
                        "max_tokens": 1000
                    },
                    timeout=30
                )

                if response.status_code != 200:
                    yield {"type": "error", "message": f"LLM API error: {response.status_code}"}
                    yield {"type": "end", "success": False, "error": f"LLM API error: {response.status_code}"}
                    return

                result = response.json()
                message = result.get("choices", [{}])[0].get("message", {})

                # 记录助手回复
                assistant_message = {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": message.get("tool_calls")
                }
                messages.append(assistant_message)

                tool_calls = message.get("tool_calls")

                # 如果没有工具调用，说明已经有最终答案
                if not tool_calls:
                    final_answer = message.get("content", "")
                    self.steps.append(AgentStep("final", final_answer))
                    yield {"type": "step", "data": AgentStep("final", final_answer).to_dict()}
                    yield {"type": "end", "success": True, "answer": final_answer, "iterations": iteration + 1}
                    return

                # 执行工具调用
                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    function_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

                    action_str = f"{function_name}({json.dumps(function_args, ensure_ascii=False)})"
                    self.steps.append(AgentStep("action", action_str))
                    yield {"type": "step", "data": AgentStep("action", action_str).to_dict()}

                    # 执行工具
                    yield {"type": "tool_start", "tool": function_name}
                    tool_result = await self.tool_registry.execute(function_name, **function_args)

                    # 格式化结果
                    if isinstance(tool_result, dict):
                        observation = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        observation = str(tool_result)

                    self.steps.append(AgentStep("observation", observation, tool_result))
                    yield {"type": "step", "data": AgentStep("observation", observation, tool_result).to_dict()}
                    yield {"type": "tool_end", "tool": function_name}

                    # 添加工具响应消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": observation
                    })

            except Exception as e:
                yield {"type": "error", "message": str(e)}
                yield {"type": "end", "success": False, "error": str(e)}
                return

        # 达到最大迭代次数
        yield {"type": "end", "success": False, "error": "Max iterations reached", "iterations": self.max_iterations}


class PlanExecuteAgent:
    """计划-执行 Agent

    先制定计划，然后逐步执行计划中的步骤
    """

    def __init__(
        self,
        llm_api_url: str = None,
        model: str = "gpt-4o-mini",
        tool_registry: ToolRegistry = None,
        verbose: bool = True
    ):
        self.llm_api_url = llm_api_url or CUBE_API_URL
        self.model = model
        self.tool_registry = tool_registry or get_tool_registry()
        self.verbose = verbose

        self.steps: List[AgentStep] = []
        self.plan: List[str] = []

    async def _make_plan(self, query: str) -> List[str]:
        """制定执行计划"""
        tools_description = self._build_tools_description()

        prompt = f"""请为以下任务制定一个分步执行计划。

可用工具：
{tools_description}

任务：{query}

请以 JSON 数组格式返回计划步骤，每个步骤是一个简短的描述。
例如：["分析需求", "搜索相关信息", "执行计算", "生成最终答案"]

计划："""

        try:
            response = requests.post(
                f"{self.llm_api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 尝试解析 JSON
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        plan = json.loads(json_match.group(0))
                        if isinstance(plan, list):
                            return [str(step) for step in plan]
                    except json.JSONDecodeError:
                        pass

                # 如果解析失败，按行分割
                lines = content.strip().split('\n')
                plan = []
                for line in lines:
                    line = re.sub(r'^[\d\.\-\*\)]+\s*', '', line.strip())
                    if line and len(line) > 3:
                        plan.append(line)
                return plan[:5]  # 最多5步

        except Exception as e:
            if self.verbose:
                logger.debug(f"Plan generation error: {e}")

        return ["执行任务", "生成答案"]

    def _build_tools_description(self) -> str:
        """构建工具描述"""
        descriptions = []
        for tool_info in self.tool_registry.list_tools():
            params = ", ".join([f"{p['name']} ({p['type']})" for p in tool_info['parameters']])
            descriptions.append(f"- {tool_info['name']}: {tool_info['description']}\n  参数: {params}")
        return "\n".join(descriptions)

    async def run(self, query: str) -> Dict[str, Any]:
        """执行计划-执行流程"""
        self.steps = []

        # 制定计划
        self.plan = await self._make_plan(query)
        self.steps.append(AgentStep("plan", json.dumps(self.plan, ensure_ascii=False)))

        if self.verbose:
            logger.debug(f"\n=== Plan ===")
            for i, step in enumerate(self.plan, 1):
                logger.debug(f"{i}. {step}")

        # 使用 Function Calling Agent 执行
        agent = FunctionCallingAgent(
            llm_api_url=self.llm_api_url,
            model=self.model,
            max_iterations=10,
            tool_registry=self.tool_registry,
            verbose=self.verbose
        )

        result = await agent.run(query)

        # 合并步骤
        self.steps.extend(agent.steps)

        return {
            "success": result.get("success", False),
            "answer": result.get("answer"),
            "error": result.get("error"),
            "plan": self.plan,
            "steps": [s.to_dict() for s in self.steps]
        }

    async def run_stream(self, query: str):
        """流式执行计划-执行流程，实时 yield 步骤

        Args:
            query: 用户问题

        Yields:
            Agent 执行步骤字典
        """
        self.steps = []

        # 发送开始事件
        yield {"type": "start", "message": "开始执行 Agent", "agent_type": "plan_execute"}

        # 制定计划
        yield {"type": "status", "message": "正在制定执行计划..."}
        self.plan = await self._make_plan(query)
        self.steps.append(AgentStep("plan", json.dumps(self.plan, ensure_ascii=False)))
        yield {"type": "step", "data": AgentStep("plan", json.dumps(self.plan, ensure_ascii=False)).to_dict()}

        if self.verbose:
            logger.debug(f"\n=== Plan ===")
            for i, step in enumerate(self.plan, 1):
                logger.debug(f"{i}. {step}")

        # 使用 Function Calling Agent 执行
        agent = FunctionCallingAgent(
            llm_api_url=self.llm_api_url,
            model=self.model,
            max_iterations=10,
            tool_registry=self.tool_registry,
            verbose=self.verbose
        )

        # 流式执行子代理
        async for event in agent.run_stream(query):
            yield event

        # 合并步骤
        self.steps.extend(agent.steps)


# Agent 工厂
def create_agent(
    agent_type: str = "react",
    model: str = "gpt-4o-mini",
    **kwargs
) -> ReActAgent | FunctionCallingAgent | PlanExecuteAgent:
    """创建 Agent 实例

    Args:
        agent_type: Agent 类型 (react, function_calling, plan_execute)
        model: LLM 模型名称
        **kwargs: 其他参数

    Returns:
        Agent 实例
    """
    if agent_type == "react":
        return ReActAgent(model=model, **kwargs)
    elif agent_type == "function_calling":
        return FunctionCallingAgent(model=model, **kwargs)
    elif agent_type == "plan_execute":
        return PlanExecuteAgent(model=model, **kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
