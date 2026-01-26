"""
统一通知服务
提供多渠道通知发送能力：邮件、短信、钉钉、企业微信、飞书、Webhook、站内信

使用方式:
    from shared.notification_service import UnifiedNotificationService, get_notification_service

    service = get_notification_service()
    await service.send_notification(
        event_type="alert",
        recipients=["user_001", "user_002"],
        variables={"alert_name": "CPU告警", "value": "95%"},
        channels=["email", "dingtalk"]
    )
"""

import os
import json
import logging
import asyncio
import smtplib
import hmac
import hashlib
import base64
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """通知渠道类型"""
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WECHAT_WORK = "wechat_work"
    FEISHU = "feishu"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


@dataclass
class NotificationResult:
    """通知发送结果"""
    success: bool
    channel: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    response_data: Optional[Dict] = None


class BaseChannel(ABC):
    """通知渠道基类"""

    channel_type: ChannelType
    timeout: int = 30

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送通知"""
        pass


class EmailChannel(BaseChannel):
    """邮件通知渠道"""

    channel_type = ChannelType.EMAIL

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host") or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(config.get("smtp_port") or os.getenv("SMTP_PORT", 587))
        self.smtp_user = config.get("smtp_user") or os.getenv("SMTP_USER")
        self.smtp_password = config.get("smtp_password") or os.getenv("SMTP_PASSWORD")
        self.smtp_from = config.get("smtp_from") or os.getenv("SMTP_FROM") or self.smtp_user
        self.use_tls = config.get("use_tls", True)

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送邮件"""
        extra = extra or {}

        if not self.smtp_user or not self.smtp_password:
            return NotificationResult(
                success=False,
                channel="email",
                error="SMTP credentials not configured",
                error_code="SMTP_NOT_CONFIGURED"
            )

        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = recipient

            # 支持 HTML 内容
            if extra.get("is_html"):
                msg.attach(MIMEText(content, "html", "utf-8"))
            else:
                msg.attach(MIMEText(content, "plain", "utf-8"))

            # 同步发送（在线程池中执行）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                recipient,
                msg
            )

            return NotificationResult(
                success=True,
                channel="email",
                message_id=f"email_{int(time.time())}"
            )

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return NotificationResult(
                success=False,
                channel="email",
                error=str(e),
                error_code="SEND_FAILED"
            )

    def _send_email_sync(self, recipient: str, msg: MIMEMultipart):
        """同步发送邮件"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_from, [recipient], msg.as_string())


class SMSChannel(BaseChannel):
    """短信通知渠道（阿里云SMS）"""

    channel_type = ChannelType.SMS

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.access_key_id = config.get("access_key_id") or os.getenv("ALIYUN_SMS_ACCESS_KEY_ID")
        self.access_key_secret = config.get("access_key_secret") or os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET")
        self.sign_name = config.get("sign_name") or os.getenv("ALIYUN_SMS_SIGN_NAME")
        self.template_code = config.get("template_code") or os.getenv("ALIYUN_SMS_TEMPLATE_CODE")

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送短信"""
        extra = extra or {}

        if not self.access_key_id or not self.access_key_secret:
            return NotificationResult(
                success=False,
                channel="sms",
                error="Aliyun SMS credentials not configured",
                error_code="SMS_NOT_CONFIGURED"
            )

        try:
            # 动态导入 alibabacloud SDK
            try:
                from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
                from alibabacloud_tea_openapi.models import Config as OpenApiConfig
                from alibabacloud_dysmsapi20170525.models import SendSmsRequest
            except ImportError:
                return NotificationResult(
                    success=False,
                    channel="sms",
                    error="alibabacloud-dysmsapi20170525 not installed",
                    error_code="DEPENDENCY_MISSING"
                )

            # 创建客户端
            config = OpenApiConfig(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
                endpoint="dysmsapi.aliyuncs.com"
            )
            client = DysmsapiClient(config)

            # 发送请求
            template_code = extra.get("template_code") or self.template_code
            template_param = extra.get("template_param") or {"content": content}

            request = SendSmsRequest(
                phone_numbers=recipient,
                sign_name=self.sign_name,
                template_code=template_code,
                template_param=json.dumps(template_param)
            )

            response = client.send_sms(request)

            if response.body.code == "OK":
                return NotificationResult(
                    success=True,
                    channel="sms",
                    message_id=response.body.biz_id,
                    response_data={"request_id": response.body.request_id}
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="sms",
                    error=response.body.message,
                    error_code=response.body.code
                )

        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return NotificationResult(
                success=False,
                channel="sms",
                error=str(e),
                error_code="SEND_FAILED"
            )


class DingTalkChannel(BaseChannel):
    """钉钉通知渠道"""

    channel_type = ChannelType.DINGTALK

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url") or os.getenv("DINGTALK_WEBHOOK_URL")
        self.secret = config.get("secret") or os.getenv("DINGTALK_SECRET")

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送钉钉通知"""
        extra = extra or {}
        webhook_url = extra.get("webhook_url") or self.webhook_url

        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="dingtalk",
                error="DingTalk webhook URL not configured",
                error_code="WEBHOOK_NOT_CONFIGURED"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="dingtalk",
                error="aiohttp not installed",
                error_code="DEPENDENCY_MISSING"
            )

        try:
            # 签名（如果配置了密钥）
            secret = extra.get("secret") or self.secret
            if secret:
                timestamp = str(round(time.time() * 1000))
                sign_string = f"{timestamp}\n{secret}"
                hmac_code = hmac.new(
                    secret.encode('utf-8'),
                    sign_string.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode())
                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            # 构建消息
            msg_type = extra.get("msg_type", "markdown")
            if msg_type == "markdown":
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": subject or content[:20],
                        "text": f"### {subject}\n\n{content}" if subject else content
                    }
                }
            else:
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"{subject}\n{content}" if subject else content}
                }

            # @ 功能
            at_config = {}
            if extra.get("at_mobiles"):
                at_config["atMobiles"] = extra["at_mobiles"]
            if extra.get("at_all"):
                at_config["isAtAll"] = True
            if at_config:
                payload["at"] = at_config

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return NotificationResult(
                            success=True,
                            channel="dingtalk",
                            response_data=result
                        )
                    else:
                        return NotificationResult(
                            success=False,
                            channel="dingtalk",
                            error=result.get("errmsg", "Unknown error"),
                            error_code=str(result.get("errcode"))
                        )

        except Exception as e:
            logger.error(f"DingTalk send failed: {e}")
            return NotificationResult(
                success=False,
                channel="dingtalk",
                error=str(e),
                error_code="SEND_FAILED"
            )


class WeChatWorkChannel(BaseChannel):
    """企业微信通知渠道"""

    channel_type = ChannelType.WECHAT_WORK

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url") or os.getenv("WECHAT_WORK_WEBHOOK_URL")

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送企业微信通知"""
        extra = extra or {}
        webhook_url = extra.get("webhook_url") or self.webhook_url

        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="wechat_work",
                error="WeChat Work webhook URL not configured",
                error_code="WEBHOOK_NOT_CONFIGURED"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="wechat_work",
                error="aiohttp not installed",
                error_code="DEPENDENCY_MISSING"
            )

        try:
            msg_type = extra.get("msg_type", "markdown")
            if msg_type == "markdown":
                full_content = f"## {subject}\n\n{content}" if subject else content
                payload = {
                    "msgtype": "markdown",
                    "markdown": {"content": full_content}
                }
            else:
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"{subject}\n{content}" if subject else content}
                }

            # @ 功能
            if extra.get("mentioned_list"):
                if msg_type == "text":
                    payload["text"]["mentioned_list"] = extra["mentioned_list"]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return NotificationResult(
                            success=True,
                            channel="wechat_work",
                            response_data=result
                        )
                    else:
                        return NotificationResult(
                            success=False,
                            channel="wechat_work",
                            error=result.get("errmsg", "Unknown error"),
                            error_code=str(result.get("errcode"))
                        )

        except Exception as e:
            logger.error(f"WeChat Work send failed: {e}")
            return NotificationResult(
                success=False,
                channel="wechat_work",
                error=str(e),
                error_code="SEND_FAILED"
            )


class FeishuChannel(BaseChannel):
    """飞书通知渠道"""

    channel_type = ChannelType.FEISHU

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url") or os.getenv("FEISHU_WEBHOOK_URL")
        self.secret = config.get("secret") or os.getenv("FEISHU_SECRET")

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送飞书通知"""
        extra = extra or {}
        webhook_url = extra.get("webhook_url") or self.webhook_url

        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="feishu",
                error="Feishu webhook URL not configured",
                error_code="WEBHOOK_NOT_CONFIGURED"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="feishu",
                error="aiohttp not installed",
                error_code="DEPENDENCY_MISSING"
            )

        try:
            # 构建消息
            msg_type = extra.get("msg_type", "post")

            if msg_type == "post":
                payload = {
                    "msg_type": "post",
                    "content": {
                        "post": {
                            "zh_cn": {
                                "title": subject,
                                "content": [[{"tag": "text", "text": content}]]
                            }
                        }
                    }
                }
            else:
                payload = {
                    "msg_type": "text",
                    "content": {"text": f"{subject}\n{content}" if subject else content}
                }

            # 签名（如果配置了密钥）
            secret = extra.get("secret") or self.secret
            if secret:
                timestamp = str(int(time.time()))
                sign_string = f"{timestamp}\n{secret}"
                hmac_code = hmac.new(
                    sign_string.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                sign = base64.b64encode(hmac_code).decode('utf-8')
                payload["timestamp"] = timestamp
                payload["sign"] = sign

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    if result.get("code") == 0 or result.get("StatusCode") == 0:
                        return NotificationResult(
                            success=True,
                            channel="feishu",
                            response_data=result
                        )
                    else:
                        return NotificationResult(
                            success=False,
                            channel="feishu",
                            error=result.get("msg", "Unknown error"),
                            error_code=str(result.get("code"))
                        )

        except Exception as e:
            logger.error(f"Feishu send failed: {e}")
            return NotificationResult(
                success=False,
                channel="feishu",
                error=str(e),
                error_code="SEND_FAILED"
            )


class WebhookChannel(BaseChannel):
    """自定义Webhook通知渠道"""

    channel_type = ChannelType.WEBHOOK

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送Webhook通知"""
        extra = extra or {}
        webhook_url = extra.get("webhook_url") or recipient

        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="webhook",
                error="Webhook URL not provided",
                error_code="WEBHOOK_NOT_PROVIDED"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="webhook",
                error="aiohttp not installed",
                error_code="DEPENDENCY_MISSING"
            )

        try:
            # 默认 payload
            payload = {
                "title": subject,
                "message": content,
                "timestamp": int(time.time()),
                **(extra.get("payload", {}))
            }

            # 自定义 payload 模板
            if extra.get("payload_template"):
                import string
                template = extra["payload_template"]
                payload = json.loads(
                    string.Template(template).safe_substitute(
                        title=subject,
                        message=content
                    )
                )

            headers = extra.get("headers", {"Content-Type": "application/json"})
            method = extra.get("method", "POST").upper()

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status < 400:
                        return NotificationResult(
                            success=True,
                            channel="webhook",
                            response_data={"status": response.status}
                        )
                    else:
                        text = await response.text()
                        return NotificationResult(
                            success=False,
                            channel="webhook",
                            error=f"HTTP {response.status}: {text}",
                            error_code=str(response.status)
                        )

        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return NotificationResult(
                success=False,
                channel="webhook",
                error=str(e),
                error_code="SEND_FAILED"
            )


class InAppChannel(BaseChannel):
    """站内信通知渠道"""

    channel_type = ChannelType.IN_APP

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.db_session_factory = config.get("db_session_factory") if config else None

    async def send(
        self,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """发送站内信（写入数据库）"""
        extra = extra or {}

        try:
            # 此处需要数据库会话来创建 UserNotification 记录
            # 实际实现中应该通过 API 调用或直接数据库操作
            if self.db_session_factory:
                # 直接数据库操作
                pass
            else:
                # 返回成功，让调用方处理数据库操作
                return NotificationResult(
                    success=True,
                    channel="in_app",
                    message_id=f"inapp_{int(time.time())}",
                    response_data={
                        "user_id": recipient,
                        "title": subject,
                        "content": content,
                        "notification_type": extra.get("notification_type", "system"),
                        "severity": extra.get("severity", "info"),
                        "action_url": extra.get("action_url"),
                    }
                )

        except Exception as e:
            logger.error(f"In-app notification failed: {e}")
            return NotificationResult(
                success=False,
                channel="in_app",
                error=str(e),
                error_code="SEND_FAILED"
            )


class UnifiedNotificationService:
    """
    统一通知服务

    整合多种通知渠道，提供统一的通知发送接口。

    使用示例:
        service = UnifiedNotificationService()

        # 发送单条通知
        result = await service.send(
            channel="dingtalk",
            recipient="webhook_url_or_user_id",
            subject="告警通知",
            content="CPU使用率超过90%"
        )

        # 基于事件类型发送通知（使用模板）
        results = await service.send_notification(
            event_type="alert",
            recipients=["user_001", "user_002"],
            variables={"alert_name": "CPU告警", "value": "95%"},
            channels=["email", "dingtalk"]
        )
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._channels: Dict[str, BaseChannel] = {}
        self._init_channels()

    def _init_channels(self):
        """初始化通知渠道"""
        self._channels = {
            "email": EmailChannel(self.config.get("email", {})),
            "sms": SMSChannel(self.config.get("sms", {})),
            "dingtalk": DingTalkChannel(self.config.get("dingtalk", {})),
            "wechat_work": WeChatWorkChannel(self.config.get("wechat_work", {})),
            "feishu": FeishuChannel(self.config.get("feishu", {})),
            "webhook": WebhookChannel(self.config.get("webhook", {})),
            "in_app": InAppChannel(self.config.get("in_app", {})),
        }

    def get_channel(self, channel_type: str) -> Optional[BaseChannel]:
        """获取通知渠道"""
        return self._channels.get(channel_type)

    def register_channel(self, channel_type: str, channel: BaseChannel):
        """注册自定义通知渠道"""
        self._channels[channel_type] = channel

    async def send(
        self,
        channel: str,
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> NotificationResult:
        """
        发送单条通知

        Args:
            channel: 渠道类型
            recipient: 接收方（邮箱/手机号/webhook地址/用户ID）
            subject: 通知标题
            content: 通知内容
            extra: 额外参数

        Returns:
            NotificationResult
        """
        channel_instance = self.get_channel(channel)
        if not channel_instance:
            return NotificationResult(
                success=False,
                channel=channel,
                error=f"Unsupported channel: {channel}",
                error_code="UNSUPPORTED_CHANNEL"
            )

        return await channel_instance.send(recipient, subject, content, extra)

    async def send_batch(
        self,
        channel: str,
        recipients: List[str],
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> List[NotificationResult]:
        """
        批量发送通知

        Args:
            channel: 渠道类型
            recipients: 接收方列表
            subject: 通知标题
            content: 通知内容
            extra: 额外参数

        Returns:
            List[NotificationResult]
        """
        tasks = [
            self.send(channel, recipient, subject, content, extra)
            for recipient in recipients
        ]
        return await asyncio.gather(*tasks)

    async def send_multi_channel(
        self,
        channels: List[str],
        recipient: str,
        subject: str,
        content: str,
        extra: Dict[str, Any] = None
    ) -> Dict[str, NotificationResult]:
        """
        多渠道发送通知

        Args:
            channels: 渠道列表
            recipient: 接收方
            subject: 通知标题
            content: 通知内容
            extra: 额外参数

        Returns:
            Dict[channel, NotificationResult]
        """
        tasks = {
            channel: self.send(channel, recipient, subject, content, extra)
            for channel in channels
        }

        results = {}
        for channel, task in tasks.items():
            results[channel] = await task

        return results

    async def send_notification(
        self,
        event_type: str,
        recipients: List[str],
        variables: Dict[str, Any],
        channels: List[str] = None,
        template_loader=None
    ) -> List[Dict[str, Any]]:
        """
        基于事件类型发送通知（使用模板）

        Args:
            event_type: 事件类型（如 alert, task_complete 等）
            recipients: 接收方列表
            variables: 模板变量
            channels: 指定渠道（可选）
            template_loader: 模板加载器（可选，用于从数据库加载模板）

        Returns:
            List of {recipient, channel, result}
        """
        results = []

        # 如果提供了模板加载器，从数据库加载模板
        templates = []
        if template_loader:
            templates = await template_loader(event_type, channels)
        else:
            # 使用默认模板
            default_channels = channels or ["email", "in_app"]
            for channel in default_channels:
                templates.append({
                    "channel": channel,
                    "subject_template": "{{event_type}} 通知",
                    "body_template": "{{content}}",
                })

        for recipient in recipients:
            for template in templates:
                channel = template["channel"]
                subject = self._render_template(template.get("subject_template", ""), variables)
                content = self._render_template(template.get("body_template", ""), variables)

                result = await self.send(
                    channel=channel,
                    recipient=recipient,
                    subject=subject,
                    content=content,
                    extra=variables.get("extra", {})
                )

                results.append({
                    "recipient": recipient,
                    "channel": channel,
                    "result": result
                })

        return results

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        result = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value) if value is not None else "")
        return result


# 单例实例
_notification_service: Optional[UnifiedNotificationService] = None


def get_notification_service(config: Dict[str, Any] = None) -> UnifiedNotificationService:
    """获取统一通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = UnifiedNotificationService(config)
    return _notification_service


def init_notification_service(config: Dict[str, Any]) -> UnifiedNotificationService:
    """初始化统一通知服务"""
    global _notification_service
    _notification_service = UnifiedNotificationService(config)
    return _notification_service
