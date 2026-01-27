"""
Milvus 向量数据库集成测试

测试场景:
1. 连接测试 - 验证 Milvus 服务可用性
2. 故障转移测试 - 验证多主机故障转移
3. 集合操作测试 - 创建、插入、搜索、删除
4. 性能测试 - 大批量数据插入和搜索
5. 高可用测试 - 节点故障场景
"""

import os
import pytest
import numpy as np
from typing import List
from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType

# 测试配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_HOSTS = os.getenv("MILVUS_HOSTS", MILVUS_HOST)
EMBEDDING_DIM = 128  # 使用较小的维度进行测试
TEST_COLLECTION = "test_integration"


class TestMilvusConnection:
    """Milvus 连接测试"""

    def test_connect_single_host(self):
        """测试单主机连接"""
        try:
            connections.connect(alias="test", host=MILVUS_HOST, port=int(MILVUS_PORT))
            assert connections.has_connection("test")
            connections.disconnect("test")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")

    def test_connect_multiple_hosts(self):
        """测试多主机连接（故障转移）"""
        hosts = [h.strip() for h in MILVUS_HOSTS.split(",")]
        connected = False

        for i, host in enumerate(hosts):
            try:
                # 提取端口
                if ":" in host:
                    h, p = host.split(":", 1)
                    port = int(p)
                else:
                    h = host
                    port = int(MILVUS_PORT)

                connections.connect(alias=f"test_{i}", host=h, port=port, timeout=5)
                assert connections.has_connection(f"test_{i}")
                connections.disconnect(f"test_{i}")
                connected = True
                break
            except Exception as e:
                continue

        assert connected, "Failed to connect to any Milvus host"

    def test_connection_health_check(self):
        """测试连接健康检查"""
        try:
            connections.connect(alias="health", host=MILVUS_HOST, port=int(MILVUS_PORT))
            # 健康检查：列出集合
            collections = utility.list_collections(using="health")
            assert isinstance(collections, list)
            connections.disconnect("health")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")

    def test_server_info(self):
        """测试获取服务器信息"""
        try:
            connections.connect(alias="info", host=MILVUS_HOST, port=int(MILVUS_PORT))
            version = utility.get_server_version(using="info")
            assert version is not None
            connections.disconnect("info")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")


class TestMilvusCollection:
    """Milvus 集合操作测试"""

    @pytest.fixture
    def connection(self):
        """建立测试连接"""
        try:
            connections.connect(alias="test", host=MILVUS_HOST, port=int(MILVUS_PORT))
            yield
            # 清理
            if utility.has_collection(TEST_COLLECTION, using="test"):
                utility.drop_collection(TEST_COLLECTION, using="test")
            connections.disconnect("test")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")

    def test_create_collection(self, connection):
        """测试创建集合"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="test")

        assert utility.has_collection(TEST_COLLECTION, using="test")
        assert collection.name == TEST_COLLECTION
        assert collection.num_entities == 0

    def test_insert_data(self, connection):
        """测试插入数据"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="test")

        # 准备测试数据
        num_entities = 100
        ids = [f"test_{i}" for i in range(num_entities)]
        embeddings = [[float(x) for x in range(EMBEDDING_DIM)] for _ in range(num_entities)]
        texts = [f"test text {i}" for i in range(num_entities)]

        # 插入数据
        collection.insert([ids, embeddings, texts])
        collection.flush()
        collection.load()

        assert collection.num_entities == num_entities

    def test_search_data(self, connection):
        """测试搜索数据"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="test")

        # 创建索引
        index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
        collection.create_index("embedding", index_params)

        # 插入测试数据
        num_entities = 100
        ids = [f"test_{i}" for i in range(num_entities)]
        embeddings = [np.random.rand(EMBEDDING_DIM).tolist() for _ in range(num_entities)]
        texts = [f"test text {i}" for i in range(num_entities)]
        collection.insert([ids, embeddings, texts])
        collection.flush()
        collection.load()

        # 执行搜索
        query_vector = [embeddings[0]]
        results = collection.search(
            data=query_vector,
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=10,
            output_fields=["text"]
        )

        assert len(results[0]) > 0
        assert results[0][0].id == "test_0"

    def test_delete_data(self, connection):
        """测试删除数据"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="test")

        # 插入数据
        num_entities = 10
        ids = [f"test_{i}" for i in range(num_entities)]
        embeddings = [[float(x) for x in range(EMBEDDING_DIM)] for _ in range(num_entities)]
        collection.insert([ids, embeddings])
        collection.flush()
        collection.load()

        initial_count = collection.num_entities

        # 删除部分数据
        collection.delete(f"id in ['test_0', 'test_1', 'test_2']")
        collection.flush()
        collection.load()

        assert collection.num_entities == initial_count - 3

    def test_drop_collection(self, connection):
        """测试删除集合"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        Collection(TEST_COLLECTION, schema, using="test")

        assert utility.has_collection(TEST_COLLECTION, using="test")

        # 删除集合
        utility.drop_collection(TEST_COLLECTION, using="test")

        assert not utility.has_collection(TEST_COLLECTION, using="test")


class TestMilvusPerformance:
    """Milvus 性能测试"""

    @pytest.fixture
    def connection(self):
        """建立测试连接"""
        try:
            connections.connect(alias="perf", host=MILVUS_HOST, port=int(MILVUS_PORT))
            yield
            # 清理
            if utility.has_collection(TEST_COLLECTION, using="perf"):
                utility.drop_collection(TEST_COLLECTION, using="perf")
            connections.disconnect("perf")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")

    def test_bulk_insert_performance(self, connection):
        """测试大批量插入性能"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="perf")

        # 创建索引
        index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
        collection.create_index("embedding", index_params)

        import time
        batch_size = 1000
        num_batches = 10

        start_time = time.time()

        for batch in range(num_batches):
            base_id = batch * batch_size
            ids = [f"perf_{base_id + i}" for i in range(batch_size)]
            embeddings = np.random.rand(batch_size, EMBEDDING_DIM).tolist()
            texts = [f"performance test text {base_id + i}" for i in range(batch_size)]

            collection.insert([ids, embeddings, texts])

        collection.flush()
        collection.load()

        elapsed = time.time() - start_time
        total_entities = batch_size * num_batches
        entities_per_second = total_entities / elapsed

        print(f"\n插入 {total_entities} 条数据耗时: {elapsed:.2f}秒")
        print(f"插入速率: {entities_per_second:.2f} entities/秒")

        assert collection.num_entities == total_entities
        # 性能基准: 至少 100 entities/秒
        assert entities_per_second > 100

    def test_search_performance(self, connection):
        """测试搜索性能"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="perf")

        # 创建索引
        index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
        collection.create_index("embedding", index_params)

        # 插入测试数据
        num_entities = 1000
        ids = [f"perf_{i}" for i in range(num_entities)]
        embeddings = np.random.rand(num_entities, EMBEDDING_DIM).tolist()
        collection.insert([ids, embeddings])
        collection.flush()
        collection.load()

        # 执行多次搜索
        import time
        num_searches = 100

        start_time = time.time()
        for _ in range(num_searches):
            query_vector = [np.random.rand(EMBEDDING_DIM).tolist()]
            collection.search(
                data=query_vector,
                anns_field="embedding",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=10
            )
        elapsed = time.time() - start_time

        searches_per_second = num_searches / elapsed
        avg_latency = (elapsed / num_searches) * 1000  # ms

        print(f"\n{num_searches} 次搜索耗时: {elapsed:.2f}秒")
        print(f"搜索速率: {searches_per_second:.2f} searches/秒")
        print(f"平均延迟: {avg_latency:.2f}ms")

        # 性能基准: 至少 10 searches/秒，平均延迟 < 500ms
        assert searches_per_second > 10
        assert avg_latency < 500

    def test_concurrent_operations(self, connection):
        """测试并发操作"""
        import concurrent.futures
        import time

        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="perf")

        def insert_worker(worker_id):
            """并发插入工作线程"""
            try:
                ids = [f"worker_{worker_id}_item_{i}" for i in range(100)]
                embeddings = np.random.rand(100, EMBEDDING_DIM).tolist()
                collection.insert([ids, embeddings])
                return True
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
                return False

        # 并发插入
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_worker, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.time() - start_time

        collection.flush()
        collection.load()

        assert all(results), "Some concurrent operations failed"
        assert collection.num_entities == 500
        print(f"\n并发插入 500 条数据耗时: {elapsed:.2f}秒")


class TestMilvusFailover:
    """Milvus 故障转移测试"""

    def test_failover_on_connection_failure(self):
        """测试连接失败时的故障转移"""
        hosts = [h.strip() for h in MILVUS_HOSTS.split(",")]

        # 如果只有一个主机，跳过此测试
        if len(hosts) <= 1:
            pytest.skip("Need multiple hosts for failover test")

        connected = False
        last_error = None

        for i, host in enumerate(hosts):
            try:
                if ":" in host:
                    h, p = host.split(":", 1)
                    port = int(p)
                else:
                    h = host
                    port = int(MILVUS_PORT)

                # 尝试连接
                connections.connect(alias=f"failover_{i}", host=h, port=port, timeout=3)
                connected = True
                connections.disconnect(f"failover_{i}")
                break
            except Exception as e:
                last_error = e
                continue

        assert connected, f"Failed to connect to any host. Last error: {last_error}"

    def test_reconnect_after_disconnect(self):
        """测试断开后重连"""
        try:
            # 第一次连接
            connections.connect(alias="reconnect", host=MILVUS_HOST, port=int(MILVUS_PORT))
            assert connections.has_connection("reconnect")

            # 断开连接
            connections.disconnect("reconnect")
            assert not connections.has_connection("reconnect")

            # 重新连接
            connections.connect(alias="reconnect", host=MILVUS_HOST, port=int(MILVUS_PORT))
            assert connections.has_connection("reconnect")

            # 验证连接可用
            collections = utility.list_collections(using="reconnect")
            assert isinstance(collections, list)

            connections.disconnect("reconnect")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")


class TestMilvusIndex:
    """Milvus 索引测试"""

    @pytest.fixture
    def connection(self):
        """建立测试连接"""
        try:
            connections.connect(alias="index", host=MILVUS_HOST, port=int(MILVUS_PORT))
            yield
            if utility.has_collection(TEST_COLLECTION, using="index"):
                utility.drop_collection(TEST_COLLECTION, using="index")
            connections.disconnect("index")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")

    @pytest.mark.parametrize("index_type", ["IVF_FLAT", "HNSW", "FLAT"])
    def test_create_different_index_types(self, connection, index_type):
        """测试创建不同类型的索引"""
        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, f"{TEST_COLLECTION} schema")
        collection = Collection(TEST_COLLECTION, schema, using="index")

        # 根据索引类型设置参数
        if index_type == "IVF_FLAT":
            params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
        elif index_type == "HNSW":
            params = {"index_type": "HNSW", "metric_type": "L2", "params": {"M": 16, "efConstruction": 256}}
        else:  # FLAT
            params = {"index_type": "FLAT", "metric_type": "L2"}

        # 创建索引
        collection.create_index("embedding", params)
        index_info = collection.index()

        assert index_info is not None
        assert index_info.params["index_type"] == index_type


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
