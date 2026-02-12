"""
集成测试共享配置
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator


class DatabaseTestConfig:
    """
    通用数据库测试配置

    可被各测试模块的 TestConfig 类继承或使用。

    使用示例:
        class TestConfig(DatabaseTestConfig):
            # 模块特定配置
            EXPECTED_TABLES = ["users", "orders"]
    """

    # MySQL 测试数据库配置
    MYSQL_CONFIG = {
        "type": "mysql",
        "host": os.getenv("TEST_MYSQL_HOST", "localhost"),
        "port": int(os.getenv("TEST_MYSQL_PORT", "3308")),
        "username": os.getenv("TEST_MYSQL_USER", "root"),
        "password": os.getenv("TEST_MYSQL_PASSWORD", "rootdev123"),
        "database": "test_ecommerce",
    }

    # PostgreSQL 测试数据库配置
    POSTGRES_CONFIG = {
        "type": "postgresql",
        "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("TEST_POSTGRES_PORT", "5436")),
        "username": os.getenv("TEST_POSTGRES_USER", "postgres"),
        "password": os.getenv("TEST_POSTGRES_PASSWORD", "postgresdev123"),
        "database": "test_ecommerce_pg",
    }

    # API 基础 URL
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")


# 通用测试表配置
EXPECTED_TEST_TABLES = [
    "users",
    "products",
    "orders",
    "order_items",
    "shopping_cart",
    "categories",
]


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_services():
    """获取所有 Mock 服务"""
    from tests.mocks import MockVLLMClient, MockMilvusClient, MockKettleClient

    vllm = MockVLLMClient()
    milvus = MockMilvusClient()
    kettle = MockKettleClient()

    await milvus.create_collection("test_collection", 1536)

    return {"vllm": vllm, "milvus": milvus, "kettle": kettle}
