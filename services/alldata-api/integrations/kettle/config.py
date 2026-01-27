"""
Kettle 配置管理

从环境变量加载 Kettle Carte 服务器连接配置。
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class KettleConfig:
    """Kettle Carte 服务器配置"""

    # Carte 服务器 URL
    carte_url: str = "http://kettle:8181"

    # 认证凭据
    carte_user: str = "cluster"
    carte_password: str = ""

    # 功能开关
    enabled: bool = True

    # 超时设置 (秒)
    timeout: int = 30
    execution_timeout: int = 3600  # 1小时

    # 轮询间隔 (秒)
    poll_interval: int = 5

    @classmethod
    def from_env(cls) -> "KettleConfig":
        """从环境变量加载配置"""
        return cls(
            carte_url=os.getenv("KETTLE_CARTE_URL", "http://kettle:8181"),
            carte_user=os.getenv("KETTLE_CARTE_USER", "cluster"),
            carte_password=os.getenv("KETTLE_CARTE_PASSWORD", ""),
            enabled=os.getenv("KETTLE_ENABLED", "true").lower() == "true",
            timeout=int(os.getenv("KETTLE_TIMEOUT", "30")),
            execution_timeout=int(os.getenv("KETTLE_EXECUTION_TIMEOUT", "3600")),
            poll_interval=int(os.getenv("KETTLE_POLL_INTERVAL", "5")),
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.enabled:
            return True  # 禁用时不需要验证

        if not self.carte_url:
            raise ValueError("KETTLE_CARTE_URL is required")

        if not self.carte_password:
            raise ValueError("KETTLE_CARTE_PASSWORD is required")

        return True
