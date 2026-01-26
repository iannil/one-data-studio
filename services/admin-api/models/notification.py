"""
通知管理数据模型
Admin API - NotificationTemplate 和 NotificationLog 模型
"""

import json
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean, Integer, ForeignKey
from sqlalchemy.sql import func

from .base import Base


class NotificationTemplate(Base):
    """通知模板表"""
    __tablename__ = "notification_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, comment='模板唯一标识')
    name = Column(String(255), nullable=False, comment='模板名称')
    description = Column(Text, comment='模板描述')

    # 模板类型
    event_type = Column(String(64), nullable=False, comment='事件类型: alert, task_complete, approval, system, etc.')
    channel = Column(String(32), nullable=False, comment='渠道类型: email, sms, dingtalk, wechat, feishu, webhook, in_app')

    # 模板内容
    subject_template = Column(String(512), comment='标题模板（支持变量占位符）')
    body_template = Column(Text, comment='正文模板（支持变量占位符）')

    # 变量定义
    variables = Column(Text, comment='变量定义 (JSON): [{name, type, required, default, description}]')

    # 状态
    is_enabled = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否为默认模板')

    # 审计字段
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_by = Column(String(128), comment='更新者')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    @staticmethod
    def generate_id() -> str:
        """生成模板ID"""
        return f"tmpl_{uuid.uuid4().hex[:12]}"

    def get_variables(self) -> list:
        """获取变量定义"""
        if not self.variables:
            return []
        try:
            return json.loads(self.variables)
        except json.JSONDecodeError:
            return []

    def set_variables(self, variables: list):
        """设置变量定义"""
        self.variables = json.dumps(variables, ensure_ascii=False)

    def render(self, context: dict) -> tuple:
        """
        渲染模板

        Args:
            context: 变量上下文 {variable_name: value}

        Returns:
            tuple: (subject, body)
        """
        subject = self.subject_template or ""
        body = self.body_template or ""

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value) if value is not None else "")
            body = body.replace(placeholder, str(value) if value is not None else "")

        return subject, body

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.template_id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "channel": self.channel,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "variables": self.get_variables(),
            "is_enabled": self.is_enabled,
            "is_default": self.is_default,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationLog(Base):
    """通知发送日志表"""
    __tablename__ = "notification_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, comment='日志唯一标识')

    # 通知信息
    channel = Column(String(32), nullable=False, comment='渠道类型')
    template_id = Column(String(64), comment='模板ID')
    subject = Column(String(512), comment='通知标题')
    content = Column(Text, comment='通知内容')

    # 接收方
    recipient_type = Column(String(32), comment='接收方类型: user, group, email, phone')
    recipient_id = Column(String(255), comment='接收方ID（用户ID或组ID）')
    recipient_address = Column(String(255), comment='实际发送地址（邮箱/手机号/webhook地址）')

    # 发送状态
    status = Column(String(32), default='pending', comment='状态: pending, sending, sent, delivered, failed')
    send_at = Column(TIMESTAMP, comment='发送时间')
    delivered_at = Column(TIMESTAMP, comment='送达时间')
    error_message = Column(Text, comment='错误信息')
    error_code = Column(String(64), comment='错误码')
    retry_count = Column(Integer, default=0, comment='重试次数')
    max_retries = Column(Integer, default=3, comment='最大重试次数')

    # 响应信息
    response_data = Column(Text, comment='第三方响应数据 (JSON)')

    # 关联业务
    source_type = Column(String(32), comment='来源类型: alert, task, system')
    source_id = Column(String(64), comment='来源ID')
    event_type = Column(String(64), comment='事件类型')

    # 审计字段
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    created_by = Column(String(128), comment='创建者/触发者')

    @staticmethod
    def generate_id() -> str:
        """生成日志ID"""
        return f"nlog_{uuid.uuid4().hex[:12]}"

    def get_response_data(self) -> dict:
        """获取响应数据"""
        if not self.response_data:
            return {}
        try:
            return json.loads(self.response_data)
        except json.JSONDecodeError:
            return {}

    def set_response_data(self, data: dict):
        """设置响应数据"""
        self.response_data = json.dumps(data, ensure_ascii=False)

    def mark_sent(self):
        """标记为已发送"""
        self.status = 'sent'
        self.send_at = datetime.utcnow()

    def mark_delivered(self):
        """标记为已送达"""
        self.status = 'delivered'
        self.delivered_at = datetime.utcnow()

    def mark_failed(self, error_message: str, error_code: str = None):
        """标记为失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.error_code = error_code

    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.status == 'failed' and self.retry_count < self.max_retries

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.log_id,
            "channel": self.channel,
            "template_id": self.template_id,
            "subject": self.subject,
            "content": self.content,
            "recipient_type": self.recipient_type,
            "recipient_id": self.recipient_id,
            "recipient_address": self.recipient_address,
            "status": self.status,
            "send_at": self.send_at.isoformat() if self.send_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "event_type": self.event_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }
