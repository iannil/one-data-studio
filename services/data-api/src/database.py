"""
数据库连接配置
管理 MySQL 数据库连接和会话

Sprint 8: 连接池优化和慢查询日志
"""

import os
import time
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from models import Base

logger = logging.getLogger(__name__)

# Sprint 8: 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))


class DatabaseManager:
    """数据库管理器 - Sprint 8: 优化版本"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        self._slow_query_count = 0
        self._query_count = 0

    def init_db(self):
        """初始化数据库连接"""
        if self._initialized:
            return

        # 从环境变量获取数据库配置
        # NOTE: For consistency, consider using shared.config.get_config().database
        # instead of reading env vars directly. The shared config provides:
        # - Centralized validation
        # - Default value management
        # - High availability (HA) support
        db_host = os.getenv('MYSQL_HOST', 'mysql.one-data-infra.svc.cluster.local')
        db_port = int(os.getenv('MYSQL_PORT', '3306'))
        db_user = os.getenv('MYSQL_USER', 'one_data')
        db_password = os.getenv('MYSQL_PASSWORD')
        db_name = os.getenv('MYSQL_DATABASE', 'one_data_studio')

        # 检查必需的凭据
        if not db_password:
            raise ValueError(
                "MYSQL_PASSWORD environment variable is required. "
                "Please set it before starting the application."
            )

        # 连接池参数 - 已优化默认值，可根据负载测试调整
        # NOTE: These values should be coordinated with shared/config.py DatabaseConfig
        pool_size = int(os.getenv('DB_POOL_SIZE', '20'))  # Higher values need monitoring
        max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '40'))  # Total max = pool_size + max_overflow
        pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        pool_pre_ping = os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true'

        # 创建数据库 URL
        database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

        logger.info(f"Connecting to MySQL at {db_host}:{db_port}/{db_name}")
        logger.info(f"Pool config: size={pool_size}, max_overflow={max_overflow}, recycle={pool_recycle}")

        # 创建引擎
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,  # 连接健康检查
            echo=False,
            # Sprint 8: 连接池事件监听
            connect_args={
                "connect_timeout": 10,
                "read_timeout": 30,
                "write_timeout": 30,
            }
        )

        # Sprint 8: 添加慢查询日志
        self._setup_slow_query_logging()

        # 设置会话工厂
        self.SessionLocal = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False  # 性能优化：避免提交后对象过期
        ))

        self._initialized = True
        logger.info("Database initialized successfully")

    def _setup_slow_query_logging(self):
        """设置慢查询日志 - Sprint 8"""
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement

        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            self._query_count += 1

            # 记录慢查询
            if total > SLOW_QUERY_THRESHOLD:
                self._slow_query_count += 1
                logger.warning(
                    f"Slow query ({total:.3f}s): {statement[:200]}..."
                )

            # 每 1000 次查询输出统计
            if self._query_count % 1000 == 0:
                slow_ratio = self._slow_query_count / self._query_count * 100
                logger.info(
                    f"Query stats: {self._query_count} queries, "
                    f"{self._slow_query_count} slow ({slow_ratio:.1f}%)"
                )

    @property
    def pool_status(self) -> dict:
        """获取连接池状态 - Sprint 8"""
        if not self.engine or not self.engine.pool:
            return {}

        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": pool.max_overflow,
            "query_count": self._query_count,
            "slow_query_count": self._slow_query_count
        }

    def create_tables(self):
        """创建所有表（开发环境使用）"""
        if not self._initialized:
            self.init_db()
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        if not self._initialized:
            self.init_db()
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self):
        """获取数据库会话（上下文管理器）"""
        if not self._initialized:
            self.init_db()

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """关闭数据库连接"""
        if self.SessionLocal:
            self.SessionLocal.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db():
    """获取数据库会话的便捷函数"""
    return db_manager.get_session()


def init_database():
    """初始化数据库"""
    db_manager.init_db()


def check_db_health():
    """检查数据库健康状态"""
    try:
        with db_manager.get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
