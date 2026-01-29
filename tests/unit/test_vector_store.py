"""
向量存储服务单元测试
Sprint 11: 测试覆盖提升
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import json


class TestVectorStore:
    """VectorStore 单元测试"""

    @pytest.fixture
    def mock_milvus_connections(self):
        """Mock Milvus connections"""
        with patch('services.agent-api.services.vector_store.connections') as mock:
            yield mock

    @pytest.fixture
    def mock_utility(self):
        """Mock Milvus utility"""
        with patch('services.agent-api.services.vector_store.utility') as mock:
            yield mock

    @pytest.fixture
    def mock_collection(self):
        """Mock Milvus Collection"""
        with patch('services.agent-api.services.vector_store.Collection') as mock:
            yield mock

    def test_get_cache_key(self):
        """测试缓存键生成"""
        from services.vector_store import VectorStore

        # 创建实例（使用 mock 避免实际连接）
        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        # 测试缓存键生成
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        key1 = store._get_cache_key("collection1", embedding, 5, None)
        key2 = store._get_cache_key("collection1", embedding, 5, None)
        key3 = store._get_cache_key("collection2", embedding, 5, None)
        key4 = store._get_cache_key("collection1", embedding, 10, None)

        # 相同参数应该生成相同的键
        assert key1 == key2
        # 不同集合应该生成不同的键
        assert key1 != key3
        # 不同 top_k 应该生成不同的键
        assert key1 != key4

    def test_get_cache_key_with_filters(self):
        """测试带过滤条件的缓存键生成"""
        from services.vector_store import VectorStore

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        embedding = [0.1] * 10
        filters1 = {"doc_id": "doc1"}
        filters2 = {"doc_id": "doc2"}

        key1 = store._get_cache_key("collection", embedding, 5, filters1)
        key2 = store._get_cache_key("collection", embedding, 5, filters2)
        key3 = store._get_cache_key("collection", embedding, 5, filters1)

        assert key1 != key2  # 不同过滤条件
        assert key1 == key3  # 相同过滤条件

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        from services.vector_store import VectorStore

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        # 清空缓存
        store.clear_search_cache()

        # 设置缓存
        cache_key = "test_cache_key"
        test_results = [{"id": "1", "score": 0.9, "text": "test"}]

        store._set_cache(cache_key, test_results)

        # 获取缓存
        cached = store._get_from_cache(cache_key)
        assert cached == test_results

    def test_cache_expiry(self):
        """测试缓存过期"""
        import time
        from services.vector_store import VectorStore, SEARCH_CACHE_TTL

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        store.clear_search_cache()

        cache_key = "expiry_test"
        test_results = [{"id": "1"}]

        # 直接设置过期的缓存
        VectorStore._search_cache[cache_key] = (test_results, time.time() - SEARCH_CACHE_TTL - 1)

        # 获取应该返回 None（已过期）
        cached = store._get_from_cache(cache_key)
        assert cached is None

    def test_cache_lru_eviction(self):
        """测试 LRU 缓存淘汰"""
        from services.vector_store import VectorStore, SEARCH_CACHE_SIZE

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        store.clear_search_cache()

        # 填满缓存
        for i in range(SEARCH_CACHE_SIZE):
            store._set_cache(f"key_{i}", [{"id": str(i)}])

        # 添加一个新条目，应该淘汰最旧的
        store._set_cache("new_key", [{"id": "new"}])

        # 缓存大小不应超过限制
        assert len(VectorStore._search_cache) <= SEARCH_CACHE_SIZE

    def test_clear_search_cache(self):
        """测试清空搜索缓存"""
        from services.vector_store import VectorStore

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        # 添加一些缓存
        store._set_cache("key1", [])
        store._set_cache("key2", [])

        # 清空
        store.clear_search_cache()

        assert len(VectorStore._search_cache) == 0


class TestVectorStoreOperations:
    """向量存储操作测试"""

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_create_collection(self, mock_conn, mock_coll, mock_util):
        """测试创建集合"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = False
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()
            result = store.create_collection("test_collection", dimension=1536)

        # 应该创建了集合
        mock_coll.assert_called()
        mock_collection.create_index.assert_called()

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_create_collection_already_exists(self, mock_conn, mock_coll, mock_util):
        """测试创建已存在的集合"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = True
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()
            result = store.create_collection("existing_collection")

        # 应该返回现有集合
        assert result is not None

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_insert(self, mock_conn, mock_coll, mock_util):
        """测试插入向量"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = True
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        texts = ["text1", "text2"]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        metadata = [{"doc_id": "doc1"}, {"doc_id": "doc2"}]

        count = store.insert("test_collection", texts, embeddings, metadata)

        assert count == 2
        mock_collection.insert.assert_called_once()
        mock_collection.flush.assert_called_once()

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_search_with_cache(self, mock_conn, mock_coll, mock_util):
        """测试带缓存的搜索"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = True
        mock_collection = MagicMock()

        # Mock 搜索结果
        mock_hit = MagicMock()
        mock_hit.id = "id1"
        mock_hit.score = 0.9
        mock_hit.entity.get.side_effect = lambda key, default="": {
            "text": "test text",
            "metadata": "{}"
        }.get(key, default)

        mock_collection.search.return_value = [[mock_hit]]
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()
            store.clear_search_cache()

        query_embedding = [0.1] * 1536

        # 第一次搜索 - 应该调用 Milvus
        result1 = store.search("test_collection", query_embedding, top_k=5)
        assert result1["cached"] is False

        # 第二次搜索 - 应该从缓存获取
        result2 = store.search("test_collection", query_embedding, top_k=5)
        assert result2["cached"] is True

    @patch('services.vector_store.utility')
    @patch('services.vector_store.connections')
    def test_search_collection_not_exists(self, mock_conn, mock_util):
        """测试搜索不存在的集合"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = False

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        result = store.search("nonexistent", [0.1] * 1536, top_k=5)

        assert result["results"] == []
        assert result["total"] == 0

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_delete_by_doc_id(self, mock_conn, mock_coll, mock_util):
        """测试按文档ID删除"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = True
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        success = store.delete_by_doc_id("test_collection", "doc123")

        assert success is True
        mock_collection.delete.assert_called_once()
        mock_collection.flush.assert_called_once()

    @patch('services.vector_store.utility')
    @patch('services.vector_store.connections')
    def test_delete_by_doc_id_collection_not_exists(self, mock_conn, mock_util):
        """测试删除时集合不存在"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = False

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        success = store.delete_by_doc_id("nonexistent", "doc123")

        assert success is False

    @patch('services.vector_store.utility')
    @patch('services.vector_store.connections')
    def test_list_collections(self, mock_conn, mock_util):
        """测试列出集合"""
        from services.vector_store import VectorStore

        mock_util.list_collections.return_value = ["coll1", "coll2", "coll3"]

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        collections = store.list_collections()

        assert collections == ["coll1", "coll2", "coll3"]

    @patch('services.vector_store.utility')
    @patch('services.vector_store.Collection')
    @patch('services.vector_store.connections')
    def test_collection_info(self, mock_conn, mock_coll, mock_util):
        """测试获取集合信息"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = True
        mock_collection = MagicMock()
        mock_collection.num_entities = 1000
        mock_collection.schema.fields = [
            MagicMock(name="id", dtype="VARCHAR", is_primary=True),
            MagicMock(name="embedding", dtype="FLOAT_VECTOR", is_primary=False),
        ]
        mock_coll.return_value = mock_collection

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        info = store.collection_info("test_collection")

        assert info["exists"] is True
        assert info["num_entities"] == 1000
        assert "schema" in info

    @patch('services.vector_store.utility')
    @patch('services.vector_store.connections')
    def test_collection_info_not_exists(self, mock_conn, mock_util):
        """测试获取不存在的集合信息"""
        from services.vector_store import VectorStore

        mock_util.has_collection.return_value = False

        with patch.object(VectorStore, '_connect'):
            store = VectorStore()

        info = store.collection_info("nonexistent")

        assert info["exists"] is False
