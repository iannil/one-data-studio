"""
Webhook通知服务
在任务状态变更时发送通知到外部系统
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook事件类型"""
    TASK_CREATED = "task.created"
    TASK_PROCESSING = "task.processing"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TEMPLATE_CREATED = "template.created"
    TEMPLATE_UPDATED = "template.updated"
    TEMPLATE_DELETED = "template.deleted"


@dataclass
class WebhookConfig:
    """Webhook配置"""
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    retry_count: int = 3
    timeout: int = 10
    enabled: bool = True


class WebhookSender:
    """Webhook发送器"""

    def __init__(self):
        self._webhooks: List[WebhookConfig] = []
        self._session = requests.Session()

    def register(self, config: WebhookConfig):
        """注册webhook"""
        self._webhooks.append(config)
        logger.info(f"Registered webhook: {config.url} for events: {[e.value for e in config.events]}")

    def unregister(self, url: str):
        """取消注册webhook"""
        self._webhooks = [w for w in self._webhooks if w.url != url]
        logger.info(f"Unregistered webhook: {url}")

    def send(
        self,
        event: WebhookEvent,
        data: Dict,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        发送webhook通知

        Args:
            event: 事件类型
            data: 事件数据
            metadata: 额外元数据

        Returns:
            发送结果列表
        """
        timestamp = datetime.now().isoformat()
        results = []

        payload = {
            "event": event.value,
            "timestamp": timestamp,
            "data": data,
            "metadata": metadata or {}
        }

        for webhook in self._webhooks:
            if not webhook.enabled:
                continue

            if event not in webhook.events:
                continue

            result = self._send_to_webhook(webhook, payload)
            results.append(result)

        return results

    def _send_to_webhook(self, webhook: WebhookConfig, payload: Dict) -> Dict:
        """发送到单个webhook"""
        result = {
            "url": webhook.url,
            "success": False,
            "status_code": None,
            "error": None
        }

        # 准备请求
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OCR-Service-Webhook/1.0"
        }

        if webhook.headers:
            headers.update(webhook.headers)

        # 添加签名（如果有secret）
        if webhook.secret:
            import hmac
            import hashlib
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                webhook.secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # 重试发送
        for attempt in range(webhook.retry_count):
            try:
                response = self._session.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout
                )

                result["status_code"] = response.status_code
                result["success"] = response.status_code < 400

                if response.status_code < 400:
                    logger.info(f"Webhook sent successfully to {webhook.url}")
                    break
                else:
                    logger.warning(f"Webhook returned {response.status_code} from {webhook.url}")

            except requests.RequestException as e:
                result["error"] = str(e)
                logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")

                if attempt == webhook.retry_count - 1:
                    logger.error(f"Webhook failed after {webhook.retry_count} attempts: {webhook.url}")

        return result

    def test_webhook(self, url: str, secret: Optional[str] = None) -> Dict:
        """
        测试webhook连接

        Args:
            url: Webhook URL
            secret: 签名密钥（可选）

        Returns:
            测试结果
        """
        test_payload = {
            "event": "webhook.test",
            "timestamp": datetime.now().isoformat(),
            "data": {"message": "Test webhook from OCR service"},
            "metadata": {"test": True}
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OCR-Service-Webhook/1.0"
        }

        if secret:
            import hmac
            import hashlib
            payload_str = json.dumps(test_payload, sort_keys=True)
            signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        try:
            response = self._session.post(url, json=test_payload, headers=headers, timeout=10)
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response.text[:200] if response.text else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局webhook发送器实例
webhook_sender = WebhookSender()


# 便捷函数
def send_task_notification(
    event: WebhookEvent,
    task_id: str,
    status: str,
    document_type: str,
    **kwargs
):
    """发送任务通知"""
    data = {
        "task_id": task_id,
        "status": status,
        "document_type": document_type,
        **kwargs
    }
    return webhook_sender.send(event, data)


def send_template_notification(
    event: WebhookEvent,
    template_id: str,
    template_name: str,
    **kwargs
):
    """发送模板通知"""
    data = {
        "template_id": template_id,
        "template_name": template_name,
        **kwargs
    }
    return webhook_sender.send(event, data)


def register_webhook(
    url: str,
    events: List[str],
    secret: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    注册webhook

    Args:
        url: Webhook URL
        events: 事件类型列表
        secret: 签名密钥
        headers: 自定义请求头

    Returns:
        是否注册成功
    """
    try:
        event_enums = [WebhookEvent(e) for e in events]
        config = WebhookConfig(
            url=url,
            events=event_enums,
            secret=secret,
            headers=headers
        )
        webhook_sender.register(config)
        return True
    except ValueError as e:
        logger.error(f"Invalid event type: {e}")
        return False


# FastAPI依赖
async def get_webhook_sender() -> WebhookSender:
    """获取webhook发送器（用于依赖注入）"""
    return webhook_sender


# 示例webhook处理器
class WebhookHandler:
    """示例webhook处理器"""

    @staticmethod
    def send_to_dingtalk(webhook_url: str, message: str):
        """发送到钉钉"""
        payload = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        requests.post(webhook_url, json=payload)

    @staticmethod
    def send_to_wechat(webhook_url: str, message: str):
        """发送到企业微信"""
        payload = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        requests.post(webhook_url, json=payload)

    @staticmethod
    def send_to_slack(webhook_url: str, message: str, channel: str = None):
        """发送到Slack"""
        payload = {
            "text": message,
            "channel": channel
        }
        requests.post(webhook_url, json=payload)

    @staticmethod
    def send_to_feishu(webhook_url: str, title: str, content: str):
        """发送到飞书"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": content
                        }
                    }
                ]
            }
        }
        requests.post(webhook_url, json=payload)
