"""
OpenMetadata 配置管理

从环境变量读取 OpenMetadata 连接配置
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OpenMetadataConfig:
    """OpenMetadata 连接配置"""

    host: str
    port: int
    enabled: bool
    api_version: str = "v1"
    timeout: int = 30
    jwt_token: Optional[str] = None

    @property
    def base_url(self) -> str:
        """API 基础 URL"""
        return f"http://{self.host}:{self.port}/api/{self.api_version}"

    @property
    def health_url(self) -> str:
        """健康检查 URL"""
        return f"http://{self.host}:{self.port}/api/{self.api_version}/system/version"

    @classmethod
    def from_env(cls) -> "OpenMetadataConfig":
        """从环境变量创建配置"""
        enabled_str = os.getenv("OPENMETADATA_ENABLED", "false").lower()
        enabled = enabled_str in ("true", "1", "yes")

        config = cls(
            host=os.getenv("OPENMETADATA_HOST", "localhost"),
            port=int(os.getenv("OPENMETADATA_PORT", "8585")),
            enabled=enabled,
            api_version=os.getenv("OPENMETADATA_API_VERSION", "v1"),
            timeout=int(os.getenv("OPENMETADATA_TIMEOUT", "30")),
            jwt_token=os.getenv("OPENMETADATA_JWT_TOKEN"),
        )

        if config.enabled:
            logger.info(
                "OpenMetadata integration enabled: %s:%d",
                config.host,
                config.port
            )
        else:
            logger.info("OpenMetadata integration disabled")

        return config

    def validate(self) -> bool:
        """验证配置有效性"""
        if not self.enabled:
            return True

        if not self.host:
            logger.error("OPENMETADATA_HOST is required when enabled")
            return False

        if self.port <= 0 or self.port > 65535:
            logger.error("OPENMETADATA_PORT must be between 1 and 65535")
            return False

        return True


# 全局配置实例
_config: Optional[OpenMetadataConfig] = None


def get_config() -> OpenMetadataConfig:
    """获取全局配置实例（单例）"""
    global _config
    if _config is None:
        _config = OpenMetadataConfig.from_env()
    return _config


def is_enabled() -> bool:
    """检查 OpenMetadata 集成是否启用"""
    return get_config().enabled
