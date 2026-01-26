"""
用户画像数据模型
Phase 1.3: 用户行为分析、分群、标签系统
"""

import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, BigInteger, String, Text, Integer, Float, Boolean, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


def generate_profile_id() -> str:
    """生成画像ID"""
    return f"prof_{uuid.uuid4().hex[:12]}"


def generate_segment_id() -> str:
    """生成分群ID"""
    return f"seg_{uuid.uuid4().hex[:8]}"


class UserProfile(Base):
    """用户画像表"""
    __tablename__ = "user_profiles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    profile_id = Column(String(64), unique=True, nullable=False, index=True, comment='画像ID')

    # 关联用户
    user_id = Column(String(128), nullable=False, index=True, comment='用户ID')
    username = Column(String(128), comment='用户名')

    # 行为标签 (JSON)
    behavior_tags = Column(Text, comment='行为标签 [{"tag": "活跃", "score": 0.9}, ...]')

    # 活跃度分数 (0-100)
    activity_score = Column(Float, default=0, comment='活跃度分数')

    # 分群信息
    segment_id = Column(String(64), ForeignKey('user_segments.segment_id'), index=True, comment='所属分群ID')

    # 偏好特征 (JSON)
    preference_features = Column(JSON, comment='偏好特征 {"preferred_hours": [...], "preferred_modules": [...]}')

    # 行为统计
    login_count = Column(Integer, default=0, comment='登录次数')
    last_login_at = Column(TIMESTAMP, comment='最后登录时间')
    login_days = Column(Integer, default=0, comment='活跃天数')

    # 功能使用统计 (JSON)
    module_usage = Column(Text, comment='模块使用统计 {"bi": 50, "etl": 30, ...}')

    # 时间偏好
    peak_hours = Column(Text, comment='活跃时段 JSON: [{"hour": 9, "count": 100}, ...]')
    peak_days = Column(Text, comment='活跃星期 JSON: [{"day": 1, "count": 50}, ...]')

    # 数据操作统计
    query_count = Column(Integer, default=0, comment='查询次数')
    export_count = Column(Integer, default=0, comment='导出次数')
    create_count = Column(Integer, default=0, comment='创建次数')

    # 异常标记
    is_risk_user = Column(Boolean, default=False, comment='是否风险用户')
    risk_reason = Column(String(255), comment='风险原因')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    last_analyzed_at = Column(TIMESTAMP, comment='最后分析时间')

    # 关系
    segment = relationship("UserSegment", back_populates="users")

    def get_behavior_tags(self) -> list:
        """获取行为标签"""
        if not self.behavior_tags:
            return []
        try:
            return json.loads(self.behavior_tags)
        except json.JSONDecodeError:
            return []

    def set_behavior_tags(self, tags: list):
        """设置行为标签"""
        self.behavior_tags = json.dumps(tags, ensure_ascii=False)

    def get_peak_hours(self) -> list:
        """获取活跃时段"""
        if not self.peak_hours:
            return []
        try:
            return json.loads(self.peak_hours)
        except json.JSONDecodeError:
            return []

    def set_peak_hours(self, hours: list):
        """设置活跃时段"""
        self.peak_hours = json.dumps(hours, ensure_ascii=False)

    def get_peak_days(self) -> list:
        """获取活跃星期"""
        if not self.peak_days:
            return []
        try:
            return json.loads(self.peak_days)
        except json.JSONDecodeError:
            return []

    def set_peak_days(self, days: list):
        """设置活跃星期"""
        self.peak_days = json.dumps(days, ensure_ascii=False)

    def get_module_usage(self) -> dict:
        """获取模块使用统计"""
        if not self.module_usage:
            return {}
        try:
            return json.loads(self.module_usage)
        except json.JSONDecodeError:
            return {}

    def set_module_usage(self, usage: dict):
        """设置模块使用统计"""
        self.module_usage = json.dumps(usage, ensure_ascii=False)

    def add_tag(self, tag: str, score: float = 1.0):
        """添加标签"""
        tags = self.get_behavior_tags()
        existing = next((t for t in tags if t["tag"] == tag), None)
        if existing:
            existing["score"] = max(existing["score"], score)
            existing["updated_at"] = datetime.utcnow().isoformat()
        else:
            tags.append({
                "tag": tag,
                "score": score,
                "created_at": datetime.utcnow().isoformat(),
            })
        self.set_behavior_tags(tags)

    def remove_tag(self, tag: str):
        """移除标签"""
        tags = self.get_behavior_tags()
        tags = [t for t in tags if t["tag"] != tag]
        self.set_behavior_tags(tags)

    def to_dict(self):
        """转换为字典"""
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "username": self.username,
            "behavior_tags": self.get_behavior_tags(),
            "activity_score": round(self.activity_score, 2),
            "segment_id": self.segment_id,
            "preference_features": self.preference_features,
            "login_count": self.login_count,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "login_days": self.login_days,
            "module_usage": self.get_module_usage(),
            "peak_hours": self.get_peak_hours(),
            "peak_days": self.get_peak_days(),
            "query_count": self.query_count,
            "export_count": self.export_count,
            "create_count": self.create_count,
            "is_risk_user": self.is_risk_user,
            "risk_reason": self.risk_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
        }


class UserSegment(Base):
    """用户分群表"""
    __tablename__ = "user_segments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), unique=True, nullable=False, index=True, comment='分群ID')

    # 分群基本信息
    segment_name = Column(String(128), nullable=False, comment='分群名称')
    segment_type = Column(String(32), nullable=False, comment='分群类型: active, exploratory, conservative, churned, new, power')
    description = Column(Text, comment='分群描述')

    # 分群规则 (JSON)
    criteria = Column(JSON, comment='分群标准 {"activity_score_min": 80, "tags": ["活跃"]}')

    # 分群特征
    characteristics = Column(JSON, comment='分群特征 {"avg_activity": 90, "common_tags": ["活跃", "专家"]}')

    # 统计信息
    user_count = Column(Integer, default=0, comment='用户数量')

    # 营销/运营策略
    strategy = Column(Text, comment='运营策略建议')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_system = Column(Boolean, default=False, comment='是否系统预置')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    last_rebuilt_at = Column(TIMESTAMP, comment='最后重建时间')

    # 关系
    users = relationship("UserProfile", back_populates="segment")

    def to_dict(self):
        """转换为字典"""
        return {
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "segment_type": self.segment_type,
            "description": self.description,
            "criteria": self.criteria,
            "characteristics": self.characteristics,
            "user_count": self.user_count,
            "strategy": self.strategy,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_rebuilt_at": self.last_rebuilt_at.isoformat() if self.last_rebuilt_at else None,
        }


class UserTag(Base):
    """用户标签定义表"""
    __tablename__ = "user_tags"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_id = Column(String(64), unique=True, nullable=False, index=True, comment='标签ID')

    # 标签信息
    tag_name = Column(String(64), nullable=False, unique=True, comment='标签名称')
    tag_category = Column(String(32), comment='标签分类: behavior, preference, ability, risk')
    display_name = Column(String(128), comment='显示名称')
    description = Column(Text, comment='标签描述')

    # 标签规则 (JSON)
    rules = Column(JSON, comment='标签规则 {"type": "activity", "threshold": 100}')

    # 标签配置
    color = Column(String(16), comment='标签颜色')
    icon = Column(String(32), comment='标签图标')
    priority = Column(Integer, default=0, comment='优先级')

    # 自动打标配置
    is_auto = Column(Boolean, default=False, comment='是否自动打标')
    update_frequency = Column(String(32), comment='更新频率: daily, weekly, monthly')

    # 统计
    user_count = Column(Integer, default=0, comment='拥有此标签的用户数')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否启用')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "tag_id": self.tag_id,
            "tag_name": self.tag_name,
            "tag_category": self.tag_category,
            "display_name": self.display_name,
            "description": self.description,
            "rules": self.rules,
            "color": self.color,
            "icon": self.icon,
            "priority": self.priority,
            "is_auto": self.is_auto,
            "update_frequency": self.update_frequency,
            "user_count": self.user_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BehaviorAnomaly(Base):
    """行为异常记录表"""
    __tablename__ = "behavior_anomalies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    anomaly_id = Column(String(64), unique=True, nullable=False, index=True, comment='异常ID')

    # 关联用户
    user_id = Column(String(128), nullable=False, index=True, comment='用户ID')
    username = Column(String(128), comment='用户名')

    # 异常信息
    anomaly_type = Column(String(32), nullable=False, comment='异常类型: login_anomaly, data_export, unusual_access, frequency_surge')
    severity = Column(String(16), default='medium', comment='严重程度: low, medium, high, critical')

    # 异常描述
    description = Column(Text, comment='异常描述')
    details = Column(JSON, comment='异常详情')

    # 状态
    status = Column(String(16), default='open', comment='状态: open, investigating, resolved, false_positive')

    # 处理信息
    handled_by = Column(String(128), comment='处理人')
    handled_at = Column(TIMESTAMP, comment='处理时间')
    resolution = Column(Text, comment='处理结果')

    # 时间戳
    detected_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='检测时间')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "anomaly_id": self.anomaly_id,
            "user_id": self.user_id,
            "username": self.username,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "details": self.details,
            "status": self.status,
            "handled_by": self.handled_by,
            "handled_at": self.handled_at.isoformat() if self.handled_at else None,
            "resolution": self.resolution,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
