"""
Apache Hop 配置管理

从环境变量加载 Hop Server 连接配置。
"""
import os
from dataclasses import dataclass


@dataclass
class HopConfig:
    """Apache Hop Server 配置"""

    # Hop Server URL
    server_url: str = "http://hop-server:8182"

    # 认证凭据
    username: str = "cluster"
    password: str = ""

    # 功能开关
    enabled: bool = False

    # 超时设置 (秒)
    timeout: int = 30
    execution_timeout: int = 3600  # 1小时

    # 轮询间隔 (秒)
    poll_interval: int = 5

    @classmethod
    def from_env(cls) -> "HopConfig":
        """从环境变量加载配置"""
        return cls(
            server_url=os.getenv("HOP_SERVER_URL", "http://hop-server:8182"),
            username=os.getenv("HOP_SERVER_USER", "cluster"),
            password=os.getenv("HOP_SERVER_PASSWORD", ""),
            enabled=os.getenv("HOP_ENABLED", "false").lower() == "true",
            timeout=int(os.getenv("HOP_TIMEOUT", "30")),
            execution_timeout=int(os.getenv("HOP_EXECUTION_TIMEOUT", "3600")),
            poll_interval=int(os.getenv("HOP_POLL_INTERVAL", "5")),
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.enabled:
            return True  # 禁用时不需要验证

        if not self.server_url:
            raise ValueError("HOP_SERVER_URL is required")

        if not self.password:
            raise ValueError("HOP_SERVER_PASSWORD is required")

        return True

    @property
    def base_url(self) -> str:
        """获取基础 URL (去除末尾斜杠)"""
        return self.server_url.rstrip("/")
