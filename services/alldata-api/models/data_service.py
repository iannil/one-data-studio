"""
数据服务模型
P5.6: 数据服务发布
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON, Float
)
from .base import Base


class DataService(Base):
    """数据服务表"""
    __tablename__ = "data_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 服务类型
    service_type = Column(String(32))  # api, stream, file, websocket

    # 数据源
    source_type = Column(String(32))  # sql, table, dataset, custom
    source_id = Column(String(64))
    sql_query = Column(Text)

    # 接口配置
    path = Column(String(255))  # API 路径
    method = Column(String(16), default="GET")  # HTTP 方法
    parameters = Column(JSON)  # 请求参数定义
    response_format = Column(String(32), default="json")  # json, xml, csv

    # 认证配置
    auth_type = Column(String(32), default="none")  # none, api_key, oauth, jwt
    auth_config = Column(JSON)

    # 限流配置
    rate_limit_enabled = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)

    # 缓存配置
    cache_enabled = Column(Boolean, default=True)
    cache_ttl = Column(Integer, default=300)  # 秒

    # 状态
    status = Column(String(32), default="stopped")  # stopped, running, error

    # 版本
    version = Column(String(32), default="v1")

    # 统计
    total_calls = Column(Integer, default=0)
    success_calls = Column(Integer, default=0)
    error_calls = Column(Integer, default=0)
    avg_response_time_ms = Column(Float)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.service_id,
            "name": self.name,
            "description": self.description,
            "service_type": self.service_type,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "sql_query": self.sql_query,
            "path": self.path,
            "method": self.method,
            "parameters": self.parameters,
            "response_format": self.response_format,
            "auth_type": self.auth_type,
            "auth_config": self.auth_config,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_day": self.rate_limit_per_day,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "status": self.status,
            "version": self.version,
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "error_calls": self.error_calls,
            "avg_response_time_ms": self.avg_response_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "created_by": self.created_by,
        }


class ServiceCallLog(Base):
    """服务调用日志表"""
    __tablename__ = "service_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True)

    # 关联服务
    service_id = Column(String(64), index=True)

    # 请求信息
    request_path = Column(String(512))
    request_method = Column(String(16))
    request_params = Column(JSON)
    request_headers = Column(JSON)
    client_ip = Column(String(64))
    user_agent = Column(String(512))

    # 响应信息
    response_status = Column(Integer)
    response_size_bytes = Column(Integer)
    response_time_ms = Column(Integer)

    # 错误信息
    error_code = Column(String(32))
    error_message = Column(Text)

    # 时间戳
    called_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.log_id,
            "service_id": self.service_id,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "request_params": self.request_params,
            "client_ip": self.client_ip,
            "response_status": self.response_status,
            "response_size_bytes": self.response_size_bytes,
            "response_time_ms": self.response_time_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "called_at": self.called_at.isoformat() if self.called_at else None,
        }
