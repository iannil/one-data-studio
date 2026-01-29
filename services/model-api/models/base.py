"""
数据库基类配置
Model API - MLOps 平台数据库连接配置
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 数据库配置 - 必须从环境变量读取
# 支持 DATABASE_URL 或 MODEL_DATABASE_URL 作为变量名
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("MODEL_DATABASE_URL") or os.getenv("CUBE_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Example: mysql+pymysql://user:password@host:3306/database"
    )

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
    用于 Flask/FastAPI 依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
