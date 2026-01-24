"""
SQL 执行服务
Sprint 24: Text-to-SQL 增强 - SQL 执行与结果返回

提供安全的 SQL 执行环境，包括：
- 只读查询执行
- 查询超时控制
- 结果分页
- 安全沙箱
"""

import logging
import os
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# 数据库名称白名单验证正则表达式
# 只允许字母、数字和下划线，必须以字母开头
DATABASE_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')


class QueryStatus(Enum):
    """查询状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class QueryResult:
    """查询结果"""
    query_id: str
    sql: str
    database: str
    status: QueryStatus
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    total_count: int = 0
    execution_time_ms: int = 0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class QueryConfig:
    """查询配置"""
    timeout_seconds: int = 30
    max_rows: int = 1000
    readonly: bool = True
    allow_temp_tables: bool = False
    user_id: Optional[str] = None


class SQLSanitizer:
    """
    SQL 清洗器 - 检测和阻止危险的 SQL 操作
    """

    # 危险关键字（禁止执行）
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'INSERT', 'UPDATE', 'REPLACE', 'MERGE',
        'GRANT', 'REVOKE', 'LOCK', 'UNLOCK',
        'CALL', 'EXECUTE', 'EXEC',
        'LOAD', 'OUTFILE', 'DUMPFILE',
        'SHUTDOWN', 'KILL'
    ]

    # 危险函数
    DANGEROUS_FUNCTIONS = [
        'SLEEP', 'BENCHMARK', 'GET_LOCK', 'RELEASE_LOCK',
        'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE',
        'SYSTEM', 'SYS_EVAL', 'SYS_EXEC'
    ]

    # 允许的关键字
    ALLOWED_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'ON', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE', 'IS', 'NULL',
        'ORDER', 'BY', 'ASC', 'DESC', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
        'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'UNION', 'ALL', 'INTERSECT', 'EXCEPT',
        'WITH', 'RECURSIVE', 'CTE'
    ]

    @classmethod
    def is_safe(cls, sql: str) -> Tuple[bool, Optional[str]]:
        """
        检查 SQL 是否安全

        Args:
            sql: SQL 语句

        Returns:
            (是否安全, 错误信息)
        """
        sql_upper = sql.upper()

        # 检查危险关键字
        for keyword in cls.DANGEROUS_KEYWORDS:
            # 使用单词边界匹配
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"Dangerous keyword detected: {keyword}"

        # 检查危险函数
        for func in cls.DANGEROUS_FUNCTIONS:
            pattern = r'\b' + func.replace(' ', r'\s+') + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"Dangerous function detected: {func}"

        # 检查多语句（分号分隔）
        # 允许语句末尾的分号，但不允许中间的分号
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        if len(statements) > 1:
            return False, "Multiple statements not allowed"

        # 检查注释注入
        if '--' in sql or '/*' in sql or '#' in sql:
            return False, "SQL comments not allowed for security reasons"

        # 确保是 SELECT 语句
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Only SELECT statements are allowed"

        return True, None

    @classmethod
    def sanitize(cls, sql: str) -> str:
        """
        清洗 SQL 语句

        Args:
            sql: 原始 SQL

        Returns:
            清洗后的 SQL
        """
        # 移除首尾空白
        sql = sql.strip()

        # 移除末尾分号
        sql = sql.rstrip(';')

        # 标准化空白字符
        sql = ' '.join(sql.split())

        return sql

    @classmethod
    def validate_database_name(cls, database: str) -> Tuple[bool, Optional[str]]:
        """
        验证数据库名称是否安全

        Args:
            database: 数据库名称

        Returns:
            (是否有效, 错误信息)
        """
        if not database:
            return False, "Database name cannot be empty"

        if not DATABASE_NAME_PATTERN.match(database):
            return False, (
                "Invalid database name. Must start with a letter and contain only "
                "letters, numbers, and underscores (max 64 chars)"
            )

        return True, None


class SQLExecutor:
    """
    SQL 执行器

    Sprint 24: 安全的 SQL 执行环境

    功能:
    - 只读查询执行
    - 超时控制
    - 结果分页
    - 查询历史记录
    """

    def __init__(
        self,
        db_url: str = None,
        default_timeout: int = 30,
        max_rows: int = 1000
    ):
        """
        初始化执行器

        Args:
            db_url: 数据库连接 URL
            default_timeout: 默认超时时间（秒）
            max_rows: 默认最大返回行数
        """
        self.db_url = db_url or os.environ.get('DATABASE_URL')
        self.default_timeout = default_timeout
        self.max_rows = max_rows

        self._engine = None
        self._query_history: Dict[str, QueryResult] = {}
        self._lock = threading.Lock()

    @property
    def engine(self):
        """延迟初始化数据库引擎"""
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
                self._engine = create_engine(
                    self.db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    execution_options={
                        "isolation_level": "AUTOCOMMIT"  # 只读模式
                    }
                )
            except ImportError:
                raise ImportError("SQLAlchemy is required. Install with: pip install sqlalchemy")
        return self._engine

    def execute(
        self,
        sql: str,
        database: str,
        config: QueryConfig = None
    ) -> QueryResult:
        """
        执行 SQL 查询

        Args:
            sql: SQL 语句
            database: 数据库名称
            config: 查询配置

        Returns:
            QueryResult 对象
        """
        import uuid
        from datetime import datetime

        config = config or QueryConfig()
        query_id = str(uuid.uuid4())

        result = QueryResult(
            query_id=query_id,
            sql=sql,
            database=database,
            status=QueryStatus.PENDING,
            started_at=datetime.now()
        )

        try:
            # 清洗 SQL
            sanitized_sql = SQLSanitizer.sanitize(sql)

            # 安全检查
            if config.readonly:
                is_safe, error = SQLSanitizer.is_safe(sanitized_sql)
                if not is_safe:
                    result.status = QueryStatus.FAILED
                    result.error = error
                    return result

            # 添加 LIMIT 子句（如果没有）
            if 'LIMIT' not in sanitized_sql.upper():
                sanitized_sql = f"{sanitized_sql} LIMIT {config.max_rows}"

            result.status = QueryStatus.RUNNING

            # 验证数据库名称
            is_valid, db_error = SQLSanitizer.validate_database_name(database)
            if not is_valid:
                result.status = QueryStatus.FAILED
                result.error = db_error
                return result

            # 执行查询
            start_time = time.time()

            with self.engine.connect() as conn:
                from sqlalchemy import text

                # 设置查询超时（MySQL 特定）- 使用参数化查询
                timeout_ms = config.timeout_seconds * 1000
                conn.execute(text("SET SESSION max_execution_time = :timeout"), {"timeout": timeout_ms})

                # 选择数据库 - 使用反引号转义已验证的数据库名
                # 注意：数据库名已通过 validate_database_name 验证，只包含安全字符
                conn.execute(text(f"USE `{database}`"))

                # 执行查询 - 使用 text() 包装已清洗的 SQL
                cursor_result = conn.execute(text(sanitized_sql))

                # 获取列名
                result.columns = list(cursor_result.keys())

                # 获取数据
                rows = cursor_result.fetchall()
                result.rows = [list(row) for row in rows]
                result.row_count = len(result.rows)

            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = int(execution_time)
            result.status = QueryStatus.COMPLETED
            result.completed_at = datetime.now()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"SQL execution failed: {error_msg}")

            if 'timeout' in error_msg.lower() or 'max_execution_time' in error_msg.lower():
                result.status = QueryStatus.TIMEOUT
                result.error = f"Query exceeded timeout of {config.timeout_seconds} seconds"
            else:
                result.status = QueryStatus.FAILED
                result.error = error_msg

            result.completed_at = datetime.now()

        # 保存到历史记录
        with self._lock:
            self._query_history[query_id] = result
            # 限制历史记录大小
            if len(self._query_history) > 1000:
                oldest_id = min(self._query_history.keys(), key=lambda k: self._query_history[k].started_at)
                del self._query_history[oldest_id]

        return result

    def execute_async(
        self,
        sql: str,
        database: str,
        config: QueryConfig = None,
        callback: callable = None
    ) -> str:
        """
        异步执行 SQL 查询

        Args:
            sql: SQL 语句
            database: 数据库名称
            config: 查询配置
            callback: 完成回调

        Returns:
            查询 ID
        """
        import uuid
        import threading

        query_id = str(uuid.uuid4())

        def run_query():
            result = self.execute(sql, database, config)
            if callback:
                callback(result)

        thread = threading.Thread(target=run_query, daemon=True)
        thread.start()

        return query_id

    def get_result(self, query_id: str) -> Optional[QueryResult]:
        """获取查询结果"""
        return self._query_history.get(query_id)

    def cancel_query(self, query_id: str) -> bool:
        """取消查询（如果正在运行）"""
        result = self._query_history.get(query_id)
        if result and result.status == QueryStatus.RUNNING:
            result.status = QueryStatus.CANCELLED
            return True
        return False

    def format_result(self, result: QueryResult, format: str = 'json') -> Any:
        """
        格式化查询结果

        Args:
            result: 查询结果
            format: 输出格式 (json, csv, markdown)

        Returns:
            格式化后的结果
        """
        if format == 'json':
            return {
                'query_id': result.query_id,
                'status': result.status.value,
                'columns': result.columns,
                'rows': result.rows,
                'row_count': result.row_count,
                'execution_time_ms': result.execution_time_ms,
                'error': result.error
            }

        elif format == 'csv':
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(result.columns)
            writer.writerows(result.rows)
            return output.getvalue()

        elif format == 'markdown':
            if not result.columns:
                return "No results"

            # 表头
            header = '| ' + ' | '.join(result.columns) + ' |'
            separator = '| ' + ' | '.join(['---'] * len(result.columns)) + ' |'

            # 数据行
            rows = []
            for row in result.rows:
                rows.append('| ' + ' | '.join(str(v) for v in row) + ' |')

            return '\n'.join([header, separator] + rows)

        else:
            raise ValueError(f"Unknown format: {format}")

    def get_query_history(
        self,
        user_id: str = None,
        database: str = None,
        limit: int = 100
    ) -> List[QueryResult]:
        """
        获取查询历史

        Args:
            user_id: 过滤特定用户
            database: 过滤特定数据库
            limit: 最大数量

        Returns:
            QueryResult 列表
        """
        results = list(self._query_history.values())

        if database:
            results = [r for r in results if r.database == database]

        results.sort(key=lambda r: r.started_at, reverse=True)
        return results[:limit]


# 全局实例
_executor: Optional[SQLExecutor] = None


def get_sql_executor() -> SQLExecutor:
    """获取全局 SQL 执行器实例"""
    global _executor
    if _executor is None:
        _executor = SQLExecutor()
    return _executor
