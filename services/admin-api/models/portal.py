"""
统一门户数据模型
P7.3: 统一门户Portal - 消息中心、工作台、个人中心
"""

import json
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean, Integer, DateTime
from sqlalchemy.sql import func

from .base import Base


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class UserNotification(Base):
    """用户通知表 - 站内信"""
    __tablename__ = "user_notifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    notification_id = Column(String(64), unique=True, nullable=False, index=True, comment='通知唯一标识')

    # 接收方
    user_id = Column(String(128), nullable=False, index=True, comment='接收用户ID')

    # 通知内容
    title = Column(String(512), nullable=False, comment='通知标题')
    content = Column(Text, comment='通知内容（支持Markdown）')
    summary = Column(String(255), comment='摘要（用于列表展示）')

    # 通知类型
    notification_type = Column(String(32), nullable=False, default='info', comment='类型: info, success, warning, error, alert, task, approval, system')
    category = Column(String(32), comment='分类: message, alert, task, announcement')

    # 严重级别
    severity = Column(String(16), default='info', comment='级别: info, low, medium, high, critical')

    # 关联操作
    action_url = Column(String(512), comment='点击跳转URL')
    action_label = Column(String(64), comment='操作按钮文本')
    action_type = Column(String(32), comment='操作类型: link, api_call, modal')

    # 来源信息
    source_type = Column(String(32), comment='来源类型: alert, etl_task, approval, system')
    source_id = Column(String(128), comment='来源ID')
    source_name = Column(String(255), comment='来源名称')

    # 状态
    is_read = Column(Boolean, default=False, comment='是否已读')
    read_at = Column(TIMESTAMP, comment='阅读时间')
    is_archived = Column(Boolean, default=False, comment='是否已归档')
    archived_at = Column(TIMESTAMP, comment='归档时间')
    is_deleted = Column(Boolean, default=False, comment='是否已删除（软删除）')

    # 扩展数据
    extra_data = Column(Text, comment='额外数据 (JSON)')

    # 审计字段
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    sender_id = Column(String(128), comment='发送者ID（系统或用户）')
    sender_name = Column(String(128), comment='发送者名称')

    @staticmethod
    def generate_id() -> str:
        """生成通知ID"""
        return generate_id("notif_")

    def mark_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def mark_archived(self):
        """归档通知"""
        self.is_archived = True
        self.archived_at = datetime.utcnow()

    def get_extra_data(self) -> dict:
        """获取额外数据"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except json.JSONDecodeError:
            return {}

    def set_extra_data(self, data: dict):
        """设置额外数据"""
        self.extra_data = json.dumps(data, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.notification_id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "notification_type": self.notification_type,
            "category": self.category,
            "severity": self.severity,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "action_type": self.action_type,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_archived": self.is_archived,
            "extra_data": self.get_extra_data(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
        }


class UserTodo(Base):
    """用户待办事项表"""
    __tablename__ = "user_todos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    todo_id = Column(String(64), unique=True, nullable=False, index=True, comment='待办唯一标识')

    # 所属用户
    user_id = Column(String(128), nullable=False, index=True, comment='用户ID')

    # 待办内容
    title = Column(String(512), nullable=False, comment='待办标题')
    description = Column(Text, comment='待办描述')

    # 待办类型
    todo_type = Column(String(32), nullable=False, comment='类型: approval, task, reminder, alert, review')
    priority = Column(String(16), default='medium', comment='优先级: low, medium, high, urgent')

    # 来源关联
    source_type = Column(String(32), comment='来源类型: etl_task, data_quality, approval_request, alert')
    source_id = Column(String(128), index=True, comment='来源ID')
    source_name = Column(String(255), comment='来源名称')
    source_url = Column(String(512), comment='来源详情URL')

    # 状态
    status = Column(String(32), default='pending', comment='状态: pending, in_progress, completed, cancelled, expired')

    # 时间相关
    due_date = Column(DateTime, comment='截止日期')
    reminder_at = Column(DateTime, comment='提醒时间')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')

    # 扩展数据
    extra_data = Column(Text, comment='额外数据 (JSON)')
    action_buttons = Column(Text, comment='操作按钮配置 (JSON): [{label, action, url, style}]')

    # 审计字段
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    created_by = Column(String(128), comment='创建者')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    @staticmethod
    def generate_id() -> str:
        """生成待办ID"""
        return generate_id("todo_")

    def start(self):
        """开始待办"""
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()

    def complete(self):
        """完成待办"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()

    def cancel(self):
        """取消待办"""
        self.status = 'cancelled'

    def is_overdue(self) -> bool:
        """是否已过期"""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date and self.status == 'pending'

    def get_extra_data(self) -> dict:
        """获取额外数据"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except json.JSONDecodeError:
            return {}

    def get_action_buttons(self) -> list:
        """获取操作按钮配置"""
        if not self.action_buttons:
            return []
        try:
            return json.loads(self.action_buttons)
        except json.JSONDecodeError:
            return []

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.todo_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "todo_type": self.todo_type,
            "priority": self.priority,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "reminder_at": self.reminder_at.isoformat() if self.reminder_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_overdue": self.is_overdue(),
            "extra_data": self.get_extra_data(),
            "action_buttons": self.get_action_buttons(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserActivityLog(Base):
    """用户行为日志表"""
    __tablename__ = "user_activity_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True, comment='日志唯一标识')

    # 用户信息
    user_id = Column(String(128), nullable=False, index=True, comment='用户ID')
    username = Column(String(128), comment='用户名')

    # 行为信息
    action = Column(String(64), nullable=False, comment='操作: login, logout, view, create, update, delete, export, search, etc.')
    action_label = Column(String(128), comment='操作显示名称')

    # 资源信息
    resource_type = Column(String(32), comment='资源类型: dataset, etl_task, model, workflow, etc.')
    resource_id = Column(String(128), index=True, comment='资源ID')
    resource_name = Column(String(255), comment='资源名称')
    resource_url = Column(String(512), comment='资源URL')

    # 请求信息
    request_method = Column(String(16), comment='HTTP方法')
    request_path = Column(String(512), comment='请求路径')
    request_params = Column(Text, comment='请求参数 (JSON)')
    request_body = Column(Text, comment='请求体 (JSON，敏感信息需脱敏)')

    # 响应信息
    response_status = Column(Integer, comment='响应状态码')
    response_message = Column(String(512), comment='响应消息')

    # 客户端信息
    ip_address = Column(String(64), comment='客户端IP')
    user_agent = Column(String(512), comment='User-Agent')
    device_type = Column(String(32), comment='设备类型: desktop, mobile, tablet')
    browser = Column(String(64), comment='浏览器')
    os = Column(String(64), comment='操作系统')

    # 地理位置
    geo_country = Column(String(64), comment='国家')
    geo_region = Column(String(64), comment='地区')
    geo_city = Column(String(64), comment='城市')

    # 会话信息
    session_id = Column(String(128), comment='会话ID')
    duration_ms = Column(Integer, comment='操作耗时（毫秒）')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='操作时间')

    @staticmethod
    def generate_id() -> str:
        """生成日志ID"""
        return generate_id("alog_")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.log_id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "action_label": self.action_label,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "resource_url": self.resource_url,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "browser": self.browser,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_dict_full(self):
        """转换为完整字典（管理员视图）"""
        return {
            **self.to_dict(),
            "request_method": self.request_method,
            "request_path": self.request_path,
            "response_status": self.response_status,
            "user_agent": self.user_agent,
            "os": self.os,
            "geo_country": self.geo_country,
            "geo_region": self.geo_region,
            "geo_city": self.geo_city,
            "session_id": self.session_id,
        }


class Announcement(Base):
    """系统公告表"""
    __tablename__ = "announcements"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    announcement_id = Column(String(64), unique=True, nullable=False, index=True, comment='公告唯一标识')

    # 公告内容
    title = Column(String(512), nullable=False, comment='公告标题')
    content = Column(Text, comment='公告内容（支持Markdown）')
    summary = Column(String(255), comment='公告摘要')

    # 公告类型
    announcement_type = Column(String(32), default='info', comment='类型: info, update, maintenance, warning, urgent')
    priority = Column(Integer, default=0, comment='优先级（越大越靠前）')

    # 展示配置
    is_pinned = Column(Boolean, default=False, comment='是否置顶')
    is_popup = Column(Boolean, default=False, comment='是否弹窗展示')
    target_roles = Column(Text, comment='目标角色 (JSON数组，为空表示全部)')
    target_users = Column(Text, comment='目标用户 (JSON数组)')

    # 时间范围
    start_time = Column(DateTime, comment='生效开始时间')
    end_time = Column(DateTime, comment='生效结束时间')

    # 状态
    status = Column(String(16), default='draft', comment='状态: draft, published, archived')
    publish_at = Column(DateTime, comment='发布时间')

    # 统计
    view_count = Column(Integer, default=0, comment='查看次数')

    # 审计字段
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    created_by = Column(String(128), comment='创建者')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    updated_by = Column(String(128), comment='更新者')

    @staticmethod
    def generate_id() -> str:
        """生成公告ID"""
        return generate_id("ann_")

    def is_active(self) -> bool:
        """是否在有效期内"""
        now = datetime.utcnow()
        if self.status != 'published':
            return False
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    def get_target_roles(self) -> list:
        """获取目标角色列表"""
        if not self.target_roles:
            return []
        try:
            return json.loads(self.target_roles)
        except json.JSONDecodeError:
            return []

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.announcement_id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "announcement_type": self.announcement_type,
            "priority": self.priority,
            "is_pinned": self.is_pinned,
            "is_popup": self.is_popup,
            "target_roles": self.get_target_roles(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None,
            "view_count": self.view_count,
            "is_active": self.is_active(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
