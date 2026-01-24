"""
工具定义和注册系统
Phase 7: Sprint 7.1

支持工具定义、注册和执行
"""

import json
import os
import re
import requests
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

# 配置
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://vllm-serving:8000")
ALDATA_API_URL = os.getenv("ALDATA_API_URL", "http://alldata-api:8080")


class ToolSchema:
    """工具参数定义"""

    def __init__(self, name: str, type_: str, description: str = "", required: bool = False, default: Any = None):
        self.name = name
        self.type = type_
        self.description = description
        self.required = required
        self.default = default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default
        }


class BaseTool(ABC):
    """工具基类"""

    name: str = "base_tool"
    description: str = "基础工具"
    parameters: List[ToolSchema] = []

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        raise NotImplementedError

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 OpenAI Function Calling 格式 schema"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证参数"""
        errors = []
        for param in self.parameters:
            if param.required and param.name not in params:
                errors.append(f"Missing required parameter: {param.name}")
        return len(errors) == 0, errors


class VectorSearchTool(BaseTool):
    """向量搜索工具"""

    name = "vector_search"
    description = "从向量数据库中搜索相关文档。用于检索知识库中的信息。"
    parameters = [
        ToolSchema("query", "string", "搜索查询文本", required=True),
        ToolSchema("collection", "string", "集合名称", required=False, default="default"),
        ToolSchema("top_k", "integer", "返回结果数量", required=False, default=5)
    ]

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        from ..services import VectorStore, EmbeddingService
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()

    async def execute(self, query: str, collection: str = "default", top_k: int = 5) -> Dict[str, Any]:
        """执行向量搜索"""
        try:
            # 生成查询向量
            query_embedding = await self.embedding_service.embed_text(query)

            # 搜索
            results = self.vector_store.search(collection, query_embedding, top_k)

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }


class SQLQueryTool(BaseTool):
    """SQL 查询工具"""

    name = "sql_query"
    description = "执行 SQL 查询。用于查询数据库中的数据。"
    parameters = [
        ToolSchema("sql", "string", "SQL 查询语句", required=True),
        ToolSchema("database", "string", "数据库名称", required=False, default="sales_dw")
    ]

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 可以配置数据库连接
        self.mock_data = self.config.get("mock_data", True)

    async def execute(self, sql: str, database: str = "sales_dw") -> Dict[str, Any]:
        """执行 SQL 查询"""
        try:
            # 安全检查
            sql_upper = sql.upper().strip()
            dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
            if any(keyword in sql_upper for keyword in dangerous_keywords):
                return {
                    "success": False,
                    "error": "Dangerous SQL operation not allowed",
                    "results": []
                }

            if self.mock_data:
                # 模拟数据返回
                if "SELECT" in sql_upper:
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [
                            {"id": 1, "product": "产品A", "sales": 10000, "date": "2024-01-01"},
                            {"id": 2, "product": "产品B", "sales": 15000, "date": "2024-01-01"},
                            {"id": 3, "product": "产品C", "sales": 8000, "date": "2024-01-01"}
                        ],
                        "row_count": 3
                    }
                else:
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [],
                        "row_count": 0
                    }
            else:
                # 真实数据库查询（需要配置连接）
                pass

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }


class HTTPRequestTool(BaseTool):
    """HTTP 请求工具"""

    name = "http_request"
    description = "发送 HTTP 请求。用于调用外部 API。"
    parameters = [
        ToolSchema("url", "string", "请求 URL", required=True),
        ToolSchema("method", "string", "HTTP 方法 (GET, POST, PUT, DELETE)", required=False, default="GET"),
        ToolSchema("headers", "object", "请求头", required=False, default={}),
        ToolSchema("body", "object", "请求体 (JSON)", required=False, default=None),
        ToolSchema("timeout", "integer", "超时时间（秒）", required=False, default=30)
    ]

    async def execute(self, url: str, method: str = "GET", headers: Dict = None,
                     body: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        try:
            headers = headers or {}
            method = method.upper()

            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=body, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported method: {method}"
                }

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "url": url,
                "method": method,
                "headers": dict(response.headers),
                "body": response.text if response.text else None,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class CalculatorTool(BaseTool):
    """计算器工具"""

    name = "calculator"
    description = "执行数学计算。支持基本运算和表达式求值。"
    parameters = [
        ToolSchema("expression", "string", "数学表达式，如 '1 + 1' 或 'sqrt(16)'", required=True)
    ]

    async def execute(self, expression: str) -> Dict[str, Any]:
        """执行计算"""
        try:
            # 安全的数学计算
            import math

            # 只允许安全的数学函数
            safe_dict = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
            }

            # 只允许数字和运算符
            if not re.match(r"^[\d\s+\-*/().a-zA-Z,]+$", expression):
                return {
                    "success": False,
                    "error": "Invalid characters in expression"
                }

            result = eval(expression, {"__builtins__": {}}, safe_dict)

            return {
                "success": True,
                "expression": expression,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "expression": expression
            }


class TextToSQLTool(BaseTool):
    """Text-to-SQL 工具"""

    name = "text_to_sql"
    description = "将自然语言转换为 SQL 查询语句。"
    parameters = [
        ToolSchema("question", "string", "自然语言问题", required=True),
        ToolSchema("database", "string", "数据库名称", required=False, default="sales_dw")
    ]

    async def execute(self, question: str, database: str = "sales_dw") -> Dict[str, Any]:
        """生成 SQL"""
        try:
            schema = """
            orders 表:
            - id: INT (主键)
            - customer_id: INT
            - amount: DECIMAL(10,2)
            - status: VARCHAR(50)
            - created_at: TIMESTAMP

            customers 表:
            - id: INT (主键)
            - name: VARCHAR(255)
            - email: VARCHAR(255)

            products 表:
            - id: INT (主键)
            - name: VARCHAR(255)
            - price: DECIMAL(10,2)
            """

            response = requests.post(
                f"{CUBE_API_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"你是 SQL 生成专家。根据以下数据库元数据生成 SQL 查询：\n数据库：{database}\n{schema}\n\n只返回 SQL 语句，不要包含任何解释。"
                        },
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                sql = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                sql = sql.replace("```sql", "").replace("```", "").strip()

                return {
                    "success": True,
                    "question": question,
                    "sql": sql
                }
            else:
                return {
                    "success": False,
                    "error": f"LLM API error: {response.status_code}",
                    "question": question
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "question": question
            }


class DateTimeTool(BaseTool):
    """日期时间工具"""

    name = "datetime"
    description = "获取当前日期时间或进行日期计算。"
    parameters = [
        ToolSchema("action", "string", "操作类型: current, add, diff, format", required=True),
        ToolSchema("date", "string", "日期字符串 (ISO 格式)，用于 add/diff 操作", required=False),
        ToolSchema("days", "integer", "天数偏移，用于 add 操作", required=False, default=0),
        ToolSchema("format", "string", "日期格式，如 '%Y-%m-%d'", required=False, default="%Y-%m-%d")
    ]

    async def execute(self, action: str, date: str = None, days: int = 0,
                     format: str = "%Y-%m-%d") -> Dict[str, Any]:
        """执行日期时间操作"""
        try:
            from datetime import datetime, timedelta

            if action == "current":
                result = datetime.now().strftime(format)
                return {
                    "success": True,
                    "action": action,
                    "result": result,
                    "iso_format": datetime.now().isoformat()
                }

            elif action == "add":
                if not date:
                    return {"success": False, "error": "date parameter required for add action"}
                base_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
                new_date = base_date + timedelta(days=days)
                return {
                    "success": True,
                    "action": action,
                    "base_date": date,
                    "days_added": days,
                    "result": new_date.strftime(format),
                    "iso_format": new_date.isoformat()
                }

            elif action == "format":
                if not date:
                    return {"success": False, "error": "date parameter required for format action"}
                base_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
                return {
                    "success": True,
                    "action": action,
                    "result": base_date.strftime(format)
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class DataAnalysisTool(BaseTool):
    """数据分析工具"""

    name = "data_analysis"
    description = "对数据集进行简单的统计分析。"
    parameters = [
        ToolSchema("data", "array", "要分析的数据数组", required=True),
        ToolSchema("operation", "string", "操作类型: mean, median, sum, min, max, count, std", required=True)
    ]

    async def execute(self, data: List[float], operation: str) -> Dict[str, Any]:
        """执行数据分析"""
        try:
            import statistics as stats

            if not data:
                return {
                    "success": False,
                    "error": "Data array is empty"
                }

            operations = {
                "mean": lambda d: stats.mean(d),
                "median": lambda d: stats.median(d),
                "sum": lambda d: sum(d),
                "min": lambda d: min(d),
                "max": lambda d: max(d),
                "count": lambda d: len(d),
                "std": lambda d: stats.stdev(d) if len(d) > 1 else 0
            }

            if operation not in operations:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }

            result = operations[operation](data)

            return {
                "success": True,
                "operation": operation,
                "result": result,
                "data_count": len(data)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 工具注册表
DEFAULT_TOOLS = [
    VectorSearchTool,
    SQLQueryTool,
    HTTPRequestTool,
    CalculatorTool,
    TextToSQLTool,
    DateTimeTool,
    DataAnalysisTool,
]


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

        # 注册默认工具
        for tool_class in DEFAULT_TOOLS:
            self.register(tool_class())

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [p.to_dict() for p in tool.parameters]
            }
            for tool in self._tools.values()
        ]

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Function Calling 格式 schema"""
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        tool = self.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool not found: {tool_name}"
            }

        # 验证参数
        is_valid, errors = tool.validate_params(kwargs)
        if not is_valid:
            return {
                "success": False,
                "error": f"Parameter validation failed: {', '.join(errors)}"
            }

        # 执行工具
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局工具注册表
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
