"""
通知工具
Sprint 17: Agent 工具扩展

功能:
- Slack 通知
- 钉钉通知
- 企业微信通知
- 邮件通知
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import os
import sys
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """通知渠道"""
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECHAT_WORK = "wechat_work"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class NotificationResult:
    """通知结果"""
    success: bool
    channel: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationTool(BaseTool):
    """
    通知工具
    Sprint 17: Agent 工具扩展

    支持多种通知渠道:
    - Slack
    - 钉钉
    - 企业微信
    - 邮件
    - 自定义 Webhook
    """

    name = "notification"
    description = "发送通知消息到 Slack、钉钉、企业微信或其他渠道。"
    parameters = [
        ToolSchema("channel", "string", "通知渠道 (slack, dingtalk, wechat_work, email, webhook)", required=True),
        ToolSchema("message", "string", "通知消息内容", required=True),
        ToolSchema("title", "string", "通知标题", default=""),
        ToolSchema("webhook_url", "string", "Webhook URL（可选，覆盖默认配置）"),
        ToolSchema("extra", "object", "额外参数", default={}),
    ]

    DEFAULT_TIMEOUT = 30  # 秒

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 从配置或环境变量获取 Webhook URL
        self.slack_webhook = (
            config.get("slack_webhook") if config else None
        ) or os.getenv("SLACK_WEBHOOK_URL")

        self.dingtalk_webhook = (
            config.get("dingtalk_webhook") if config else None
        ) or os.getenv("DINGTALK_WEBHOOK_URL")

        self.dingtalk_secret = (
            config.get("dingtalk_secret") if config else None
        ) or os.getenv("DINGTALK_SECRET")

        self.wechat_webhook = (
            config.get("wechat_webhook") if config else None
        ) or os.getenv("WECHAT_WORK_WEBHOOK_URL")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """发送通知"""
        channel = kwargs.get("channel")
        message = kwargs.get("message")
        title = kwargs.get("title", "")
        webhook_url = kwargs.get("webhook_url")
        extra = kwargs.get("extra", {})

        if not channel:
            return {"success": False, "error": "Channel is required"}

        if not message:
            return {"success": False, "error": "Message is required"}

        try:
            channel_enum = NotificationChannel(channel.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"不支持的渠道: {channel}。支持: {[c.value for c in NotificationChannel]}"
            }

        try:
            if channel_enum == NotificationChannel.SLACK:
                result = await self._send_slack(webhook_url or self.slack_webhook, message, title, extra)
            elif channel_enum == NotificationChannel.DINGTALK:
                result = await self._send_dingtalk(webhook_url or self.dingtalk_webhook, message, title, extra)
            elif channel_enum == NotificationChannel.WECHAT_WORK:
                result = await self._send_wechat_work(webhook_url or self.wechat_webhook, message, title, extra)
            elif channel_enum == NotificationChannel.WEBHOOK:
                if not webhook_url:
                    return {"success": False, "error": "Webhook URL is required for webhook channel"}
                result = await self._send_webhook(webhook_url, message, title, extra)
            else:
                return {"success": False, "error": f"渠道 {channel} 尚未实现"}

            return {
                "success": result.success,
                "channel": result.channel,
                "message_id": result.message_id,
                "error": result.error,
            }

        except Exception as e:
            logger.error(f"Notification failed: {e}")
            return {"success": False, "error": str(e)}

    async def _send_slack(
        self,
        webhook_url: str,
        message: str,
        title: str,
        extra: Dict[str, Any]
    ) -> NotificationResult:
        """发送 Slack 通知"""
        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="slack",
                error="Slack Webhook URL 未配置"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="slack",
                error="aiohttp is required. Install with: pip install aiohttp"
            )

        # 构建 Slack 消息
        blocks = []
        if title:
            blocks.append({
                "type": "header",
                "text": {"type": "plain_text", "text": title}
            })
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": message}
        })

        payload = {
            "text": title or message[:100],
            "blocks": blocks,
        }

        # 添加额外字段
        if extra.get("color"):
            payload["attachments"] = [{"color": extra["color"], "text": ""}]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as response:
                if response.status == 200:
                    return NotificationResult(success=True, channel="slack")
                else:
                    text = await response.text()
                    return NotificationResult(
                        success=False,
                        channel="slack",
                        error=f"HTTP {response.status}: {text}"
                    )

    async def _send_dingtalk(
        self,
        webhook_url: str,
        message: str,
        title: str,
        extra: Dict[str, Any]
    ) -> NotificationResult:
        """发送钉钉通知"""
        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="dingtalk",
                error="钉钉 Webhook URL 未配置"
            )

        try:
            import aiohttp
            import time
            import hmac
            import hashlib
            import base64
            import urllib.parse
        except ImportError:
            return NotificationResult(
                success=False,
                channel="dingtalk",
                error="aiohttp is required"
            )

        # 钉钉签名（如果配置了密钥）
        if self.dingtalk_secret:
            timestamp = str(round(time.time() * 1000))
            sign_string = f"{timestamp}\n{self.dingtalk_secret}"
            hmac_code = hmac.new(
                self.dingtalk_secret.encode('utf-8'),
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
                    "title": title or message[:20],
                    "text": f"### {title}\n\n{message}" if title else message
                }
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {"content": f"{title}\n{message}" if title else message}
            }

        # 添加 @ 功能
        if extra.get("at_mobiles"):
            payload["at"] = {"atMobiles": extra["at_mobiles"]}
        if extra.get("at_all"):
            payload["at"] = payload.get("at", {})
            payload["at"]["isAtAll"] = True

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    return NotificationResult(success=True, channel="dingtalk")
                else:
                    return NotificationResult(
                        success=False,
                        channel="dingtalk",
                        error=result.get("errmsg", "Unknown error")
                    )

    async def _send_wechat_work(
        self,
        webhook_url: str,
        message: str,
        title: str,
        extra: Dict[str, Any]
    ) -> NotificationResult:
        """发送企业微信通知"""
        if not webhook_url:
            return NotificationResult(
                success=False,
                channel="wechat_work",
                error="企业微信 Webhook URL 未配置"
            )

        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="wechat_work",
                error="aiohttp is required"
            )

        # 构建消息
        msg_type = extra.get("msg_type", "markdown")

        if msg_type == "markdown":
            content = f"## {title}\n\n{message}" if title else message
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": content}
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {"content": f"{title}\n{message}" if title else message}
            }

        # 添加 @ 功能
        if extra.get("mentioned_list"):
            if msg_type == "text":
                payload["text"]["mentioned_list"] = extra["mentioned_list"]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    return NotificationResult(success=True, channel="wechat_work")
                else:
                    return NotificationResult(
                        success=False,
                        channel="wechat_work",
                        error=result.get("errmsg", "Unknown error")
                    )

    async def _send_webhook(
        self,
        webhook_url: str,
        message: str,
        title: str,
        extra: Dict[str, Any]
    ) -> NotificationResult:
        """发送自定义 Webhook"""
        try:
            import aiohttp
        except ImportError:
            return NotificationResult(
                success=False,
                channel="webhook",
                error="aiohttp is required"
            )

        # 默认 payload
        payload = {
            "title": title,
            "message": message,
            "timestamp": int(asyncio.get_event_loop().time()),
            **extra
        }

        # 自定义 payload 模板
        if extra.get("payload_template"):
            import string
            template = extra["payload_template"]
            payload = json.loads(
                string.Template(template).safe_substitute(
                    title=title,
                    message=message
                )
            )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            ) as response:
                if response.status < 400:
                    return NotificationResult(success=True, channel="webhook")
                else:
                    text = await response.text()
                    return NotificationResult(
                        success=False,
                        channel="webhook",
                        error=f"HTTP {response.status}: {text}"
                    )
