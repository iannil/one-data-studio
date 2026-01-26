"""
API端点和调用日志数据模型
Phase 2.2: API可视化管理
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, TIMESTAMP, JSON, Index
from sqlalchemy.sql import func

from .base import Base


def generate_api_endpoint_id() -> str:
    """生成API端点ID"""
    return f"api_{uuid.uuid4().hex[:12]}"


def generate_api_call_id() -> str:
    """生成API调用ID"""
    return f"call_{uuid.uuid4().hex[:12]}"


class ApiEndpoint(Base):
    """API端点表"""
    __tablename__ = "api_endpoints"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    endpoint_id = Column(String(64), unique=True, nullable=False, index=True, comment='端点ID')

    # 基本信息
    path = Column(String(512), nullable=False, comment='API路径')
    method = Column(String(16), nullable=False, comment='HTTP方法')
    service = Column(String(64), comment='服务名称')
    blueprint = Column(String(64), comment='蓝图名称')

    # 文档
    endpoint_name = Column(String(255), comment='端点名称')
    description = Column(Text, comment='API描述')
    summary = Column(Text, comment='简要说明')

    # 请求/响应模式
    request_schema = Column(JSON, comment='请求模式 (OpenAPI)')
    response_schema = Column(JSON, comment='响应模式 (OpenAPI)')

    # 参数定义
    parameters = Column(JSON, comment='路径参数定义')
    query_params = Column(JSON, comment='查询参数定义')
    body_params = Column(JSON, comment='请求体参数定义')

    # 标签
    tags = Column(JSON, comment='标签列表')

    # 访问控制
    requires_auth = Column(Boolean, default=True, comment='是否需要认证')
    required_permissions = Column(JSON, comment='所需权限列表')

    # 统计
    call_count = Column(Integer, default=0, comment='调用次数')
    error_count = Column(Integer, default=0, comment='错误次数')
    avg_duration_ms = Column(Integer, comment='平均耗时（毫秒）')

    # 时间戳
    first_call = Column(TIMESTAMP, comment='首次调用时间')
    last_call = Column(TIMESTAMP, comment='最后调用时间')

    def get_tags(self) -> list:
        """获取标签列表"""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list):
        """设置标签列表"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def get_required_permissions(self) -> list:
        """获取所需权限列表"""
        if not self.required_permissions:
            return []
        try:
            return json.loads(self.required_permissions)
        except json.JSONDecodeError:
            return []

    def set_required_permissions(self, permissions: list):
        """设置所需权限列表"""
        self.required_permissions = json.dumps(permissions, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "endpoint_id": self.endpoint_id,
            "path": self.path,
            "method": self.method,
            "service": self.service,
            "blueprint": self.blueprint,
            "endpoint_name": self.endpoint_name,
            "description": self.description,
            "summary": self.summary,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
            "parameters": self.parameters,
            "query_params": self.query_params,
            "body_params": self.body_params,
            "tags": self.get_tags(),
            "requires_auth": self.requires_auth,
            "required_permissions": self.get_required_permissions(),
            "call_count": self.call_count,
            "error_count": self.error_count,
            "avg_duration_ms": self.avg_duration_ms,
            "first_call": self.first_call.isoformat() if self.first_call else None,
            "last_call": self.last_call.isoformat() if self.last_call else None,
        }


class ApiCallLog(Base):
    """API调用日志表"""
    __tablename__ = "api_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    call_id = Column(String(64), unique=True, nullable=False, index=True, comment='调用ID')

    # 请求信息
    path = Column(String(512), nullable=False, index=True, comment='请求路径')
    method = Column(String(16), nullable=False, comment='HTTP方法')
    query_params = Column(Text, comment='查询参数')
    request_body = Column(Text, comment='请求体')
    request_headers = Column(Text, comment='请求头')

    # 用户信息
    user_id = Column(String(128), index=True, comment='用户ID')
    username = Column(String(128), comment='用户名')

    # 响应信息
    status_code = Column(Integer, nullable=False, comment='响应状态码')
    response_body = Column(Text, comment='响应体')
    error_message = Column(Text, comment='错误信息')

    # 性能
    duration_ms = Column(Integer, comment='耗时（毫秒）')

    # 额外信息
    client_ip = Column(String(64), comment='客户端IP')
    user_agent = Column(String(512), comment='User-Agent')
    extra_data = Column(Text, comment='额外数据 (JSON)')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='创建时间')

    def get_query_params(self) -> dict:
        """获取查询参数"""
        if not self.query_params:
            return {}
        try:
            return json.loads(self.query_params)
        except json.JSONDecodeError:
            return {}

    def get_request_body(self) -> Any:
        """获取请求体"""
        if not self.request_body:
            return None
        try:
            return json.loads(self.request_body)
        except json.JSONDecodeError:
            return self.request_body

    def to_dict(self):
        """转换为字典"""
        return {
            "call_id": self.call_id,
            "path": self.path,
            "method": self.method,
            "user_id": self.user_id,
            "username": self.username,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "client_ip": self.client_ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
