"""
系统设置数据模型
Admin API - SystemSettings 和 NotificationChannel 模型
"""

import json
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean, Integer
from sqlalchemy.sql import func

from .base import Base


class SystemSettings(Base):
    """系统设置表"""
    __tablename__ = "system_settings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    setting_key = Column(String(128), unique=True, nullable=False, comment='设置键')
    setting_value = Column(Text, comment='设置值 (JSON)')
    setting_type = Column(String(32), default='string', comment='类型: string, number, boolean, json')
    category = Column(String(64), comment='分类: general, email, storage, security, features')
    description = Column(Text, comment='描述')
    is_secret = Column(Boolean, default=False, comment='是否敏感数据')
    updated_by = Column(String(128), comment='更新者')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_value(self):
        """获取设置值（根据类型解析）"""
        if not self.setting_value:
            return None

        if self.setting_type == 'json':
            try:
                return json.loads(self.setting_value)
            except json.JSONDecodeError:
                return self.setting_value
        elif self.setting_type == 'number':
            try:
                if '.' in self.setting_value:
                    return float(self.setting_value)
                return int(self.setting_value)
            except ValueError:
                return 0
        elif self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        else:
            return self.setting_value

    def set_value(self, value):
        """设置值"""
        if isinstance(value, dict) or isinstance(value, list):
            self.setting_type = 'json'
            self.setting_value = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            self.setting_type = 'boolean'
            self.setting_value = 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            self.setting_type = 'number'
            self.setting_value = str(value)
        else:
            self.setting_type = 'string'
            self.setting_value = str(value) if value is not None else ''

    def to_dict(self, hide_secret: bool = True):
        """转换为字典"""
        value = self.get_value()
        if hide_secret and self.is_secret and value:
            value = "******"

        return {
            "key": self.setting_key,
            "value": value,
            "type": self.setting_type,
            "category": self.category,
            "description": self.description,
            "is_secret": self.is_secret,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationChannel(Base):
    """通知渠道表"""
    __tablename__ = "notification_channels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(String(64), unique=True, nullable=False, comment='渠道唯一标识')
    name = Column(String(128), nullable=False, comment='渠道名称')
    channel_type = Column(String(32), nullable=False, comment='渠道类型: email, webhook, dingtalk, feishu, slack, wechat')
    enabled = Column(Boolean, default=True, comment='是否启用')
    config = Column(Text, comment='渠道配置 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_config(self) -> dict:
        """获取配置"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict):
        """设置配置"""
        self.config = json.dumps(config, ensure_ascii=False)

    def to_dict(self, hide_secrets: bool = True):
        """转换为字典"""
        config = self.get_config()
        if hide_secrets and config.get('secret'):
            config['secret'] = '******'

        return {
            "id": self.channel_id,
            "name": self.name,
            "type": self.channel_type,
            "enabled": self.enabled,
            "config": config,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationRule(Base):
    """通知规则表"""
    __tablename__ = "notification_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, comment='规则唯一标识')
    name = Column(String(128), nullable=False, comment='规则名称')
    enabled = Column(Boolean, default=True, comment='是否启用')
    events = Column(Text, comment='触发事件 (JSON数组)')
    channel_ids = Column(Text, comment='通知渠道IDs (JSON数组)')
    conditions = Column(Text, comment='触发条件 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def get_events(self) -> list:
        """获取触发事件"""
        if not self.events:
            return []
        try:
            return json.loads(self.events)
        except json.JSONDecodeError:
            return []

    def set_events(self, events: list):
        """设置触发事件"""
        self.events = json.dumps(events, ensure_ascii=False)

    def get_channel_ids(self) -> list:
        """获取通知渠道IDs"""
        if not self.channel_ids:
            return []
        try:
            return json.loads(self.channel_ids)
        except json.JSONDecodeError:
            return []

    def set_channel_ids(self, channel_ids: list):
        """设置通知渠道IDs"""
        self.channel_ids = json.dumps(channel_ids, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "events": self.get_events(),
            "channel_ids": self.get_channel_ids(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
