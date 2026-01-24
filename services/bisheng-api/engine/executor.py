"""
工作流执行器
Phase 6: Sprint 6.1

支持解析和执行简单的工作流定义
"""

import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

from .nodes import get_node_executor, BaseNode


class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, workflow_id: str, definition: Dict[str, Any]):
        """
        初始化执行器

        Args:
            workflow_id: 工作流ID
            definition: 工作流定义（JSON解析后的字典）
        """
        self.workflow_id = workflow_id
        self.definition = definition

        # 解析节点和边
        self.nodes = {n["id"]: n for n in definition.get("nodes", [])}
        self.edges = definition.get("edges", [])

        # 执行状态
        self.execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        self.status = "pending"
        self.context = {}
        self.node_results = {}
        self.errors = []
        self.started_at = None
        self.completed_at = None

        # 构建邻接表
        self._build_graph()

    def _build_graph(self):
        """构建图结构"""
        self.adjacency = defaultdict(list)
        self.reverse_adjacency = defaultdict(list)

        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                self.adjacency[source].append(target)
                self.reverse_adjacency[target].append(source)

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证工作流定义

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 检查版本
        if self.definition.get("version") != "1.0":
            errors.append(f"不支持的版本: {self.definition.get('version')}")

        # 检查节点
        if not self.nodes:
            errors.append("工作流没有定义任何节点")

        # 检查是否有起始节点（input 类型）
        has_input = any(n.get("type") == "input" for n in self.nodes.values())
        if not has_input:
            errors.append("工作流缺少输入节点（input类型）")

        # 检查边的引用
        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and source not in self.nodes:
                errors.append(f"边的源节点不存在: {source}")
            if target and target not in self.nodes:
                errors.append(f"边的目标节点不存在: {target}")

        # 检查孤立节点（除了 input 节点）
        connected = set()
        for edge in self.edges:
            connected.add(edge.get("source"))
            connected.add(edge.get("target"))

        for node_id, node in self.nodes.items():
            if node.get("type") != "input" and node_id not in connected:
                errors.append(f"节点 {node_id} 没有连接到工作流")

        return len(errors) == 0, errors

    def _topological_sort(self) -> List[str]:
        """
        拓扑排序，返回执行顺序

        Returns:
            节点ID列表，按执行顺序排列
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            target = edge.get("target")
            if target:
                in_degree[target] += 1

        # 找到入度为0的节点（应该是input节点）
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for neighbor in self.adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否有环
        if len(result) != len(self.nodes):
            raise ValueError("工作流存在循环依赖")

        return result

    async def execute(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行工作流

        Args:
            inputs: 输入数据

        Returns:
            执行结果
        """
        self.status = "running"
        self.started_at = datetime.now()
        self.context = {"_initial_input": inputs or {}}

        try:
            # 验证工作流
            is_valid, errors = self.validate()
            if not is_valid:
                self.status = "failed"
                self.errors = errors
                self.completed_at = datetime.now()
                return {
                    "execution_id": self.execution_id,
                    "status": "failed",
                    "errors": errors
                }

            # 获取执行顺序
            execution_order = self._topological_sort()

            # 按顺序执行节点
            for node_id in execution_order:
                node_def = self.nodes[node_id]

                try:
                    # 创建节点执行器
                    executor = get_node_executor(node_def)

                    # 执行节点
                    result = await executor.execute(self.context)

                    # 更新上下文
                    self.context.update(result)
                    self.node_results[node_id] = {
                        "status": "success",
                        "result": result
                    }

                except Exception as e:
                    # 节点执行失败
                    self.node_results[node_id] = {
                        "status": "error",
                        "error": str(e)
                    }
                    self.errors.append(f"节点 {node_id} 执行失败: {str(e)}")

                    # 是否继续执行？默认遇到错误停止
                    if node_def.get("config", {}).get("continue_on_error", False):
                        continue
                    else:
                        self.status = "failed"
                        self.completed_at = datetime.now()
                        return {
                            "execution_id": self.execution_id,
                            "status": "failed",
                            "errors": self.errors,
                            "node_results": self.node_results
                        }

            # 执行成功
            self.status = "completed"
            self.completed_at = datetime.now()

            # 收集输出节点结果
            output_result = None
            for node_id, node in self.nodes.items():
                if node.get("type") == "output" and node_id in self.context:
                    output_result = self.context[node_id].get("final_result")

            return {
                "execution_id": self.execution_id,
                "status": "completed",
                "output": output_result,
                "node_results": self.node_results,
                "context": self.context
            }

        except Exception as e:
            self.status = "failed"
            self.errors.append(str(e))
            self.completed_at = datetime.now()
            return {
                "execution_id": self.execution_id,
                "status": "failed",
                "errors": self.errors
            }

    def get_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "node_results": self.node_results,
            "errors": self.errors
        }

    @staticmethod
    def parse_definition(definition_json: str) -> Dict[str, Any]:
        """
        解析工作流定义JSON

        Args:
            definition_json: JSON字符串

        Returns:
            解析后的字典
        """
        try:
            return json.loads(definition_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的工作流定义JSON: {str(e)}")


# 全局执行器存储（用于跟踪运行中的执行）
_running_executions: Dict[str, WorkflowExecutor] = {}


def get_execution(execution_id: str) -> Optional[WorkflowExecutor]:
    """获取运行中的执行器"""
    return _running_executions.get(execution_id)


def register_execution(execution: WorkflowExecutor):
    """注册执行器"""
    _running_executions[execution.execution_id] = execution


def unregister_execution(execution_id: str):
    """注销执行器"""
    if execution_id in _running_executions:
        del _running_executions[execution_id]


def stop_execution(execution_id: str) -> bool:
    """停止执行（标记为取消）"""
    executor = get_execution(execution_id)
    if executor:
        executor.status = "stopped"
        executor.completed_at = datetime.now()
        unregister_execution(execution_id)
        return True
    return False
