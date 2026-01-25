"""
数据标准模型
P5.5: 数据标准管理
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON
)
from .base import Base


class DataStandard(Base):
    """数据标准表"""
    __tablename__ = "data_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # 分类
    category = Column(String(64))  # naming, format, range, enum, reference

    # 标准规则
    rule_type = Column(String(32))  # regex, enum, range, reference, custom
    rule_config = Column(JSON)  # 规则配置

    # 适用范围
    apply_to = Column(JSON)  # 适用的字段类型或表
    data_types = Column(JSON)  # 适用的数据类型

    # 示例
    examples = Column(JSON)  # 正例和反例

    # 状态
    status = Column(String(32), default="active")  # draft, active, deprecated
    is_required = Column(Boolean, default=False)

    # 版本
    version = Column(String(32), default="1.0")

    # 统计
    apply_count = Column(Integer, default=0)  # 应用次数
    violation_count = Column(Integer, default=0)  # 违规次数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.standard_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "rule_type": self.rule_type,
            "rule_config": self.rule_config,
            "apply_to": self.apply_to,
            "data_types": self.data_types,
            "examples": self.examples,
            "status": self.status,
            "is_required": self.is_required,
            "version": self.version,
            "apply_count": self.apply_count,
            "violation_count": self.violation_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class StandardValidation(Base):
    """标准验证记录表"""
    __tablename__ = "standard_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    validation_id = Column(String(64), unique=True, nullable=False, index=True)

    # 关联标准
    standard_id = Column(String(64), index=True)
    standard_name = Column(String(255))

    # 验证目标
    target_type = Column(String(32))  # table, column, value
    target_id = Column(String(255))
    target_name = Column(String(255))

    # 验证数据
    input_value = Column(Text)

    # 验证结果
    is_valid = Column(Boolean)
    error_message = Column(Text)
    details = Column(JSON)

    # 时间戳
    validated_at = Column(DateTime, default=datetime.utcnow)
    validated_by = Column(String(64))

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.validation_id,
            "standard_id": self.standard_id,
            "standard_name": self.standard_name,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "input_value": self.input_value,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "details": self.details,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "validated_by": self.validated_by,
        }
