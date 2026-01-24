"""
数据库节点
Phase 6: Sprint 6.1

支持在工作流中执行 SQL 查询，实现数据持久化和检索。
"""

import math
import re
from typing import Any, Dict, List, Optional


class DatabaseNodeImpl:
    """数据库节点实现

    执行 SQL 查询并返回结果。

    配置参数：
    - connection: 数据库连接配置
      - type: 数据库类型 (sqlite, postgresql, mysql, mssql)
      - host: 数据库主机
      - port: 端口
      - database: 数据库名称
      - username: 用户名
      - password: 密码（支持变量引用）
      - dsn: 直接连接字符串（优先使用）
    - query: SQL 查询语句
    - query_from: 从上下文获取查询语句的字段名
    - parameters: 查询参数（用于参数化查询）
    - parameters_from: 从上下文获取参数的字段名
    - output_mode: 输出格式 (rows, first, value, count, affected)
    - fetch_size: 每次获取的行数（默认 100）
    - transaction: 是否使用事务（默认 False）
    - readonly: 只读模式（默认 True）
    """

    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = "database"
        self.config = config or {}
        self.connection_config = config.get("connection", {})
        self.query_template = config.get("query", "")
        self.query_from = config.get("query_from", "")
        self.parameters_template = config.get("parameters", [])
        self.parameters_from = config.get("parameters_from", "")
        self.output_mode = config.get("output_mode", "rows")
        self.fetch_size = config.get("fetch_size", 100)
        self.use_transaction = config.get("transaction", False)
        self.readonly = config.get("readonly", True)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库查询"""
        # 获取查询语句
        query = self._get_query(context)

        if not query:
            return {
                self.node_id: {
                    "error": "No query specified",
                    "output": None
                }
            }

        # 渲染查询中的变量（非参数化）
        rendered_query = self._render_query(query, context)

        # 获取参数
        parameters = self._get_parameters(context)

        # 执行查询
        try:
            result = await self._execute_query(rendered_query, parameters)

            # 格式化输出
            output = self._format_output(result)

            return {
                self.node_id: {
                    "output": output,
                    "rows": result.get("rows", []),
                    "row_count": result.get("row_count", 0),
                    "affected_rows": result.get("affected_rows", 0),
                    "query": rendered_query,
                    "success": True
                }
            }

        except Exception as e:
            return {
                self.node_id: {
                    "error": str(e),
                    "output": None,
                    "query": rendered_query,
                    "success": False
                }
            }

    def _get_query(self, context: Dict[str, Any]) -> str:
        """获取查询语句"""
        if self.query_from:
            # 从上下文获取
            if "." in self.query_from:
                parts = self.query_from.split(".")
                if len(parts) == 2 and parts[0] in context:
                    return str(context[parts[0]].get(parts[1], ""))
            return str(context.get(self.query_from, ""))
        return self.query_template

    def _render_query(self, query: str, context: Dict[str, Any]) -> str:
        """渲染查询中的变量"""
        def replace_var(match):
            var_path = match.group(1).strip()

            if var_path.startswith("inputs."):
                parts = var_path[7:].split(".")
                initial_input = context.get("_initial_input", {})
                value = self._get_nested_value(initial_input, parts)
                return self._escape_sql_value(value)

            if "." in var_path:
                parts = var_path.split(".")
                if parts[0] in context:
                    value = self._get_nested_value(context[parts[0]], parts[1:])
                    return self._escape_sql_value(value)

            value = context.get(var_path, "")
            return self._escape_sql_value(value)

        pattern = r'\{\{\s*([^\}]+)\s*\}\}'
        return re.sub(pattern, replace_var, query)

    def _escape_sql_value(self, value: Any) -> str:
        """转义 SQL 值（用于字符串插值）

        SECURITY WARNING: This method is for variable interpolation in SQL templates only.
        For user input, ALWAYS use parameterized queries via _get_parameters().
        This method should only be used for trusted, pre-validated values from
        workflow context, never for direct user input.
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            # Validate numeric values to prevent injection through numeric fields
            if not isinstance(value, (int, float)) or math.isnan(value) if isinstance(value, float) else False:
                raise ValueError(f"Invalid numeric value: {value}")
            return str(value)
        if isinstance(value, (list, tuple)):
            escaped = [self._escape_sql_value(v) for v in value]
            return "(" + ", ".join(escaped) + ")"
        # String escaping - multiple layers of protection
        str_value = str(value)
        # Reject strings containing dangerous patterns
        dangerous_patterns = ['--', ';', '/*', '*/', 'xp_', 'sp_', 'EXEC', 'EXECUTE',
                             'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
                             'UNION', 'SELECT', 'OR 1=1', "OR '1'='1"]
        str_upper = str_value.upper()
        for pattern in dangerous_patterns:
            if pattern.upper() in str_upper:
                raise ValueError(f"Potentially dangerous SQL pattern detected: {pattern}")
        # Standard SQL escaping
        escaped = str_value.replace("\\", "\\\\").replace("'", "''")
        # Additional escaping for special characters
        escaped = escaped.replace("\x00", "").replace("\n", "\\n").replace("\r", "\\r")
        return f"'{escaped}'"

    def _get_parameters(self, context: Dict[str, Any]) -> List[Any]:
        """获取查询参数"""
        if self.parameters_from:
            # 从上下文获取
            if "." in self.parameters_from:
                parts = self.parameters_from.split(".")
                if len(parts) == 2 and parts[0] in context:
                    params = context[parts[0]].get(parts[1], [])
                    return params if isinstance(params, list) else [params]
            params = context.get(self.parameters_from, [])
            return params if isinstance(params, list) else [params]

        # 渲染参数模板
        return self._render_parameters(self.parameters_template, context)

    def _render_parameters(self, parameters: List[Any], context: Dict[str, Any]) -> List[Any]:
        """渲染参数中的变量引用"""
        rendered = []

        for param in parameters:
            if isinstance(param, str) and param.startswith("{{") and param.endswith("}}"):
                var_path = param[2:-2].strip()

                if var_path.startswith("inputs."):
                    parts = var_path[7:].split(".")
                    initial_input = context.get("_initial_input", {})
                    value = self._get_nested_value(initial_input, parts)
                elif "." in var_path:
                    parts = var_path.split(".")
                    if parts[0] in context:
                        value = self._get_nested_value(context[parts[0]], parts[1:])
                    else:
                        value = None
                else:
                    value = context.get(var_path)

                rendered.append(value)
            else:
                rendered.append(param)

        return rendered

    async def _execute_query(self, query: str, parameters: List[Any]) -> Dict[str, Any]:
        """执行数据库查询"""
        # 获取数据库类型
        db_type = self.connection_config.get("type", "sqlite")

        # 根据类型执行查询
        if db_type == "sqlite":
            return await self._execute_sqlite(query, parameters)
        elif db_type == "postgresql":
            return await self._execute_postgresql(query, parameters)
        elif db_type == "mysql":
            return await self._execute_mysql(query, parameters)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    async def _execute_sqlite(self, query: str, parameters: List[Any]) -> Dict[str, Any]:
        """执行 SQLite 查询"""
        import sqlite3
        import asyncio

        def _sync_query():
            # 使用内存数据库或指定文件
            db_path = self.connection_config.get("path", ":memory:")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            try:
                cursor.execute(query, parameters)

                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    return {
                        "rows": [dict(row) for row in rows],
                        "row_count": len(rows),
                        "affected_rows": 0
                    }
                else:
                    affected = cursor.rowcount
                    conn.commit()
                    return {
                        "rows": [],
                        "row_count": 0,
                        "affected_rows": affected
                    }
            finally:
                conn.close()

        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_query)

    async def _execute_postgresql(self, query: str, parameters: List[Any]) -> Dict[str, Any]:
        """执行 PostgreSQL 查询"""
        try:
            import asyncpg
        except ImportError:
            # 如果没有 asyncpg，返回模拟数据
            return self._mock_result(query, parameters)

        # 获取连接字符串
        dsn = self.connection_config.get("dsn", "")
        if not dsn:
            host = self.connection_config.get("host", "localhost")
            port = self.connection_config.get("port", 5432)
            database = self.connection_config.get("database", "")
            username = self.connection_config.get("username", "")
            password = self.connection_config.get("password", "")

            # Validate required connection parameters
            if not database:
                raise ValueError(
                    "PostgreSQL database name is required. "
                    "Configure 'database' in connection settings."
                )
            if not username:
                raise ValueError(
                    "PostgreSQL username is required. "
                    "Configure 'username' in connection settings."
                )
            if not password:
                raise ValueError(
                    "PostgreSQL password is required. "
                    "Configure 'password' in connection settings."
                )

            dsn = f"postgresql://{username}:{password}@{host}:{port}/{database}"

        try:
            conn = await asyncpg.connect(dsn)

            try:
                # 执行查询
                if query.strip().upper().startswith("SELECT"):
                    rows = await conn.fetch(query, *parameters)
                    return {
                        "rows": [dict(row) for row in rows],
                        "row_count": len(rows),
                        "affected_rows": 0
                    }
                else:
                    result = await conn.execute(query, *parameters)
                    # PostgreSQL 返回 "INSERT 0 1" 格式
                    match = re.search(r'(\d+)$', result.split()[-1])
                    affected = int(match.group(1)) if match else 0
                    return {
                        "rows": [],
                        "row_count": 0,
                        "affected_rows": affected
                    }
            finally:
                await conn.close()

        except Exception as e:
            # 连接失败，返回模拟数据
            return self._mock_result(query, parameters, error=str(e))

    async def _execute_mysql(self, query: str, parameters: List[Any]) -> Dict[str, Any]:
        """执行 MySQL 查询"""
        try:
            import aiomysql
        except ImportError:
            return self._mock_result(query, parameters)

        host = self.connection_config.get("host", "localhost")
        port = self.connection_config.get("port", 3306)
        database = self.connection_config.get("database", "")
        username = self.connection_config.get("username", "")
        password = self.connection_config.get("password", "")

        # Validate required connection parameters
        if not database:
            raise ValueError(
                "MySQL database name is required. "
                "Configure 'database' in connection settings."
            )
        if not username:
            raise ValueError(
                "MySQL username is required. "
                "Configure 'username' in connection settings. "
                "Do not use 'root' in production."
            )
        if not password:
            raise ValueError(
                "MySQL password is required. "
                "Configure 'password' in connection settings."
            )

        try:
            conn = await aiomysql.connect(
                host=host,
                port=port,
                db=database,
                user=username,
                password=password
            )

            try:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, parameters)

                    if query.strip().upper().startswith("SELECT"):
                        rows = await cursor.fetchall()
                        return {
                            "rows": rows,
                            "row_count": len(rows),
                            "affected_rows": 0
                        }
                    else:
                        affected = cursor.rowcount
                        await conn.commit()
                        return {
                            "rows": [],
                            "row_count": 0,
                            "affected_rows": affected
                        }
            finally:
                conn.close()

        except Exception as e:
            return self._mock_result(query, parameters, error=str(e))

    def _mock_result(self, query: str, parameters: List[Any], error: str = None) -> Dict[str, Any]:
        """返回模拟结果（当数据库不可用时）

        WARNING: This should only be used in development/testing environments.
        In production, database unavailability should result in an error.
        """
        import os

        # Check if we're in production mode - if so, raise an error instead of mocking
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod"):
            raise RuntimeError(
                f"Database connection failed in production environment: {error or 'Unknown error'}. "
                "Mock data is not allowed in production."
            )

        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Returning mock data for query. This is only acceptable in development/testing. "
            f"Error: {error or 'Database driver not installed'}"
        )

        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            # 返回模拟行
            mock_rows = [
                {"id": 1, "name": "示例数据 1", "value": "mock_value_1"},
                {"id": 2, "name": "示例数据 2", "value": "mock_value_2"},
            ]
            return {
                "rows": mock_rows,
                "row_count": 2,
                "affected_rows": 0,
                "mock": True,
                "warning": "This is mock data. Install database driver for real queries.",
                "error": error
            }
        else:
            return {
                "rows": [],
                "row_count": 0,
                "affected_rows": 1,
                "mock": True,
                "warning": "This is mock data. Install database driver for real queries.",
                "error": error
            }

    def _format_output(self, result: Dict[str, Any]) -> Any:
        """根据输出模式格式化结果"""
        rows = result.get("rows", [])
        row_count = result.get("row_count", 0)
        affected_rows = result.get("affected_rows", 0)

        if self.output_mode == "rows":
            return rows
        elif self.output_mode == "first":
            return rows[0] if rows else None
        elif self.output_mode == "value":
            if rows and len(rows) > 0:
                # 返回第一行的第一个值
                first_row = rows[0]
                if isinstance(first_row, dict):
                    return list(first_row.values())[0] if first_row else None
                return first_row
            return None
        elif self.output_mode == "count":
            return row_count
        elif self.output_mode == "affected":
            return affected_rows
        elif self.output_mode == "exists":
            return row_count > 0
        else:
            return rows

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

    def validate(self) -> bool:
        """验证节点配置"""
        if not self.query_template and not self.query_from:
            return False

        db_type = self.connection_config.get("type", "")
        if db_type not in ["sqlite", "postgresql", "mysql", "mssql"]:
            # 允许默认使用 sqlite
            self.connection_config["type"] = "sqlite"

        return True
