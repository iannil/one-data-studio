"""
ShardingSphere Proxy 客户端

提供与 ShardingSphere Proxy 通信的功能，
支持脱敏规则管理和 DistSQL 执行。
"""
import logging
from typing import Optional, Dict, Any, List

from .config import ShardingSphereConfig


logger = logging.getLogger(__name__)


class ShardingSphereClient:
    """
    ShardingSphere Proxy 客户端

    通过 MySQL 协议连接 ShardingSphere Proxy，
    执行 DistSQL 管理脱敏规则。
    """

    def __init__(self, config: Optional[ShardingSphereConfig] = None):
        """
        初始化 ShardingSphere 客户端

        Args:
            config: ShardingSphere 配置，如果为 None 则从环境变量加载
        """
        self.config = config or ShardingSphereConfig.from_env()
        self._connection = None

    def _get_connection(self):
        """获取数据库连接"""
        if self._connection is None or not self._connection.open:
            try:
                import pymysql
                self._connection = pymysql.connect(
                    host=self.config.proxy_host,
                    port=self.config.proxy_port,
                    user=self.config.username,
                    password=self.config.password,
                    connect_timeout=self.config.timeout,
                    autocommit=True,
                )
            except Exception as e:
                logger.error(f"Failed to connect to ShardingSphere Proxy: {e}")
                raise
        return self._connection

    def close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

    def health_check(self) -> bool:
        """
        检查 ShardingSphere Proxy 健康状态

        Returns:
            服务是否可用
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                return True
        except Exception as e:
            logger.error(f"ShardingSphere health check failed: {e}")
            return False

    def execute_distsql(self, sql: str) -> List[Dict[str, Any]]:
        """
        执行 DistSQL 语句

        Args:
            sql: DistSQL 语句

        Returns:
            查询结果（如果是 SELECT/SHOW 类语句）
        """
        try:
            conn = self._get_connection()
            results = []

            # 支持多条语句（以 ; 分隔）
            statements = [s.strip() for s in sql.split(";") if s.strip()]

            for stmt in statements:
                with conn.cursor() as cursor:
                    cursor.execute(stmt)

                    # 如果有结果集，获取结果
                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        for row in rows:
                            results.append(dict(zip(columns, row)))

            return results

        except Exception as e:
            logger.error(f"Failed to execute DistSQL: {e}")
            raise

    def show_databases(self) -> List[str]:
        """
        列出所有数据库

        Returns:
            数据库名称列表
        """
        results = self.execute_distsql("SHOW DATABASES")
        return [r.get("Database", r.get("database", "")) for r in results]

    def list_mask_rules(self, database: str) -> List[Dict[str, Any]]:
        """
        列出指定数据库的脱敏规则

        Args:
            database: 数据库名

        Returns:
            脱敏规则列表
        """
        sql = f"USE {database}; SHOW MASK RULES"
        return self.execute_distsql(sql)

    def apply_mask_rules(self, sql: str) -> bool:
        """
        应用脱敏规则 (CREATE MASK RULE)

        Args:
            sql: CREATE MASK RULE 的 DistSQL

        Returns:
            是否应用成功
        """
        try:
            self.execute_distsql(sql)
            logger.info("Mask rules applied successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to apply mask rules: {e}")
            return False

    def remove_mask_rules(self, database: str, table: str) -> bool:
        """
        移除指定表的脱敏规则

        Args:
            database: 数据库名
            table: 表名

        Returns:
            是否移除成功
        """
        try:
            sql = f"USE {database}; DROP MASK RULE IF EXISTS {table}"
            self.execute_distsql(sql)
            logger.info(f"Mask rules for {database}.{table} removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove mask rules: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        获取 ShardingSphere Proxy 状态

        Returns:
            状态信息
        """
        try:
            databases = self.show_databases()
            return {
                "available": True,
                "host": self.config.proxy_host,
                "port": self.config.proxy_port,
                "databases": databases,
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "host": self.config.proxy_host,
                "port": self.config.proxy_port,
            }

    def show_compute_nodes(self) -> List[Dict[str, Any]]:
        """
        列出计算节点

        Returns:
            计算节点列表
        """
        try:
            return self.execute_distsql("SHOW COMPUTE NODES")
        except Exception:
            return []

    def show_storage_units(self, database: str) -> List[Dict[str, Any]]:
        """
        列出存储单元

        Args:
            database: 数据库名

        Returns:
            存储单元列表
        """
        try:
            sql = f"USE {database}; SHOW STORAGE UNITS"
            return self.execute_distsql(sql)
        except Exception:
            return []
