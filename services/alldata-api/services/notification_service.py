"""
统一通知管理服务
支持多渠道通知：邮件、短信、Webhook、应用内通知
"""

import logging
import smtplib
import secrets
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ==================== 通知渠道定义 ====================

class NotificationChannel:
    """通知渠道基类"""

    CHANNEL_TYPE = "base"

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = config.get("name", self.CHANNEL_TYPE)

    def send(self, recipient: str, message: 'NotificationMessage') -> bool:
        """发送通知"""
        if not self.enabled:
            logger.warning(f"Channel {self.name} is disabled")
            return False
        return self._send(recipient, message)

    def _send(self, recipient: str, message: 'NotificationMessage') -> bool:
        """实际发送逻辑，由子类实现"""
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    """邮件通知渠道"""

    CHANNEL_TYPE = "email"

    def _send(self, recipient: str, message: 'NotificationMessage') -> bool:
        try:
            smtp_config = self.config.get("smtp", {})
            smtp_host = smtp_config.get("host", "localhost")
            smtp_port = smtp_config.get("port", 587)
            smtp_user = smtp_config.get("user")
            smtp_password = smtp_config.get("password")
            use_tls = smtp_config.get("use_tls", True)
            from_addr = smtp_config.get("from_addr", "noreply@example.com")

            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = from_addr
            msg["To"] = recipient

            # HTML 内容
            html_content = self._render_html(message)
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if use_tls:
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipient}: {message.subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

    def _render_html(self, message: 'NotificationMessage') -> str:
        """渲染 HTML 邮件模板"""
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{message.title or message.subject}</h2>
                </div>
                <div class="content">
                    <p>{message.body}</p>
                    {message.action_url and f'<p><a href="{message.action_url}" class="button">查看详情</a></p>'}
                </div>
                <div class="footer">
                    <p>本邮件由系统自动发送，请勿直接回复。</p>
                    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """


class SMSChannel(NotificationChannel):
    """短信通知渠道"""

    CHANNEL_TYPE = "sms"

    def _send(self, recipient: str, message: 'NotificationMessage') -> bool:
        try:
            # 集成短信服务商（阿里云、腾讯云等）
            provider = self.config.get("provider", "mock")

            if provider == "aliyun":
                return self._send_aliyun(recipient, message)
            elif provider == "tencent":
                return self._send_tencent(recipient, message)
            else:
                # Mock 发送
                logger.info(f"[MOCK] SMS to {recipient}: {message.body[:100]}")
                return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {recipient}: {e}")
            return False

    def _send_aliyun(self, recipient: str, message: 'NotificationMessage') -> bool:
        """阿里云短信发送"""
        # 实际实现需要调用阿里云 SDK
        logger.info(f"[Aliyun SMS] to {recipient}: {message.subject}")
        return True

    def _send_tencent(self, recipient: str, message: 'NotificationMessage') -> bool:
        """腾讯云短信发送"""
        # 实际实现需要调用腾讯云 SDK
        logger.info(f"[Tencent SMS] to {recipient}: {message.subject}")
        return True


class WebhookChannel(NotificationChannel):
    """Webhook 通知渠道"""

    CHANNEL_TYPE = "webhook"

    def _send(self, recipient: str, message: 'NotificationMessage') -> bool:
        try:
            import requests

            url = recipient
            headers = self.config.get("headers", {"Content-Type": "application/json"})

            payload = {
                "id": message.message_id,
                "title": message.title,
                "subject": message.subject,
                "body": message.body,
                "type": message.type,
                "priority": message.priority,
                "timestamp": message.created_at.isoformat(),
            }

            if message.action_url:
                payload["action_url"] = message.action_url

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            logger.info(f"Webhook sent to {url}: {message.subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook to {recipient}: {e}")
            return False


class InAppChannel(NotificationChannel):
    """应用内通知渠道"""

    CHANNEL_TYPE = "inapp"

    def _send(self, recipient: str, message: 'NotificationMessage') -> bool:
        """存储到数据库，供前端轮询或 WebSocket 推送"""
        # 实际实现中，这里会将通知存入数据库
        logger.info(f"[InApp] to {recipient}: {message.subject}")
        return True


# ==================== 通知消息 ====================

@dataclass
class NotificationMessage:
    """通知消息"""
    message_id: str
    subject: str
    title: str
    body: str
    type: str = "info"  # info, warning, error, success
    priority: str = "normal"  # low, normal, high, urgent
    action_url: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


# ==================== 通知模板 ====================

@dataclass
class NotificationTemplate:
    """通知模板"""
    template_id: str
    name: str
    description: str
    subject_template: str
    body_template: str
    type: str = "info"
    supported_channels: List[str] = field(default_factory=lambda: ["inapp"])
    variables: List[str] = field(default_factory=list)
    enabled: bool = True


# ==================== 通知规则 ====================

@dataclass
class NotificationRule:
    """通知规则"""
    rule_id: str
    name: str
    description: str
    event_type: str  # 触发事件类型
    conditions: Dict[str, Any]  # 触发条件
    template_id: str
    channels: List[str]  # 使用的渠道
    recipients: List[str]  # 接收者（用户ID、邮箱、手机号等）
    enabled: bool = True
    throttle_minutes: int = 60  # 限流：相同接收者最小发送间隔（分钟）


# ==================== 通知历史 ====================

@dataclass
class NotificationHistory:
    """通知历史记录"""
    history_id: str
    message_id: str
    recipient: str
    channel: str
    status: str  # pending, sent, failed
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    retry_count: int = 0


# ==================== 通知服务 ====================

class NotificationService:
    """统一通知管理服务"""

    def __init__(self):
        self._channels: Dict[str, NotificationChannel] = {}
        self._templates: Dict[str, NotificationTemplate] = {}
        self._rules: Dict[str, NotificationRule] = {}
        self._history: List[NotificationHistory] = []

        # 初始化默认模板
        self._init_default_templates()

        # 初始化默认规则
        self._init_default_rules()

    def register_channel(self, channel: NotificationChannel):
        """注册通知渠道"""
        self._channels[channel.CHANNEL_TYPE] = channel
        logger.info(f"Registered notification channel: {channel.CHANNEL_TYPE}")

    def unregister_channel(self, channel_type: str):
        """注销通知渠道"""
        if channel_type in self._channels:
            del self._channels[channel_type]
            logger.info(f"Unregistered notification channel: {channel_type}")

    def get_channel(self, channel_type: str) -> Optional[NotificationChannel]:
        """获取通知渠道"""
        return self._channels.get(channel_type)

    def list_channels(self) -> List[Dict]:
        """列出所有已注册渠道"""
        return [
            {
                "type": channel.CHANNEL_TYPE,
                "name": channel.name,
                "enabled": channel.enabled,
            }
            for channel in self._channels.values()
        ]

    # ==================== 模板管理 ====================

    def _init_default_templates(self):
        """初始化默认通知模板"""
        self._templates = {
            "system_alert": NotificationTemplate(
                template_id="system_alert",
                name="系统告警通知",
                description="系统异常或告警通知模板",
                subject_template="【系统告警】{alert_title}",
                body_template="检测到系统告警：\n\n告警类型：{alert_type}\n告警级别：{severity}\n告警详情：{details}\n\n请及时处理。",
                type="warning",
                supported_channels=["email", "sms", "webhook", "inapp"],
                variables=["alert_title", "alert_type", "severity", "details"],
            ),
            "data_quality": NotificationTemplate(
                template_id="data_quality",
                name="数据质量告警",
                description="数据质量问题通知模板",
                subject_template="【数据质量】{table_name} 检测到 {issue_count} 个问题",
                body_template="数据质量检测发现以下问题：\n\n数据表：{table_name}\n问题数量：{issue_count}\n问题类型：{issue_types}\n\n请前往数据质量管理页面查看详情。",
                type="warning",
                supported_channels=["email", "inapp"],
                variables=["table_name", "issue_count", "issue_types"],
            ),
            "task_complete": NotificationTemplate(
                template_id="task_complete",
                name="任务完成通知",
                description="任务执行完成通知模板",
                subject_template="【任务完成】{task_name} 执行{status}",
                body_template="您的任务已执行完成：\n\n任务名称：{task_name}\n执行状态：{status}\n开始时间：{start_time}\n结束时间：{end_time}\n{error_message}",
                type="info",
                supported_channels=["email", "inapp"],
                variables=["task_name", "status", "start_time", "end_time", "error_message"],
            ),
            "approval_pending": NotificationTemplate(
                template_id="approval_pending",
                name="待审批通知",
                description="审批待办通知模板",
                subject_template="【待审批】{approval_title} 需要您的审批",
                body_template="您有一个待审批事项：\n\n审批标题：{approval_title}\n申请人：{applicant}\n申请时间：{apply_time}\n审批说明：{description}\n\n请及时处理。",
                type="info",
                supported_channels=["email", "sms", "inapp"],
                variables=["approval_title", "applicant", "apply_time", "description"],
            ),
            "model_training": NotificationTemplate(
                template_id="model_training",
                name="模型训练通知",
                description="模型训练完成或失败通知模板",
                subject_template="【模型训练】{model_name} 训练{status}",
                body_template="模型训练{status}：\n\n模型名称：{model_name}\n训练状态：{status}\n准确率：{accuracy}\n训练时长：{duration}\n\n{next_step}",
                type="info",
                supported_channels=["email", "inapp"],
                variables=["model_name", "status", "accuracy", "duration", "next_step"],
            ),
            "password_reset": NotificationTemplate(
                template_id="password_reset",
                name="密码重置",
                description="密码重置验证码通知模板",
                subject_template="【密码重置】您的验证码是 {verification_code}",
                body_template="您正在重置密码，验证码为：\n\n{verification_code}\n\n验证码有效期为 {valid_minutes} 分钟，请勿泄露给他人。",
                type="info",
                supported_channels=["email", "sms"],
                variables=["verification_code", "valid_minutes"],
            ),
        }

    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        subject_template: str,
        body_template: str,
        type: str = "info",
        supported_channels: List[str] = None,
        variables: List[str] = None,
    ) -> NotificationTemplate:
        """创建通知模板"""
        template = NotificationTemplate(
            template_id=template_id,
            name=name,
            description=description,
            subject_template=subject_template,
            body_template=body_template,
            type=type,
            supported_channels=supported_channels or ["inapp"],
            variables=variables or [],
        )
        self._templates[template_id] = template
        return template

    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        return self._templates.get(template_id)

    def list_templates(self) -> List[NotificationTemplate]:
        """列出所有模板"""
        return list(self._templates.values())

    def update_template(self, template_id: str, **kwargs) -> Optional[NotificationTemplate]:
        """更新通知模板"""
        template = self._templates.get(template_id)
        if template:
            for key, value in kwargs.items():
                if hasattr(template, key):
                    setattr(template, key, value)
        return template

    def delete_template(self, template_id: str) -> bool:
        """删除通知模板"""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def render_template(self, template_id: str, variables: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """渲染模板"""
        template = self._templates.get(template_id)
        if not template:
            return None

        try:
            subject = template.subject_template.format(**variables)
            body = template.body_template.format(**variables)
            return {
                "subject": subject,
                "body": body,
                "type": template.type,
            }
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return None

    # ==================== 规则管理 ====================

    def _init_default_rules(self):
        """初始化默认通知规则"""
        self._rules = {
            "quality_alert": NotificationRule(
                rule_id="quality_alert",
                name="数据质量告警规则",
                description="数据质量检测到问题时发送通知",
                event_type="data.quality.issue",
                conditions={"severity": ["warning", "error"]},
                template_id="data_quality",
                channels=["email", "inapp"],
                recipients=["data_owner", "quality_admin"],
            ),
            "task_failure": NotificationRule(
                rule_id="task_failure",
                name="任务失败通知规则",
                description="任务执行失败时发送通知",
                event_type="task.failed",
                conditions={},
                template_id="task_complete",
                channels=["email", "inapp"],
                recipients=["task_owner"],
            ),
            "approval_request": NotificationRule(
                rule_id="approval_request",
                name="审批请求通知规则",
                description="有新的审批请求时发送通知",
                event_type="approval.created",
                conditions={},
                template_id="approval_pending",
                channels=["email", "inapp"],
                recipients=["approver"],
            ),
        }

    def create_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        event_type: str,
        conditions: Dict[str, Any],
        template_id: str,
        channels: List[str],
        recipients: List[str],
        throttle_minutes: int = 60,
    ) -> NotificationRule:
        """创建通知规则"""
        rule = NotificationRule(
            rule_id=rule_id,
            name=name,
            description=description,
            event_type=event_type,
            conditions=conditions,
            template_id=template_id,
            channels=channels,
            recipients=recipients,
            throttle_minutes=throttle_minutes,
        )
        self._rules[rule_id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[NotificationRule]:
        """获取通知规则"""
        return self._rules.get(rule_id)

    def list_rules(self) -> List[NotificationRule]:
        """列出所有规则"""
        return list(self._rules.values())

    def update_rule(self, rule_id: str, **kwargs) -> Optional[NotificationRule]:
        """更新通知规则"""
        rule = self._rules.get(rule_id)
        if rule:
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """删除通知规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    # ==================== 通知发送 ====================

    def send(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        channels: List[str],
        title: str = None,
        type: str = "info",
        priority: str = "normal",
        action_url: str = None,
        data: Dict[str, Any] = None,
    ) -> List[str]:
        """
        发送通知

        Args:
            recipients: 接收者列表（根据渠道不同，可以是用户ID、邮箱、手机号等）
            subject: 通知主题
            body: 通知内容
            channels: 使用的渠道列表
            title: 通知标题（可选，用于应用内通知）
            type: 通知类型
            priority: 优先级
            action_url: 操作链接
            data: 附加数据

        Returns:
            发送成功的消息ID列表
        """
        message = NotificationMessage(
            message_id=f"msg_{secrets.token_hex(16)}",
            subject=subject,
            title=title or subject,
            body=body,
            type=type,
            priority=priority,
            action_url=action_url,
            data=data or {},
        )

        sent_ids = []

        for channel_type in channels:
            channel = self._channels.get(channel_type)
            if not channel:
                logger.warning(f"Channel {channel_type} not registered, skipping")
                continue

            for recipient in recipients:
                success = channel.send(recipient, message)
                if success:
                    sent_ids.append(message.message_id)
                    # 记录历史
                    self._history.append(NotificationHistory(
                        history_id=f"hist_{secrets.token_hex(16)}",
                        message_id=message.message_id,
                        recipient=recipient,
                        channel=channel_type,
                        status="sent",
                        sent_at=datetime.now(),
                    ))
                else:
                    self._history.append(NotificationHistory(
                        history_id=f"hist_{secrets.token_hex(16)}",
                        message_id=message.message_id,
                        recipient=recipient,
                        channel=channel_type,
                        status="failed",
                        error_message="Send failed",
                    ))

        return sent_ids

    def send_by_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        recipients: List[str],
        channels: List[str],
        action_url: str = None,
    ) -> List[str]:
        """
        使用模板发送通知

        Args:
            template_id: 模板ID
            variables: 模板变量
            recipients: 接收者列表
            channels: 使用的渠道列表
            action_url: 操作链接

        Returns:
            发送成功的消息ID列表
        """
        rendered = self.render_template(template_id, variables)
        if not rendered:
            logger.error(f"Failed to render template: {template_id}")
            return []

        template = self._templates.get(template_id)

        return self.send(
            recipients=recipients,
            subject=rendered["subject"],
            body=rendered["body"],
            channels=channels,
            type=rendered.get("type", "info"),
            action_url=action_url,
        )

    def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> List[str]:
        """
        触发事件，自动匹配规则发送通知

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            发送成功的消息ID列表
        """
        sent_ids = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if rule.event_type != event_type:
                continue

            # 检查条件是否匹配
            if not self._match_conditions(rule.conditions, event_data):
                continue

            # 使用规则配置的模板发送通知
            msg_ids = self.send_by_template(
                template_id=rule.template_id,
                variables=event_data,
                recipients=rule.recipients,
                channels=rule.channels,
            )
            sent_ids.extend(msg_ids)

        return sent_ids

    def _match_conditions(self, conditions: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """检查事件数据是否匹配条件"""
        for key, value in conditions.items():
            if key not in event_data:
                return False
            if isinstance(value, list):
                if event_data[key] not in value:
                    return False
            elif event_data[key] != value:
                return False
        return True

    # ==================== 通知历史 ====================

    def get_history(
        self,
        recipient: str = None,
        channel: str = None,
        status: str = None,
        limit: int = 100,
    ) -> List[NotificationHistory]:
        """获取通知历史"""
        history = self._history

        if recipient:
            history = [h for h in history if h.recipient == recipient]
        if channel:
            history = [h for h in history if h.channel == channel]
        if status:
            history = [h for h in history if h.status == status]

        # 按时间倒序排序
        history.sort(key=lambda h: h.sent_at or datetime.min, reverse=True)

        return history[:limit]

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取通知统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_history = [h for h in self._history if h.sent_at and h.sent_at >= cutoff]

        total = len(recent_history)
        sent = sum(1 for h in recent_history if h.status == "sent")
        failed = sum(1 for h in recent_history if h.status == "failed")

        channel_stats = {}
        for h in recent_history:
            if h.channel not in channel_stats:
                channel_stats[h.channel] = {"total": 0, "sent": 0, "failed": 0}
            channel_stats[h.channel]["total"] += 1
            if h.status == "sent":
                channel_stats[h.channel]["sent"] += 1
            elif h.status == "failed":
                channel_stats[h.channel]["failed"] += 1

        return {
            "period_days": days,
            "total_notifications": total,
            "sent": sent,
            "failed": failed,
            "success_rate": sent / total if total > 0 else 0,
            "by_channel": channel_stats,
        }


# 创建全局服务实例
_notification_service = None


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
        # 注册默认渠道
        _notification_service.register_channel(InAppChannel({}))
    return _notification_service
