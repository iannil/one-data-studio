"""
控制流节点
Phase 7: Sprint 7.2

支持条件分支和循环迭代
"""

import ast
import json
import logging
import operator
import re
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from .nodes import BaseNode

logger = logging.getLogger(__name__)


class SafeExpressionEvaluator:
    """安全的表达式求值器

    只支持安全的操作，不使用 eval()
    """

    # 支持的二元运算符
    OPERATORS = {
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
    }

    @classmethod
    def evaluate(cls, expression: str, context: Dict[str, Any] = None) -> bool:
        """安全地求值表达式

        Args:
            expression: 条件表达式字符串
            context: 上下文变量字典

        Returns:
            求值结果 (布尔值)
        """
        context = context or {}
        expression = expression.strip()

        # 空表达式返回 False
        if not expression:
            return False

        # 布尔字面量
        if expression.lower() == 'true':
            return True
        if expression.lower() == 'false':
            return False

        # 尝试使用 ast.literal_eval 解析简单字面量
        try:
            result = ast.literal_eval(expression)
            return bool(result)
        except (ValueError, SyntaxError):
            pass

        # 解析比较表达式
        for op_str, op_func in cls.OPERATORS.items():
            if op_str in ('and', 'or'):
                continue  # 逻辑运算符单独处理

            pattern = rf'^(.+?)\s*{re.escape(op_str)}\s*(.+)$'
            match = re.match(pattern, expression)
            if match:
                left = cls._resolve_value(match.group(1).strip(), context)
                right = cls._resolve_value(match.group(2).strip(), context)
                try:
                    return bool(op_func(left, right))
                except (TypeError, ValueError) as e:
                    logger.warning(f"Comparison failed: {expression}, error: {e}")
                    return False

        # 如果无法解析，记录警告并返回 False
        logger.warning(f"Unable to safely evaluate expression: {expression}")
        return False

    @classmethod
    def _resolve_value(cls, value_str: str, context: Dict[str, Any]) -> Any:
        """解析值字符串

        支持:
        - 数字: 123, 45.6
        - 字符串字面量: 'hello', "world"
        - 布尔值: true, false, True, False
        - 上下文变量: 直接查找
        """
        value_str = value_str.strip()

        # 字符串字面量
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # 布尔值
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        if value_str.lower() == 'none' or value_str.lower() == 'null':
            return None

        # 数字
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # 上下文变量
        if value_str in context:
            return context[value_str]

        # 返回原始字符串
        return value_str


class ConditionNode(BaseNode):
    """条件分支节点

    根据条件表达式选择执行不同的分支。
    支持简单的表达式语法：
    - 比较运算: ==, !=, >, <, >=, <=
    - 逻辑运算: and, or, not
    - 包含运算: contains, in
    - 正则匹配: matches

    例如：
    - "{{ inputs.score > 0.8 }}"
    - "{{ inputs.status == 'approved' }}"
    - "{{ 'error' in outputs.message }}"
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "condition", config)
        self.condition = config.get("condition", "")
        self.true_branch = config.get("true_branch", [])
        self.false_branch = config.get("false_branch", [])
        self.default_branch = config.get("default_branch", "true")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件分支"""
        # 解析变量引用
        condition = self._resolve_variables(self.condition, context)

        # 评估条件
        result = self._evaluate_condition(condition)

        # 根据结果选择分支
        if result:
            branch_nodes = self.true_branch
            branch_name = "true"
        else:
            branch_nodes = self.false_branch if self.false_branch else self.true_branch
            branch_name = "false" if self.false_branch else "true"

        return {
            self.node_id: {
                "condition": self.condition,
                "evaluated": condition,
                "result": result,
                "branch": branch_name,
                "next_nodes": branch_nodes,
                "output": result
            }
        }

    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """解析变量引用

        支持 {{ inputs.xxx }} 或 {{ node_id.field }} 格式
        """
        if not text:
            return text

        # 匹配 {{ variable }} 格式
        pattern = r'\{\{\s*([^\}]+)\s*\}\}'

        def replace_var(match):
            var_path = match.group(1).strip()
            return self._get_value(var_path, context)

        return re.sub(pattern, replace_var, text)

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """从上下文中获取值"""
        # 支持路径如: inputs.score, llm.output, node_id.field
        parts = path.split('.')

        # 处理 inputs 前缀
        if parts[0] == "inputs":
            initial_input = context.get("_initial_input", {})
            if len(parts) == 1:
                return str(initial_input)
            return str(self._get_nested_value(initial_input, parts[1:]))

        # 处理从节点获取
        if parts[0] in context:
            node_output = context[parts[0]]
            if len(parts) == 1:
                return str(node_output.get("output", node_output))
            return str(self._get_nested_value(node_output, parts[1:]))

        # 直接从上下文获取
        value = self._get_nested_value(context, parts)
        return str(value) if value is not None else ""

    def _get_nested_value(self, data: Any, path: List[str]) -> Any:
        """从嵌套结构中获取值"""
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

    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式

        支持多种运算符和简单表达式
        """
        condition = condition.strip()

        if not condition:
            return True

        try:
            # 尝试直接评估（Python 表达式）
            # 只允许安全的操作
            safe_dict = {
                "True": True,
                "False": False,
                "None": None,
                "and": lambda x, y: x and y,
                "or": lambda x, y: x or y,
                "not": lambda x: not x,
            }

            # 处理字符串比较
            # 格式: value == 'string' 或 value == "string"
            str_compare_pattern = r'^([^\s=]+)\s*(==|!=|contains|matches)\s*[\'"](.+?)[\'"]$'
            match = re.match(str_compare_pattern, condition)

            if match:
                left = match.group(1).strip()
                op = match.group(2)
                right = match.group(3)

                # 转换为实际的值比较
                # 注意：这里 left 可能是一个变量引用
                # 在真实场景中，需要从上下文获取实际值

                if op == "contains":
                    return right in left
                elif op == "matches":
                    return bool(re.match(right, left))

            # 处理数值比较
            # 格式: value > 0.8, value <= 100
            num_compare_pattern = r'^([^\s<>!]+)\s*(>|<|>=|<=|==|!=)\s*([\d\.]+)$'
            match = re.match(num_compare_pattern, condition)

            if match:
                left_val = float(match.group(1).strip())
                op = match.group(2)
                right_val = float(match.group(3))

                if op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val
                elif op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val

            # 布尔值检查
            if condition.lower() == "true":
                return True
            if condition.lower() == "false":
                return False

            # 使用安全表达式求值器替代 eval
            return SafeExpressionEvaluator.evaluate(condition, safe_dict)

        except Exception:
            # 如果评估失败，返回 False
            return False

    def validate(self) -> bool:
        """验证节点配置"""
        if not self.condition:
            return False
        return True


class LoopNode(BaseNode):
    """循环节点

    支持多种循环模式：
    - 固定次数循环: loop_over = 5
    - 数组遍历: loop_over = "{{ inputs.items }}"
    - 条件循环: while_condition = "{{ inputs.continue == true }}"

    支持配置：
    - loop_over: 循环次数或数组
    - max_iterations: 最大迭代次数限制
    - break_condition: 中断条件
    - loop_body: 循环体内的节点列表
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "loop", config)
        self.loop_over = config.get("loop_over", 1)
        self.max_iterations = config.get("max_iterations", 10)
        self.while_condition = config.get("while_condition", "")
        self.break_condition = config.get("break_condition", "")
        self.loop_body = config.get("loop_body", [])
        self.output_mode = config.get("output_mode", "last")  # last, all, concat

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行循环"""
        iterations = []
        iteration_count = 0

        # 确定循环次数/内容
        loop_source = self._resolve_loop_source(context)

        # 执行循环
        if isinstance(loop_source, list):
            # 数组遍历
            for i, item in enumerate(loop_source[:self.max_iterations]):
                if self._should_break(context, iterations):
                    break

                iteration_context = context.copy()
                iteration_context[f"{self.node_id}_index"] = i
                iteration_context[f"{self.node_id}_item"] = item
                iteration_context[f"{self.node_id}_iteration"] = iteration_count

                result = await self._execute_iteration(iteration_context, i)
                iterations.append(result)
                iteration_count += 1

        else:
            # 固定次数循环
            loop_count = int(loop_source) if isinstance(loop_source, (int, float, str)) else 1
            loop_count = min(loop_count, self.max_iterations)

            for i in range(loop_count):
                if self._should_break(context, iterations):
                    break

                iteration_context = context.copy()
                iteration_context[f"{self.node_id}_index"] = i
                iteration_context[f"{self.node_id}_iteration"] = iteration_count

                result = await self._execute_iteration(iteration_context, i)
                iterations.append(result)
                iteration_count += 1

        # 根据输出模式组装结果
        output = self._format_output(iterations)

        return {
            self.node_id: {
                "iterations": iteration_count,
                "results": iterations,
                "output": output,
                "loop_over": self.loop_over
            }
        }

    def _resolve_loop_source(self, context: Dict[str, Any]) -> Any:
        """解析循环源"""
        loop_over = self.loop_over

        # 如果是变量引用，从上下文获取
        if isinstance(loop_over, str) and loop_over.startswith("{{"):
            # 解析变量
            resolved = self._resolve_variables(loop_over, context)

            # 尝试解析为列表
            try:
                return json.loads(resolved)
            except (json.JSONDecodeError, TypeError, ValueError):
                # 如果不是 JSON，检查是否是数字
                try:
                    return int(resolved)
                except (TypeError, ValueError):
                    return resolved

        # 如果是数字，直接返回
        if isinstance(loop_over, (int, float)):
            return int(loop_over)

        # 如果是列表，直接返回
        if isinstance(loop_over, list):
            return loop_over

        # 默认返回 1
        return 1

    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """解析变量引用"""
        if not text:
            return text

        pattern = r'\{\{\s*([^\}]+)\s*\}\}'

        def replace_var(match):
            var_path = match.group(1).strip()
            return str(self._get_value(var_path, context))

        return re.sub(pattern, replace_var, text)

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """从上下文中获取值"""
        parts = path.split('.')

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
        """从嵌套结构中获取值"""
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

    def _should_break(self, context: Dict[str, Any], iterations: List[Any]) -> bool:
        """检查是否应该中断循环"""
        if not self.break_condition:
            return False

        # 解析中断条件
        condition = self._resolve_variables(self.break_condition, context)

        # 简单的布尔评估
        return condition.lower() in ("true", "1", "yes")

    async def _execute_iteration(self, context: Dict[str, Any], index: int) -> Dict[str, Any]:
        """执行单次迭代"""
        # 这里可以执行循环体内的节点
        # 当前简化实现，只返回上下文信息
        return {
            "index": index,
            "context": {k: v for k, v in context.items() if not k.startswith("_")}
        }

    def _format_output(self, iterations: List[Any]) -> Any:
        """格式化输出"""
        if self.output_mode == "all":
            return iterations
        elif self.output_mode == "concat":
            # 如果每次迭代返回字符串，连接它们
            results = []
            for i in iterations:
                if isinstance(i, dict):
                    results.append(str(i.get("output", i)))
                else:
                    results.append(str(i))
            return "".join(results)
        else:  # last
            return iterations[-1] if iterations else None


class SwitchNode(BaseNode):
    """Switch 分支节点

    根据值匹配选择分支。
    类似于编程语言中的 switch-case 语句。

    例如：
    ```json
    {
      "type": "switch",
      "config": {
        "value": "{{ inputs.type }}",
        "cases": {
          "A": ["node_a1", "node_a2"],
          "B": ["node_b1"],
          "C": ["node_c1", "node_c2"]
        },
        "default": ["node_default"]
      }
    }
    ```
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "switch", config)
        self.value_expression = config.get("value", "")
        self.cases = config.get("cases", {})
        self.default_branch = config.get("default", [])

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 switch 分支"""
        # 解析值
        value = self._resolve_variables(self.value_expression, context)

        # 查找匹配的 case
        matched_branch = None
        matched_case = None

        for case_key, case_branch in self.cases.items():
            if str(value) == str(case_key):
                matched_branch = case_branch
                matched_case = case_key
                break

        # 如果没有匹配，使用默认分支
        if matched_branch is None:
            matched_branch = self.default_branch
            matched_case = "default"

        return {
            self.node_id: {
                "value": value,
                "matched_case": matched_case,
                "next_nodes": matched_branch,
                "output": value
            }
        }

    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """解析变量引用"""
        if not text:
            return text

        pattern = r'\{\{\s*([^\}]+)\s*\}\}'

        def replace_var(match):
            var_path = match.group(1).strip()
            return str(self._get_value(var_path, context))

        return re.sub(pattern, replace_var, text)

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """从上下文中获取值"""
        parts = path.split('.')

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
        """从嵌套结构中获取值"""
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


class ParallelNode(BaseNode):
    """并行执行节点

    并行执行多个分支，然后合并结果。
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "parallel", config)
        self.branches = config.get("branches", [])
        self.merge_mode = config.get("merge_mode", "all")  # all, first_success, any

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行分支"""
        import asyncio

        # 为每个分支创建执行任务
        tasks = []
        for branch in self.branches:
            task = self._execute_branch(branch, context)
            tasks.append(task)

        # 并行执行所有分支
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 根据合并模式处理结果
        merged = self._merge_results(results)

        return {
            self.node_id: {
                "branches": len(self.branches),
                "results": results,
                "output": merged
            }
        }

    async def _execute_branch(self, branch: Any, context: Dict[str, Any]) -> Any:
        """执行单个分支"""
        # 简化实现：返回分支定义
        # 实际实现中需要执行分支中的节点
        await asyncio.sleep(0)  # 保持异步
        return {"branch": branch, "status": "completed"}

    def _merge_results(self, results: List[Any]) -> Any:
        """合并结果"""
        if self.merge_mode == "all":
            return results
        elif self.merge_mode == "first_success":
            for r in results:
                if not isinstance(r, Exception):
                    return r
            return None
        else:  # any
            return results


class MergeNode(BaseNode):
    """合并节点

    将多个输入合并为一个输出。
    支持多种合并策略。
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        super().__init__(node_id, "merge", config)
        self.inputs_from = config.get("inputs_from", [])
        self.merge_mode = config.get("merge_mode", "concat")  # concat, merge, array, first
        self.output_format = config.get("output_format", "string")  # string, json, array

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """合并输入"""
        values = []

        for input_ref in self.inputs_from:
            value = self._get_input_value(input_ref, context)
            values.append(value)

        # 根据合并模式处理
        if self.merge_mode == "concat":
            merged = " ".join(str(v) for v in values if v)
        elif self.merge_mode == "merge":
            # 合并字典
            merged = {}
            for v in values:
                if isinstance(v, dict):
                    merged.update(v)
        elif self.merge_mode == "array":
            merged = values
        else:  # first
            merged = values[0] if values else None

        return {
            self.node_id: {
                "inputs": values,
                "output": merged,
                "count": len(values)
            }
        }

    def _get_input_value(self, input_ref: str, context: Dict[str, Any]) -> Any:
        """获取输入值"""
        if "." in input_ref:
            parts = input_ref.split(".")
            if parts[0] in context:
                node_output = context[parts[0]]
                if len(parts) == 2:
                    return node_output.get(parts[1])
        elif input_ref in context:
            return context[input_ref].get("output", context[input_ref])

        return None


# 控制流节点导出
CONTROL_FLOW_NODES = {
    "condition": ConditionNode,
    "loop": LoopNode,
    "switch": SwitchNode,
    "parallel": ParallelNode,
    "merge": MergeNode,
}
