"""
MySQL存储管理器

提供：
1. 数据库连接管理
2. 批量插入数据
3. 幂等性支持（先检查后插入）
4. 数据清理功能
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None
    DictCursor = None

from ..config import DatabaseConfig
from ..base import generate_id


logger = logging.getLogger(__name__)


class MySQLManager:
    """
    MySQL存储管理器

    提供：
    - 连接池管理
    - 批量插入
    - 幂等性插入（先检查是否存在）
    - 数据清理
    """

    def __init__(self, config: DatabaseConfig = None):
        """
        初始化MySQL管理器

        Args:
            config: 数据库配置
        """
        self.config = config or DatabaseConfig.from_env()
        self._connection = None
        self._connected = False

    @property
    def is_available(self) -> bool:
        """检查pymysql是否可用"""
        return pymysql is not None

    def connect(self) -> bool:
        """
        建立数据库连接

        Returns:
            连接是否成功
        """
        if not self.is_available:
            raise ImportError("pymysql is required. Install it with: pip install pymysql")

        if self._connected and self._connection:
            return True

        try:
            kwargs = self.config.get_pymysql_kwargs()
            self._connection = pymysql.connect(**kwargs)
            self._connected = True
            logger.info(f"Connected to MySQL at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False

    def disconnect(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._connected = False
            logger.info("Disconnected from MySQL")

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器

        Usage:
            with mysql.transaction():
                # 执行操作
                pass
        """
        if not self._connected:
            self.connect()

        try:
            self._connection.begin()
            yield
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Transaction failed, rolled back: {e}")
            raise

    def execute(self, sql: str, params: Tuple = None, *, commit: bool = True) -> int:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: SQL参数
            commit: 是否提交

        Returns:
            影响的行数
        """
        if not self._connected:
            self.connect()

        with self._connection.cursor() as cursor:
            affected = cursor.execute(sql, params)
            if commit:
                self._connection.commit()
            return affected

    def fetch_one(self, sql: str, params: Tuple = None) -> Optional[Dict]:
        """
        查询单行数据

        Args:
            sql: SQL语句
            params: SQL参数

        Returns:
            查询结果字典
        """
        if not self._connected:
            self.connect()

        with self._connection.cursor(DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetch_all(self, sql: str, params: Tuple = None) -> List[Dict]:
        """
        查询多行数据

        Args:
            sql: SQL语句
            params: SQL参数

        Returns:
            查询结果列表
        """
        if not self._connected:
            self.connect()

        with self._connection.cursor(DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        result = self.fetch_one(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (self.config.database, table_name)
        )
        return result and result.get('cnt', 0) > 0

    def count_rows(self, table_name: str, where: str = "", params: Tuple = None) -> int:
        """
        统计表行数

        Args:
            table_name: 表名
            where: WHERE条件
            params: SQL参数

        Returns:
            行数
        """
        sql = f"SELECT COUNT(*) as cnt FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        result = self.fetch_one(sql, params)
        return result.get('cnt', 0) if result else 0

    def truncate_table(self, table_name: str) -> int:
        """
        清空表

        Args:
            table_name: 表名

        Returns:
            影响的行数
        """
        return self.execute(f"TRUNCATE TABLE {table_name}")

    def delete_rows(self, table_name: str, where: str = "", params: Tuple = None) -> int:
        """
        删除指定行

        Args:
            table_name: 表名
            where: WHERE条件
            params: SQL参数

        Returns:
            影响的行数
        """
        sql = f"DELETE FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        return self.execute(sql, params)

    # ==================== 批量插入 ====================

    def batch_insert(
        self,
        table_name: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        *,
        idempotent: bool = False,
        idempotent_columns: List[str] = None,
        chunk_size: int = 100,
        replace: bool = False
    ) -> int:
        """
        批量插入数据

        Args:
            table_name: 表名
            columns: 列名列表
            rows: 数据行列表（字典列表）
            idempotent: 是否启用幂等性（先检查后插入）
            idempotent_columns: 用于幂等性检查的列（默认使用所有列）
            chunk_size: 批量插入的块大小
            replace: 是否使用REPLACE INTO

        Returns:
            插入的行数
        """
        if not rows:
            return 0

        # 如果启用幂等性，先过滤已存在的数据
        if idempotent:
            check_columns = idempotent_columns or columns
            rows = self._filter_existing_rows(table_name, check_columns, rows)
            if not rows:
                return 0

        # 分块插入
        total_inserted = 0
        for chunk in self._chunk_rows(rows, chunk_size):
            total_inserted += self._execute_batch_insert(
                table_name, columns, chunk, replace
            )

        return total_inserted

    def _filter_existing_rows(
        self,
        table_name: str,
        check_columns: List[str],
        rows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的行（幂等性检查）

        Args:
            table_name: 表名
            check_columns: 用于检查的列
            rows: 待检查的行

        Returns:
            不存在的行
        """
        if not rows:
            return []

        # 获取表中已有的值
        existing_values = set()
        for column in check_columns:
            values = [row.get(column) for row in rows if row.get(column)]
            if values:
                sql = f"SELECT DISTINCT {column} FROM {table_name} WHERE {column} IN %s"
                results = self.fetch_all(sql, (tuple(values),))
                existing_values.update(
                    f"{column}:{result[column]}" for result in results
                )

        # 过滤已存在的行
        filtered = []
        for row in rows:
            exists = False
            for column in check_columns:
                key = f"{column}:{row.get(column)}"
                if key in existing_values:
                    exists = True
                    break
            if not exists:
                filtered.append(row)

        return filtered

    def _chunk_rows(self, rows: List[Dict], chunk_size: int) -> List[List[Dict]]:
        """将行分块"""
        return [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]

    def _execute_batch_insert(
        self,
        table_name: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        replace: bool = False
    ) -> int:
        """
        执行批量插入

        Args:
            table_name: 表名
            columns: 列名列表
            rows: 数据行
            replace: 是否使用REPLACE INTO

        Returns:
            插入的行数
        """
        if not rows:
            return 0

        # 构建SQL
        keyword = "REPLACE" if replace else "INSERT"
        placeholders = ", ".join(["%s"] * len(columns))
        column_str = ", ".join(columns)
        sql = f"{keyword} INTO {table_name} ({column_str}) VALUES ({placeholders})"

        # 准备数据
        values = []
        for row in rows:
            row_values = [row.get(col) for col in columns]
            values.append(row_values)

        # 执行批量插入
        with self._connection.cursor() as cursor:
            affected = cursor.executemany(sql, values)
            self._connection.commit()
            return affected

    # ==================== 便捷方法 ====================

    def insert_user(self, user_data: Dict[str, Any]) -> bool:
        """插入用户数据"""
        return self.insert_row("users", user_data) > 0

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        插入单行数据

        Args:
            table_name: 表名
            data: 数据字典

        Returns:
            影响的行数
        """
        if not data:
            return 0

        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_str = ", ".join(columns)
        values = [data[col] for col in columns]

        sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholders})"
        return self.execute(sql, tuple(values))

    def update_row(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: str,
        params: Tuple = None
    ) -> int:
        """
        更新数据

        Args:
            table_name: 表名
            data: 要更新的数据
            where: WHERE条件
            params: WHERE参数

        Returns:
            影响的行数
        """
        if not data:
            return 0

        set_clause = ", ".join([f"{col} = %s" for col in data.keys()])
        values = list(data.values())
        if params:
            values.extend(params)

        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        return self.execute(sql, tuple(values))

    # ==================== 清理方法 ====================

    def cleanup_table(self, table_name: str, where: str = "", params: Tuple = None) -> int:
        """
        清理表数据

        Args:
            table_name: 表名
            where: WHERE条件（可选）
            params: SQL参数

        Returns:
            删除的行数
        """
        if not self.table_exists(table_name):
            return 0

        if where:
            return self.delete_rows(table_name, where, params)
        else:
            return self.truncate_table(table_name)

    def cleanup_by_prefix(self, table_name: str, id_column: str, prefix: str) -> int:
        """
        根据ID前缀清理数据

        Args:
            table_name: 表名
            id_column: ID列名
            prefix: ID前缀

        Returns:
            删除的行数
        """
        where = f"{id_column} LIKE %s"
        return self.delete_rows(table_name, where, (f"{prefix}%",))

    def cleanup_test_data(self, prefixes: List[str] = None) -> Dict[str, int]:
        """
        清理所有测试数据

        Args:
            prefixes: ID前缀列表，用于识别测试数据

        Returns:
            各表删除的行数
        """
        if prefixes is None:
            prefixes = ["test_", "user_", "ds_", "tbl_", "col_", "etl_", "kb_"]

        results = {}

        # 定义要清理的表和ID列
        tables_to_cleanup = [
            ("users", "user_id"),
            ("etl_tasks", "task_id"),
            ("etl_task_logs", "log_id"),
            ("knowledge_bases", "kb_id"),
            ("indexed_documents", "doc_id"),
            ("data_assets", "asset_id"),
            ("datasources", "source_id"),
            ("metadata_databases", "database_name"),
            ("metadata_tables", "table_name"),
            ("metadata_columns", "column_name"),
        ]

        for table_name, id_column in tables_to_cleanup:
            for prefix in prefixes:
                deleted = self.cleanup_by_prefix(table_name, id_column, prefix)
                if deleted > 0:
                    results[f"{table_name}:{prefix}"] = deleted

        return results

    # ==================== 统计方法 ====================

    def get_table_stats(self) -> Dict[str, int]:
        """
        获取所有表的行数统计

        Returns:
            表名和行数的字典
        """
        tables = [
            "users", "roles", "permissions", "user_roles",
            "datasources", "metadata_databases", "metadata_tables", "metadata_columns",
            "etl_tasks", "etl_task_logs",
            "sensitivity_scan_tasks", "sensitivity_scan_results", "masking_rules",
            "data_assets", "asset_categories", "asset_value_history",
            "data_lineage", "data_lineage_events",
            "ml_models", "model_versions", "model_deployments",
            "knowledge_bases", "indexed_documents",
            "bi_dashboards", "bi_charts",
            "alert_rules", "alert_history",
        ]

        stats = {}
        for table in tables:
            if self.table_exists(table):
                stats[table] = self.count_rows(table)
            else:
                stats[table] = 0

        return stats


class MockMySQLManager:
    """
    MySQL管理器的Mock实现（用于测试或无数据库场景）
    """

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self._data: Dict[str, List[Dict]] = {}
        self._connected = False

    def connect(self) -> bool:
        """模拟连接"""
        self._connected = True
        return True

    def disconnect(self):
        """模拟断开"""
        self._connected = False

    @property
    def transaction(self):
        """模拟事务"""
        class MockTransaction:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return MockTransaction

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self._data

    def count_rows(self, table_name: str, where: str = "", params: Tuple = None) -> int:
        """统计行数"""
        return len(self._data.get(table_name, []))

    def batch_insert(
        self,
        table_name: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        **kwargs
    ) -> int:
        """批量插入"""
        if table_name not in self._data:
            self._data[table_name] = []
        self._data[table_name].extend(rows)
        return len(rows)

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """插入单行"""
        if table_name not in self._data:
            self._data[table_name] = []
        self._data[table_name].append(data)
        return 1

    def fetch_all(self, sql: str, params: Tuple = None) -> List[Dict]:
        """模拟查询"""
        return []

    def fetch_one(self, sql: str, params: Tuple = None) -> Optional[Dict]:
        """模拟查询单行"""
        return None

    def cleanup_by_prefix(self, table_name: str, id_column: str, prefix: str) -> int:
        """清理数据"""
        if table_name not in self._data:
            return 0
        original_len = len(self._data[table_name])
        self._data[table_name] = [
            row for row in self._data[table_name]
            if not str(row.get(id_column, "")).startswith(prefix)
        ]
        return original_len - len(self._data[table_name])

    def get_table_stats(self) -> Dict[str, int]:
        """获取统计"""
        return {k: len(v) for k, v in self._data.items()}

    def get_all_data(self) -> Dict[str, List[Dict]]:
        """获取所有数据（用于测试验证）"""
        return self._data.copy()


def get_mysql_manager(config: DatabaseConfig = None, mock: bool = False) -> MySQLManager:
    """
    获取MySQL管理器实例

    Args:
        config: 数据库配置
        mock: 是否使用Mock实现

    Returns:
        MySQL管理器实例
    """
    if mock:
        return MockMySQLManager(config)
    return MySQLManager(config)
