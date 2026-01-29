"""
数据库初始化脚本
Cube API - 创建数据库表
"""

import logging
from models import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """初始化数据库"""
    logger.info("开始初始化 Cube API 数据库...")
    try:
        init_db()
        logger.info("数据库初始化成功!")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    main()
