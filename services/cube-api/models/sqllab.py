"""
SQL Lab 模型
P4.6: SQL Lab
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class SqlQuery(Base):
    """SQL 查询执行记录表"""
    __tablename__ = "sql_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), unique=True, nullable=False, index=True)

    # 查询内容
    sql_content = Column(Text, nullable=False)
    database_name = Column(String(128))

    # 执行状态
    status = Column(String(32), default="pending")  # pending, running, completed, failed, cancelled
    error_message = Column(Text)

    # 执行时间
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)

    # 结果
    row_count = Column(Integer, default=0)
    result_path = Column(String(512))  # 大结果集存储路径
    columns = Column(JSON)  # [{name, type}]
    preview_data = Column(JSON)  # 前 100 行数据

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.query_id,
            "sql_content": self.sql_content,
            "database_name": self.database_name,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "row_count": self.row_count,
            "columns": self.columns,
            "preview_data": self.preview_data,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SavedQuery(Base):
    """保存的 SQL 查询表"""
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 查询内容
    sql_content = Column(Text, nullable=False)
    database_name = Column(String(128))

    # 分类
    category = Column(String(64))

    # 标签
    tags = Column(JSON)

    # 共享
    is_public = Column(Boolean, default=False)

    # 使用统计
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime)

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.query_id,
            "name": self.name,
            "description": self.description,
            "sql_content": self.sql_content,
            "database_name": self.database_name,
            "category": self.category,
            "tags": self.tags,
            "is_public": self.is_public,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DatabaseConnection(Base):
    """数据库连接表"""
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 连接类型
    database_type = Column(String(32), nullable=False)  # mysql, postgresql, clickhouse, hive, etc.

    # 连接配置
    host = Column(String(255))
    port = Column(Integer)
    database = Column(String(128))
    username = Column(String(128))
    # 密码应加密存储
    password_encrypted = Column(String(512))

    # 额外配置
    extra_config = Column(JSON)

    # 状态
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime)
    test_status = Column(String(32))  # success, failed

    # 时间戳
    created_by = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典（不包含密码）"""
        return {
            "id": self.connection_id,
            "name": self.name,
            "description": self.description,
            "database_type": self.database_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "extra_config": self.extra_config,
            "is_active": self.is_active,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "test_status": self.test_status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
