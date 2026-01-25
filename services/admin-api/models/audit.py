"""
审计日志数据模型
Admin API - AuditLog 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func

from .base import Base


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audit_id = Column(String(64), unique=True, nullable=False, comment='审计日志唯一标识')
    action = Column(String(32), nullable=False, comment='操作类型: login, logout, create, update, delete, execute, export, import, start, stop, deploy, undeploy')
    resource_type = Column(String(64), nullable=False, comment='资源类型: user, group, role, datasource, dataset, workflow, experiment, model, service, prompt, knowledge, metric, settings, system')
    resource_id = Column(String(64), comment='资源ID')
    resource_name = Column(String(255), comment='资源名称')
    user_id = Column(String(64), nullable=False, comment='操作用户ID')
    username = Column(String(128), nullable=False, comment='操作用户名')
    user_ip = Column(String(64), comment='用户IP')
    user_agent = Column(String(512), comment='用户代理')
    success = Column(Boolean, default=True, comment='操作是否成功')
    error_message = Column(Text, comment='错误信息')
    changes = Column(Text, comment='变更内容 (JSON: {before, after})')
    request_id = Column(String(64), comment='请求ID')
    extra_data = Column(Text, comment='扩展数据 (JSON)')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    def get_changes(self) -> dict:
        """获取变更内容"""
        if not self.changes:
            return {}
        try:
            return json.loads(self.changes)
        except json.JSONDecodeError:
            return {}

    def set_changes(self, before: dict = None, after: dict = None):
        """设置变更内容"""
        self.changes = json.dumps({
            "before": before,
            "after": after
        }, ensure_ascii=False)

    def get_extra_data(self) -> dict:
        """获取扩展数据"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except json.JSONDecodeError:
            return {}

    def set_extra_data(self, data: dict):
        """设置扩展数据"""
        self.extra_data = json.dumps(data, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "audit_id": self.audit_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "user_id": self.user_id,
            "username": self.username,
            "user_ip": self.user_ip,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "changes": self.get_changes(),
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
