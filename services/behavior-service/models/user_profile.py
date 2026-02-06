"""
用户画像模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, Boolean

from models.base import Base


class UserProfile(Base):
    """用户画像表"""
    __tablename__ = "user_profiles"

    id = Column(String(64), primary_key=True, comment="画像ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), nullable=False, unique=True, index=True, comment="用户ID")

    # 基础属性
    username = Column(String(100), comment="用户名")
    email = Column(String(200), comment="邮箱")
    department = Column(String(100), comment="部门")
    position = Column(String(100), comment="职位")
    level = Column(String(50), comment="级别")

    # 活跃度属性
    activity_level = Column(String(20), comment="活跃度等级: high/medium/low")
    last_active_at = Column(DateTime, comment="最后活跃时间")
    login_frequency = Column(Float, comment="登录频率(次/天)")
    avg_session_duration = Column(Float, comment="平均会话时长(分钟)")

    # 行为偏好
    preferred_modules = Column(JSON, comment="偏好模块列表")
    preferred_time_ranges = Column(JSON, comment="偏好时间段")
    common_actions = Column(JSON, comment="常用操作")

    # 技能标签
    skill_tags = Column(JSON, comment="技能标签")
    interest_tags = Column(JSON, comment="兴趣标签")

    # 统计指标
    total_sessions = Column(Integer, default=0, comment="总会话数")
    total_page_views = Column(Integer, default=0, comment="总页面浏览数")
    total_actions = Column(Integer, default=0, comment="总操作数")
    avg_daily_usage = Column(Float, comment="平均日使用时长(分钟)")

    # 分群标签
    segment_tags = Column(JSON, comment="分群标签")
    # 示例: ["power_user", "data_analyst", "early_adopter"]

    # 风险评分
    risk_score = Column(Float, default=0.0, comment="风险评分 0-100")
    risk_factors = Column(JSON, comment="风险因素")

    # 元数据
    profile_version = Column(Integer, default=1, comment="画像版本")
    meta_data = Column(JSON, comment="额外元数据")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "department": self.department,
            "position": self.position,
            "activity_level": self.activity_level,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "login_frequency": self.login_frequency,
            "avg_session_duration": self.avg_session_duration,
            "preferred_modules": self.preferred_modules,
            "preferred_time_ranges": self.preferred_time_ranges,
            "skill_tags": self.skill_tags,
            "interest_tags": self.interest_tags,
            "total_sessions": self.total_sessions,
            "total_page_views": self.total_page_views,
            "segment_tags": self.segment_tags,
            "risk_score": self.risk_score,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BehaviorMetric(Base):
    """行为指标统计表"""
    __tablename__ = "behavior_metrics"

    id = Column(String(64), primary_key=True, comment="指标ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")

    # 指标基本信息
    metric_type = Column(String(50), nullable=False, comment="指标类型")
    metric_name = Column(String(100), nullable=False, comment="指标名称")
    dimension = Column(String(50), comment="维度(user/page/module等)")

    # 时间维度
    date = Column(DateTime, comment="统计日期")
    hour = Column(Integer, comment="统计小时")
    period = Column(String(20), comment="统计周期: hourly/daily/weekly/monthly")

    # 指标值
    count = Column(Integer, default=0, comment="计数")
    unique_users = Column(Integer, default=0, comment="唯一用户数")
    avg_duration = Column(Float, comment="平均时长")
    avg_value = Column(Float, comment="平均值")

    # 额外数据
    segment_values = Column(JSON, comment="细分数据")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "dimension": self.dimension,
            "date": self.date.isoformat() if self.date else None,
            "period": self.period,
            "count": self.count,
            "unique_users": self.unique_users,
            "avg_duration": self.avg_duration,
        }


class BehaviorAnomaly(Base):
    """行为异常记录表"""
    __tablename__ = "behavior_anomalies"

    id = Column(String(64), primary_key=True, comment="异常ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), nullable=False, index=True, comment="用户ID")

    # 异常信息
    anomaly_type = Column(String(50), nullable=False, comment="异常类型")
    severity = Column(String(20), nullable=False, comment="严重程度: low/medium/high/critical")
    description = Column(Text, comment="异常描述")

    # 异常详情
    detected_at = Column(DateTime, nullable=False, comment="检测时间")
    behavior_data = Column(JSON, comment="相关行为数据")

    # 规则信息
    rule_id = Column(String(64), comment="触发规则ID")
    rule_name = Column(String(100), comment="规则名称")

    # 状态
    status = Column(String(20), default="open", comment="状态: open/investigated/resolved/false_positive")
    investigated_by = Column(String(64), comment="调查人ID")
    investigated_at = Column(DateTime, comment="调查时间")
    investigation_notes = Column(Text, comment="调查备注")

    # 处理动作
    actions_taken = Column(JSON, comment="采取的措施")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": self.status,
            "investigated_by": self.investigated_by,
            "actions_taken": self.actions_taken,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
