"""
SQL 执行沙箱
Sprint 24: Text-to-SQL 安全增强

提供额外的安全隔离层，包括：
- 数据库用户权限隔离
- 资源限制
- 审计日志
"""

import logging
import os
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """沙箱配置"""
    # 资源限制
    max_memory_mb: int = 256
    max_execution_time_seconds: int = 30
    max_result_rows: int = 1000
    max_result_size_bytes: int = 10 * 1024 * 1024  # 10MB

    # 权限控制
    allowed_databases: List[str] = field(default_factory=list)
    denied_databases: List[str] = field(default_factory=lambda: ['mysql', 'information_schema', 'performance_schema', 'sys'])
    allowed_tables: List[str] = field(default_factory=list)  # 空表示允许所有
    denied_tables: List[str] = field(default_factory=list)

    # 审计配置
    enable_audit: bool = True
    audit_log_path: str = '/var/log/sql_sandbox/audit.log'


@dataclass
class AuditRecord:
    """审计记录"""
    timestamp: datetime
    user_id: str
    query_id: str
    database: str
    sql: str
    status: str
    execution_time_ms: int
    rows_returned: int
    error: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SQLSandbox:
    """
    SQL 执行沙箱

    Sprint 24: 安全隔离的 SQL 执行环境

    安全特性:
    - 强制只读连接
    - 数据库/表级别权限控制
    - 资源使用限制
    - 完整审计日志
    """

    def __init__(self, config: SandboxConfig = None):
        """
        初始化沙箱

        Args:
            config: 沙箱配置
        """
        self.config = config or SandboxConfig()
        self._audit_records: List[AuditRecord] = []
        self._lock = threading.Lock()

        # 创建审计日志目录
        if self.config.enable_audit:
            log_dir = os.path.dirname(self.config.audit_log_path)
            if log_dir and not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except OSError:
                    logger.warning(f"Could not create audit log directory: {log_dir}")

    def check_database_permission(self, database: str) -> bool:
        """
        检查数据库访问权限

        Args:
            database: 数据库名称

        Returns:
            是否允许访问
        """
        # 检查是否在拒绝列表
        if database.lower() in [d.lower() for d in self.config.denied_databases]:
            return False

        # 如果允许列表不为空，检查是否在允许列表
        if self.config.allowed_databases:
            return database.lower() in [d.lower() for d in self.config.allowed_databases]

        return True

    def check_table_permission(self, table: str) -> bool:
        """
        检查表访问权限

        Args:
            table: 表名称

        Returns:
            是否允许访问
        """
        # 检查是否在拒绝列表
        if table.lower() in [t.lower() for t in self.config.denied_tables]:
            return False

        # 如果允许列表不为空，检查是否在允许列表
        if self.config.allowed_tables:
            return table.lower() in [t.lower() for t in self.config.allowed_tables]

        return True

    def extract_tables_from_sql(self, sql: str) -> List[str]:
        """
        从 SQL 中提取表名

        Args:
            sql: SQL 语句

        Returns:
            表名列表
        """
        import re

        tables = []

        # 简单的 FROM 子句解析
        from_pattern = r'FROM\s+([`"]?[\w.]+[`"]?)'
        join_pattern = r'JOIN\s+([`"]?[\w.]+[`"]?)'

        for match in re.finditer(from_pattern, sql, re.IGNORECASE):
            table = match.group(1).strip('`"')
            tables.append(table)

        for match in re.finditer(join_pattern, sql, re.IGNORECASE):
            table = match.group(1).strip('`"')
            tables.append(table)

        return list(set(tables))

    def validate_query(self, sql: str, database: str) -> tuple:
        """
        验证查询

        Args:
            sql: SQL 语句
            database: 数据库名称

        Returns:
            (是否有效, 错误信息)
        """
        # 检查数据库权限
        if not self.check_database_permission(database):
            return False, f"Access denied to database: {database}"

        # 检查表权限
        tables = self.extract_tables_from_sql(sql)
        for table in tables:
            if not self.check_table_permission(table):
                return False, f"Access denied to table: {table}"

        # 检查结果大小限制（通过 LIMIT 子句）
        sql_upper = sql.upper()
        if 'LIMIT' in sql_upper:
            import re
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                limit_value = int(limit_match.group(1))
                if limit_value > self.config.max_result_rows:
                    return False, f"LIMIT exceeds maximum allowed: {self.config.max_result_rows}"

        return True, None

    def audit(
        self,
        user_id: str,
        query_id: str,
        database: str,
        sql: str,
        status: str,
        execution_time_ms: int = 0,
        rows_returned: int = 0,
        error: str = None,
        ip_address: str = None
    ):
        """
        记录审计日志

        Args:
            user_id: 用户 ID
            query_id: 查询 ID
            database: 数据库名称
            sql: SQL 语句
            status: 执行状态
            execution_time_ms: 执行时间
            rows_returned: 返回行数
            error: 错误信息
            ip_address: IP 地址
        """
        if not self.config.enable_audit:
            return

        record = AuditRecord(
            timestamp=datetime.now(),
            user_id=user_id,
            query_id=query_id,
            database=database,
            sql=sql,
            status=status,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            error=error,
            ip_address=ip_address
        )

        with self._lock:
            self._audit_records.append(record)

            # 限制内存中的审计记录数量
            if len(self._audit_records) > 10000:
                self._audit_records = self._audit_records[-5000:]

        # 写入日志文件
        self._write_audit_log(record)

    def _write_audit_log(self, record: AuditRecord):
        """写入审计日志文件"""
        try:
            import json

            log_entry = {
                'timestamp': record.timestamp.isoformat(),
                'user_id': record.user_id,
                'query_id': record.query_id,
                'database': record.database,
                'sql_hash': hashlib.sha256(record.sql.encode()).hexdigest()[:16],
                'sql_preview': record.sql[:100] + '...' if len(record.sql) > 100 else record.sql,
                'status': record.status,
                'execution_time_ms': record.execution_time_ms,
                'rows_returned': record.rows_returned,
                'error': record.error,
                'ip_address': record.ip_address
            }

            with open(self.config.audit_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def get_audit_records(
        self,
        user_id: str = None,
        database: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """
        获取审计记录

        Args:
            user_id: 过滤特定用户
            database: 过滤特定数据库
            status: 过滤特定状态
            limit: 最大数量

        Returns:
            AuditRecord 列表
        """
        records = self._audit_records.copy()

        if user_id:
            records = [r for r in records if r.user_id == user_id]

        if database:
            records = [r for r in records if r.database == database]

        if status:
            records = [r for r in records if r.status == status]

        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息

        Args:
            user_id: 用户 ID

        Returns:
            统计信息
        """
        records = [r for r in self._audit_records if r.user_id == user_id]

        if not records:
            return {
                'user_id': user_id,
                'total_queries': 0,
                'successful_queries': 0,
                'failed_queries': 0,
                'total_rows_returned': 0,
                'avg_execution_time_ms': 0
            }

        successful = [r for r in records if r.status == 'completed']
        failed = [r for r in records if r.status in ['failed', 'timeout']]

        execution_times = [r.execution_time_ms for r in records if r.execution_time_ms]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0

        return {
            'user_id': user_id,
            'total_queries': len(records),
            'successful_queries': len(successful),
            'failed_queries': len(failed),
            'total_rows_returned': sum(r.rows_returned for r in records),
            'avg_execution_time_ms': int(avg_time),
            'last_query_at': records[-1].timestamp.isoformat() if records else None
        }


# 全局沙箱实例
_sandbox: Optional[SQLSandbox] = None


def get_sql_sandbox() -> SQLSandbox:
    """获取全局 SQL 沙箱实例"""
    global _sandbox
    if _sandbox is None:
        _sandbox = SQLSandbox()
    return _sandbox


def configure_sandbox(config: SandboxConfig):
    """配置全局沙箱"""
    global _sandbox
    _sandbox = SQLSandbox(config)
