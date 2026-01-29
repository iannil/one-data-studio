"""
工具定义和注册系统
Phase 7: Sprint 7.1

支持工具定义、注册和执行
"""

import ast
import json
import logging
import math
import operator
import os
import re
import requests
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL", "http://vllm-serving:8000")
DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:8080")

# SSL verification for HTTP requests
# In production, this should always be True. Only disable for local development with self-signed certs.
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"
if not VERIFY_SSL:
    if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
        raise ValueError(
            "CRITICAL: VERIFY_SSL cannot be disabled in production environment."
        )
    logger.warning(
        "SECURITY WARNING: SSL verification is disabled for HTTP tools. "
        "This should ONLY be used for local development."
    )


class SafeMathEvaluator:
    """安全的数学表达式求值器

    使用 AST 解析而非 eval()，只支持安全的数学运算。
    """

    # 支持的二元运算符
    BINARY_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    # 支持的一元运算符
    UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    # 支持的数学函数
    SAFE_FUNCTIONS = {
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
        "floor": math.floor,
        "ceil": math.ceil,
        "fabs": math.fabs,
    }

    # 支持的常量
    SAFE_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    @classmethod
    def evaluate(cls, expression: str) -> Any:
        """安全地求值数学表达式

        Args:
            expression: 数学表达式字符串

        Returns:
            计算结果

        Raises:
            ValueError: 表达式无效或包含不安全的操作
        """
        try:
            tree = ast.parse(expression, mode='eval')
            return cls._eval_node(tree.body)
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Any:
        """递归求值 AST 节点"""
        if isinstance(node, ast.Constant):
            # Python 3.8+ 使用 ast.Constant
            if isinstance(node.value, (int, float, complex)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        elif isinstance(node, ast.Num):
            # Python 3.7 兼容
            return node.n

        elif isinstance(node, ast.Name):
            # 变量名 - 仅支持常量
            name = node.id
            if name in cls.SAFE_CONSTANTS:
                return cls.SAFE_CONSTANTS[name]
            raise ValueError(f"Unknown variable: {name}")

        elif isinstance(node, ast.BinOp):
            # 二元运算
            op_type = type(node.op)
            if op_type not in cls.BINARY_OPS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            return cls.BINARY_OPS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            # 一元运算
            op_type = type(node.op)
            if op_type not in cls.UNARY_OPS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = cls._eval_node(node.operand)
            return cls.UNARY_OPS[op_type](operand)

        elif isinstance(node, ast.Call):
            # 函数调用
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls are allowed")

            func_name = node.func.id
            if func_name not in cls.SAFE_FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")

            args = [cls._eval_node(arg) for arg in node.args]
            return cls.SAFE_FUNCTIONS[func_name](*args)

        elif isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            # 元组/列表 - 用于 min, max, sum 等
            return [cls._eval_node(elt) for elt in node.elts]

        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")


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
        try:
            from ..services import VectorStore, EmbeddingService
        except ImportError:
            from services import VectorStore, EmbeddingService
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
    """SQL 查询工具 - Production: 使用 AST 解析的安全验证"""

    name = "sql_query"
    description = "执行 SQL 查询。用于查询数据库中的数据。只允许 SELECT 查询，自动添加安全限制。"
    parameters = [
        ToolSchema("sql", "string", "SQL 查询语句", required=True),
        ToolSchema("database", "string", "数据库名称", required=False, default="sales_dw"),
        ToolSchema("timeout", "integer", "查询超时时间（秒）", required=False, default=30),
        ToolSchema("row_limit", "integer", "返回行数限制", required=False, default=1000)
    ]

    # 数据库连接池
    _connection_pools: Dict[str, Any] = {}
    _sql_validator = None

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # Check environment - mock data is not allowed in production
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod"):
            # In production, mock_data must be explicitly disabled
            if self.config.get("mock_data", False):
                raise RuntimeError(
                    "SECURITY: mock_data=True is not allowed in production environment. "
                    "Configure real database connections instead."
                )
            self.mock_data = False
        else:
            self.mock_data = self.config.get("mock_data", True)
        self.db_connections = self.config.get("db_connections", {})

        # 延迟加载 SQL 验证器
        if SQLQueryTool._sql_validator is None:
            try:
                from ..services.sql_validator import get_sql_validator
                SQLQueryTool._sql_validator = get_sql_validator(self.config)
            except ImportError:
                logger.warning("SQL validator module not available, using fallback validation")

    async def execute(self, sql: str, database: str = "sales_dw", timeout: int = 30,
                     row_limit: int = 1000) -> Dict[str, Any]:
        """执行 SQL 查询（带安全验证）"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # 使用增强的 SQL 安全检查器
            if SQLQueryTool._sql_validator:
                # 使用新的验证器
                sanitized_sql, validation_result = SQLQueryTool._sql_validator.sanitize_sql(sql)

                if not validation_result.is_valid:
                    logger.warning(f"SQL validation failed: {validation_result.errors}")
                    return {
                        "success": False,
                        "error": f"SQL 验证失败: {validation_result.errors[0]}",
                        "validation_errors": validation_result.errors,
                        "results": []
                    }

                if validation_result.warnings:
                    logger.info(f"SQL validation warnings: {validation_result.warnings}")

                # 使用清理后的 SQL（包含 LIMIT）
                sql = sanitized_sql

                # 应用请求的行数限制
                if row_limit < SQLQueryTool._sql_validator.max_row_limit:
                    sql = SQLQueryTool._sql_validator.add_limit_if_missing(sql, row_limit)

            else:
                # 回退到基础验证
                validation_result = self._basic_validation(sql)
                if not validation_result["is_valid"]:
                    logger.warning(f"SQL validation failed: {validation_result['error']}")
                    return {
                        "success": False,
                        "error": validation_result["error"],
                        "results": []
                    }
                # 添加基础 LIMIT
                sql = self._add_limit_basic(sql, row_limit)

            if self.mock_data:
                # Double-check production environment (defense in depth)
                env = os.getenv("ENVIRONMENT", "development").lower()
                if env in ("production", "prod"):
                    logger.error("Mock data attempted in production environment!")
                    return {
                        "success": False,
                        "error": "Mock data is not allowed in production",
                        "results": []
                    }

                logger.warning(
                    "SQL query returning mock data. This is only acceptable in development/testing."
                )
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
                # 真实数据库查询
                return await self._execute_real_query(sql, database, timeout)

        except Exception as e:
            logger.error(f"SQL query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def _execute_real_query(self, sql: str, database: str, timeout: int) -> Dict[str, Any]:
        """执行真实数据库查询"""
        import logging
        import asyncio
        logger = logging.getLogger(__name__)

        # 获取数据库连接配置
        db_config = self.db_connections.get(database, {})
        db_type = db_config.get("type", "mysql")

        if not db_config:
            # 尝试从环境变量获取默认数据库配置
            import os
            db_url = os.getenv("DATABASE_URL", "")
            if db_url:
                db_config = {"url": db_url, "type": "mysql"}
            else:
                return {
                    "success": False,
                    "error": f"Database '{database}' not configured",
                    "results": []
                }

        try:
            if db_type == "mysql":
                return await self._execute_mysql(sql, db_config, timeout)
            elif db_type == "postgresql":
                return await self._execute_postgresql(sql, db_config, timeout)
            elif db_type == "sqlite":
                return await self._execute_sqlite(sql, db_config, timeout)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported database type: {db_type}",
                    "results": []
                }
        except asyncio.TimeoutError:
            logger.error(f"SQL query timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Query execution timed out after {timeout} seconds",
                "results": []
            }

    async def _execute_mysql(self, sql: str, config: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """执行 MySQL 查询"""
        import asyncio

        try:
            import aiomysql
        except ImportError:
            return {
                "success": False,
                "error": "aiomysql not installed. Run: pip install aiomysql",
                "results": []
            }

        # 解析连接配置
        if "url" in config:
            # 解析 DATABASE_URL 格式
            import urllib.parse
            parsed = urllib.parse.urlparse(config["url"])
            host = parsed.hostname or "localhost"
            port = parsed.port or 3306
            user = parsed.username or "root"
            password = urllib.parse.unquote(parsed.password or "")
            db = parsed.path.lstrip("/") or "test"
        else:
            host = config.get("host", "localhost")
            port = config.get("port", 3306)
            user = config.get("user", "root")
            password = config.get("password", "")
            db = config.get("database", "test")

        async def run_query():
            conn = await aiomysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=db,
                autocommit=True
            )
            try:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(sql)
                    if sql.strip().upper().startswith("SELECT"):
                        rows = await cursor.fetchall()
                        return {
                            "success": True,
                            "sql": sql,
                            "results": list(rows),
                            "row_count": len(rows)
                        }
                    else:
                        return {
                            "success": True,
                            "sql": sql,
                            "results": [],
                            "row_count": 0,
                            "affected_rows": cursor.rowcount
                        }
            finally:
                conn.close()

        return await asyncio.wait_for(run_query(), timeout=timeout)

    async def _execute_postgresql(self, sql: str, config: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """执行 PostgreSQL 查询"""
        import asyncio

        try:
            import asyncpg
        except ImportError:
            return {
                "success": False,
                "error": "asyncpg not installed. Run: pip install asyncpg",
                "results": []
            }

        # 解析连接配置
        if "url" in config:
            dsn = config["url"]
        else:
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            user = config.get("user", "postgres")
            password = config.get("password", "")
            db = config.get("database", "postgres")
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{db}"

        async def run_query():
            conn = await asyncpg.connect(dsn)
            try:
                if sql.strip().upper().startswith("SELECT"):
                    rows = await conn.fetch(sql)
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    result = await conn.execute(sql)
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [],
                        "row_count": 0,
                        "affected_rows": int(result.split()[-1]) if result else 0
                    }
            finally:
                await conn.close()

        return await asyncio.wait_for(run_query(), timeout=timeout)

    async def _execute_sqlite(self, sql: str, config: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """执行 SQLite 查询"""
        import sqlite3
        import asyncio

        db_path = config.get("path", ":memory:")

        def run_sync():
            conn = sqlite3.connect(db_path, timeout=timeout)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(sql)
                if sql.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    conn.commit()
                    return {
                        "success": True,
                        "sql": sql,
                        "results": [],
                        "row_count": 0,
                        "affected_rows": cursor.rowcount
                    }
            finally:
                conn.close()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_sync)

    def _basic_validation(self, sql: str) -> Dict[str, Any]:
        """
        基础 SQL 验证（回退方法）

        当 sqlglot 不可用时使用此方法进行基础验证。
        """
        sql_upper = sql.upper().strip()

        # 危险关键词检查
        dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE",
            "INSERT", "UPDATE", "REPLACE", "GRANT", "REVOKE"
        ]
        for keyword in dangerous_keywords:
            if re.search(r"\b" + keyword + r"\b", sql_upper):
                return {
                    "is_valid": False,
                    "error": f"不允许的操作: {keyword}"
                }

        # 确保是 SELECT 查询
        if not re.match(r"^\s*SELECT", sql_upper):
            return {
                "is_valid": False,
                "error": "只允许 SELECT 查询"
            }

        # 注入模式检查
        injection_patterns = [
            r";\s*--", r"';--", r"'\s*OR\s*'.*='", r"1\s*=\s*1\s*OR",
            r"UNION\s+SELECT"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, sql_upper):
                return {
                    "is_valid": False,
                    "error": "检测到潜在 SQL 注入"
                }

        return {"is_valid": True}

    def _add_limit_basic(self, sql: str, limit: int) -> str:
        """基础 LIMIT 添加方法"""
        # 移除结尾分号
        sql_clean = sql.rstrip().rstrip(";").strip()

        # 检查是否已有 LIMIT
        if re.search(r"\bLIMIT\s+\d+", sql_clean, re.IGNORECASE):
            return sql

        return f"{sql_clean} LIMIT {limit};"


class SSRFProtection:
    """SSRF 防护工具

    防止服务端请求伪造攻击，阻止对内网 IP 和敏感服务的访问。
    """

    # 私有 IP 段（RFC 1918 + 特殊地址）
    PRIVATE_IP_RANGES = [
        ("10.0.0.0", "10.255.255.255"),      # 10.0.0.0/8
        ("172.16.0.0", "172.31.255.255"),    # 172.16.0.0/12
        ("192.168.0.0", "192.168.255.255"),  # 192.168.0.0/16
        ("127.0.0.0", "127.255.255.255"),    # 127.0.0.0/8 (localhost)
        ("169.254.0.0", "169.254.255.255"),  # 169.254.0.0/16 (link-local)
        ("0.0.0.0", "0.255.255.255"),        # 0.0.0.0/8
        ("100.64.0.0", "100.127.255.255"),   # 100.64.0.0/10 (Carrier-grade NAT)
        ("192.0.0.0", "192.0.0.255"),        # 192.0.0.0/24 (IETF Protocol)
        ("192.0.2.0", "192.0.2.255"),        # 192.0.2.0/24 (TEST-NET-1)
        ("198.51.100.0", "198.51.100.255"),  # 198.51.100.0/24 (TEST-NET-2)
        ("203.0.113.0", "203.0.113.255"),    # 203.0.113.0/24 (TEST-NET-3)
        ("224.0.0.0", "239.255.255.255"),    # 224.0.0.0/4 (Multicast)
        ("240.0.0.0", "255.255.255.255"),    # 240.0.0.0/4 (Reserved)
    ]

    # 禁止访问的主机名模式
    BLOCKED_HOSTNAMES = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "[::]",
        "metadata.google.internal",       # GCP metadata
        "169.254.169.254",                # AWS/Azure/GCP metadata
        "metadata.azure.com",             # Azure metadata
        "kubernetes.default",             # K8s internal
        "kubernetes.default.svc",
        "kubernetes.default.svc.cluster.local",
    ]

    # 禁止的 URL schemes
    BLOCKED_SCHEMES = ["file", "ftp", "gopher", "data", "javascript"]

    # 允许的域名白名单（可通过环境变量配置）
    _allowed_domains: List[str] = None

    @classmethod
    def get_allowed_domains(cls) -> List[str]:
        """获取允许的域名白名单"""
        if cls._allowed_domains is None:
            env_domains = os.getenv("HTTP_TOOL_ALLOWED_DOMAINS", "")
            if env_domains:
                cls._allowed_domains = [d.strip().lower() for d in env_domains.split(",") if d.strip()]
            else:
                cls._allowed_domains = []
        return cls._allowed_domains

    @classmethod
    def _ip_to_int(cls, ip: str) -> int:
        """将 IP 地址转换为整数"""
        parts = ip.split(".")
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

    @classmethod
    def _is_private_ip(cls, ip: str) -> bool:
        """检查是否为私有 IP"""
        try:
            ip_int = cls._ip_to_int(ip)
            for start, end in cls.PRIVATE_IP_RANGES:
                if cls._ip_to_int(start) <= ip_int <= cls._ip_to_int(end):
                    return True
            return False
        except (ValueError, IndexError):
            return True  # 解析失败时保守处理

    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """
        验证 URL 是否安全

        Args:
            url: 要验证的 URL

        Returns:
            (is_safe, error_message)
        """
        import socket
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)

            # 检查 scheme
            scheme = parsed.scheme.lower()
            if not scheme:
                return False, "URL must have a scheme (http/https)"
            if scheme in cls.BLOCKED_SCHEMES:
                return False, f"URL scheme '{scheme}' is not allowed"
            if scheme not in ["http", "https"]:
                return False, f"Only http/https schemes are allowed, got '{scheme}'"

            # 检查主机名
            hostname = parsed.hostname
            if not hostname:
                return False, "URL must have a hostname"

            hostname_lower = hostname.lower()

            # 检查禁止的主机名
            for blocked in cls.BLOCKED_HOSTNAMES:
                if hostname_lower == blocked or hostname_lower.endswith("." + blocked):
                    return False, f"Access to '{hostname}' is not allowed"

            # 检查白名单（如果配置了）
            allowed = cls.get_allowed_domains()
            if allowed:
                is_allowed = False
                for domain in allowed:
                    if hostname_lower == domain or hostname_lower.endswith("." + domain):
                        is_allowed = True
                        break
                if not is_allowed:
                    return False, f"Domain '{hostname}' is not in the allowed list"

            # 解析 IP 并检查私有地址
            try:
                ip_addresses = socket.gethostbyname_ex(hostname)[2]
                for ip in ip_addresses:
                    if cls._is_private_ip(ip):
                        return False, f"Access to private IP '{ip}' is not allowed (SSRF protection)"
            except socket.gaierror:
                # DNS 解析失败，可能是无效域名
                return False, f"Unable to resolve hostname '{hostname}'"

            return True, ""

        except Exception as e:
            return False, f"URL validation error: {str(e)}"


class HTTPRequestTool(BaseTool):
    """HTTP 请求工具（带 SSRF 防护）"""

    name = "http_request"
    description = "发送 HTTP 请求。用于调用外部 API。注意：出于安全考虑，无法访问内网地址。"
    parameters = [
        ToolSchema("url", "string", "请求 URL（必须是外部可访问的 HTTPS 地址）", required=True),
        ToolSchema("method", "string", "HTTP 方法 (GET, POST, PUT, DELETE)", required=False, default="GET"),
        ToolSchema("headers", "object", "请求头", required=False, default={}),
        ToolSchema("body", "object", "请求体 (JSON)", required=False, default=None),
        ToolSchema("timeout", "integer", "超时时间（秒）", required=False, default=30)
    ]

    async def execute(self, url: str, method: str = "GET", headers: Dict = None,
                     body: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """执行 HTTP 请求（带 SSRF 防护）"""
        try:
            # SSRF 防护检查
            is_safe, error_msg = SSRFProtection.validate_url(url)
            if not is_safe:
                logger.warning(f"SSRF protection blocked request to: {url[:100]} - {error_msg}")
                return {
                    "success": False,
                    "error": f"Request blocked: {error_msg}",
                    "url": url
                }

            headers = headers or {}
            method = method.upper()

            # 限制超时时间
            timeout = min(timeout, 60)

            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False, verify=VERIFY_SSL)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=timeout, allow_redirects=False, verify=VERIFY_SSL)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=body, timeout=timeout, allow_redirects=False, verify=VERIFY_SSL)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout, allow_redirects=False, verify=VERIFY_SSL)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported method: {method}"
                }

            # 处理重定向（需要再次验证目标 URL）
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get("Location")
                if redirect_url:
                    is_safe, error_msg = SSRFProtection.validate_url(redirect_url)
                    if not is_safe:
                        logger.warning(f"SSRF protection blocked redirect to: {redirect_url[:100]}")
                        return {
                            "success": False,
                            "error": f"Redirect blocked: {error_msg}",
                            "url": url,
                            "redirect_url": redirect_url
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

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Request timed out after {timeout} seconds",
                "url": url
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
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
        """执行计算 - 使用安全的 AST 解析而非 eval()"""
        try:
            # 使用安全的数学表达式求值器
            result = SafeMathEvaluator.evaluate(expression)

            return {
                "success": True,
                "expression": expression,
                "result": result
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "expression": expression
            }
        except (ZeroDivisionError, OverflowError, ArithmeticError) as e:
            return {
                "success": False,
                "error": f"Arithmetic error: {e}",
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
                f"{MODEL_API_URL}/v1/chat/completions",
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
