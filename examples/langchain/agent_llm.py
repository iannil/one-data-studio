"""
Agent 平台 LLM 适配器 for LangChain

将 ONE-DATA-STUDIO (Agent 平台) 的 LLM 服务封装为 LangChain 兼容的 LLM 类，
使用户可以在 LangChain 应用中无缝使用平台部署的模型。

用法示例：
    from agent_llm import AgentLLM

    llm = AgentLLM(
        api_base="http://localhost:8000",
        model_name="qwen-7b-chat",
        api_key="your-api-key"
    )

    # 作为 LangChain LLM 使用
    response = llm.invoke("Hello, who are you?")
    print(response)

    # 在 Chain 中使用
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate

    prompt = PromptTemplate.from_template("Tell me a joke about {topic}")
    chain = LLMChain(llm=llm, prompt=prompt)
    result = chain.run(topic="programming")
"""

import os
import logging
from typing import Any, Dict, Iterator, List, Mapping, Optional

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk

logger = logging.getLogger(__name__)


class AgentLLM(LLM):
    """
    Agent 平台 (ONE-DATA-STUDIO) LLM 适配器

    通过 OpenAI 兼容 API 连接到 Agent 平台部署的模型服务。

    Attributes:
        api_base: Agent 平台 API 基础 URL
        model_name: 模型名称
        api_key: API 密钥
        temperature: 采样温度
        max_tokens: 最大生成 token 数
        top_p: Top-p 采样参数
        frequency_penalty: 频率惩罚
        presence_penalty: 存在惩罚
        stop: 停止序列
        timeout: 请求超时时间（秒）
    """

    api_base: str = "http://localhost:8000"
    model_name: str = "default"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    timeout: int = 60
    streaming: bool = False

    def __init__(self, **kwargs: Any):
        """初始化 Agent LLM"""
        super().__init__(**kwargs)

        # 从环境变量获取配置
        if not self.api_base:
            self.api_base = os.getenv("AGENT_API_BASE", "http://localhost:8000")
        if not self.api_key:
            self.api_key = os.getenv("AGENT_API_KEY", os.getenv("OPENAI_API_KEY"))

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型标识"""
        return "agent"

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """返回用于识别此 LLM 的参数"""
        return {
            "api_base": self.api_base,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        调用 LLM 生成文本

        Args:
            prompt: 输入提示
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # 构建请求体 (OpenAI 兼容格式)
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
            "stream": False,
        }

        # 处理停止序列
        stop_sequences = stop or self.stop
        if stop_sequences:
            payload["stop"] = stop_sequences

        try:
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            # 提取生成的文本
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning(f"Unexpected response format: {result}")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise ValueError(f"Agent API request failed: {e}")

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """
        流式调用 LLM

        Args:
            prompt: 输入提示
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数

        Yields:
            生成的文本块
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": True,
        }

        stop_sequences = stop or self.stop
        if stop_sequences:
            payload["stop"] = stop_sequences

        try:
            with requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk_data = json.loads(data)
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        chunk = GenerationChunk(text=content)
                                        if run_manager:
                                            run_manager.on_llm_new_token(content)
                                        yield chunk
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Streaming request failed: {e}")
            raise ValueError(f"Agent streaming request failed: {e}")

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        异步调用 LLM

        Args:
            prompt: 输入提示
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        import aiohttp

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": False,
        }

        stop_sequences = stop or self.stop
        if stop_sequences:
            payload["stop"] = stop_sequences

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return ""

        except aiohttp.ClientError as e:
            logger.error(f"Async API request failed: {e}")
            raise ValueError(f"Agent async API request failed: {e}")


class AgentChatModel:
    """
    Agent 平台 Chat Model 适配器

    用于对话场景，支持多轮对话历史。

    用法示例：
        from agent_llm import AgentChatModel
        from langchain_core.messages import HumanMessage, SystemMessage

        chat = AgentChatModel(
            api_base="http://localhost:8000",
            model_name="qwen-7b-chat"
        )

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is the capital of France?")
        ]

        response = chat.invoke(messages)
    """

    def __init__(
        self,
        api_base: str = "http://localhost:8000",
        model_name: str = "default",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        self.api_base = api_base or os.getenv("AGENT_API_BASE", "http://localhost:8000")
        self.model_name = model_name
        self.api_key = api_key or os.getenv("AGENT_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def invoke(self, messages: List[Dict[str, str]]) -> str:
        """
        调用聊天模型

        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]

        Returns:
            助手回复内容
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # 转换 LangChain 消息格式
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, "type"):
                role = "user" if msg.type == "human" else ("system" if msg.type == "system" else "assistant")
                formatted_messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                formatted_messages.append(msg)

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        response = requests.post(
            f"{self.api_base}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return ""


# 便捷函数
def create_agent_llm(
    api_base: Optional[str] = None,
    model_name: str = "default",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AgentLLM:
    """
    创建 Agent LLM 实例

    Args:
        api_base: API 基础 URL
        model_name: 模型名称
        api_key: API 密钥
        **kwargs: 其他 LLM 参数

    Returns:
        AgentLLM 实例
    """
    return AgentLLM(
        api_base=api_base or os.getenv("AGENT_API_BASE", "http://localhost:8000"),
        model_name=model_name,
        api_key=api_key,
        **kwargs,
    )


if __name__ == "__main__":
    # 简单测试
    llm = AgentLLM(
        api_base="http://localhost:8000",
        model_name="qwen-7b-chat",
    )
    print(f"LLM Type: {llm._llm_type}")
    print(f"Identifying Params: {llm._identifying_params}")
