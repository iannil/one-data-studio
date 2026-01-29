"""
节点执行器
支持节点类型：input, retriever, llm, output, agent, tool_call, condition, loop
Phase 6: Sprint 6.1 - 扩展节点 (http, filter, database)
Phase 7: Sprint 7.1-7.2 - Agent 编排与控制流
"""

import json
import logging
import os
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL") or os.getenv("CUBE_API_URL", "http://vllm-serving:8000")

# 导入向量检索服务
try:
    from ..services.vector_store import VectorStore
    from ..services.embedding import EmbeddingService
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# 导入 Agent 相关模块
try:
    from .agents import create_agent, get_tool_registry
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

# 导入控制流节点
try:
    from .control_flow import CONTROL_FLOW_NODES
    CONTROL_FLOW_AVAILABLE = True
except ImportError:
    CONTROL_FLOW_AVAILABLE = False

# 导入扩展节点 (Phase 6: Sprint 6.1)
try:
    from .extension_nodes import EXTENSION_NODES
    EXTENSION_NODES_AVAILABLE = True
except ImportError:
    EXTENSION_NODES_AVAILABLE = False


class BaseNode(ABC):
    """节点基类"""

    def __init__(self, node_id: str, node_type: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config or {}

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行节点逻辑

        Args:
            context: 执行上下文，包含前面节点的输出

        Returns:
            节点执行结果，将合并到上下文中
        """
        raise NotImplementedError

    def validate(self) -> bool:
        """验证节点配置"""
        return True


class InputNode(BaseNode):
    """输入节点 - 接收外部输入"""

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "input", config)
        self.input_key = config.get("key", "input")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """返回输入数据"""
        # 从初始输入中获取数据
        initial_input = context.get("_initial_input", {})
        value = initial_input.get(self.input_key, initial_input.get("query", ""))
        return {self.node_id: {"value": value}}


class RetrieverNode(BaseNode):
    """检索节点 - 从向量数据库检索文档

    配置参数：
    - collection: 向量集合名称 (默认: documents)
    - top_k: 返回结果数量 (默认: 5)
    - query_from: 查询文本来源 (默认: input)
    - score_threshold: 相似度阈值 (可选，过滤低相关结果)
    - alert_on_fallback: 是否在降级时发送告警 (默认: True)
    """

    # 降级告警计数器（用于避免告警风暴）
    _fallback_count = 0
    _fallback_alert_threshold = 10  # 每 N 次降级发送一次汇总告警
    _services_initialized = False
    _shared_vector_store = None
    _shared_embedding_service = None

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "retriever", config)
        self.collection_name = config.get("collection", "documents")
        self.top_k = config.get("top_k", 5)
        self.query_key = config.get("query_from", "input")
        self.score_threshold = config.get("score_threshold", 0.0)
        self.alert_on_fallback = config.get("alert_on_fallback", True)

        # 初始化向量检索服务（使用类级别共享实例）
        self.vector_store = None
        self.embedding_service = None

        if not RetrieverNode._services_initialized:
            RetrieverNode._initialize_services()

        self.vector_store = RetrieverNode._shared_vector_store
        self.embedding_service = RetrieverNode._shared_embedding_service

    @classmethod
    def _initialize_services(cls):
        """类级别初始化向量服务，确保只初始化一次"""
        cls._services_initialized = True

        if not VECTOR_AVAILABLE:
            logger.warning(
                "向量检索模块未安装。检索请求将使用降级数据响应。"
                "要启用向量检索，请安装 pymilvus 并配置 MILVUS_HOST 环境变量。"
            )
            return

        try:
            cls._shared_vector_store = VectorStore()
            logger.info("向量存储服务初始化成功")
        except Exception as e:
            logger.warning(f"向量存储服务初始化失败: {e}。检索请求将使用降级数据响应。")

        try:
            cls._shared_embedding_service = EmbeddingService()
            logger.info("Embedding 服务初始化成功")
        except Exception as e:
            logger.warning(f"Embedding 服务初始化失败: {e}。检索请求将使用降级数据响应。")

    @classmethod
    def check_services_health(cls) -> Dict[str, Any]:
        """检查向量服务健康状态"""
        health = {
            "vector_available": VECTOR_AVAILABLE,
            "vector_store_initialized": cls._shared_vector_store is not None,
            "embedding_service_initialized": cls._shared_embedding_service is not None,
            "fallback_count": cls._fallback_count,
        }

        if cls._shared_vector_store:
            try:
                vs_health = cls._shared_vector_store.health_check()
                health["vector_store_health"] = vs_health
            except Exception as e:
                health["vector_store_health"] = {"status": "error", "error": str(e)}

        return health

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行检索"""
        # 获取查询文本
        query = self._get_query(context)

        # 如果向量服务不可用，返回模拟数据
        if not self.vector_store or not self.embedding_service:
            self._emit_fallback_alert(
                reason="vector_service_unavailable",
                query=query,
                error="Vector service not initialized"
            )
            return {
                self.node_id: {
                    "query": query,
                    "documents": self._mock_results(query),
                    "fallback": True,
                    "fallback_reason": "vector_service_unavailable",
                    "message": "Vector service not available"
                }
            }

        # 生成查询向量
        try:
            query_embedding = await self.embedding_service.embed_text(query)
        except Exception as e:
            self._emit_fallback_alert(
                reason="embedding_generation_failed",
                query=query,
                error=str(e)
            )
            return {
                self.node_id: {
                    "query": query,
                    "documents": self._mock_results(query),
                    "fallback": True,
                    "fallback_reason": "embedding_generation_failed",
                    "error": str(e)
                }
            }

        # 向量检索
        try:
            results = self.vector_store.search(
                collection_name=self.collection_name,
                query_embedding=query_embedding,
                top_k=self.top_k
            )

            # 应用相似度阈值过滤
            if self.score_threshold > 0:
                results = [
                    r for r in results
                    if r.get("score", 0) >= self.score_threshold
                ]

            return {
                self.node_id: {
                    "query": query,
                    "documents": results,
                    "count": len(results)
                }
            }

        except Exception as e:
            self._emit_fallback_alert(
                reason="vector_search_failed",
                query=query,
                error=str(e)
            )
            return {
                self.node_id: {
                    "query": query,
                    "documents": self._mock_results(query),
                    "fallback": True,
                    "fallback_reason": "vector_search_failed",
                    "error": str(e)
                }
            }

    def _emit_fallback_alert(self, reason: str, query: str, error: str):
        """
        发送降级告警

        Args:
            reason: 降级原因 (vector_service_unavailable, embedding_generation_failed, vector_search_failed)
            query: 查询文本
            error: 错误信息
        """
        if not self.alert_on_fallback:
            return

        RetrieverNode._fallback_count += 1

        # 构建告警上下文
        alert_context = {
            "node_id": self.node_id,
            "collection": self.collection_name,
            "reason": reason,
            "query_length": len(query),
            "error": error,
            "fallback_count": RetrieverNode._fallback_count
        }

        # 始终记录警告日志
        logger.warning(
            f"RetrieverNode 降级告警: reason={reason}, node_id={self.node_id}, "
            f"collection={self.collection_name}, error={error}"
        )

        # 每 N 次降级发送一次汇总告警（防止告警风暴）
        if RetrieverNode._fallback_count % self._fallback_alert_threshold == 0:
            logger.error(
                f"RetrieverNode 降级频繁: 最近 {self._fallback_alert_threshold} 次检索使用了降级数据。"
                f"请检查向量服务状态。最近错误: {error}"
            )

            # 尝试发送指标（如果有监控系统）
            try:
                self._emit_metric("retriever_fallback_total", RetrieverNode._fallback_count, {
                    "reason": reason,
                    "collection": self.collection_name
                })
            except Exception:
                pass  # 指标发送失败不影响主流程

    def _emit_metric(self, metric_name: str, value: int, labels: Dict[str, str]):
        """
        发送指标到监控系统

        Args:
            metric_name: 指标名称
            value: 指标值
            labels: 标签
        """
        # 尝试使用 Prometheus 客户端（如果可用）
        try:
            from prometheus_client import Counter, Gauge
            # 这里可以根据实际监控系统进行扩展
            logger.debug(f"Metric: {metric_name}={value}, labels={labels}")
        except ImportError:
            pass

    def _get_query(self, context: Dict[str, Any]) -> str:
        """获取查询文本"""
        query = ""

        if "." in self.query_key:
            # 支持从其他节点获取，如 "input.value"
            parts = self.query_key.split(".")
            if len(parts) == 2 and parts[0] in context:
                query = context[parts[0]].get(parts[1], "")
        else:
            query = context.get(self.query_key, "")

        if not query:
            query = context.get("_initial_input", {}).get("query", "")

        return query

    def _mock_results(self, query: str) -> List[Dict[str, Any]]:
        """生成模拟检索结果（降级方案）

        注意：此方法仅在向量服务不可用时作为降级方案使用。
        返回的数据是通用的占位内容，不代表真实检索结果。
        """
        logger.info(f"使用降级数据响应检索请求: query_length={len(query)}")
        return [
            {
                "text": f"关于 '{query}' 的检索结果 1：ONE-DATA-STUDIO 是一个企业级 AI 平台。",
                "score": 0.95,
                "is_fallback": True
            },
            {
                "text": f"关于 '{query}' 的检索结果 2：平台包含数据治理、模型训练、应用编排三大模块。",
                "score": 0.87,
                "is_fallback": True
            }
        ][:self.top_k]


class LLMNode(BaseNode):
    """大语言模型节点 - 调用 LLM 生成文本"""

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "llm", config)
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.system_prompt = config.get("system_prompt", "你是一个有用的AI助手。")
        self.input_key = config.get("input_from", "input")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """调用 LLM 生成文本"""
        # 构建输入消息
        user_message = ""
        if "." in self.input_key:
            parts = self.input_key.split(".")
            if len(parts) == 2 and parts[0] in context:
                node_output = context[parts[0]]
                if parts[1] == "documents":
                    # 从检索结果组合上下文
                    docs = node_output.get("documents", [])
                    context_text = "\n".join([d["text"] for d in docs])
                    user_message = f"参考以下上下文回答：\n\n{context_text}"
                else:
                    user_message = str(node_output.get(parts[1], ""))
        else:
            user_message = str(context.get(self.input_key, ""))

        if not user_message:
            user_message = str(context.get("_initial_input", {}).get("query", ""))

        # 调用 LLM API
        try:
            response = requests.post(
                f"{MODEL_API_URL}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})

                return {
                    self.node_id: {
                        "output": content,
                        "tokens": usage.get("total_tokens", 0),
                        "model": self.model
                    }
                }
            else:
                return {
                    self.node_id: {
                        "error": f"LLM API error: {response.status_code}",
                        "output": None
                    }
                }
        except Exception as e:
            return {
                self.node_id: {
                    "error": str(e),
                    "output": None
                }
            }


class OutputNode(BaseNode):
    """输出节点 - 收集并返回最终结果"""

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "output", config)
        self.output_key = config.get("output_key", "result")
        self.input_from = config.get("input_from", "llm")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """收集最终输出"""
        # 从指定节点获取输出
        output_value = ""
        source_node = self.input_from

        if "." in source_node:
            parts = source_node.split(".")
            if len(parts) == 2 and parts[0] in context:
                output_value = context[parts[0]].get(parts[1], "")
        elif source_node in context:
            output_value = context[source_node].get("output", "")

        return {
            self.node_id: {
                "output": output_value,
                "final_result": output_value
            }
        }


class TransformNode(BaseNode):
    """转换节点 - 对数据进行转换处理"""

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "transform", config)
        self.transform_type = config.get("type", "pass_through")
        self.input_from = config.get("input_from", "input")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行转换"""
        input_data = context.get(self.input_from, {})

        if self.transform_type == "pass_through":
            result = input_data
        elif self.transform_type == "extract_documents":
            # 从检索结果提取文档文本
            docs = input_data.get("documents", [])
            result = {"texts": [d["text"] for d in docs]}
        else:
            result = input_data

        return {self.node_id: result}


# ============================================================
# Agent 节点 (Phase 7: Sprint 7.1)
# ============================================================

class AgentNode(BaseNode):
    """Agent 节点 - 执行 ReAct 或 Function Calling Agent

    配置参数：
    - agent_type: Agent 类型 (react, function_calling, plan_execute)
    - model: LLM 模型名称
    - max_iterations: 最大迭代次数
    - input_from: 输入来源节点
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "agent", config)
        self.agent_type = config.get("agent_type", "react")
        self.model = config.get("model", "gpt-4o-mini")
        self.max_iterations = config.get("max_iterations", 10)
        self.input_from = config.get("input_from", "input")

        if AGENT_AVAILABLE:
            self.tool_registry = get_tool_registry()
        else:
            self.tool_registry = None

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent"""
        if not AGENT_AVAILABLE:
            return {
                self.node_id: {
                    "error": "Agent module not available",
                    "output": None
                }
            }

        # 获取输入查询
        query = self._get_input(context)

        if not query:
            return {
                self.node_id: {
                    "error": "No input query found",
                    "output": None
                }
            }

        # 创建 Agent
        agent = create_agent(
            agent_type=self.agent_type,
            model=self.model,
            max_iterations=self.max_iterations,
            tool_registry=self.tool_registry,
            verbose=False
        )

        # 执行 Agent
        result = await agent.run(query)

        return {
            self.node_id: {
                "output": result.get("answer"),
                "agent_type": self.agent_type,
                "iterations": result.get("iterations", 0),
                "steps": result.get("steps", []),
                "success": result.get("success", False),
                "error": result.get("error")
            }
        }

    def _get_input(self, context: Dict[str, Any]) -> str:
        """获取输入查询"""
        if "." in self.input_from:
            parts = self.input_from.split(".")
            if len(parts) == 2 and parts[0] in context:
                return str(context[parts[0]].get(parts[1], ""))

        if self.input_from in context:
            return str(context[self.input_from].get("output", ""))

        return context.get("_initial_input", {}).get("query", "")


class ToolCallNode(BaseNode):
    """工具调用节点 - 单次工具调用

    配置参数：
    - tool_name: 工具名称
    - parameters: 工具参数（可使用变量引用）
    - input_from: 输入来源（用于参数中的变量）
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "tool_call", config)
        self.tool_name = config.get("tool_name", "")
        self.parameters = config.get("parameters", {})
        self.input_from = config.get("input_from", "input")

        if AGENT_AVAILABLE:
            self.tool_registry = get_tool_registry()
        else:
            self.tool_registry = None

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if not AGENT_AVAILABLE:
            return {
                self.node_id: {
                    "error": "Tool registry not available",
                    "output": None
                }
            }

        # 解析参数中的变量引用
        resolved_params = self._resolve_parameters(self.parameters, context)

        # 执行工具
        result = await self.tool_registry.execute(self.tool_name, **resolved_params)

        return {
            self.node_id: {
                "tool": self.tool_name,
                "parameters": resolved_params,
                "output": result,
                "success": result.get("success", False) if isinstance(result, dict) else True
            }
        }

    def _resolve_parameters(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数中的变量引用"""
        import re

        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # 解析变量引用
                var_path = value[2:-2].strip()
                resolved[key] = self._get_value(var_path, context)
            else:
                resolved[key] = value

        return resolved

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """从上下文获取值"""
        parts = path.split(".")

        if parts[0] == "inputs":
            initial_input = context.get("_initial_input", {})
            if len(parts) == 1:
                return initial_input
            return self._get_nested_value(initial_input, parts[1:])

        if parts[0] in context:
            node_output = context[parts[0]]
            if len(parts) == 1:
                return node_output.get("output", node_output)
            return self._get_nested_value(node_output, parts[1:])

        return self._get_nested_value(context, parts)

    def _get_nested_value(self, data: Any, path: List[str]) -> Any:
        """从嵌套结构获取值"""
        current = data
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current


class ThinkNode(BaseNode):
    """思考节点 - 使用 LLM 进行推理

    配置参数：
    - prompt: 提示模板
    - model: 模型名称
    - temperature: 温度参数
    - input_from: 输入来源
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "think", config)
        self.prompt_template = config.get("prompt", "请分析以下内容：{{ input }}")
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.7)
        self.input_from = config.get("input_from", "input")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行思考"""
        # 获取输入
        input_value = self._get_input(context)

        # 构建提示
        prompt = self.prompt_template.replace("{{ input }}", str(input_value))

        # 调用 LLM
        try:
            response = requests.post(
                f"{MODEL_API_URL}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 1000
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                return {
                    self.node_id: {
                        "output": content,
                        "thought": content,
                        "input": input_value
                    }
                }
            else:
                return {
                    self.node_id: {
                        "error": f"LLM API error: {response.status_code}",
                        "output": None
                    }
                }
        except Exception as e:
            return {
                self.node_id: {
                    "error": str(e),
                    "output": None
                }
            }

    def _get_input(self, context: Dict[str, Any]) -> str:
        """获取输入"""
        if "." in self.input_from:
            parts = self.input_from.split(".")
            if len(parts) == 2 and parts[0] in context:
                return str(context[parts[0]].get(parts[1], ""))

        if self.input_from in context:
            return str(context[self.input_from].get("output", ""))

        return context.get("_initial_input", {}).get("query", "")


# 节点工厂函数
NODE_REGISTRY = {
    "input": InputNode,
    "retriever": RetrieverNode,
    "llm": LLMNode,
    "output": OutputNode,
    "transform": TransformNode,
    # Agent 节点 (Phase 7)
    "agent": AgentNode,
    "tool_call": ToolCallNode,
    "think": ThinkNode,
}

# 合并控制流节点
if CONTROL_FLOW_AVAILABLE:
    NODE_REGISTRY.update(CONTROL_FLOW_NODES)

# 合并扩展节点 (Phase 6: Sprint 6.1)
if EXTENSION_NODES_AVAILABLE:
    NODE_REGISTRY.update(EXTENSION_NODES)


def get_node_executor(node: Dict[str, Any]) -> BaseNode:
    """
    根据节点定义创建对应的执行器

    Args:
        node: 节点定义字典

    Returns:
        节点执行器实例
    """
    node_type = node.get("type", "input")
    node_id = node.get("id", "unknown")
    config = node.get("config", {})

    node_class = NODE_REGISTRY.get(node_type)
    if not node_class:
        raise ValueError(f"Unknown node type: {node_type}")

    return node_class(node_id, config)


def register_node_type(node_type: str, node_class: type):
    """注册自定义节点类型"""
    NODE_REGISTRY[node_type] = node_class
