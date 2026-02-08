"""
E2E 测试数据库辅助类

提供数据库连接、查询、验证等操作
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class E2EDatabaseHelper:
    """E2E 测试数据库辅助类"""

    # E2E 测试环境默认配置
    MYSQL_CONFIG = {
        "host": os.getenv("TEST_MYSQL_HOST", "localhost"),
        "port": int(os.getenv("TEST_MYSQL_PORT", "3310")),
        "user": os.getenv("TEST_MYSQL_USER", "root"),
        "password": os.getenv("TEST_MYSQL_PASSWORD", "e2eroot123"),
        "charset": "utf8mb4",
    }

    POSTGRES_CONFIG = {
        "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("TEST_POSTGRES_PORT", "5438")),
        "user": os.getenv("TEST_POSTGRES_USER", "postgres"),
        "password": os.getenv("TEST_POSTGRES_PASSWORD", "e2epostgres123"),
        "database": os.getenv("TEST_POSTGRES_DATABASE", "e2e_ecommerce_pg"),
    }

    def __init__(self, e2e_mode: bool = True):
        """
        初始化数据库辅助类

        Args:
            e2e_mode: 是否使用 E2E 模式（端口 3310/5438）
        """
        self.e2e_mode = e2e_mode
        if e2e_mode:
            self.MYSQL_CONFIG["port"] = 3310
            self.MYSQL_CONFIG["password"] = "e2eroot123"
            self.POSTGRES_CONFIG["port"] = 5438
            self.POSTGRES_CONFIG["password"] = "e2epostgres123"

        self.mysql_conn = None
        self.postgres_conn = None

    # ========================================================================
    # MySQL 连接管理
    # ========================================================================

    @contextmanager
    def get_mysql_connection(self, database: str = None):
        """
        获取 MySQL 连接（上下文管理器）

        Args:
            database: 数据库名称，默认连接到系统数据库

        Yields:
            MySQL 连接对象
        """
        import pymysql

        conn = pymysql.connect(
            host=self.MYSQL_CONFIG["host"],
            port=self.MYSQL_CONFIG["port"],
            user=self.MYSQL_CONFIG["user"],
            password=self.MYSQL_CONFIG["password"],
            database=database,
            charset=self.MYSQL_CONFIG["charset"],
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()

    def connect_mysql(self, database: str = None) -> bool:
        """
        建立 MySQL 连接

        Args:
            database: 数据库名称

        Returns:
            连接是否成功
        """
        try:
            import pymysql

            self.mysql_conn = pymysql.connect(
                host=self.MYSQL_CONFIG["host"],
                port=self.MYSQL_CONFIG["port"],
                user=self.MYSQL_CONFIG["user"],
                password=self.MYSQL_CONFIG["password"],
                database=database,
                charset=self.MYSQL_CONFIG["charset"],
                cursorclass=pymysql.cursors.DictCursor,
            )
            logger.info(f"Connected to MySQL at {self.MYSQL_CONFIG['host']}:{self.MYSQL_CONFIG['port']}")
            return True
        except Exception as e:
            logger.error(f"MySQL connection failed: {e}")
            return False

    # ========================================================================
    # PostgreSQL 连接管理
    # ========================================================================

    @contextmanager
    def get_postgres_connection(self, database: str = None):
        """
        获取 PostgreSQL 连接（上下文管理器）

        Args:
            database: 数据库名称

        Yields:
            PostgreSQL 连接对象
        """
        import psycopg2

        db = database or self.POSTGRES_CONFIG.get("database", "postgres")
        conn = psycopg2.connect(
            host=self.POSTGRES_CONFIG["host"],
            port=self.POSTGRES_CONFIG["port"],
            user=self.POSTGRES_CONFIG["user"],
            password=self.POSTGRES_CONFIG["password"],
            database=db,
        )
        try:
            yield conn
        finally:
            conn.close()

    def connect_postgres(self, database: str = None) -> bool:
        """
        建立 PostgreSQL 连接

        Args:
            database: 数据库名称

        Returns:
            连接是否成功
        """
        try:
            import psycopg2

            db = database or self.POSTGRES_CONFIG.get("database", "postgres")
            self.postgres_conn = psycopg2.connect(
                host=self.POSTGRES_CONFIG["host"],
                port=self.POSTGRES_CONFIG["port"],
                user=self.POSTGRES_CONFIG["user"],
                password=self.POSTGRES_CONFIG["password"],
                database=db,
            )
            logger.info(f"Connected to PostgreSQL at {self.POSTGRES_CONFIG['host']}:{self.POSTGRES_CONFIG['port']}")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False

    def close_all(self):
        """关闭所有数据库连接"""
        if self.mysql_conn:
            self.mysql_conn.close()
            self.mysql_conn = None
        if self.postgres_conn:
            self.postgres_conn.close()
            self.postgres_conn = None

    # ========================================================================
    # 数据查询方法
    # ========================================================================

    def get_mysql_table_count(
        self, database: str, table: str
    ) -> Optional[int]:
        """
        获取 MySQL 表行数

        Args:
            database: 数据库名称
            table: 表名

        Returns:
            表行数，查询失败返回 None
        """
        try:
            with self.get_mysql_connection(database) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                    result = cursor.fetchone()
                    return result["cnt"] if result else None
        except Exception as e:
            logger.error(f"Failed to get MySQL table count: {e}")
            return None

    def get_postgres_table_count(
        self, database: str, table: str
    ) -> Optional[int]:
        """
        获取 PostgreSQL 表行数

        Args:
            database: 数据库名称
            table: 表名

        Returns:
            表行数，查询失败返回 None
        """
        try:
            with self.get_postgres_connection(database) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL table count: {e}")
            return None

    def get_mysql_tables(self, database: str) -> List[str]:
        """
        获取 MySQL 数据库的所有表名

        Args:
            database: 数据库名称

        Returns:
            表名列表
        """
        try:
            with self.get_mysql_connection(database) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES FROM {database}")
                    results = cursor.fetchall()
                    return [list(r.values())[0] for r in results]
        except Exception as e:
            logger.error(f"Failed to get MySQL tables: {e}")
            return []

    def get_postgres_tables(self, database: str) -> List[str]:
        """
        获取 PostgreSQL 数据库的所有表名

        Args:
            database: 数据库名称

        Returns:
            表名列表
        """
        try:
            with self.get_postgres_connection(database) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                    )
                    results = cursor.fetchall()
                    return [r[0] for r in results]
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL tables: {e}")
            return []

    # ========================================================================
    # 数据验证方法
    # ========================================================================

    def verify_data_count(
        self, db_type: str, database: str, table: str, expected_min: int
    ) -> Tuple[bool, int]:
        """
        验证表数据量

        Args:
            db_type: 数据库类型 (mysql/postgres)
            database: 数据库名称
            table: 表名
            expected_min: 预期最小行数

        Returns:
            (是否通过验证, 实际行数)
        """
        if db_type == "mysql":
            count = self.get_mysql_table_count(database, table)
        elif db_type == "postgres":
            count = self.get_postgres_table_count(database, table)
        else:
            return False, 0

        if count is None:
            return False, 0

        return count >= expected_min, count

    def verify_database_exists(self, db_type: str, database: str) -> bool:
        """
        验证数据库是否存在

        Args:
            db_type: 数据库类型 (mysql/postgres)
            database: 数据库名称

        Returns:
            数据库是否存在
        """
        if db_type == "mysql":
            try:
                with self.get_mysql_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SHOW DATABASES LIKE '{database}'")
                        return cursor.fetchone() is not None
            except Exception as e:
                logger.error(f"Failed to verify MySQL database: {e}")
                return False

        elif db_type == "postgres":
            try:
                with self.get_postgres_connection("postgres") as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT 1 FROM pg_database WHERE datname = %s",
                            (database,)
                        )
                        return cursor.fetchone() is not None
            except Exception as e:
                logger.error(f"Failed to verify PostgreSQL database: {e}")
                return False

        return False

    def verify_table_exists(
        self, db_type: str, database: str, table: str
    ) -> bool:
        """
        验证表是否存在

        Args:
            db_type: 数据库类型 (mysql/postgres)
            database: 数据库名称
            table: 表名

        Returns:
            表是否存在
        """
        if db_type == "mysql":
            try:
                with self.get_mysql_connection(database) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SHOW TABLES LIKE '{table}'")
                        return cursor.fetchone() is not None
            except Exception as e:
                logger.error(f"Failed to verify MySQL table: {e}")
                return False

        elif db_type == "postgres":
            try:
                with self.get_postgres_connection(database) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = %s",
                            (table,)
                        )
                        return cursor.fetchone() is not None
            except Exception as e:
                logger.error(f"Failed to verify PostgreSQL table: {e}")
                return False

        return False

    def get_mysql_databases(self) -> List[str]:
        """
        获取所有 MySQL 数据库名称

        Returns:
            数据库名称列表
        """
        try:
            with self.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW DATABASES")
                    results = cursor.fetchall()
                    return [r["Database"] for r in results]
        except Exception as e:
            logger.error(f"Failed to get MySQL databases: {e}")
            return []

    def get_postgres_databases(self) -> List[str]:
        """
        获取所有 PostgreSQL 数据库名称

        Returns:
            数据库名称列表
        """
        try:
            with self.get_postgres_connection("postgres") as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
                    results = cursor.fetchall()
                    return [r[0] for r in results]
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL databases: {e}")
            return []

    # ========================================================================
    # 数据清理方法
    # ========================================================================

    def cleanup_test_data(self, db_type: str, database: str, tables: List[str]) -> bool:
        """
        清理测试数据

        Args:
            db_type: 数据库类型 (mysql/postgres)
            database: 数据库名称
            tables: 要清理的表名列表

        Returns:
            清理是否成功
        """
        try:
            if db_type == "mysql":
                with self.get_mysql_connection(database) as conn:
                    with conn.cursor() as cursor:
                        for table in tables:
                            cursor.execute(f"TRUNCATE TABLE {table}")
                        conn.commit()
                        logger.info(f"Cleaned up MySQL tables: {tables}")
                        return True

            elif db_type == "postgres":
                with self.get_postgres_connection(database) as conn:
                    with conn.cursor() as cursor:
                        for table in tables:
                            cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                        conn.commit()
                        logger.info(f"Cleaned up PostgreSQL tables: {tables}")
                        return True

        except Exception as e:
            logger.error(f"Failed to cleanup test data: {e}")
            return False

    # ========================================================================
    # E2E 环境检查
    # ========================================================================

    def check_e2e_environment(self) -> Dict[str, Any]:
        """
        检查 E2E 测试环境状态

        Returns:
            环境状态信息
        """
        result = {
            "mysql": {"connected": False, "databases": []},
            "postgres": {"connected": False, "databases": []},
            "e2e_databases_found": [],
        }

        # 检查 MySQL
        if self.connect_mysql():
            result["mysql"]["connected"] = True
            result["mysql"]["databases"] = self.get_mysql_databases()
            e2e_mysql_dbs = [db for db in result["mysql"]["databases"] if db.startswith("e2e_")]
            result["e2e_databases_found"].extend(e2e_mysql_dbs)
            self.mysql_conn.close()

        # 检查 PostgreSQL
        if self.connect_postgres():
            result["postgres"]["connected"] = True
            result["postgres"]["databases"] = self.get_postgres_databases()
            e2e_pg_dbs = [db for db in result["postgres"]["databases"] if db.startswith("e2e_")]
            result["e2e_databases_found"].extend(e2e_pg_dbs)
            self.postgres_conn.close()

        return result

    def get_data_summary(self) -> Dict[str, Any]:
        """
        获取 E2E 测试数据摘要

        Returns:
            数据摘要信息
        """
        summary = {
            "mysql": {},
            "postgres": {}
        }

        # MySQL 数据摘要
        mysql_dbs = ["e2e_ecommerce", "e2e_user_mgmt", "e2e_logs"]
        for db in mysql_dbs:
            if not self.verify_database_exists("mysql", db):
                continue
            tables = self.get_mysql_tables(db)
            summary["mysql"][db] = {}
            for table in tables:
                count = self.get_mysql_table_count(db, table)
                summary["mysql"][db][table] = count

        # PostgreSQL 数据摘要
        pg_dbs = ["e2e_ecommerce_pg", "e2e_user_mgmt_pg", "e2e_logs_pg"]
        for db in pg_dbs:
            if not self.verify_database_exists("postgres", db):
                continue
            tables = self.get_postgres_tables(db)
            summary["postgres"][db] = {}
            for table in tables:
                count = self.get_postgres_table_count(db, table)
                summary["postgres"][db][table] = count

        return summary
