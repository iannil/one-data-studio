"""
数据库基类配置
Sprint 4.2: SQLAlchemy 数据库连接配置
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://one_data:OneDataPassword123!@mysql.one-data-infra.svc.cluster.local:3306/one_data_bisheng"
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
    用于 FastAPI/Flask 依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
