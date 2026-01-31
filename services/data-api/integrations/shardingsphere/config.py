"""
ShardingSphere 配置管理

从环境变量加载 ShardingSphere Proxy 连接配置。
"""
import os
from dataclasses import dataclass


@dataclass
class ShardingSphereConfig:
    """ShardingSphere Proxy 配置"""

    # Proxy MySQL 协议端口 (用于连接和执行 DistSQL)
    proxy_host: str = "shardingsphere-proxy"
    proxy_port: int = 3307

    # Admin HTTP API (如果启用)
    admin_url: str = "http://shardingsphere-proxy:33071"

    # 认证凭据
    username: str = "root"
    password: str = ""

    # 功能开关
    enabled: bool = False

    # 超时设置 (秒)
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "ShardingSphereConfig":
        """从环境变量加载配置"""
        # SHARDINGSPHERE_PROXY_URL 格式: host:port
        proxy_url = os.getenv("SHARDINGSPHERE_PROXY_URL", "shardingsphere-proxy:3307")
        if ":" in proxy_url:
            host, port = proxy_url.rsplit(":", 1)
            port = int(port)
        else:
            host = proxy_url
            port = 3307

        return cls(
            proxy_host=host,
            proxy_port=port,
            admin_url=os.getenv("SHARDINGSPHERE_ADMIN_URL", "http://shardingsphere-proxy:33071"),
            username=os.getenv("SHARDINGSPHERE_USER", "root"),
            password=os.getenv("SHARDINGSPHERE_PASSWORD", ""),
            enabled=os.getenv("SHARDINGSPHERE_ENABLED", "false").lower() == "true",
            timeout=int(os.getenv("SHARDINGSPHERE_TIMEOUT", "30")),
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.enabled:
            return True  # 禁用时不需要验证

        if not self.proxy_host:
            raise ValueError("SHARDINGSPHERE_PROXY_URL is required")

        return True

    @property
    def dsn(self) -> str:
        """获取 PyMySQL DSN 连接字符串"""
        return f"mysql+pymysql://{self.username}:{self.password}@{self.proxy_host}:{self.proxy_port}"
