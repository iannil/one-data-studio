"""
数据库连接配置
管理 MySQL 数据库连接和会话
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False

    def init_db(self):
        """初始化数据库连接"""
        if self._initialized:
            return

        # 从环境变量获取数据库配置
        db_host = os.getenv('MYSQL_HOST', 'mysql.one-data-infra.svc.cluster.local')
        db_port = int(os.getenv('MYSQL_PORT', '3306'))
        db_user = os.getenv('MYSQL_USER', 'one_data')
        db_password = os.getenv('MYSQL_PASSWORD', 'OneDataPassword123!')
        db_name = os.getenv('MYSQL_DATABASE', 'one_data_alldata')

        # 创建数据库 URL
        database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

        logger.info(f"Connecting to MySQL at {db_host}:{db_port}/{db_name}")

        # 创建引擎
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )

        # 设置会话工厂
        self.SessionLocal = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        ))

        self._initialized = True
        logger.info("Database initialized successfully")

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
            session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
