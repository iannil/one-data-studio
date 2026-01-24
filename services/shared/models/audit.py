"""
审计日志数据模型
Sprint 29: 企业安全强化

提供审计日志的数据库存储模型
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Integer, Index, JSON
from sqlalchemy.ext.declarative import declarative_base

AuditLogBase = declarative_base()


class AuditLog(AuditLogBase):
    """
    审计日志表

    存储所有审计事件用于安全审计和合规
    """
    __tablename__ = 'audit_logs'

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 事件信息
    action = Column(String(50), nullable=False, index=True, comment='动作类型')
    severity = Column(String(20), nullable=False, default='info', comment='严重级别')
    status = Column(String(20), nullable=False, default='success', comment='执行状态')

    # 用户信息
    user_id = Column(String(64), nullable=True, index=True, comment='用户ID')
    username = Column(String(128), nullable=True, comment='用户名')
    tenant_id = Column(String(64), nullable=True, index=True, comment='租户ID')

    # 请求信息
    ip_address = Column(String(45), nullable=True, comment='IP地址')
    user_agent = Column(String(500), nullable=True, comment='User Agent')
    request_id = Column(String(64), nullable=True, index=True, comment='请求ID')

    # 资源信息
    resource_type = Column(String(50), nullable=True, index=True, comment='资源类型')
    resource_id = Column(String(128), nullable=True, index=True, comment='资源ID')

    # 错误信息
    error_code = Column(String(50), nullable=True, comment='错误码')
    error_message = Column(Text, nullable=True, comment='错误消息')

    # 详细信息
    extra_metadata = Column(JSON, nullable=True, comment='元数据')

    # 时间戳
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 复合索引优化查询
    __table_args__ = (
        Index('ix_audit_logs_user_action', 'user_id', 'action'),
        Index('ix_audit_logs_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_logs_timestamp_desc', timestamp.desc()),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'comment': '审计日志表'
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'action': self.action,
            'severity': self.severity,
            'status': self.status,
            'user_id': self.user_id,
            'username': self.username,
            'tenant_id': self.tenant_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'extra_metadata': self.extra_metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_event(cls, event) -> 'AuditLog':
        """
        从 AuditEvent 创建 AuditLog 实例

        Args:
            event: AuditEvent 实例

        Returns:
            AuditLog 实例
        """
        return cls(
            action=event.action.value if hasattr(event.action, 'value') else str(event.action),
            severity=event.severity.value if hasattr(event.severity, 'value') else str(event.severity),
            status=event.status,
            user_id=event.user_id,
            username=event.username,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            error_code=event.error_code,
            error_message=event.error_message,
            extra_metadata=event.metadata,
            timestamp=event.timestamp,
        )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"


# 审计日志保留策略配置
class AuditRetentionPolicy:
    """审计日志保留策略"""

    # 默认保留天数
    DEFAULT_RETENTION_DAYS = 90

    # 敏感操作保留天数（更长）
    SENSITIVE_RETENTION_DAYS = 365

    # 敏感操作列表
    SENSITIVE_ACTIONS = {
        'login', 'logout', 'login_failed',
        'password_change', 'password_reset',
        'permission_change', 'config_change',
        'data_delete', 'workflow_delete', 'document_delete'
    }

    @classmethod
    def get_retention_days(cls, action: str) -> int:
        """获取指定操作的保留天数"""
        if action in cls.SENSITIVE_ACTIONS:
            return cls.SENSITIVE_RETENTION_DAYS
        return cls.DEFAULT_RETENTION_DAYS
