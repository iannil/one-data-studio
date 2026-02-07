"""
Milvus向量数据库管理器

提供：
1. Milvus连接管理
2. 向量插入功能
3. 向量搜索功能
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    from pymilvus import (
        MilvusClient,
        Collection,
        connections,
        utility,
        FieldSchema,
        CollectionSchema,
        DataType
    )
except ImportError:
    MilvusClient = None
    Collection = None
    connections = None
    utility = None
    FieldSchema = None
    CollectionSchema = None
    DataType = None

from ..config import MilvusConfig


logger = logging.getLogger(__name__)


class MilvusManager:
    """
    Milvus向量数据库管理器

    提供：
    - Collection管理
    - 向量插入
    - 向量搜索
    """

    DEFAULT_VECTOR_DIM = 1536  # OpenAI text-embedding-ada-002维度

    def __init__(self, config: MilvusConfig = None):
        """
        初始化Milvus管理器

        Args:
            config: Milvus配置
        """
        self.config = config or MilvusConfig.from_env()
        self._client = None
        self._connected = False

    @property
    def is_available(self) -> bool:
        """检查pymilvus是否可用"""
        return MilvusClient is not None

    def connect(self) -> bool:
        """
        建立Milvus连接

        Returns:
            连接是否成功
        """
        if not self.is_available:
            logger.warning("pymilvus library not available, using mock mode")
            self._connected = True
            return True

        if self._connected and self._client:
            return True

        try:
            # 使用MilvusClient（新版本API）
            self._client = MilvusClient(
                uri=f"http://{self.config.host}:{self.config.port}",
                user=self.config.user,
                password=self.config.password
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            self._connected = True  # 设置为True以避免重复尝试
            return False

    def disconnect(self):
        """断开Milvus连接"""
        if connections:
            try:
                connections.disconnect("default")
            except Exception:
                pass
        self._client = None
        self._connected = False
        logger.info("Disconnected from Milvus")

    def ensure_collection(
        self,
        collection_name: str,
        dimension: int = DEFAULT_VECTOR_DIM,
        drop_existing: bool = False
    ) -> bool:
        """
        确保collection存在

        Args:
            collection_name: Collection名称
            dimension: 向量维度
            drop_existing: 是否删除已存在的collection

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        if not self._client:
            return False

        try:
            # 检查collection是否存在
            if self._client.has_collection(collection_name):
                if drop_existing:
                    self._client.drop_collection(collection_name)
                    logger.info(f"Dropped existing collection: {collection_name}")
                else:
                    return True

            # 创建collection
            schema = self._create_default_schema(dimension)
            self._client.create_collection(collection_name, dimension=dimension)
            logger.info(f"Created collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure collection {collection_name}: {e}")
            return False

    def _create_default_schema(self, dimension: int) -> CollectionSchema:
        """创建默认schema"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        return CollectionSchema(fields=fields)

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        texts: List[str] = None,
        metadata: List[Dict] = None
    ) -> int:
        """
        批量插入向量

        Args:
            collection_name: Collection名称
            vectors: 向量列表
            ids: ID列表
            texts: 文本列表（可选）
            metadata: 元数据列表（可选）

        Returns:
            插入的数量
        """
        if not self._connected:
            self.connect()

        if not self._client or not vectors:
            return 0

        try:
            # 确保collection存在
            self.ensure_collection(collection_name, dimension=len(vectors[0]))

            # 构建数据
            data = [{"id": id_, "vector": vec} for id_, vec in zip(ids, vectors)]

            # 添加文本
            if texts:
                for i, item in enumerate(data):
                    if i < len(texts):
                        item["text"] = texts[i]

            # 添加元数据
            if metadata:
                for i, item in enumerate(data):
                    if i < len(metadata):
                        item["metadata"] = metadata[i]

            # 插入数据
            self._client.insert(collection_name, data)
            logger.info(f"Inserted {len(data)} vectors into {collection_name}")
            return len(data)

        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return 0

    def insert_vector(
        self,
        collection_name: str,
        vector: List[float],
        id: str,
        text: str = None,
        metadata: Dict = None
    ) -> bool:
        """
        插入单个向量

        Args:
            collection_name: Collection名称
            vector: 向量
            id: ID
            text: 文本（可选）
            metadata: 元数据（可选）

        Returns:
            是否成功
        """
        return self.insert_vectors(
            collection_name,
            [vector],
            [id],
            [text] if text else None,
            [metadata] if metadata else None
        ) > 0

    def search_vectors(
        self,
        collection_name: str,
        vector: List[float],
        top_k: int = 10,
        filter: str = None
    ) -> List[Dict]:
        """
        向量搜索

        Args:
            collection_name: Collection名称
            vector: 查询向量
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            搜索结果列表
        """
        if not self._connected:
            self.connect()

        if not self._client:
            return []

        try:
            results = self._client.search(
                collection_name=collection_name,
                data=[vector],
                limit=top_k,
                filter=filter
            )
            return results[0] if results else []
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def delete_vectors(self, collection_name: str, ids: List[str]) -> int:
        """
        删除向量

        Args:
            collection_name: Collection名称
            ids: ID列表

        Returns:
            删除的数量
        """
        if not self._connected:
            self.connect()

        if not self._client or not ids:
            return 0

        try:
            self._client.delete(collection_name, ids)
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return 0

    def drop_collection(self, collection_name: str) -> bool:
        """
        删除collection

        Args:
            collection_name: Collection名称

        Returns:
            是否成功
        """
        if not self._connected:
            self.connect()

        if not self._client:
            return False

        try:
            if self._client.has_collection(collection_name):
                self._client.drop_collection(collection_name)
                logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            return False

    def get_collection_stats(self, collection_name: str) -> Dict:
        """
        获取collection统计信息

        Args:
            collection_name: Collection名称

        Returns:
            统计信息字典
        """
        if not self._connected:
            self.connect()

        if not self._client:
            return {}

        try:
            stats = self._client.get_collection_stats(collection_name)
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

    # ==================== 便捷方法 ====================

    def insert_document_chunks(
        self,
        collection_name: str,
        doc_id: str,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        插入文档分块向量

        Args:
            collection_name: Collection名称
            doc_id: 文档ID
            chunks: 分块列表，每个包含vector, text, metadata

        Returns:
            插入的数量
        """
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        vectors = [chunk.get("vector", []) for chunk in chunks]
        texts = [chunk.get("text", "") for chunk in chunks]
        metadata = [{"doc_id": doc_id, **chunk.get("metadata", {})} for chunk in chunks]

        return self.insert_vectors(collection_name, vectors, ids, texts, metadata)

    def generate_mock_vector(self, dimension: int = None) -> List[float]:
        """
        生成模拟向量（用于测试）

        Args:
            dimension: 向量维度

        Returns:
            随机向量
        """
        import random
        dim = dimension or self.DEFAULT_VECTOR_DIM
        return [random.random() for _ in range(dim)]


class MockMilvusManager:
    """
    Milvus管理器的Mock实现（用于测试）
    """

    DEFAULT_VECTOR_DIM = 1536

    def __init__(self, config: MilvusConfig = None):
        self.config = config or MilvusConfig()
        self._collections: Dict[str, List[Dict]] = {}
        self._connected = False

    def connect(self) -> bool:
        """模拟连接"""
        self._connected = True
        return True

    def disconnect(self):
        """模拟断开"""
        self._connected = False

    def ensure_collection(self, collection_name: str, dimension: int = None, **kwargs) -> bool:
        """模拟创建collection"""
        if collection_name not in self._collections:
            self._collections[collection_name] = []
        return True

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        texts: List[str] = None,
        metadata: List[Dict] = None
    ) -> int:
        """模拟插入向量"""
        if collection_name not in self._collections:
            self._collections[collection_name] = []

        for i, (vec, id_) in enumerate(zip(vectors, ids)):
            item = {
                "id": id_,
                "vector": vec,
                "text": texts[i] if texts and i < len(texts) else "",
                "metadata": metadata[i] if metadata and i < len(metadata) else {}
            }
            self._collections[collection_name].append(item)

        return len(vectors)

    def insert_vector(
        self,
        collection_name: str,
        vector: List[float],
        id: str,
        text: str = None,
        metadata: Dict = None
    ) -> bool:
        """模拟插入单个向量"""
        return self.insert_vectors(collection_name, [vector], [id], [text] if text else None, [metadata] if metadata else None) > 0

    def search_vectors(
        self,
        collection_name: str,
        vector: List[float],
        top_k: int = 10,
        **kwargs
    ) -> List[Dict]:
        """模拟搜索（返回随机结果）"""
        if collection_name not in self._collections:
            return []

        import random
        items = self._collections[collection_name]
        count = min(top_k, len(items))
        return random.sample(items, count) if items else []

    def delete_vectors(self, collection_name: str, ids: List[str]) -> int:
        """模拟删除向量"""
        if collection_name not in self._collections:
            return 0

        original_len = len(self._collections[collection_name])
        id_set = set(ids)
        self._collections[collection_name] = [
            item for item in self._collections[collection_name]
            if item["id"] not in id_set
        ]
        return original_len - len(self._collections[collection_name])

    def drop_collection(self, collection_name: str) -> bool:
        """模拟删除collection"""
        self._collections.pop(collection_name, None)
        return True

    def get_collection_stats(self, collection_name: str) -> Dict:
        """模拟获取统计"""
        if collection_name in self._collections:
            return {"row_count": len(self._collections[collection_name])}
        return {}

    def insert_document_chunks(self, collection_name: str, doc_id: str, chunks: List[Dict]) -> int:
        """模拟插入文档分块"""
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        vectors = [chunk.get("vector", []) for chunk in chunks]
        texts = [chunk.get("text", "") for chunk in chunks]
        return self.insert_vectors(collection_name, vectors, ids, texts)

    def generate_mock_vector(self, dimension: int = None) -> List[float]:
        """生成模拟向量"""
        import random
        dim = dimension or self.DEFAULT_VECTOR_DIM
        return [random.random() for _ in range(dim)]

    def get_all_collections(self) -> Dict[str, List[Dict]]:
        """获取所有collection（用于测试验证）"""
        return self._collections.copy()


def get_milvus_manager(config: MilvusConfig = None, mock: bool = False) -> MilvusManager:
    """
    获取Milvus管理器实例

    Args:
        config: Milvus配置
        mock: 是否使用Mock实现

    Returns:
        Milvus管理器实例
    """
    if mock or MilvusClient is None:
        return MockMilvusManager(config)
    return MilvusManager(config)
