"""
过滤节点
Phase 6: Sprint 6.1

支持基于条件的数据过滤，用于处理工作流中的数据管道。
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Callable

from ..control_flow import SafeExpressionEvaluator

logger = logging.getLogger(__name__)


class FilterNodeImpl:
    """过滤节点实现

    根据指定条件过滤数组或对象中的数据。

    配置参数：
    - input_from: 输入来源节点或字段
    - conditions: 过滤条件列表
      - field: 字段路径 (如: "name", "user.age", "items[0].id")
      - operator: 操作符 (eq, ne, gt, lt, gte, lte, contains, starts_with, ends_with, matches, in, not_in, is_null, is_not_null, is_empty, is_not_empty)
      - value: 比较值（支持变量引用）
      - logic: 条件逻辑 (and, or) - 用于多个条件组合
    - condition_expression: 自定义条件表达式（JavaScript 风格）
    - output_mode: 输出模式 (filtered, count, first, last, all)
    - limit: 最大输出数量

    简单过滤示例：
    ```json
    {
      "type": "filter",
      "config": {
        "input_from": "previous_node",
        "conditions": [
          {"field": "status", "operator": "eq", "value": "active"},
          {"field": "score", "operator": "gte", "value": 80}
        ],
        "logic": "and"
      }
    }
    ```
    """

    # 支持的操作符
    OPERATORS = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: FilterNodeImpl._compare_numeric(a, b, lambda x, y: x > y),
        "lt": lambda a, b: FilterNodeImpl._compare_numeric(a, b, lambda x, y: x < y),
        "gte": lambda a, b: FilterNodeImpl._compare_numeric(a, b, lambda x, y: x >= y),
        "lte": lambda a, b: FilterNodeImpl._compare_numeric(a, b, lambda x, y: x <= y),
        "contains": lambda a, b: b in a if isinstance(a, (str, list)) else False,
        "not_contains": lambda a, b: b not in a if isinstance(a, (str, list)) else True,
        "starts_with": lambda a, b: str(a).startswith(str(b)) if a is not None else False,
        "ends_with": lambda a, b: str(a).endswith(str(b)) if a is not None else False,
        "matches": lambda a, b: bool(re.match(b, str(a))) if a is not None else False,
        "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
        "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
        "is_null": lambda a, b=None: a is None,
        "is_not_null": lambda a, b=None: a is not None,
        "is_empty": lambda a, b=None: a == "" or a == [] or a == {},
        "is_not_empty": lambda a, b=None: a not in ["", [], {}, None],
        "between": lambda a, b: FilterNodeImpl._is_between(a, b),
        "type_eq": lambda a, b: type(a).__name__ == b,
    }

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = "filter"
        self.config = config or {}
        self.input_from = config.get("input_from", "input")
        self.conditions = config.get("conditions", [])
        self.logic = config.get("logic", "and").lower()
        self.condition_expression = config.get("condition_expression", "")
        self.output_mode = config.get("output_mode", "filtered")
        self.limit = config.get("limit", 0)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行过滤"""
        # 获取输入数据
        input_data = self._get_input(context)

        # 确保输入是列表
        if not isinstance(input_data, list):
            if isinstance(input_data, dict):
                input_data = [input_data]
            elif input_data is None:
                input_data = []
            else:
                input_data = [{"value": input_data}]

        # 执行过滤
        filtered_data = await self._filter_items(input_data, context)

        # 应用限制
        if self.limit > 0 and len(filtered_data) > self.limit:
            filtered_data = filtered_data[:self.limit]

        # 根据输出模式格式化结果
        output = self._format_output(filtered_data)

        return {
            self.node_id: {
                "output": output,
                "filtered": filtered_data,
                "count": len(filtered_data),
                "input_count": len(input_data),
                "filtered_count": len(input_data) - len(filtered_data)
            }
        }

    async def _filter_items(self, items: List[Any], context: Dict[str, Any]) -> List[Any]:
        """过滤列表中的项目"""
        if self.condition_expression:
            return await self._filter_by_expression(items, context)

        if not self.conditions:
            return items

        filtered = []
        for item in items:
            if self._matches_conditions(item, context):
                filtered.append(item)

        return filtered

    def _matches_conditions(self, item: Any, context: Dict[str, Any]) -> bool:
        """检查项目是否匹配所有条件"""
        results = []

        for condition in self.conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "eq")
            value = condition.get("value", None)

            # 获取字段值
            field_value = self._get_field_value(item, field)

            # 渲染值中的变量
            if isinstance(value, str):
                value = self._render_value(value, context)

            # 评估条件
            result = self._evaluate_condition(field_value, operator, value)
            results.append(result)

        # 根据逻辑组合结果
        if self.logic == "or":
            return any(results)
        return all(results)

    async def _filter_by_expression(self, items: List[Any], context: Dict[str, Any]) -> List[Any]:
        """使用表达式过滤"""
        filtered = []

        for item in items:
            if self._evaluate_expression(item, context):
                filtered.append(item)

        return filtered

    def _evaluate_expression(self, item: Any, context: Dict[str, Any]) -> bool:
        """评估 JavaScript 风格的表达式 - 使用安全的表达式求值器"""
        if not self.condition_expression:
            return True

        expr = self.condition_expression

        # 替换 item.field 引用
        expr = self._substitute_item_fields(expr, item)

        # 替换 inputs 引用
        expr = self._substitute_inputs(expr, context)

        # 替换运算符为 Python 格式
        expr = expr.replace("&&", " and ").replace("||", " or ").replace("!", " not ")

        try:
            # 使用安全的表达式求值器
            return SafeExpressionEvaluator.evaluate(expr, {})
        except Exception as e:
            logger.warning(f"Failed to evaluate filter expression: {expr}, error: {e}")
            return False

    def _substitute_item_fields(self, expr: str, item: Any) -> str:
        """替换表达式中的 item.field 引用"""
        pattern = r'item\.([a-zA-Z_][a-zA-Z0-9_.]*)'

        def replace_field(match):
            field_path = match.group(1)
            value = self._get_field_value(item, field_path)
            if isinstance(value, str):
                return f'"{value}"'
            return str(value)

        return re.sub(pattern, replace_field, expr)

    def _substitute_inputs(self, expr: str, context: Dict[str, Any]) -> str:
        """替换表达式中的 inputs 引用"""
        pattern = r'inputs\.([a-zA-Z_][a-zA-Z0-9_.]*)'

        def replace_input(match):
            input_path = match.group(1)
            initial_input = context.get("_initial_input", {})
            value = self._get_field_value(initial_input, input_path)
            if isinstance(value, str):
                return f'"{value}"'
            return str(value)

        return re.sub(pattern, replace_input, expr)

    def _get_field_value(self, item: Any, field_path: str) -> Any:
        """从项目中获取字段值"""
        if not field_path:
            return item

        parts = self._parse_field_path(field_path)
        return self._get_nested_value(item, parts)

    def _parse_field_path(self, path: str) -> List[str]:
        """解析字段路径"""
        parts = []
        current = ""

        i = 0
        while i < len(path):
            char = path[i]

            if char == '.':
                if current:
                    parts.append(current)
                    current = ""
                i += 1
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ""
                j = i + 1
                while j < len(path) and path[j] != ']':
                    j += 1
                if j < len(path):
                    index = path[i+1:j].strip('\'"')
                    parts.append(index)
                    i = j + 1
                else:
                    current += char
                    i += 1
            else:
                current += char
                i += 1

        if current:
            parts.append(current)

        return parts

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

    def _evaluate_condition(self, field_value: Any, operator: str, expected_value: Any) -> bool:
        """评估单个条件"""
        operator_func = self.OPERATORS.get(operator)
        if operator_func:
            try:
                return operator_func(field_value, expected_value)
            except Exception:
                return False
        return False

    def _get_input(self, context: Dict[str, Any]) -> Any:
        """获取输入数据"""
        if "." in self.input_from:
            parts = self.input_from.split(".")
            if len(parts) == 2 and parts[0] in context:
                node_output = context[parts[0]]
                return node_output.get(parts[1], [])
        elif self.input_from in context:
            return context[self.input_from].get("output", context[self.input_from])

        return context.get("_initial_input", {}).get("data", [])

    def _render_value(self, value: str, context: Dict[str, Any]) -> Any:
        """渲染值中的变量引用"""
        def replace_var(match):
            var_path = match.group(1).strip()

            if var_path.startswith("inputs."):
                parts = var_path[7:].split(".")
                initial_input = context.get("_initial_input", {})
                return self._get_nested_value(initial_input, parts)

            if "." in var_path:
                parts = var_path.split(".")
                if parts[0] in context:
                    return self._get_nested_value(context[parts[0]], parts[1:])

            return context.get(var_path, "")

        pattern = r'\{\{\s*([^\}]+)\s*\}\}'
        rendered = re.sub(pattern, replace_var, value)

        # 尝试解析为数字或布尔值
        if rendered.isdigit():
            return int(rendered)
        try:
            return float(rendered)
        except ValueError:
            pass

        if rendered.lower() == "true":
            return True
        if rendered.lower() == "false":
            return False

        return rendered

    def _format_output(self, filtered_data: List[Any]) -> Any:
        """根据输出模式格式化结果"""
        if self.output_mode == "filtered":
            return filtered_data
        elif self.output_mode == "count":
            return len(filtered_data)
        elif self.output_mode == "first":
            return filtered_data[0] if filtered_data else None
        elif self.output_mode == "last":
            return filtered_data[-1] if filtered_data else None
        elif self.output_mode == "all":
            return {
                "items": filtered_data,
                "count": len(filtered_data)
            }
        return filtered_data

    @staticmethod
    def _compare_numeric(a: Any, b: Any, comparator: Callable) -> bool:
        """数值比较（处理字符串转数值）"""
        try:
            a_num = float(a) if isinstance(a, (str, int, float)) else 0
            b_num = float(b) if isinstance(b, (str, int, float)) else 0
            return comparator(a_num, b_num)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_between(value: Any, range_values: Any) -> bool:
        """检查值是否在范围内"""
        try:
            num = float(value)
            if isinstance(range_values, (list, tuple)) and len(range_values) >= 2:
                return float(range_values[0]) <= num <= float(range_values[1])
            return False
        except (ValueError, TypeError):
            return False

    def validate(self) -> bool:
        """验证节点配置"""
        if self.condition_expression:
            return True

        if not self.conditions:
            return True

        # 验证条件配置
        for condition in self.conditions:
            if "operator" not in condition:
                return False
            if condition["operator"] not in self.OPERATORS:
                return False

        return True
