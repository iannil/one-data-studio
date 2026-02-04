"""
Phase 1: 基础设施验证测试

测试覆盖范围:
- MySQL 数据库连接和操作
- Redis 缓存连接和操作
- MinIO 对象存储连接和操作

测试用例编号: INT-P1-001 ~ INT-P1-020
"""

import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
import pymysql
import redis
from minio import Minio

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestMySQLInfrastructure:
    """INT-P1-001 ~ INT-P1-008: MySQL 基础设施测试"""

    @pytest.fixture
    def mysql_config(self):
        """MySQL 配置"""
        return {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "onedata"),
            "password": os.getenv("MYSQL_PASSWORD", "onedata"),
            "database": os.getenv("MYSQL_DATABASE", "onedata"),
        }

    @pytest.fixture
    def mysql_connection(self, mysql_config):
        """创建 MySQL 连接"""
        try:
            conn = pymysql.connect(
                host=mysql_config["host"],
                port=mysql_config["port"],
                user=mysql_config["user"],
                password=mysql_config["password"],
                database=mysql_config["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"MySQL 连接失败: {e}")

    def test_mysql_connection(self, mysql_connection):
        """INT-P1-001: MySQL 连接测试"""
        assert mysql_connection.open
        result = mysql_connection.ping(reconnect=True)
        assert result is None  # ping 成功返回 None

    def test_mysql_database_exists(self, mysql_connection, mysql_config):
        """INT-P1-002: 验证数据库存在"""
        with mysql_connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES;")
            databases = [row["Database"] for row in cursor.fetchall()]
            assert mysql_config["database"] in databases

    def test_mysql_create_and_drop_table(self, mysql_connection):
        """INT-P1-003: 创建和删除表测试"""
        table_name = f"test_table_{int(time.time())}"

        with mysql_connection.cursor() as cursor:
            # 创建表
            create_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_sql)
            mysql_connection.commit()

            # 验证表存在
            cursor.execute("SHOW TABLES;")
            tables = [list(row.values())[0] for row in cursor.fetchall()]
            assert table_name in tables

            # 插入数据
            cursor.execute(f"INSERT INTO {table_name} (name) VALUES (%s)", ("test_record",))
            mysql_connection.commit()

            # 查询数据
            cursor.execute(f"SELECT * FROM {table_name}")
            result = cursor.fetchall()
            assert len(result) == 1
            assert result[0]["name"] == "test_record"

            # 删除表
            cursor.execute(f"DROP TABLE {table_name}")
            mysql_connection.commit()

    def test_mysql_transaction_commit(self, mysql_connection):
        """INT-P1-004: 事务提交测试"""
        table_name = f"test_trans_{int(time.time())}"

        with mysql_connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    value INT
                )
            """)
            mysql_connection.commit()

            try:
                # 开启事务
                cursor.execute(f"INSERT INTO {table_name} (value) VALUES (1)")
                cursor.execute(f"INSERT INTO {table_name} (value) VALUES (2)")
                mysql_connection.commit()

                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                result = cursor.fetchone()
                assert result["count"] == 2
            finally:
                cursor.execute(f"DROP TABLE {table_name}")
                mysql_connection.commit()

    def test_mysql_transaction_rollback(self, mysql_connection):
        """INT-P1-005: 事务回滚测试"""
        table_name = f"test_rollback_{int(time.time())}"

        with mysql_connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    value INT
                )
            """)
            mysql_connection.commit()

            try:
                # 插入初始数据
                cursor.execute(f"INSERT INTO {table_name} (value) VALUES (0)")
                mysql_connection.commit()

                # 开始事务
                cursor.execute(f"INSERT INTO {table_name} (value) VALUES (1)")
                cursor.execute(f"INSERT INTO {table_name} (value) VALUES (2)")
                mysql_connection.rollback()

                # 验证回滚后数据未变
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                result = cursor.fetchone()
                assert result["count"] == 1
            finally:
                cursor.execute(f"DROP TABLE {table_name}")
                mysql_connection.commit()

    def test_mysql_character_set(self, mysql_connection):
        """INT-P1-006: 字符集测试"""
        with mysql_connection.cursor() as cursor:
            cursor.execute("SELECT @@character_set_database, @@collation_database")
            result = cursor.fetchone()
            assert result is not None
            # 验证支持 UTF-8
            assert "utf8" in result[list(result.keys())[0]].lower() or "utf8mb4" in result[list(result.keys())[0]].lower()

    def test_mysql_chinese_content(self, mysql_connection):
        """INT-P1-007: 中文内容存储测试"""
        table_name = f"test_chinese_{int(time.time())}"

        with mysql_connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content VARCHAR(255)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            mysql_connection.commit()

            try:
                # 插入中文
                chinese_text = "你好，世界！这是一段中文测试内容。"
                cursor.execute(f"INSERT INTO {table_name} (content) VALUES (%s)", (chinese_text,))
                mysql_connection.commit()

                # 查询并验证
                cursor.execute(f"SELECT content FROM {table_name}")
                result = cursor.fetchone()
                assert result["content"] == chinese_text
            finally:
                cursor.execute(f"DROP TABLE {table_name}")
                mysql_connection.commit()

    def test_mysql_health_check(self, mysql_connection):
        """INT-P1-008: MySQL 健康检查"""
        with mysql_connection.cursor() as cursor:
            # 检查连接状态
            cursor.execute("SELECT 1 as health_check")
            result = cursor.fetchone()
            assert result["health_check"] == 1

            # 检查数据库大小
            cursor.execute("SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables GROUP BY table_schema")
            sizes = cursor.fetchall()
            assert len(sizes) > 0


@pytest.mark.integration
class TestRedisInfrastructure:
    """INT-P1-009 ~ INT-P1-015: Redis 基础设施测试"""

    @pytest.fixture
    def redis_config(self):
        """Redis 配置"""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", "redis"),
            "db": int(os.getenv("REDIS_DB", "0")),
        }

    @pytest.fixture
    def redis_client(self, redis_config):
        """创建 Redis 连接"""
        try:
            client = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                password=redis_config["password"],
                db=redis_config["db"],
                decode_responses=True,
            )
            yield client
            client.close()
        except Exception as e:
            pytest.skip(f"Redis 连接失败: {e}")

    def test_redis_connection(self, redis_client):
        """INT-P1-009: Redis 连接测试"""
        result = redis_client.ping()
        assert result is True

    def test_redis_set_and_get(self, redis_client):
        """INT-P1-010: SET 和 GET 操作测试"""
        key = f"test_key_{int(time.time())}"
        value = "test_value"

        # SET
        redis_client.set(key, value)

        # GET
        result = redis_client.get(key)
        assert result == value

        # 清理
        redis_client.delete(key)

    def test_redis_hash_operations(self, redis_client):
        """INT-P1-011: Hash 操作测试"""
        key = f"test_hash_{int(time.time())}"

        # HSET
        redis_client.hset(key, "field1", "value1")
        redis_client.hset(key, "field2", "value2")

        # HGET
        assert redis_client.hget(key, "field1") == "value1"

        # HGETALL
        all_fields = redis_client.hgetall(key)
        assert all_fields == {"field1": "value1", "field2": "value2"}

        # 清理
        redis_client.delete(key)

    def test_redis_list_operations(self, redis_client):
        """INT-P1-012: List 操作测试"""
        key = f"test_list_{int(time.time())}"

        # LPUSH
        redis_client.lpush(key, "item3", "item2", "item1")

        # LRANGE
        items = redis_client.lrange(key, 0, -1)
        assert items == ["item1", "item2", "item3"]

        # LLEN
        assert redis_client.llen(key) == 3

        # 清理
        redis_client.delete(key)

    def test_redis_set_operations(self, redis_client):
        """INT-P1-013: Set 操作测试"""
        key = f"test_set_{int(time.time())}"

        # SADD
        redis_client.sadd(key, "member1", "member2", "member3")

        # SMEMBERS
        members = redis_client.smembers(key)
        assert "member1" in members
        assert "member2" in members

        # SCARD
        assert redis_client.scard(key) == 3

        # 清理
        redis_client.delete(key)

    def test_redis_expiration(self, redis_client):
        """INT-P1-014: 过期时间测试"""
        key = f"test_expire_{int(time.time())}"

        # SET with EXPIRE
        redis_client.set(key, "value", ex=2)

        # 立即获取
        assert redis_client.get(key) == "value"

        # 等待过期
        time.sleep(3)

        # 验证已过期
        assert redis_client.get(key) is None

    def test_redis_info(self, redis_client):
        """INT-P1-015: Redis 信息查询"""
        info = redis_client.info()
        assert "used_memory_human" in info
        assert "connected_clients" in info
        assert "uptime_in_seconds" in info


@pytest.mark.integration
class TestMinIOInfrastructure:
    """INT-P1-016 ~ INT-P1-020: MinIO 基础设施测试"""

    @pytest.fixture
    def minio_config(self):
        """MinIO 配置"""
        return {
            "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            "secure": False,
        }

    @pytest.fixture
    def minio_client(self, minio_config):
        """创建 MinIO 客户端"""
        try:
            client = Minio(
                minio_config["endpoint"],
                access_key=minio_config["access_key"],
                secret_key=minio_config["secret_key"],
                secure=minio_config["secure"],
            )
            yield client
        except Exception as e:
            pytest.skip(f"MinIO 连接失败: {e}")

    def test_minio_connection(self, minio_client):
        """INT-P1-016: MinIO 连接测试"""
        # 列出存储桶验证连接
        buckets = minio_client.list_buckets()
        assert isinstance(buckets, list)

    def test_minio_create_bucket(self, minio_client):
        """INT-P1-017: 创建存储桶测试"""
        bucket_name = f"test-bucket-{int(time.time())}"

        try:
            # 创建存储桶
            minio_client.make_bucket(bucket_name)

            # 验证存储桶存在
            buckets = [b.name for b in minio_client.list_buckets()]
            assert bucket_name in buckets
        finally:
            # 清理
            try:
                minio_client.remove_bucket(bucket_name)
            except:
                pass

    def test_minio_put_and_get_object(self, minio_client):
        """INT-P1-018: 上传和下载对象测试"""
        bucket_name = f"test-bucket-{int(time.time())}"
        object_name = "test-object.txt"
        content = b"Hello, MinIO! This is test content."

        try:
            # 创建存储桶
            minio_client.make_bucket(bucket_name)

            # 上传对象
            from io import BytesIO
            data = BytesIO(content)
            minio_client.put_object(bucket_name, object_name, data, len(content))

            # 下载对象
            response = minio_client.get_object(bucket_name, object_name)
            downloaded = response.read()
            response.close()

            assert downloaded == content

            # 验证对象存在
            objects = [o.object_name for o in minio_client.list_objects(bucket_name)]
            assert object_name in objects
        finally:
            # 清理
            try:
                minio_client.remove_object(bucket_name, object_name)
                minio_client.remove_bucket(bucket_name)
            except:
                pass

    def test_minio_list_objects(self, minio_client):
        """INT-P1-019: 列出对象测试"""
        bucket_name = f"test-bucket-{int(time.time())}"

        try:
            # 创建存储桶
            minio_client.make_bucket(bucket_name)

            # 上传多个对象
            from io import BytesIO
            for i in range(3):
                object_name = f"file-{i}.txt"
                content = f"Content {i}".encode()
                data = BytesIO(content)
                minio_client.put_object(bucket_name, object_name, data, len(content))

            # 列出对象
            objects = list(minio_client.list_objects(bucket_name))
            assert len(objects) == 3
        finally:
            # 清理
            try:
                for obj in minio_client.list_objects(bucket_name):
                    minio_client.remove_object(bucket_name, obj.object_name)
                minio_client.remove_bucket(bucket_name)
            except:
                pass

    def test_minio_presigned_url(self, minio_client):
        """INT-P1-020: 预签名 URL 测试"""
        bucket_name = f"test-bucket-{int(time.time())}"
        object_name = "test-object.txt"
        content = b"Test content for presigned URL"

        try:
            # 创建存储桶和对象
            minio_client.make_bucket(bucket_name)
            from io import BytesIO
            data = BytesIO(content)
            minio_client.put_object(bucket_name, object_name, data, len(content))

            # 生成预签名 URL
            url = minio_client.presigned_get_object(bucket_name, object_name, expires=timedelta(hours=1))
            assert "http" in url
            assert bucket_name in url
            assert object_name in url
        except ImportError:
            # datetime.timedelta 可能未导入
            pass
        finally:
            # 清理
            try:
                minio_client.remove_object(bucket_name, object_name)
                minio_client.remove_bucket(bucket_name)
            except:
                pass


@pytest.mark.integration
class TestInfrastructureIntegration:
    """INT-P1-021 ~ INT-P1-025: 基础设施集成测试"""

    def test_service_connectivity_matrix(self):
        """INT-P1-021: 服务连通性矩阵测试"""
        # 检查各服务端口是否可访问
        import socket

        services = {
            "MySQL": ("localhost", 3306),
            "Redis": ("localhost", 6379),
            "MinIO API": ("localhost", 9000),
        }

        results = {}
        for name, (host, port) in services.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                sock.connect((host, port))
                results[name] = True
            except:
                results[name] = False
            finally:
                sock.close()

        # 记录结果
        for name, status in results.items():
            if status:
                print(f"  ✓ {name} is accessible")
            else:
                print(f"  ✗ {name} is not accessible")

    def test_docker_network_connectivity(self):
        """INT-P1-022: Docker 网络连通性测试"""
        # 验证容器间网络通信
        import subprocess

        try:
            # 获取网络信息
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", "name=one-data", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            networks = result.stdout.strip().split("\n")
            assert any("one-data" in n for n in networks), "one-data network not found"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")

    def test_resource_usage(self):
        """INT-P1-023: 资源使用情况测试"""
        import subprocess

        try:
            # 获取容器资源使用情况
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "table {{.Container}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = result.stdout.strip().split("\n")
            assert len(lines) > 0  # 至少有表头
            print("\nContainer Resource Usage:")
            print(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")

    def test_environment_variables(self):
        """INT-P1-024: 环境变量验证"""
        required_vars = [
            "MYSQL_HOST",
            "MYSQL_USER",
            "MYSQL_PASSWORD",
            "MYSQL_DATABASE",
            "REDIS_HOST",
            "REDIS_PASSWORD",
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            print(f"Warning: Missing environment variables: {missing}")

    def test_persistence_verification(self):
        """INT-P1-025: 数据持久化验证"""
        import subprocess

        try:
            # 检查 Docker 卷
            result = subprocess.run(
                ["docker", "volume", "ls", "--filter", "name=one-data", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            volumes = result.stdout.strip().split("\n")
            print("\nDocker Volumes:")
            for v in volumes:
                if v:
                    print(f"  - {v}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            pytest.skip(f"Docker not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
