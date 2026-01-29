"""
Embedding 生成服务
调用 OpenAI 兼容的 Embedding API
Phase 6: Sprint 6.2
"""

import logging
import os
import requests
from typing import List, Optional, Union

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL", "http://vllm-serving:8000")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
# 是否启用模拟 embedding（仅用于开发测试）
EMBEDDING_MOCK_ENABLED = os.getenv("EMBEDDING_MOCK_ENABLED", "false").lower() in ("true", "1", "yes")


def _make_embedding_request(api_url: str, text: str, model: str) -> requests.Response:
    """Make embedding request with optional retry"""
    return requests.post(
        f"{api_url}/v1/embeddings",
        json={"input": text, "model": model},
        timeout=30
    )


# Apply retry decorator if tenacity is available
if HAS_TENACITY:
    _make_embedding_request = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError,
                                       requests.exceptions.Timeout)),
        before_sleep=lambda retry_state: logger.warning(
            f"Embedding request failed, retrying ({retry_state.attempt_number}/3)..."
        )
    )(_make_embedding_request)


class EmbeddingService:
    """Embedding 生成服务"""

    def __init__(self, api_url: str = None):
        """
        初始化 Embedding 服务

        Args:
            api_url: Embedding API 地址
        """
        self.api_url = api_url or MODEL_API_URL
        self.model = EMBEDDING_MODEL

    async def embed_text(self, text: str) -> List[float]:
        """
        生成单个文本的向量

        Args:
            text: 输入文本

        Returns:
            向量列表

        Raises:
            RuntimeError: 当 API 调用失败且未启用模拟模式时
        """
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        try:
            response = _make_embedding_request(self.api_url, text, self.model)

            if response.status_code == 200:
                result = response.json()
                embedding = result.get("data", [{}])[0].get("embedding", [])
                return embedding
            else:
                error_msg = f"Embedding API error: {response.status_code}"
                if EMBEDDING_MOCK_ENABLED:
                    logger.warning(f"{error_msg}, falling back to mock embedding (EMBEDDING_MOCK_ENABLED=true)")
                    return self._mock_embedding(text)
                else:
                    logger.error(f"{error_msg}. Set EMBEDDING_MOCK_ENABLED=true for development or configure a valid embedding service.")
                    raise RuntimeError(f"{error_msg}. Embedding service unavailable.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Embedding API connection failed: {e}"
            if EMBEDDING_MOCK_ENABLED:
                logger.warning(f"{error_msg}, falling back to mock embedding (EMBEDDING_MOCK_ENABLED=true)")
                return self._mock_embedding(text)
            else:
                logger.error(f"{error_msg}. Set EMBEDDING_MOCK_ENABLED=true for development or configure a valid embedding service.")
                raise RuntimeError(f"Embedding service unavailable: {e}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成向量

        Args:
            texts: 输入文本列表

        Returns:
            向量列表的列表
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings

    def _mock_embedding(self, text: str) -> List[float]:
        """
        生成模拟向量（用于开发测试）

        Args:
            text: 输入文本

        Returns:
            模拟向量
        """
        # 简单的基于字符的哈希向量
        import hashlib

        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # 扩展到目标维度
        embedding = []
        for i in range(EMBEDDING_DIM):
            # 循环使用哈希字节
            byte_val = hash_bytes[i % len(hash_bytes)]
            # 归一化到 [-1, 1]
            normalized = (byte_val - 128) / 128.0
            embedding.append(normalized)

        return embedding

    def sync_embed_text(self, text: str) -> List[float]:
        """同步版本的 embed_text"""
        import asyncio
        return asyncio.run(self.embed_text(text))

    def sync_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """同步版本的 embed_texts"""
        import asyncio
        return asyncio.run(self.embed_texts(texts))

    def embed_query(self, query: str) -> List[float]:
        """
        嵌入查询文本（同步接口）

        这是 sync_embed_text 的别名，用于兼容性
        """
        return self.sync_embed_text(query)


# ==================== 全局服务实例 ====================

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取全局 Embedding 服务实例（单例模式）

    Returns:
        EmbeddingService: 全局 Embedding 服务实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        logger.info("Embedding service initialized")
    return _embedding_service


def reset_embedding_service() -> None:
    """重置全局 Embedding 服务（主要用于测试）"""
    global _embedding_service
    _embedding_service = None
