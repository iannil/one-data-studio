"""
用户行为模型
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, Boolean, BigInteger, Index
from sqlalchemy.dialects.mysql import BIGINT

from models.base import Base


class UserBehavior(Base):
    """用户行为记录表"""
    __tablename__ = "user_behaviors"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="行为ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), nullable=False, index=True, comment="用户ID")
    session_id = Column(String(64), index=True, comment="会话ID")

    # 行为基本信息
    behavior_type = Column(String(50), nullable=False, index=True, comment="行为类型")
    action = Column(String(100), comment="操作名称")
    target_type = Column(String(50), comment="目标类型(page/button/api等)")
    target_id = Column(String(200), comment="目标ID")

    # 行为详情
    page_url = Column(String(500), comment="页面URL")
    page_title = Column(String(200), comment="页面标题")
    referrer = Column(String(500), comment="来源页面")
    module = Column(String(100), comment="功能模块")

    # 客户端信息
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    device_type = Column(String(20), comment="设备类型(pc/mobile/tablet)")
    browser = Column(String(50), comment="浏览器")
    os = Column(String(50), comment="操作系统")

    # 性能信息
    duration = Column(Float, comment="停留时长(秒)")
    load_time = Column(Float, comment="页面加载时间(毫秒)")

    # 额外数据
    meta_data = Column(JSON, comment="额外元数据")

    # 时间信息
    occurred_at = Column(DateTime, nullable=False, index=True, comment="行为发生时间")
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")

    # 索引
    __table_args__ = (
        Index('idx_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_behavior_type', 'behavior_type'),
        Index('idx_occurred_at', 'occurred_at'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "behavior_type": self.behavior_type,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "referrer": self.referrer,
            "module": self.module,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "browser": self.browser,
            "os": self.os,
            "duration": self.duration,
            "load_time": self.load_time,
            "meta_data": self.meta_data,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True, comment="会话ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), nullable=False, index=True, comment="用户ID")

    # 会话信息
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration = Column(Float, comment="会话时长(秒)")

    # 访问信息
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    device_type = Column(String(20), comment="设备类型")
    location = Column(String(100), comment="地理位置")

    # 活动统计
    page_views = Column(Integer, default=0, comment="页面浏览数")
    clicks = Column(Integer, default=0, comment="点击次数")
    actions = Column(Integer, default=0, comment="操作次数")

    # 入口和出口
    entry_page = Column(String(500), comment="入口页面")
    exit_page = Column(String(500), comment="出口页面")
    referrer = Column(String(500), comment="来源")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否活跃")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "location": self.location,
            "page_views": self.page_views,
            "clicks": self.clicks,
            "actions": self.actions,
            "entry_page": self.entry_page,
            "exit_page": self.exit_page,
            "referrer": self.referrer,
            "is_active": self.is_active,
        }


class BehaviorRule(Base):
    """行为规则表"""
    __tablename__ = "behavior_rules"

    id = Column(String(64), primary_key=True, comment="规则ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")

    # 规则基本信息
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(Text, comment="规则描述")
    rule_type = Column(String(50), nullable=False, comment="规则类型: anomaly/alert/segment")

    # 规则配置
    conditions = Column(JSON, nullable=False, comment="触发条件")
    # 示例: {
    #   "behavior_type": "login",
    #   "frequency": "high",
    #   "time_window": "1h",
    #   "threshold": 10
    # }

    actions = Column(JSON, nullable=False, comment="触发动作")
    # 示例: {
    #   "notify": true,
    #   "notify_channels": ["email", "sms"],
    #   "block": false,
    #   "alert_level": "warning"
    # }

    # 规则状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级")

    # 统计信息
    trigger_count = Column(Integer, default=0, comment="触发次数")
    last_triggered_at = Column(DateTime, comment="最后触发时间")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "conditions": self.conditions,
            "actions": self.actions,
            "is_active": self.is_active,
            "priority": self.priority,
            "trigger_count": self.trigger_count,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }
