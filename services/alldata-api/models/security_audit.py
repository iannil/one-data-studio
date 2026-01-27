"""
数据安全审计日志模型
Phase 1.1: 数据安全操作审计追踪
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, TIMESTAMP, JSON
from sqlalchemy.sql import func

from .base import Base


class DataSecurityAuditLog(Base):
    """数据安全审计日志表"""
    __tablename__ = "data_security_audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audit_id = Column(String(64), unique=True, nullable=False, index=True, comment='审计ID')

    # 操作信息
    operation = Column(String(32), nullable=False, comment='操作类型: scan, mask, encrypt, decrypt, verify')
    operation_status = Column(String(16), default='success', comment='操作状态: success, failed, partial')

    # 操作人
    user_id = Column(String(128), nullable=False, comment='操作用户ID')
    user_name = Column(String(128), comment='操作用户名')
    ip_address = Column(String(64), comment='操作IP地址')
    user_agent = Column(String(512), comment='用户代理')

    # 操作目标
    resource_type = Column(String(32), nullable=False, comment='资源类型: database, table, column, dataset, scan_task')
    resource_id = Column(String(128), comment='资源ID')
    resource_name = Column(String(255), comment='资源名称')

    # 操作详情
    details = Column(JSON, comment='操作详情（JSON）')
    affected_rows = Column(Integer, default=0, comment='影响的行数')
    affected_columns = Column(Integer, default=0, comment='影响的列数')

    # 敏感数据相关
    sensitivity_types = Column(Text, comment='涉及的敏感类型列表（JSON）')
    masking_strategies = Column(Text, comment='使用的脱敏策略列表（JSON）')

    # 执行时间
    duration_ms = Column(Integer, comment='执行耗时（毫秒）')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 错误信息（如果失败）
    error_message = Column(Text, comment='错误信息')

    def get_sensitivity_types(self) -> list:
        """获取敏感类型列表"""
        if not self.sensitivity_types:
            return []
        import json
        try:
            return json.loads(self.sensitivity_types)
        except json.JSONDecodeError:
            return []

    def set_sensitivity_types(self, types: list):
        """设置敏感类型列表"""
        import json
        self.sensitivity_types = json.dumps(types, ensure_ascii=False)

    def get_masking_strategies(self) -> list:
        """获取脱敏策略列表"""
        if not self.masking_strategies:
            return []
        import json
        try:
            return json.loads(self.masking_strategies)
        except json.JSONDecodeError:
            return []

    def set_masking_strategies(self, strategies: list):
        """设置脱敏策略列表"""
        import json
        self.masking_strategies = json.dumps(strategies, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "audit_id": self.audit_id,
            "operation": self.operation,
            "operation_status": self.operation_status,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "details": self.details,
            "affected_rows": self.affected_rows,
            "affected_columns": self.affected_columns,
            "sensitivity_types": self.get_sensitivity_types(),
            "masking_strategies": self.get_masking_strategies(),
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "error_message": self.error_message,
        }


class MaskingRule(Base):
    """脱敏规则配置表（持久化）"""
    __tablename__ = "masking_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True, comment='规则ID')

    # 基本信息
    name = Column(String(128), nullable=False, comment='规则名称')
    description = Column(Text, comment='规则描述')

    # 匹配条件
    sensitivity_type = Column(String(64), default='any', comment='敏感类型: pii, financial, health, credential, any')
    sensitivity_level = Column(String(32), default='any', comment='敏感级别: public, internal, confidential, restricted, any')
    column_pattern = Column(String(255), comment='列名匹配正则表达式')
    data_type = Column(String(32), comment='数据类型: string, number, date')

    # 脱敏配置
    strategy = Column(String(32), nullable=False, comment='脱敏策略: partial_mask, full_mask, hash, encrypt, etc.')
    options = Column(JSON, comment='策略选项（JSON）')

    # 状态
    enabled = Column(Integer, default=1, comment='是否启用: 0-禁用, 1-启用')
    priority = Column(Integer, default=0, comment='优先级，数字越大优先级越高')
    is_system = Column(Integer, default=0, comment='是否系统预置: 0-自定义, 1-系统')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    created_by = Column(String(128), comment='创建者')

    def to_dict(self):
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "sensitivity_type": self.sensitivity_type,
            "sensitivity_level": self.sensitivity_level,
            "column_pattern": self.column_pattern,
            "data_type": self.data_type,
            "strategy": self.strategy,
            "options": self.options,
            "enabled": bool(self.enabled),
            "priority": self.priority,
            "is_system": bool(self.is_system),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
