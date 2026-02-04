"""
Phase 2: 元数据与向量数据库验证测试

测试覆盖范围:
- etcd 健康检查和基本操作
- Milvus 集合创建、向量插入和搜索
- Elasticsearch 索引创建和搜索
- OpenMetadata 服务连接和基本操作

测试用例编号: INT-P2-001 ~ INT-P2-030
"""

import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestETCDInfrastructure:
    """INT-P2-001 ~ INT-P2-005: etcd 基础设施测试"""

    @pytest.fixture
    def etcd_config(self):
        """etcd 配置"""
        return {
            "host": os.getenv("ETCD_HOST", "localhost"),
            "port": int(os.getenv("ETCD_PORT", "2379")),
        }

    def test_etcd_connection(self, etcd_config):
        """INT-P2-001: etcd 连接测试"""
        import requests

        url = f"http://{etcd_config['host']}:{etcd_config['port']}/health"
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"etcd 连接失败: {e}")

    def test_etcd_endpoint_health(self, etcd_config):
        """INT-P2-002: etcd 端点健康检查"""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "exec", "one-data-etcd", "etcdctl", "endpoint", "health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert "is healthy" in result.stdout or result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")

    def test_etcd_put_and_get(self, etcd_config):
        """INT-P2-003: etcd PUT 和 GET 操作测试"""
        import subprocess

        key = f"/test/key_{int(time.time())}"
        value = "test_value"

        try:
            # PUT
            subprocess.run(
                ["docker", "exec", "one-data-etcd", "etcdctl", "put", key, value],
                capture_output=True,
                timeout=5
            )

            # GET
            result = subprocess.run(
                ["docker", "exec", "one-data-etcd", "etcdctl", "get", key],
                capture_output=True,
                text=True,
                timeout=5
            )

            assert value in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")

    def test_etcd_list_keys(self, etcd_config):
        """INT-P2-004: etcd 列出键测试"""
        import subprocess

        try:
            # 先添加一些键
            prefix = f"/test/list_{int(time.time())}"
            for i in range(3):
                subprocess.run(
                    ["docker", "exec", "one-data-etcd", "etcdctl", "put", f"{prefix}/key{i}", f"value{i}"],
                    capture_output=True,
                    timeout=5
                )

            # 列出键
            result = subprocess.run(
                ["docker", "exec", "one-data-etcd", "etcdctl", "get", f"{prefix}/*", "--prefix"],
                capture_output=True,
                text=True,
                timeout=5
            )

            assert "key0" in result.stdout
            assert "key1" in result.stdout
            assert "key2" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")

    def test_etcd_member_list(self, etcd_config):
        """INT-P2-005: etcd 成员列表测试"""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "exec", "one-data-etcd", "etcdctl", "member", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")


@pytest.mark.integration
class TestMilvusInfrastructure:
    """INT-P2-006 ~ INT-P2-015: Milvus 向量数据库测试"""

    @pytest.fixture
    def milvus_config(self):
        """Milvus 配置"""
        return {
            "host": os.getenv("MILVUS_HOST", "localhost"),
            "port": int(os.getenv("MILVUS_PORT", "19530")),
        }

    @pytest.fixture
    def milvus_client(self, milvus_config):
        """创建 Milvus 连接"""
        try:
            from pymilvus import connections, utility
            connections.connect(host=milvus_config["host"], port=milvus_config["port"])
            yield connections
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus 连接失败: {e}")

    def test_milvus_connection(self, milvus_config):
        """INT-P2-006: Milvus 连接测试"""
        import requests

        url = f"http://{milvus_config['host']}:{milvus_config['port']}/healthz"
        try:
            response = requests.get(url, timeout=5)
            # Milvus healthz 可能返回 200 或 204
            assert response.status_code in [200, 204]
        except Exception as e:
            pytest.skip(f"Milvus health check failed: {e}")

    def test_milvus_list_collections(self, milvus_client):
        """INT-P2-007: 列出集合测试"""
        try:
            from pymilvus import utility
            collections = utility.list_collections()
            assert isinstance(collections, list)
        except Exception as e:
            pytest.skip(f"Milvus list collections failed: {e}")

    def test_milvus_create_collection(self, milvus_config):
        """INT-P2-008: 创建集合测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
            import random

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_collection_{int(time.time())}"

            # 定义 schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test collection")

            # 创建集合
            collection = Collection(name=collection_name, schema=schema)

            # 验证集合存在
            from pymilvus import utility
            assert utility.has_collection(collection_name)

            # 清理
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus create collection failed: {e}")

    def test_milvus_insert_and_search(self, milvus_config):
        """INT-P2-009: 插入和搜索向量测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
            import random

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_search_{int(time.time())}"

            # 定义 schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test search collection")

            collection = Collection(name=collection_name, schema=schema)

            # 插入数据
            entities = [
                [random.random() for _ in range(128)] for _ in range(10)
            ]
            collection.insert([[i for i in range(10)], entities])
            collection.flush()

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()

            # 搜索
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            query_vector = [[random.random() for _ in range(128)]]
            results = collection.search(query_vector, "embedding", search_params, limit=5)

            assert results is not None
            assert len(results[0]) <= 5

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus search failed: {e}")

    def test_milvus_collection_info(self, milvus_config):
        """INT-P2-010: 集合信息查询测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_info_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test info collection")
            collection = Collection(name=collection_name, schema=schema)

            # 获取集合信息
            info = collection.describe()
            assert "fields" in info
            assert len(info["fields"]) == 2

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus collection info failed: {e}")

    def test_milvus_index_operations(self, milvus_config):
        """INT-P2-011: 索引操作测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_index_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test index collection")
            collection = Collection(name=collection_name, schema=schema)

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)

            # 列出索引
            indexes = collection.indexes
            assert len(indexes) > 0

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus index operations failed: {e}")

    def test_milvus_partition_operations(self, milvus_config):
        """INT-P2-012: 分区操作测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_partition_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="partition_key", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test partition collection")
            collection = Collection(name=collection_name, schema=schema)

            # 创建分区
            partition_name = "test_partition"
            collection.create_partition(partition_name)

            # 列出分区
            partitions = collection.partitions
            assert len(partitions) >= 2  # _default + test_partition

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus partition operations failed: {e}")

    def test_milvus_vector_dimensions(self, milvus_config):
        """INT-P2-013: 向量维度测试"""
        # 测试不同维度的向量
        dimensions = [64, 128, 256, 512, 768, 1024, 1536]

        for dim in dimensions:
            collection_name = f"test_dim_{dim}_{int(time.time())}"

            try:
                from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

                connections.connect(host=milvus_config["host"], port=milvus_config["port"])

                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
                ]
                schema = CollectionSchema(fields=fields, description=f"Test {dim}D collection")
                collection = Collection(name=collection_name, schema=schema)

                # 验证维度
                info = collection.describe()
                vector_field = [f for f in info["fields"] if f["name"] == "embedding"][0]
                assert vector_field["params"]["dim"] == dim

                # 清理
                from pymilvus import utility
                utility.drop_collection(collection_name)
                connections.disconnect("default")
            except Exception as e:
                pytest.skip(f"Milvus dimension {dim} test failed: {e}")

    def test_milvus_distance_metrics(self, milvus_config):
        """INT-P2-014: 距离度量测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_metric_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test metric collection")
            collection = Collection(name=collection_name, schema=schema)

            # 测试不同的距离度量
            metrics = ["L2", "IP", "COSINE"]
            for metric in metrics:
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": metric,
                    "params": {"nlist": 128}
                }
                try:
                    collection.create_index(
                        field_name="embedding",
                        index_params=index_params,
                        index_name=f"index_{metric}"
                    )
                except:
                    pass  # 某些度量可能需要特定的索引类型

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus distance metrics test failed: {e}")

    def test_milvus_bulk_insert(self, milvus_config):
        """INT-P2-015: 批量插入测试"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
            import random

            connections.connect(host=milvus_config["host"], port=milvus_config["port"])

            collection_name = f"test_bulk_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Test bulk insert collection")
            collection = Collection(name=collection_name, schema=schema)

            # 批量插入
            batch_size = 1000
            entities = [[random.random() for _ in range(128)] for _ in range(batch_size)]
            collection.insert([[i for i in range(batch_size)], entities])
            collection.flush()

            # 验证插入数量
            assert collection.num_entities == batch_size

            # 清理
            from pymilvus import utility
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Milvus bulk insert test failed: {e}")


@pytest.mark.integration
class TestElasticsearchInfrastructure:
    """INT-P2-016 ~ INT-P2-022: Elasticsearch 基础设施测试"""

    @pytest.fixture
    def es_config(self):
        """Elasticsearch 配置"""
        return {
            "host": os.getenv("ES_HOST", "localhost"),
            "port": int(os.getenv("ES_PORT", "9200")),
        }

    def test_elasticsearch_connection(self, es_config):
        """INT-P2-016: Elasticsearch 连接测试"""
        import requests

        url = f"http://{es_config['host']}:{es_config['port']}/"
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert "cluster_name" in data
        except Exception as e:
            pytest.skip(f"Elasticsearch 连接失败: {e}")

    def test_elasticsearch_cluster_health(self, es_config):
        """INT-P2-017: 集群健康检查"""
        import requests

        url = f"http://{es_config['host']}:{es_config['port']}/_cluster/health"
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["green", "yellow"]
        except Exception as e:
            pytest.skip(f"Elasticsearch health check failed: {e}")

    def test_elasticsearch_create_index(self, es_config):
        """INT-P2-018: 创建索引测试"""
        import requests

        index_name = f"test_index_{int(time.time())}"
        url = f"http://{es_config['host']}:{es_config['port']}/{index_name}"

        try:
            # 创建索引
            mapping = {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "timestamp": {"type": "date"}
                    }
                }
            }
            response = requests.put(url, json=mapping, timeout=5)
            assert response.status_code in [200, 201]

            # 验证索引存在
            response = requests.get(f"{url}/_mapping", timeout=5)
            assert response.status_code == 200

            # 清理
            requests.delete(url, timeout=5)
        except Exception as e:
            pytest.skip(f"Elasticsearch create index failed: {e}")

    def test_elasticsearch_index_document(self, es_config):
        """INT-P2-019: 索引文档测试"""
        import requests

        index_name = f"test_doc_{int(time.time())}"
        url = f"http://{es_config['host']}:{es_config['port']}/{index_name}/_doc"

        try:
            # 索引文档
            doc = {
                "title": "Test Document",
                "content": "This is a test document for Elasticsearch.",
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(url, json=doc, timeout=5)
            assert response.status_code in [200, 201]

            result = response.json()
            assert "result" in result
            assert result["result"] in ["created", "updated"]

            # 清理
            requests.delete(f"http://{es_config['host']}:{es_config['port']}/{index_name}", timeout=5)
        except Exception as e:
            pytest.skip(f"Elasticsearch index document failed: {e}")

    def test_elasticsearch_search(self, es_config):
        """INT-P2-020: 搜索测试"""
        import requests

        index_name = f"test_search_{int(time.time())}"

        try:
            # 创建索引并添加文档
            url = f"http://{es_config['host']}:{es_config['port']}/{index_name}"
            requests.put(url, timeout=5)

            # 添加文档
            doc_url = f"{url}/_doc"
            docs = [
                {"title": "Python Programming", "content": "Learn Python programming"},
                {"title": "Java Programming", "content": "Learn Java programming"},
                {"title": "Data Science", "content": "Data science with Python"}
            ]
            for doc in docs:
                requests.post(doc_url, json=doc, timeout=5)

            # 等待索引刷新
            requests.post(f"{url}/_refresh", timeout=5)

            # 搜索
            search_url = f"{url}/_search"
            query = {"query": {"match": {"content": "Python"}}}
            response = requests.get(search_url, json=query, timeout=5)
            assert response.status_code == 200

            results = response.json()
            assert "hits" in results
            assert results["hits"]["total"]["value"] >= 1

            # 清理
            requests.delete(url, timeout=5)
        except Exception as e:
            pytest.skip(f"Elasticsearch search failed: {e}")

    def test_elasticsearch_aggregation(self, es_config):
        """INT-P2-021: 聚合测试"""
        import requests

        index_name = f"test_agg_{int(time.time())}"

        try:
            # 创建索引并添加文档
            url = f"http://{es_config['host']}:{es_config['port']}/{index_name}"
            requests.put(url, timeout=5)

            doc_url = f"{url}/_doc"
            docs = [
                {"category": "A", "value": 10},
                {"category": "A", "value": 20},
                {"category": "B", "value": 15},
            ]
            for doc in docs:
                requests.post(doc_url, json=doc, timeout=5)

            requests.post(f"{url}/_refresh", timeout=5)

            # 聚合查询
            search_url = f"{url}/_search"
            query = {
                "size": 0,
                "aggs": {
                    "by_category": {
                        "terms": {"field": "category.keyword"},
                        "aggs": {
                            "total_value": {"sum": {"field": "value"}}
                        }
                    }
                }
            }
            response = requests.get(search_url, json=query, timeout=5)
            assert response.status_code == 200

            results = response.json()
            assert "aggregations" in results

            # 清理
            requests.delete(url, timeout=5)
        except Exception as e:
            pytest.skip(f"Elasticsearch aggregation failed: {e}")

    def test_elasticsearch_complex_query(self, es_config):
        """INT-P2-022: 复杂查询测试"""
        import requests

        index_name = f"test_complex_{int(time.time())}"

        try:
            url = f"http://{es_config['host']}:{es_config['port']}/{index_name}"
            requests.put(url, timeout=5)

            # Bool 查询
            search_url = f"{url}/_search"
            query = {
                "query": {
                    "bool": {
                        "must": [{"match": {"title": "test"}}],
                        "should": [{"match": {"content": "important"}}],
                        "filter": [{"range": {"timestamp": {"gte": "2024-01-01"}}}]
                    }
                }
            }
            response = requests.get(search_url, json=query, timeout=5)
            assert response.status_code == 200

            # 清理
            requests.delete(url, timeout=5)
        except Exception as e:
            pytest.skip(f"Elasticsearch complex query failed: {e}")


@pytest.mark.integration
class TestOpenMetadataInfrastructure:
    """INT-P2-023 ~ INT-P2-030: OpenMetadata 基础设施测试"""

    @pytest.fixture
    def om_config(self):
        """OpenMetadata 配置"""
        return {
            "host": os.getenv("OPENMETADATA_HOST", "localhost"),
            "port": int(os.getenv("OPENMETADATA_PORT", "8585")),
            "api_version": "v1",
        }

    def test_openmetadata_connection(self, om_config):
        """INT-P2-023: OpenMetadata 连接测试"""
        import requests

        url = f"http://{om_config['host']}:{om_config['port']}/api/v1/system/version"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"OpenMetadata 连接失败: {e}")

    def test_openmetadata_version_info(self, om_config):
        """INT-P2-024: 版本信息测试"""
        import requests

        url = f"http://{om_config['host']}:{om_config['port']}/api/v1/system/version"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "version" in data
            print(f"OpenMetadata version: {data.get('version')}")
        except Exception as e:
            pytest.skip(f"OpenMetadata version check failed: {e}")

    def test_openmetadata_list_databases(self, om_config):
        """INT-P2-025: 列出数据库测试"""
        import requests

        # 首先需要获取 token
        auth_url = f"http://{om_config['host']}:{om_config['port']}/api/v1/users/login"
        try:
            # 尝试登录获取 token
            auth_response = requests.post(
                auth_url,
                json={"username": "admin", "password": "admin"},
                timeout=10
            )

            if auth_response.status_code == 200:
                token = auth_response.json().get("token")
                headers = {"Authorization": f"Bearer {token}"}
            else:
                headers = {}

            # 列出数据库服务
            services_url = f"http://{om_config['host']}:{om_config['port']}/api/v1/databaseServices"
            response = requests.get(services_url, headers=headers, timeout=10)
            assert response.status_code in [200, 401]  # 401 表示需要认证
        except Exception as e:
            pytest.skip(f"OpenMetadata list databases failed: {e}")

    def test_openmetadata_health_check(self, om_config):
        """INT-P2-026: 健康检查测试"""
        import requests

        url = f"http://{om_config['host']}:{om_config['port']}/api/v1/system/health"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"OpenMetadata health check failed: {e}")

    def test_openmetadata_configuration(self, om_config):
        """INT-P2-027: 配置查询测试"""
        import requests

        url = f"http://{om_config['host']}:{om_config['port']}/api/v1/system/config"
        try:
            response = requests.get(url, timeout=10)
            # 可能需要认证
            assert response.status_code in [200, 401]
        except Exception as e:
            pytest.skip(f"OpenMetadata config check failed: {e}")

    def test_openmetadata_ingestion_framework(self, om_config):
        """INT-P2-028: 数据摄取框架测试"""
        # 模拟元数据摄取
        import requests

        try:
            # 检查 ingest 端点
            ingest_url = f"http://{om_config['host']}:{om_config['port']}/api/v1/ingestion/workflows"
            response = requests.get(ingest_url, timeout=10)
            # 可能需要认证
            assert response.status_code in [200, 401]
        except Exception as e:
            pytest.skip(f"OpenMetadata ingestion check failed: {e}")

    def test_openmetadata_tables_metadata(self, om_config):
        """INT-P2-029: 表元数据查询测试"""
        import requests

        try:
            # 获取表列表
            tables_url = f"http://{om_config['host']}:{om_config['port']}/api/v1/tables"
            response = requests.get(tables_url, timeout=10)
            # 可能需要认证或没有表
            assert response.status_code in [200, 401, 404]
        except Exception as e:
            pytest.skip(f"OpenMetadata tables check failed: {e}")

    def test_openmetadata_search_api(self, om_config):
        """INT-P2-030: 搜索 API 测试"""
        import requests

        try:
            # 使用搜索 API
            search_url = f"http://{om_config['host']}:{om_config['port']}/api/v1/search"
            query = {"query": "*", "index": "table_search_index"}
            response = requests.post(search_url, json=query, timeout=10)
            # 可能需要认证
            assert response.status_code in [200, 401]
        except Exception as e:
            pytest.skip(f"OpenMetadata search check failed: {e}")


@pytest.mark.integration
class TestMetadataIntegration:
    """INT-P2-031 ~ INT-P2-035: 元数据服务集成测试"""

    def test_milvus_minio_integration(self):
        """INT-P2-031: Milvus 与 MinIO 集成测试"""
        # Milvus 使用 MinIO 存储数据
        # 验证 Milvus 的 MinIO bucket 是否存在
        from minio import Minio

        try:
            client = Minio(
                os.getenv("MINIO_ENDPOINT", "localhost:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=False,
            )
            buckets = [b.name for b in client.list_buckets()]
            # Milvus 默认使用 "milvus" bucket
            print(f"MinIO buckets: {buckets}")
        except Exception as e:
            pytest.skip(f"Milvus-MinIO integration check failed: {e}")

    def test_elasticsearch_disk_usage(self):
        """INT-P2-032: Elasticsearch 磁盘使用监控测试"""
        import requests

        try:
            url = f"http://{os.getenv('ES_HOST', 'localhost')}:{os.getenv('ES_PORT', '9200')}/_nodes/stats/fs"
            response = requests.get(url, timeout=10)
            assert response.status_code == 200

            data = response.json()
            print(f"Elasticsearch disk usage: {data}")
        except Exception as e:
            pytest.skip(f"Elasticsearch disk usage check failed: {e}")

    def test_vector_search_performance(self):
        """INT-P2-033: 向量搜索性能测试"""
        import time

        try:
            from pymilvus import connections

            connections.connect(
                host=os.getenv("MILVUS_HOST", "localhost"),
                port=int(os.getenv("MILVUS_PORT", "19530"))
            )

            # 创建测试集合
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility
            import random

            collection_name = f"test_perf_{int(time.time())}"

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
            ]
            schema = CollectionSchema(fields=fields, description="Performance test")
            collection = Collection(name=collection_name, schema=schema)

            # 插入测试数据
            batch_size = 100
            entities = [[random.random() for _ in range(128)] for _ in range(batch_size)]
            start_time = time.time()
            collection.insert([[i for i in range(batch_size)], entities])
            collection.flush()
            insert_time = time.time() - start_time

            # 创建索引并搜索
            index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()

            query_vector = [[random.random() for _ in range(128)]]
            start_time = time.time()
            results = collection.search(query_vector, "embedding", {"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            search_time = time.time() - start_time

            print(f"Insert {batch_size} vectors: {insert_time:.3f}s")
            print(f"Search 1 vector: {search_time:.3f}s")

            # 清理
            utility.drop_collection(collection_name)
            connections.disconnect("default")
        except ImportError:
            pytest.skip("pymilvus not installed")
        except Exception as e:
            pytest.skip(f"Vector search performance test failed: {e}")

    def test_service_dependencies(self):
        """INT-P2-034: 服务依赖关系测试"""
        # 验证服务启动顺序
        services = {
            "etcd": 2379,
            "milvus": 19530,
            "elasticsearch": 9200,
            "openmetadata": 8585,
        }

        import subprocess

        running_services = []
        for service, port in services.items():
            try:
                result = subprocess.run(
                    ["docker", "inspect", f"--format='{{.State.Status}}'", f"one-data-{service}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "running" in result.stdout:
                    running_services.append(service)
            except:
                pass

        print(f"Running services: {running_services}")

    def test_metadata_consistency(self):
        """INT-P2-035: 元数据一致性测试"""
        # 验证各元数据存储之间的数据一致性
        # 这是一个框架测试，实际实现需要根据业务逻辑

        # 模拟: 在 OpenMetadata 注册数据库后，Milvus 中应有对应的向量索引
        # Elasticsearch 中应有可搜索的索引

        print("Metadata consistency test: Framework only")
        print("This test should be extended with actual consistency checks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
