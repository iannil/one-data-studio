"""
即时通讯机器人对接服务
支持企业微信、钉钉等IM平台的消息推送和交互
"""

import logging
import secrets
import hmac
import hashlib
import base64
import urllib.parse
import time
import json
import requests
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class IMPlatform(str, Enum):
    """IM 平台"""
    WECHAT_WORK = "wechat_work"      # 企业微信
    DINGTALK = "dingtalk"             # 钉钉
    FEISHU = "feishu"                 # 飞书
    SLACK = "slack"                   # Slack
    TEAMS = "teams"                   # Microsoft Teams
    WEBHOOK = "webhook"               # 通用 Webhook


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    FILE = "file"
    LINK = "link"
    ACTION_CARD = "action_card"
    FEED_CARD = "feed_card"
    TEMPLATE_CARD = "template_card"


class NotificationLevel(str, Enum):
    """通知级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


# ==================== 数据类定义 ====================

@dataclass
class IMRobotConfig:
    """机器人配置"""
    robot_id: str
    name: str
    platform: IMPlatform
    webhook_url: str
    secret: str = ""  # 签名密钥
    enabled: bool = True
    description: str = ""

    # 通知配置
    notify_levels: List[NotificationLevel] = field(default_factory=lambda: [
        NotificationLevel.WARNING, NotificationLevel.ERROR, NotificationLevel.CRITICAL
    ])
    mention_all: bool = False
    mention_users: List[str] = field(default_factory=list)  # @指定用户
    mention_mobiles: List[str] = field(default_factory=list)  # @手机号

    # 限流配置
    rate_limit_per_minute: int = 20
    rate_limit_per_hour: int = 100

    # 元数据
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "robot_id": self.robot_id,
            "name": self.name,
            "platform": self.platform.value,
            "webhook_url": self.webhook_url[:50] + "...",  # 隐藏完整URL
            "enabled": self.enabled,
            "description": self.description,
            "notify_levels": [l.value for l in self.notify_levels],
            "mention_all": self.mention_all,
            "mention_users": self.mention_users,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }


@dataclass
class NotificationMessage:
    """通知消息"""
    message_id: str
    title: str
    content: str
    message_type: MessageType = MessageType.TEXT
    level: NotificationLevel = NotificationLevel.INFO

    # 附加内容
    links: List[Dict[str, str]] = field(default_factory=list)
    buttons: List[Dict[str, str]] = field(default_factory=list)
    image_url: str = ""
    file_url: str = ""

    # 元数据
    source: str = ""  # 消息来源
    event_type: str = ""  # 事件类型
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "title": self.title,
            "content": self.content,
            "message_type": self.message_type.value,
            "level": self.level.value,
            "links": self.links,
            "buttons": self.buttons,
            "image_url": self.image_url,
            "file_url": self.file_url,
            "source": self.source,
            "event_type": self.event_type,
            "metadata": self.metadata,
        }


@dataclass
class NotificationRecord:
    """通知记录"""
    record_id: str
    robot_id: str
    message_id: str
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: str = ""
    retry_count: int = 0
    response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "robot_id": self.robot_id,
            "message_id": self.message_id,
            "status": self.status.value,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


# ==================== 消息格式化器 ====================

class MessageFormatter(ABC):
    """消息格式化器基类"""

    @abstractmethod
    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        pass

    @abstractmethod
    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 Markdown 消息"""
        pass

    @abstractmethod
    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 ActionCard 消息"""
        pass


class WeChatWorkFormatter(MessageFormatter):
    """企业微信消息格式化器"""

    LEVEL_COLORS = {
        NotificationLevel.INFO: "info",
        NotificationLevel.WARNING: "warning",
        NotificationLevel.ERROR: "warning",
        NotificationLevel.CRITICAL: "warning",
    }

    LEVEL_EMOJI = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨",
    }

    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        content = f"{self.LEVEL_EMOJI.get(message.level, '')} {message.title}\n\n{message.content}"

        # 添加 @
        mentioned_list = []
        mentioned_mobile_list = []

        if config.mention_all:
            mentioned_list.append("@all")
        mentioned_list.extend(config.mention_users)
        mentioned_mobile_list.extend(config.mention_mobiles)

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            }
        }

        if mentioned_list:
            payload["text"]["mentioned_list"] = mentioned_list
        if mentioned_mobile_list:
            payload["text"]["mentioned_mobile_list"] = mentioned_mobile_list

        return payload

    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 Markdown 消息"""
        # 构建 Markdown 内容
        md_content = f"## {self.LEVEL_EMOJI.get(message.level, '')} {message.title}\n\n"
        md_content += f"{message.content}\n\n"

        # 添加链接
        if message.links:
            md_content += "### 相关链接\n"
            for link in message.links:
                md_content += f"- [{link.get('title', '链接')}]({link.get('url', '')})\n"

        # 添加元数据
        if message.metadata:
            md_content += "\n### 详细信息\n"
            for key, value in message.metadata.items():
                md_content += f"- **{key}**: {value}\n"

        # 添加 @
        if config.mention_all:
            md_content += "\n<@all>"
        for user in config.mention_users:
            md_content += f"\n<@{user}>"

        return {
            "msgtype": "markdown",
            "markdown": {
                "content": md_content,
            }
        }

    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化模板卡片消息"""
        card = {
            "msgtype": "template_card",
            "template_card": {
                "card_type": "text_notice",
                "source": {
                    "icon_url": "https://example.com/icon.png",
                    "desc": message.source or "ONE-DATA-STUDIO",
                    "desc_color": 0,
                },
                "main_title": {
                    "title": message.title,
                    "desc": f"级别: {message.level.value}",
                },
                "sub_title_text": message.content[:100],
                "horizontal_content_list": [],
                "card_action": {
                    "type": 1,
                    "url": message.links[0]["url"] if message.links else "",
                },
            }
        }

        # 添加水平内容列表
        if message.metadata:
            for key, value in list(message.metadata.items())[:3]:
                card["template_card"]["horizontal_content_list"].append({
                    "keyname": key,
                    "value": str(value),
                })

        return card


class DingTalkFormatter(MessageFormatter):
    """钉钉消息格式化器"""

    LEVEL_EMOJI = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨",
    }

    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        content = f"{self.LEVEL_EMOJI.get(message.level, '')} {message.title}\n\n{message.content}"

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
            "at": {
                "isAtAll": config.mention_all,
                "atMobiles": config.mention_mobiles,
                "atUserIds": config.mention_users,
            }
        }

        return payload

    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 Markdown 消息"""
        # 构建 Markdown 内容
        md_content = f"## {self.LEVEL_EMOJI.get(message.level, '')} {message.title}\n\n"
        md_content += f"{message.content}\n\n"

        # 添加链接
        if message.links:
            md_content += "### 相关链接\n"
            for link in message.links:
                md_content += f"- [{link.get('title', '链接')}]({link.get('url', '')})\n"

        # 添加元数据
        if message.metadata:
            md_content += "\n### 详细信息\n"
            for key, value in message.metadata.items():
                md_content += f"- **{key}**: {value}\n"

        # 添加 @
        at_content = ""
        if config.mention_all:
            at_content += "@所有人 "
        for mobile in config.mention_mobiles:
            at_content += f"@{mobile} "

        if at_content:
            md_content += f"\n{at_content}"

        return {
            "msgtype": "markdown",
            "markdown": {
                "title": message.title,
                "text": md_content,
            },
            "at": {
                "isAtAll": config.mention_all,
                "atMobiles": config.mention_mobiles,
                "atUserIds": config.mention_users,
            }
        }

    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 ActionCard 消息"""
        # 构建 Markdown 内容
        md_content = f"## {message.title}\n\n"
        md_content += f"{message.content}\n\n"

        if message.metadata:
            md_content += "---\n"
            for key, value in message.metadata.items():
                md_content += f"**{key}**: {value}\n\n"

        card = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": message.title,
                "text": md_content,
                "btnOrientation": "0",  # 按钮纵向排列
            }
        }

        # 添加按钮
        if message.buttons:
            if len(message.buttons) == 1:
                card["actionCard"]["singleTitle"] = message.buttons[0].get("title", "查看详情")
                card["actionCard"]["singleURL"] = message.buttons[0].get("url", "")
            else:
                card["actionCard"]["btns"] = [
                    {"title": btn.get("title", ""), "actionURL": btn.get("url", "")}
                    for btn in message.buttons
                ]
        elif message.links:
            card["actionCard"]["singleTitle"] = "查看详情"
            card["actionCard"]["singleURL"] = message.links[0].get("url", "")

        return card


class FeishuFormatter(MessageFormatter):
    """飞书消息格式化器"""

    LEVEL_COLORS = {
        NotificationLevel.INFO: "blue",
        NotificationLevel.WARNING: "orange",
        NotificationLevel.ERROR: "red",
        NotificationLevel.CRITICAL: "red",
    }

    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        content = f"{message.title}\n\n{message.content}"

        return {
            "msg_type": "text",
            "content": {
                "text": content,
            }
        }

    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化富文本消息（飞书使用 post 类型）"""
        # 飞书使用 post 类型的富文本消息
        content = []

        # 标题
        content.append([{"tag": "text", "text": f"【{message.level.value.upper()}】{message.title}"}])

        # 内容
        content.append([{"tag": "text", "text": message.content}])

        # 链接
        if message.links:
            for link in message.links:
                content.append([
                    {"tag": "text", "text": "🔗 "},
                    {"tag": "a", "text": link.get("title", "链接"), "href": link.get("url", "")},
                ])

        # @用户
        if config.mention_all:
            content.append([{"tag": "at", "user_id": "all"}])
        for user in config.mention_users:
            content.append([{"tag": "at", "user_id": user}])

        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": message.title,
                        "content": content,
                    }
                }
            }
        }

    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化交互卡片消息"""
        elements = []

        # 内容
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": message.content,
            }
        })

        # 分隔线
        elements.append({"tag": "hr"})

        # 元数据
        if message.metadata:
            fields = []
            for key, value in list(message.metadata.items())[:6]:
                fields.append({
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{key}**\n{value}",
                    }
                })
            elements.append({"tag": "div", "fields": fields})

        # 按钮
        if message.buttons or message.links:
            actions = []
            buttons = message.buttons or [
                {"title": "查看详情", "url": message.links[0].get("url", "")}
                for link in message.links[:3]
            ]
            for btn in buttons[:3]:
                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": btn.get("title", "")},
                    "type": "primary",
                    "url": btn.get("url", ""),
                })
            elements.append({"tag": "action", "actions": actions})

        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": message.title},
                    "template": self.LEVEL_COLORS.get(message.level, "blue"),
                },
                "elements": elements,
            }
        }


class SlackFormatter(MessageFormatter):
    """Slack 消息格式化器"""

    LEVEL_EMOJI = {
        NotificationLevel.INFO: ":information_source:",
        NotificationLevel.WARNING: ":warning:",
        NotificationLevel.ERROR: ":x:",
        NotificationLevel.CRITICAL: ":rotating_light:",
    }

    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")
        text = f"{emoji} *{message.title}*\n\n{message.content}"

        return {
            "text": text,
        }

    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 Markdown 消息（Slack mrkdwn 格式）"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{message.title}*",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message.content,
                }
            },
        ]

        # 添加链接
        if message.links:
            link_text = "*相关链接*\n" + "\n".join(
                f"• <{link.get('url', '')}|{link.get('title', '链接')}>"
                for link in message.links
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": link_text,
                }
            })

        # 添加元数据
        if message.metadata:
            fields = []
            for key, value in list(message.metadata.items())[:10]:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}*\n{value}",
                })
            blocks.append({
                "type": "section",
                "fields": fields,
            })

        return {
            "text": f"{message.title}: {message.content[:100]}",
            "blocks": blocks,
        }

    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化带按钮的消息"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{message.title}*\n\n{message.content}",
                }
            },
        ]

        # 添加元数据
        if message.metadata:
            fields = []
            for key, value in list(message.metadata.items())[:6]:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}*\n{value}",
                })
            blocks.append({
                "type": "section",
                "fields": fields,
            })

        # 添加按钮
        buttons_list = message.buttons or [
            {"title": link.get("title", "查看"), "url": link.get("url", "")}
            for link in message.links[:3]
        ]

        if buttons_list:
            elements = []
            for btn in buttons_list[:5]:
                elements.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": btn.get("title", "查看"),
                    },
                    "url": btn.get("url", ""),
                })
            blocks.append({
                "type": "actions",
                "elements": elements,
            })

        return {
            "text": f"{message.title}: {message.content[:100]}",
            "blocks": blocks,
        }


class TeamsFormatter(MessageFormatter):
    """Microsoft Teams 消息格式化器"""

    LEVEL_COLORS = {
        NotificationLevel.INFO: "0076D7",
        NotificationLevel.WARNING: "FFA500",
        NotificationLevel.ERROR: "FF0000",
        NotificationLevel.CRITICAL: "8B0000",
    }

    LEVEL_EMOJI = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨",
    }

    def format_text(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化文本消息"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"{emoji} {message.title}",
                                "weight": "bolder",
                                "size": "medium",
                            },
                            {
                                "type": "TextBlock",
                                "text": message.content,
                                "wrap": True,
                            },
                        ],
                    }
                }
            ]
        }

    def format_markdown(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化 Markdown 消息（Adaptive Card with facts）"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")
        color = self.LEVEL_COLORS.get(message.level, "0076D7")

        body = [
            {
                "type": "TextBlock",
                "text": f"{emoji} {message.title}",
                "weight": "bolder",
                "size": "medium",
                "color": "attention" if message.level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL] else "default",
            },
            {
                "type": "TextBlock",
                "text": message.content,
                "wrap": True,
            },
        ]

        # 添加元数据作为 FactSet
        if message.metadata:
            facts = [
                {"title": key, "value": str(value)}
                for key, value in list(message.metadata.items())[:10]
            ]
            body.append({
                "type": "FactSet",
                "facts": facts,
            })

        # 添加链接
        if message.links:
            for link in message.links[:3]:
                body.append({
                    "type": "TextBlock",
                    "text": f"[{link.get('title', '链接')}]({link.get('url', '')})",
                    "wrap": True,
                })

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body,
                    }
                }
            ]
        }

    def format_action_card(self, message: NotificationMessage, config: IMRobotConfig) -> Dict:
        """格式化带按钮的消息（Adaptive Card with actions）"""
        emoji = self.LEVEL_EMOJI.get(message.level, "")

        body = [
            {
                "type": "TextBlock",
                "text": f"{emoji} {message.title}",
                "weight": "bolder",
                "size": "medium",
            },
            {
                "type": "TextBlock",
                "text": message.content,
                "wrap": True,
            },
        ]

        # 添加元数据作为 FactSet
        if message.metadata:
            facts = [
                {"title": key, "value": str(value)}
                for key, value in list(message.metadata.items())[:6]
            ]
            body.append({
                "type": "FactSet",
                "facts": facts,
            })

        # 添加按钮
        buttons_list = message.buttons or [
            {"title": link.get("title", "查看"), "url": link.get("url", "")}
            for link in message.links[:3]
        ]

        actions = []
        for btn in buttons_list[:5]:
            actions.append({
                "type": "Action.OpenUrl",
                "title": btn.get("title", "查看"),
                "url": btn.get("url", ""),
            })

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body,
                        "actions": actions,
                    }
                }
            ]
        }


# ==================== IM 机器人服务 ====================

class IMRobotService:
    """IM 机器人服务"""

    def __init__(self, max_retries: int = 3):
        self._robots: Dict[str, IMRobotConfig] = {}
        self._records: Dict[str, NotificationRecord] = {}
        self._formatters: Dict[IMPlatform, MessageFormatter] = {
            IMPlatform.WECHAT_WORK: WeChatWorkFormatter(),
            IMPlatform.DINGTALK: DingTalkFormatter(),
            IMPlatform.FEISHU: FeishuFormatter(),
            IMPlatform.SLACK: SlackFormatter(),
            IMPlatform.TEAMS: TeamsFormatter(),
        }

        # 重试配置
        self._max_retries = max_retries

        # 限流计数器
        self._rate_counters: Dict[str, Dict[str, int]] = {}

        # 消息处理器（用于接收回调）
        self._message_handlers: List[Callable[[Dict], None]] = []

        # 统计
        self._stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
        }

        # 初始化示例机器人
        self._init_sample_robots()

    def _init_sample_robots(self):
        """初始化示例机器人"""
        sample_robots = [
            IMRobotConfig(
                robot_id="robot_wechat_ops",
                name="运维告警机器人",
                platform=IMPlatform.WECHAT_WORK,
                webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
                description="用于推送运维告警消息",
                notify_levels=[NotificationLevel.WARNING, NotificationLevel.ERROR, NotificationLevel.CRITICAL],
                created_by="system",
                tags=["ops", "alert"],
            ),
            IMRobotConfig(
                robot_id="robot_dingtalk_data",
                name="数据处理通知机器人",
                platform=IMPlatform.DINGTALK,
                webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx",
                secret="SEC123456789",
                description="用于推送数据处理相关通知",
                notify_levels=[NotificationLevel.INFO, NotificationLevel.WARNING, NotificationLevel.ERROR],
                created_by="system",
                tags=["data", "etl"],
            ),
            IMRobotConfig(
                robot_id="robot_feishu_ml",
                name="模型训练通知机器人",
                platform=IMPlatform.FEISHU,
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                description="用于推送模型训练相关通知",
                notify_levels=[NotificationLevel.INFO, NotificationLevel.ERROR],
                created_by="system",
                tags=["ml", "training"],
            ),
        ]

        for robot in sample_robots:
            self._robots[robot.robot_id] = robot

    # ==================== 机器人管理 ====================

    def create_robot(
        self,
        name: str,
        platform: IMPlatform,
        webhook_url: str,
        secret: str = "",
        description: str = "",
        notify_levels: List[NotificationLevel] = None,
        mention_all: bool = False,
        mention_users: List[str] = None,
        mention_mobiles: List[str] = None,
        created_by: str = "",
        tags: List[str] = None,
    ) -> IMRobotConfig:
        """创建机器人"""
        robot = IMRobotConfig(
            robot_id=f"robot_{secrets.token_hex(8)}",
            name=name,
            platform=platform,
            webhook_url=webhook_url,
            secret=secret,
            description=description,
            notify_levels=notify_levels or [NotificationLevel.WARNING, NotificationLevel.ERROR],
            mention_all=mention_all,
            mention_users=mention_users or [],
            mention_mobiles=mention_mobiles or [],
            created_by=created_by,
            tags=tags or [],
        )

        self._robots[robot.robot_id] = robot
        logger.info(f"创建 IM 机器人: {robot.robot_id} - {name}")

        return robot

    def get_robot(self, robot_id: str) -> Optional[IMRobotConfig]:
        """获取机器人"""
        return self._robots.get(robot_id)

    def list_robots(
        self,
        platform: IMPlatform = None,
        enabled: bool = None,
        tags: List[str] = None,
    ) -> List[IMRobotConfig]:
        """列出机器人"""
        robots = list(self._robots.values())

        if platform:
            robots = [r for r in robots if r.platform == platform]
        if enabled is not None:
            robots = [r for r in robots if r.enabled == enabled]
        if tags:
            robots = [r for r in robots if any(t in r.tags for t in tags)]

        return robots

    def update_robot(
        self,
        robot_id: str,
        **updates
    ) -> Optional[IMRobotConfig]:
        """更新机器人"""
        robot = self._robots.get(robot_id)
        if not robot:
            return None

        for key, value in updates.items():
            if hasattr(robot, key):
                if key == "platform" and isinstance(value, str):
                    value = IMPlatform(value)
                elif key == "notify_levels" and isinstance(value, list):
                    value = [NotificationLevel(v) if isinstance(v, str) else v for v in value]
                setattr(robot, key, value)

        return robot

    def delete_robot(self, robot_id: str) -> bool:
        """删除机器人"""
        if robot_id in self._robots:
            del self._robots[robot_id]
            return True
        return False

    def enable_robot(self, robot_id: str) -> bool:
        """启用机器人"""
        robot = self._robots.get(robot_id)
        if robot:
            robot.enabled = True
            return True
        return False

    def disable_robot(self, robot_id: str) -> bool:
        """禁用机器人"""
        robot = self._robots.get(robot_id)
        if robot:
            robot.enabled = False
            return True
        return False

    # ==================== 消息发送 ====================

    def send_notification(
        self,
        robot_id: str,
        title: str,
        content: str,
        level: NotificationLevel = NotificationLevel.INFO,
        message_type: MessageType = MessageType.MARKDOWN,
        links: List[Dict[str, str]] = None,
        buttons: List[Dict[str, str]] = None,
        metadata: Dict[str, Any] = None,
        source: str = "",
        event_type: str = "",
    ) -> NotificationRecord:
        """发送通知"""
        robot = self._robots.get(robot_id)
        if not robot:
            return NotificationRecord(
                record_id=f"rec_{secrets.token_hex(8)}",
                robot_id=robot_id,
                message_id="",
                status=NotificationStatus.FAILED,
                error_message="机器人不存在",
            )

        if not robot.enabled:
            return NotificationRecord(
                record_id=f"rec_{secrets.token_hex(8)}",
                robot_id=robot_id,
                message_id="",
                status=NotificationStatus.FAILED,
                error_message="机器人已禁用",
            )

        # 检查通知级别
        if level not in robot.notify_levels:
            return NotificationRecord(
                record_id=f"rec_{secrets.token_hex(8)}",
                robot_id=robot_id,
                message_id="",
                status=NotificationStatus.FAILED,
                error_message=f"通知级别 {level.value} 不在机器人配置的通知级别中",
            )

        # 检查限流
        if not self._check_rate_limit(robot_id, robot):
            return NotificationRecord(
                record_id=f"rec_{secrets.token_hex(8)}",
                robot_id=robot_id,
                message_id="",
                status=NotificationStatus.FAILED,
                error_message="超过限流配置",
            )

        # 创建消息
        message = NotificationMessage(
            message_id=f"msg_{secrets.token_hex(8)}",
            title=title,
            content=content,
            message_type=message_type,
            level=level,
            links=links or [],
            buttons=buttons or [],
            source=source,
            event_type=event_type,
            metadata=metadata or {},
        )

        # 创建记录
        record = NotificationRecord(
            record_id=f"rec_{secrets.token_hex(8)}",
            robot_id=robot_id,
            message_id=message.message_id,
        )

        try:
            # 格式化消息
            payload = self._format_message(robot, message)

            # 发送消息
            success, response = self._send_to_webhook(robot, payload)

            if success:
                record.status = NotificationStatus.SENT
                record.sent_at = datetime.now()
                record.response = response
                self._stats["total_sent"] += 1

                # 标记为已送达（简化处理）
                record.status = NotificationStatus.DELIVERED
                record.delivered_at = datetime.now()
                self._stats["total_delivered"] += 1

                logger.info(f"通知发送成功: {record.record_id} -> {robot.name}")
            else:
                record.status = NotificationStatus.FAILED
                record.error_message = response.get("errmsg", "发送失败")
                self._stats["total_failed"] += 1

                logger.error(f"通知发送失败: {record.record_id} - {record.error_message}")

        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            self._stats["total_failed"] += 1
            logger.error(f"通知发送异常: {record.record_id} - {e}")

        # 保存记录
        self._records[record.record_id] = record

        return record

    def send_to_all(
        self,
        title: str,
        content: str,
        level: NotificationLevel = NotificationLevel.INFO,
        message_type: MessageType = MessageType.MARKDOWN,
        tags: List[str] = None,
        **kwargs
    ) -> List[NotificationRecord]:
        """发送到所有匹配的机器人"""
        robots = self.list_robots(enabled=True, tags=tags)
        records = []

        for robot in robots:
            if level in robot.notify_levels:
                record = self.send_notification(
                    robot_id=robot.robot_id,
                    title=title,
                    content=content,
                    level=level,
                    message_type=message_type,
                    **kwargs
                )
                records.append(record)

        return records

    def test_webhook(self, robot_id: str) -> Dict[str, Any]:
        """测试 Webhook 是否正常工作"""
        robot = self._robots.get(robot_id)
        if not robot:
            return {
                "success": False,
                "error": "机器人不存在",
            }

        # 创建测试消息
        test_message = NotificationMessage(
            message_id=f"test_{secrets.token_hex(4)}",
            title="Webhook 测试消息",
            content="这是一条测试消息，用于验证 Webhook 配置是否正确。",
            message_type=MessageType.TEXT,
            level=NotificationLevel.INFO,
            source="ONE-DATA-STUDIO",
            event_type="webhook_test",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "robot_id": robot_id,
                "robot_name": robot.name,
            },
        )

        try:
            # 格式化消息
            payload = self._format_message(robot, test_message)

            # 发送消息
            success, response = self._send_to_webhook(robot, payload)

            return {
                "success": success,
                "robot_id": robot_id,
                "robot_name": robot.name,
                "platform": robot.platform.value,
                "response": response,
                "tested_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Webhook 测试异常: {robot_id} - {e}")
            return {
                "success": False,
                "robot_id": robot_id,
                "robot_name": robot.name,
                "platform": robot.platform.value,
                "error": str(e),
                "tested_at": datetime.now().isoformat(),
            }

    def _format_message(
        self,
        robot: IMRobotConfig,
        message: NotificationMessage,
    ) -> Dict:
        """格式化消息"""
        formatter = self._formatters.get(robot.platform)
        if not formatter:
            # 使用通用格式
            return {
                "text": f"{message.title}\n\n{message.content}",
            }

        if message.message_type == MessageType.TEXT:
            return formatter.format_text(message, robot)
        elif message.message_type == MessageType.MARKDOWN:
            return formatter.format_markdown(message, robot)
        elif message.message_type == MessageType.ACTION_CARD:
            return formatter.format_action_card(message, robot)
        else:
            return formatter.format_text(message, robot)

    def _send_to_webhook(
        self,
        robot: IMRobotConfig,
        payload: Dict,
    ) -> tuple[bool, Dict]:
        """发送到 Webhook（带重试逻辑）"""
        url = robot.webhook_url
        headers = {"Content-Type": "application/json"}

        # 处理签名
        if robot.platform == IMPlatform.DINGTALK and robot.secret:
            # 钉钉签名
            timestamp = str(int(time.time() * 1000))
            sign = self._generate_dingtalk_sign(robot.secret, timestamp)
            url = f"{url}&timestamp={timestamp}&sign={sign}"

        elif robot.platform == IMPlatform.FEISHU and robot.secret:
            # 飞书签名
            timestamp = str(int(time.time()))
            sign = self._generate_feishu_sign(robot.secret, timestamp)
            payload["timestamp"] = timestamp
            payload["sign"] = sign

        last_error = None
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"发送 Webhook (尝试 {attempt + 1}/{self._max_retries}): {url[:50]}...")

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )

                # 检查 HTTP 状态码
                response.raise_for_status()

                # 解析响应
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {"raw": response.text}

                # 检查业务错误码
                errcode = response_data.get("errcode", response_data.get("code", 0))
                if errcode != 0:
                    error_msg = response_data.get("errmsg", response_data.get("msg", "未知错误"))
                    logger.warning(f"Webhook 返回业务错误: {errcode} - {error_msg}")
                    return False, response_data

                return True, response_data

            except requests.exceptions.Timeout as e:
                last_error = f"请求超时: {e}"
                logger.warning(f"Webhook 超时 (尝试 {attempt + 1}/{self._max_retries}): {last_error}")

            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP 错误: {e.response.status_code} - {e.response.text[:200]}"
                logger.warning(f"Webhook HTTP 错误 (尝试 {attempt + 1}/{self._max_retries}): {last_error}")
                # 4xx 错误不重试
                if 400 <= e.response.status_code < 500:
                    return False, {"errcode": e.response.status_code, "errmsg": last_error}

            except requests.exceptions.RequestException as e:
                last_error = f"请求异常: {e}"
                logger.warning(f"Webhook 请求异常 (尝试 {attempt + 1}/{self._max_retries}): {last_error}")

            except Exception as e:
                last_error = f"未知异常: {e}"
                logger.error(f"Webhook 未知异常 (尝试 {attempt + 1}/{self._max_retries}): {last_error}")

            # 指数退避
            if attempt < self._max_retries - 1:
                backoff_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s...
                time.sleep(backoff_time)

        return False, {"errcode": -1, "errmsg": last_error or "发送失败"}

    def _generate_dingtalk_sign(self, secret: str, timestamp: str) -> str:
        """生成钉钉签名"""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))

    def _generate_feishu_sign(self, secret: str, timestamp: str) -> str:
        """生成飞书签名"""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _check_rate_limit(self, robot_id: str, robot: IMRobotConfig) -> bool:
        """检查限流"""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        hour_key = now.strftime("%Y%m%d%H")

        if robot_id not in self._rate_counters:
            self._rate_counters[robot_id] = {}

        counters = self._rate_counters[robot_id]

        # 分钟限流
        minute_count = counters.get(minute_key, 0)
        if minute_count >= robot.rate_limit_per_minute:
            return False

        # 小时限流
        hour_count = sum(
            v for k, v in counters.items()
            if k.startswith(hour_key)
        )
        if hour_count >= robot.rate_limit_per_hour:
            return False

        # 更新计数
        counters[minute_key] = minute_count + 1

        # 清理旧计数
        old_keys = [k for k in counters.keys() if k < hour_key]
        for k in old_keys:
            del counters[k]

        return True

    # ==================== 便捷方法 ====================

    def send_alert(
        self,
        title: str,
        content: str,
        level: NotificationLevel = NotificationLevel.ERROR,
        source: str = "system",
        **kwargs
    ) -> List[NotificationRecord]:
        """发送告警（到所有配置了该级别的机器人）"""
        return self.send_to_all(
            title=f"[告警] {title}",
            content=content,
            level=level,
            source=source,
            event_type="alert",
            **kwargs
        )

    def send_etl_notification(
        self,
        job_name: str,
        status: str,
        details: Dict[str, Any] = None,
    ) -> List[NotificationRecord]:
        """发送 ETL 任务通知"""
        level = NotificationLevel.INFO if status == "success" else NotificationLevel.ERROR
        title = f"ETL 任务{'完成' if status == 'success' else '失败'}: {job_name}"
        content = f"任务 **{job_name}** 执行{status}"

        if details:
            content += "\n\n**详细信息**:\n"
            for key, value in details.items():
                content += f"- {key}: {value}\n"

        return self.send_to_all(
            title=title,
            content=content,
            level=level,
            source="ETL",
            event_type="etl_job",
            metadata=details,
            tags=["etl"],
        )

    def send_training_notification(
        self,
        model_name: str,
        status: str,
        metrics: Dict[str, float] = None,
    ) -> List[NotificationRecord]:
        """发送模型训练通知"""
        level = NotificationLevel.INFO if status == "completed" else NotificationLevel.ERROR
        title = f"模型训练{'完成' if status == 'completed' else '失败'}: {model_name}"
        content = f"模型 **{model_name}** 训练{status}"

        if metrics:
            content += "\n\n**模型指标**:\n"
            for key, value in metrics.items():
                content += f"- {key}: {value:.4f}\n"

        return self.send_to_all(
            title=title,
            content=content,
            level=level,
            source="MLOps",
            event_type="model_training",
            metadata=metrics,
            tags=["ml", "training"],
        )

    def send_data_quality_alert(
        self,
        table_name: str,
        issue_type: str,
        details: str,
    ) -> List[NotificationRecord]:
        """发送数据质量告警"""
        return self.send_alert(
            title=f"数据质量问题: {table_name}",
            content=f"**问题类型**: {issue_type}\n\n**详情**: {details}",
            source="DataQuality",
            metadata={
                "table": table_name,
                "issue_type": issue_type,
            },
        )

    # ==================== 回调处理 ====================

    def register_message_handler(self, handler: Callable[[Dict], None]):
        """注册消息处理器（用于接收回调）"""
        self._message_handlers.append(handler)

    def handle_callback(self, platform: IMPlatform, data: Dict) -> Dict:
        """处理回调消息"""
        # 验证签名等（略）

        for handler in self._message_handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"回调处理异常: {e}")

        return {"code": 0, "message": "ok"}

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_robots": len(self._robots),
            "enabled_robots": len([r for r in self._robots.values() if r.enabled]),
            "robots_by_platform": {
                platform.value: len([
                    r for r in self._robots.values()
                    if r.platform == platform
                ])
                for platform in IMPlatform
            },
            "notification_stats": self._stats.copy(),
            "recent_records": len(self._records),
        }

    def get_records(
        self,
        robot_id: str = None,
        status: NotificationStatus = None,
        limit: int = 50,
    ) -> List[NotificationRecord]:
        """获取通知记录"""
        records = list(self._records.values())

        if robot_id:
            records = [r for r in records if r.robot_id == robot_id]
        if status:
            records = [r for r in records if r.status == status]

        # 按时间排序
        records.sort(
            key=lambda r: r.sent_at or datetime.min,
            reverse=True
        )

        return records[:limit]


# ==================== 全局服务实例 ====================

_im_robot_service: Optional[IMRobotService] = None


def get_im_robot_service() -> IMRobotService:
    """获取 IM 机器人服务实例"""
    global _im_robot_service
    if _im_robot_service is None:
        _im_robot_service = IMRobotService()
    return _im_robot_service
