"""
子工作流节点
Sprint 18: 工作流节点扩展

支持在工作流中调用其他工作流
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SubflowNodeConfig:
    """子工作流节点配置"""
    workflow_id: str = ""  # 子工作流 ID
    input_mapping: Dict[str, str] = None  # 输入映射
    output_mapping: Dict[str, str] = None  # 输出映射
    timeout: float = 600.0  # 执行超时
    async_mode: bool = False  # 是否异步执行
    inherit_context: bool = True  # 是否继承父上下文


class SubflowNode:
    """
    子工作流节点
    Sprint 18: 工作流节点扩展

    支持:
    - 调用其他工作流
    - 输入/输出映射
    - 同步/异步执行
    - 上下文继承
    """

    node_type = "subflow"
    name = "SubflowNode"
    description = "调用子工作流"

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化子工作流节点

        Args:
            config: 节点配置
        """
        self.config = SubflowNodeConfig(
            workflow_id=config.get("workflow_id", ""),
            input_mapping=config.get("input_mapping", {}),
            output_mapping=config.get("output_mapping", {}),
            timeout=config.get("timeout", 600.0),
            async_mode=config.get("async_mode", False),
            inherit_context=config.get("inherit_context", True),
        ) if config else SubflowNodeConfig()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        executor = None
    ) -> Dict[str, Any]:
        """
        执行子工作流

        Args:
            input_data: 输入数据
            context: 执行上下文
            executor: 工作流执行器

        Returns:
            执行结果
        """
        if not self.config.workflow_id:
            return {
                "success": False,
                "error": "Workflow ID is required"
            }

        if not executor:
            return {
                "success": False,
                "error": "Executor is required for subflow execution"
            }

        logger.info(f"Executing subflow: {self.config.workflow_id}")

        try:
            # 应用输入映射
            mapped_input = self._apply_input_mapping(input_data)

            # 准备子工作流上下文
            subflow_context = {}
            if self.config.inherit_context and context:
                subflow_context.update(context)

            subflow_context["parent_workflow_id"] = context.get("workflow_id") if context else None
            subflow_context["parent_execution_id"] = context.get("execution_id") if context else None

            # 执行子工作流
            if self.config.async_mode:
                # 异步执行（启动后立即返回）
                execution_id = await executor.start_workflow_async(
                    self.config.workflow_id,
                    mapped_input,
                    subflow_context
                )
                return {
                    "success": True,
                    "async": True,
                    "execution_id": execution_id,
                    "workflow_id": self.config.workflow_id
                }
            else:
                # 同步执行（等待完成）
                import asyncio
                result = await asyncio.wait_for(
                    executor.execute_workflow(
                        self.config.workflow_id,
                        mapped_input,
                        subflow_context
                    ),
                    timeout=self.config.timeout
                )

                # 应用输出映射
                if result.get("success") and self.config.output_mapping:
                    result["output"] = self._apply_output_mapping(result.get("output", {}))

                return {
                    "success": result.get("success", False),
                    "async": False,
                    "workflow_id": self.config.workflow_id,
                    "output": result.get("output"),
                    "error": result.get("error"),
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Subflow execution timeout after {self.config.timeout}s"
            }
        except Exception as e:
            logger.exception(f"Subflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _apply_input_mapping(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用输入映射"""
        if not self.config.input_mapping:
            return input_data

        mapped = {}
        for target_key, source_key in self.config.input_mapping.items():
            if source_key in input_data:
                mapped[target_key] = input_data[source_key]

        # 保留未映射的字段
        for key, value in input_data.items():
            if key not in mapped:
                mapped[key] = value

        return mapped

    def _apply_output_mapping(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用输出映射"""
        if not self.config.output_mapping:
            return output_data

        mapped = {}
        for target_key, source_key in self.config.output_mapping.items():
            if source_key in output_data:
                mapped[target_key] = output_data[source_key]

        return mapped

    def get_schema(self) -> Dict[str, Any]:
        """获取节点 schema"""
        return {
            "type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": {
                "workflow_id": {
                    "type": "string",
                    "description": "子工作流 ID",
                    "required": True
                },
                "input_mapping": {
                    "type": "object",
                    "description": "输入字段映射",
                },
                "output_mapping": {
                    "type": "object",
                    "description": "输出字段映射",
                },
                "timeout": {
                    "type": "number",
                    "description": "执行超时时间（秒）",
                    "default": 600
                },
                "async_mode": {
                    "type": "boolean",
                    "description": "是否异步执行",
                    "default": False
                },
            },
            "outputs": {
                "success": {"type": "boolean"},
                "output": {"type": "object"},
                "execution_id": {"type": "string"},
            }
        }
