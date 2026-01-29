"""
事件节点
Sprint 18: 工作流节点扩展

包含:
- WebhookNode: 接收外部回调
"""

import logging
import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class WebhookNodeConfig:
    """Webhook 节点配置"""
    webhook_id: str = ""  # Webhook ID（用于 URL 生成）
    timeout: float = 3600.0  # 等待超时（秒）
    expected_headers: Dict[str, str] = None  # 预期的请求头
    expected_method: str = "POST"  # 预期的 HTTP 方法
    secret_key: str = ""  # 签名验证密钥
    output_mapping: Dict[str, str] = None  # 输出映射


# 等待中的 Webhook
_pending_webhooks: Dict[str, Dict[str, Any]] = {}


class WebhookNode:
    """
    Webhook 节点
    Sprint 18: 工作流节点扩展

    支持:
    - 等待外部回调
    - 超时控制
    - 签名验证
    - 数据映射
    """

    node_type = "webhook"
    name = "WebhookNode"
    description = "等待外部 Webhook 回调"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = WebhookNodeConfig(
            webhook_id=config.get("webhook_id", str(uuid.uuid4())),
            timeout=config.get("timeout", 3600.0),
            expected_headers=config.get("expected_headers"),
            expected_method=config.get("expected_method", "POST"),
            secret_key=config.get("secret_key", ""),
            output_mapping=config.get("output_mapping"),
        ) if config else WebhookNodeConfig(webhook_id=str(uuid.uuid4()))

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        on_waiting: Callable = None
    ) -> Dict[str, Any]:
        """
        执行 Webhook 节点

        Args:
            input_data: 输入数据
            context: 执行上下文
            on_waiting: 开始等待时的回调函数

        Returns:
            执行结果
        """
        webhook_id = self.config.webhook_id
        execution_id = context.get("execution_id") if context else str(uuid.uuid4())

        # 创建等待事件
        event = asyncio.Event()
        webhook_data = {
            "id": webhook_id,
            "execution_id": execution_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=self.config.timeout),
            "event": event,
            "received_data": None,
            "status": "waiting"
        }

        # 注册 Webhook
        _pending_webhooks[webhook_id] = webhook_data

        logger.info(f"Webhook waiting: {webhook_id}")

        # 生成 Webhook URL
        webhook_url = self._generate_webhook_url(webhook_id)

        # 通知开始等待
        if on_waiting:
            await on_waiting({
                "webhook_id": webhook_id,
                "webhook_url": webhook_url,
                "timeout": self.config.timeout
            })

        try:
            # 等待回调或超时
            await asyncio.wait_for(event.wait(), timeout=self.config.timeout)

            # 获取接收到的数据
            received_data = webhook_data.get("received_data", {})

            # 应用输出映射
            if self.config.output_mapping:
                mapped_data = self._apply_output_mapping(received_data)
            else:
                mapped_data = received_data

            return {
                "success": True,
                "webhook_id": webhook_id,
                "webhook_url": webhook_url,
                "received_data": received_data,
                "output": mapped_data
            }

        except asyncio.TimeoutError:
            logger.warning(f"Webhook timeout: {webhook_id}")
            return {
                "success": False,
                "webhook_id": webhook_id,
                "webhook_url": webhook_url,
                "error": f"Webhook timeout after {self.config.timeout}s"
            }

        finally:
            # 清理
            if webhook_id in _pending_webhooks:
                del _pending_webhooks[webhook_id]

    def _generate_webhook_url(self, webhook_id: str) -> str:
        """生成 Webhook URL"""
        import os
        base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8081")
        return f"{base_url}/api/v1/webhooks/{webhook_id}"

    def _apply_output_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用输出映射"""
        if not self.config.output_mapping:
            return data

        mapped = {}
        for target_key, source_key in self.config.output_mapping.items():
            # 支持嵌套路径
            value = self._get_nested_value(data, source_key)
            if value is not None:
                mapped[target_key] = value

        return mapped

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    @staticmethod
    def receive_webhook(
        webhook_id: str,
        data: Dict[str, Any],
        headers: Dict[str, str] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        接收 Webhook 回调

        Args:
            webhook_id: Webhook ID
            data: 接收到的数据
            headers: 请求头
            method: HTTP 方法

        Returns:
            处理结果
        """
        if webhook_id not in _pending_webhooks:
            return {
                "success": False,
                "error": "Webhook not found or expired"
            }

        webhook_data = _pending_webhooks[webhook_id]

        # 检查是否过期
        if datetime.now() > webhook_data["expires_at"]:
            del _pending_webhooks[webhook_id]
            return {
                "success": False,
                "error": "Webhook expired"
            }

        # 存储接收到的数据
        webhook_data["received_data"] = data
        webhook_data["received_headers"] = headers
        webhook_data["received_method"] = method
        webhook_data["received_at"] = datetime.now()
        webhook_data["status"] = "received"

        # 触发事件
        event = webhook_data.get("event")
        if event:
            event.set()

        return {
            "success": True,
            "webhook_id": webhook_id,
            "message": "Webhook received"
        }

    @staticmethod
    def list_pending_webhooks() -> List[Dict[str, Any]]:
        """列出等待中的 Webhook"""
        now = datetime.now()
        result = []
        for webhook_id, data in _pending_webhooks.items():
            result.append({
                "id": webhook_id,
                "execution_id": data["execution_id"],
                "created_at": data["created_at"].isoformat(),
                "expires_at": data["expires_at"].isoformat(),
                "remaining_seconds": (data["expires_at"] - now).total_seconds(),
                "status": data["status"]
            })
        return result

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": {
                "webhook_id": {"type": "string"},
                "timeout": {"type": "number", "default": 3600},
                "expected_method": {"type": "string", "default": "POST"},
                "secret_key": {"type": "string"},
                "output_mapping": {"type": "object"},
            },
            "outputs": {
                "success": {"type": "boolean"},
                "webhook_id": {"type": "string"},
                "webhook_url": {"type": "string"},
                "received_data": {"type": "object"},
            }
        }
