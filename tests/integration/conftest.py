"""
集成测试共享配置
"""

import pytest
import asyncio
from typing import AsyncGenerator


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

    await milvus.create_collection('test_collection', 1536)

    return {
        'vllm': vllm,
        'milvus': milvus,
        'kettle': kettle
    }
