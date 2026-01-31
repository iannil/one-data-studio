"""
Great Expectations 配置
"""

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GEConfig:
    """Great Expectations 连接配置"""
    enabled: bool = False
    context_root_dir: str = "/data/ge"
    datasource_name: str = "onedata_datasource"
    db_url: str = ""

    @classmethod
    def from_env(cls) -> "GEConfig":
        """从环境变量加载配置"""
        enabled = os.getenv("GE_ENABLED", "false").lower() == "true"
        context_root_dir = os.getenv("GE_CONTEXT_ROOT_DIR", "/data/ge")
        datasource_name = os.getenv("GE_DATASOURCE_NAME", "onedata_datasource")

        # 构建数据库 URL（复用已有的 MySQL 配置）
        mysql_host = os.getenv("MYSQL_HOST", "localhost")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", "onedata")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_database = os.getenv("MYSQL_DATABASE", "onedata")
        db_url = os.getenv(
            "GE_DB_URL",
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
        )

        return cls(
            enabled=enabled,
            context_root_dir=context_root_dir,
            datasource_name=datasource_name,
            db_url=db_url,
        )
