"""
数据库基类配置
Sprint 4.2: SQLAlchemy 数据库连接配置
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 数据库配置 - 支持从 DATABASE_URL 或 MYSQL_* 变量构造
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # 从 MYSQL_* 环境变量构造 DATABASE_URL
    db_host = os.getenv("MYSQL_HOST", "localhost")
    db_port = os.getenv("MYSQL_PORT", "3306")
    db_user = os.getenv("MYSQL_USER", "root")
    db_password = os.getenv("MYSQL_PASSWORD")
    db_name = os.getenv("MYSQL_DATABASE", "onedata")

    if not db_password:
        raise ValueError(
            "Either DATABASE_URL or MYSQL_PASSWORD environment variable is required. "
            "Example: DATABASE_URL=mysql+pymysql://user:password@host:3306/database"
        )

    DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    logger.info(f"Constructed DATABASE_URL from MYSQL_* variables")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# 创建 SessionLocal 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Base 类
Base = declarative_base()


def get_db():
    """
    依赖注入函数：获取数据库会话
    用于 FastAPI/Flask 依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """创建所有数据库表（开发环境使用）"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
