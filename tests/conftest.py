"""
Pytest 配置和共享 Fixtures
Sprint 6: 单元测试框架
"""

import os
import sys
import pytest
import tempfile
import logging
from pathlib import Path
from typing import AsyncGenerator, Generator


# 导入生命周期测试 fixtures
pytest_plugins = ["fixtures.lifecycle_fixtures"]


# ==================== 环境变量配置 ====================
# 必须在导入其他模块之前设置

def setup_test_env():
    """设置测试环境变量"""
    os.environ.update({
        'ENVIRONMENT': 'test',
        # 数据库配置
        'MYSQL_HOST': os.getenv('TEST_MYSQL_HOST', 'localhost'),
        'MYSQL_PORT': os.getenv('TEST_MYSQL_PORT', '3306'),
        'MYSQL_USER': os.getenv('TEST_MYSQL_USER', 'test_user'),
        'MYSQL_PASSWORD': os.getenv('TEST_MYSQL_PASSWORD', 'test_password'),
        'MYSQL_DATABASE': os.getenv('TEST_MYSQL_DATABASE', 'test_one_data'),
        # Milvus 配置
        'MILVUS_HOST': os.getenv('TEST_MILVUS_HOST', 'localhost'),
        'MILVUS_PORT': os.getenv('TEST_MILVUS_PORT', '19530'),
        # MinIO 配置
        'MINIO_ENDPOINT': os.getenv('TEST_MINIO_ENDPOINT', 'localhost:9000'),
        'MINIO_ACCESS_KEY': os.getenv('TEST_MINIO_ACCESS_KEY', 'minioadmin'),
        'MINIO_SECRET_KEY': os.getenv('TEST_MINIO_SECRET_KEY', 'minioadmin'),
        # OpenAI 配置
        'OPENAI_API_KEY': os.getenv('TEST_OPENAI_API_KEY', 'test-api-key-for-testing'),
        'OPENAI_BASE_URL': 'http://mock-openai:8000/v1',
        # JWT 和安全配置 (注意: config.py 使用 JWT_SECRET_KEY)
        'JWT_SECRET_KEY': os.getenv('TEST_JWT_SECRET_KEY', 'test-jwt-secret-key-for-testing-only-32chars'),
        'JWT_ALGORITHM': 'HS256',
        'JWT_ACCESS_TOKEN_EXPIRE': '3600',
        'JWT_REFRESH_TOKEN_EXPIRE': '604800',
        # CSRF 配置 (注意: csrf.py 使用 CSRF_SECRET_KEY)
        'CSRF_SECRET_KEY': os.getenv('TEST_CSRF_SECRET_KEY', 'test-csrf-secret-key-for-testing-32chars'),
        # Redis 配置
        'REDIS_HOST': os.getenv('TEST_REDIS_HOST', 'localhost'),
        'REDIS_PORT': os.getenv('TEST_REDIS_PORT', '6379'),
        'REDIS_PASSWORD': os.getenv('TEST_REDIS_PASSWORD', ''),
        'REDIS_DB': '0',
        'REDIS_ENABLED': 'true',
        # Celery 配置
        'CELERY_BROKER_URL': 'memory://',
        'CELERY_RESULT_BACKEND': 'cache+memory://',
        # 服务 URL 配置
        'BISHENG_API_URL': 'http://localhost:8081',
        'ALLDATA_API_URL': 'http://localhost:8082',
        'ALDATA_API_URL': 'http://localhost:8082',  # config.py 使用此名称
        'CUBE_API_URL': 'http://localhost:8083',
        'ADMIN_API_URL': 'http://localhost:8084',
        'OPENAI_PROXY_URL': 'http://localhost:8085',
        # CORS 配置
        'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,http://localhost:5173',
        # 日志配置
        'LOG_LEVEL': 'DEBUG',
    })


# 必须在 sys.path 配置之前调用
setup_test_env()

# 添加服务路径到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services"))
sys.path.insert(0, str(project_root / "services" / "bisheng-api"))
sys.path.insert(0, str(project_root / "services" / "alldata-api"))
sys.path.insert(0, str(project_root / "services" / "alldata-api" / "src"))
sys.path.insert(0, str(project_root / "services" / "cube-api"))
sys.path.insert(0, str(project_root / "services" / "shared"))
sys.path.insert(0, str(project_root / "services" / "admin-api"))
sys.path.insert(0, str(project_root / "services" / "openai-proxy"))

try:
    import pymysql
except ImportError:
    pymysql = None

# 配置日志
logging.basicConfig(level=logging.DEBUG)


# ==================== Pytest 配置 ====================

def pytest_configure(config):
    """Pytest 初始化配置"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "benchmark: 性能基准测试")
    config.addinivalue_line("markers", "requires_db: 需要数据库")
    config.addinivalue_line("markers", "requires_milvus: 需要 Milvus")
    config.addinivalue_line("markers", "requires_minio: 需要 MinIO")
    config.addinivalue_line("markers", "security: 安全测试")


def pytest_collection_modifyitems(config, items):
    """根据标记修改测试项"""
    skip_slow = pytest.mark.skip(reason="跳过慢速测试 (使用 --runslow 跳过)")
    skip_db = pytest.mark.skip(reason="跳过需要数据库的测试 (使用 --with-db 跳过)")
    skip_milvus = pytest.mark.skip(reason="跳过需要 Milvus 的测试 (使用 --with-milvus 跳过)")
    skip_minio = pytest.mark.skip(reason="跳过需要 MinIO 的测试 (使用 --with-minio 跳过)")
    skip_benchmark = pytest.mark.skip(reason="跳过性能基准测试 (使用 --benchmark 运行)")

    if not config.getoption("--runslow", default=False):
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--with-db", default=False):
        for item in items:
            if "requires_db" in item.keywords:
                item.add_marker(skip_db)

    if not config.getoption("--with-milvus", default=False):
        for item in items:
            if "requires_milvus" in item.keywords:
                item.add_marker(skip_milvus)

    if not config.getoption("--with-minio", default=False):
        for item in items:
            if "requires_minio" in item.keywords:
                item.add_marker(skip_minio)

    if not config.getoption("--benchmark", default=False):
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_benchmark)


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="运行慢速测试"
    )
    parser.addoption(
        "--with-db",
        action="store_true",
        default=False,
        help="运行需要数据库的测试"
    )
    parser.addoption(
        "--with-milvus",
        action="store_true",
        default=False,
        help="运行需要 Milvus 的测试"
    )
    parser.addoption(
        "--with-minio",
        action="store_true",
        default=False,
        help="运行需要 MinIO 的测试"
    )
    parser.addoption(
        "--benchmark",
        action="store_true",
        default=False,
        help="运行性能基准测试"
    )


# ==================== Singleton Reset Fixtures ====================

@pytest.fixture(autouse=True)
def reset_config_singleton():
    """自动重置配置单例（确保每个测试使用新的配置实例）"""
    # 先重置以确保使用测试环境变量
    try:
        import services.shared.config as config_module
        config_module._config = None
    except ImportError:
        pass

    yield

    # 测试结束后也重置
    try:
        import services.shared.config as config_module
        config_module._config = None
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def reset_csrf_singleton():
    """自动重置 CSRF 单例"""
    yield

    try:
        import services.shared.security.csrf as csrf_module
        csrf_module._csrf_protection = None
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def reset_celery_singleton():
    """自动重置 Celery 任务管理器单例"""
    yield

    try:
        import services.shared.celery_app as celery_module
        celery_module._task_manager = None
    except ImportError:
        pass


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        'mysql_host': os.getenv('TEST_MYSQL_HOST', 'localhost'),
        'mysql_port': int(os.getenv('TEST_MYSQL_PORT', '3306')),
        'mysql_user': os.getenv('TEST_MYSQL_USER', 'test_user'),
        'mysql_password': os.getenv('TEST_MYSQL_PASSWORD', 'test_password'),
        'mysql_database': os.getenv('TEST_MYSQL_DATABASE', 'test_one_data'),
    }


@pytest.fixture(scope="session")
def db_connection(test_config):
    """数据库连接 Fixture"""
    if pymysql is None:
        pytest.skip("pymysql 未安装")
    try:
        conn = pymysql.connect(
            host=test_config['mysql_host'],
            port=test_config['mysql_port'],
            user=test_config['mysql_user'],
            password=test_config['mysql_password'],
            database=test_config['mysql_database'],
            charset='utf8mb4'
        )
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"无法连接到测试数据库: {e}")


@pytest.fixture
def db_session(db_connection):
    """数据库会话 Fixture（每个测试自动回滚）"""
    cursor = db_connection.cursor()
    db_connection.begin()  # 开始事务

    yield cursor

    db_connection.rollback()  # 测试后回滚
    cursor.close()


@pytest.fixture
def mock_env():
    """临时环境变量 Fixture"""
    original_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_file():
    """临时文件 Fixture"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as f:
        temp_path = f.name
    yield temp_path
    # 清理
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def sample_user():
    """示例用户数据"""
    return {
        'user_id': 'test-user-001',
        'username': 'testuser',
        'email': 'test@example.com',
        'roles': ['user']
    }


@pytest.fixture
def sample_conversation(sample_user):
    """示例会话数据"""
    return {
        'conversation_id': 'test-conv-001',
        'user_id': sample_user['user_id'],
        'title': 'Test Conversation',
        'model': 'gpt-4o-mini'
    }


@pytest.fixture
def sample_workflow(sample_user):
    """示例工作流数据"""
    return {
        'workflow_id': 'test-wf-001',
        'name': 'Test Workflow',
        'description': 'A test workflow',
        'type': 'rag',
        'status': 'stopped',
        'created_by': sample_user['user_id'],
        'definition': {
            'version': '1.0',
            'nodes': [
                {'id': 'input-1', 'type': 'input', 'position': {'x': 100, 'y': 100}},
                {'id': 'output-1', 'type': 'output', 'position': {'x': 300, 'y': 100}}
            ],
            'edges': []
        }
    }


@pytest.fixture
def sample_document(sample_user):
    """示例文档数据"""
    return {
        'doc_id': 'test-doc-001',
        'file_name': 'test.txt',
        'title': 'Test Document',
        'content': 'This is a test document content.',
        'collection_name': 'test_collection',
        'created_by': sample_user['user_id']
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI 响应"""
    return {
        'id': 'chatcmpl-test',
        'object': 'chat.completion',
        'created': 1234567890,
        'model': 'gpt-4o-mini',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': 'This is a test response.'
            },
            'finish_reason': 'stop'
        }],
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'total_tokens': 30
        }
    }


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_vector_store():
    """Mock 向量存储"""
    class MockVectorStore:
        def __init__(self):
            self.data = {}

        def insert(self, collection, texts, embeddings, metadata=None):
            if collection not in self.data:
                self.data[collection] = []
            for i, text in enumerate(texts):
                self.data[collection].append({
                    'text': text,
                    'embedding': embeddings[i] if i < len(embeddings) else None,
                    'metadata': metadata[i] if metadata and i < len(metadata) else {}
                })
            return len(texts)

        def search(self, collection, query_embedding, top_k=5):
            if collection not in self.data:
                return []
            return [
                {
                    'text': item['text'],
                    'score': 0.9,
                    'metadata': item.get('metadata', {})
                }
                for item in self.data.get(collection, [])[:top_k]
            ]

        def delete_by_doc_id(self, collection, doc_id):
            return True

    return MockVectorStore()


@pytest.fixture
def mock_embedding_service():
    """Mock 嵌入服务"""
    class MockEmbeddingService:
        def embed_text(self, text):
            import asyncio
            # 返回固定维度的 mock 向量
            return [0.1] * 1536

        async def embed_texts(self, texts):
            return [[0.1] * 1536 for _ in texts]

        def sync_embed_texts(self, texts):
            return [[0.1] * 1536 for _ in texts]

    return MockEmbeddingService()


@pytest.fixture
def mock_minio_client():
    """Mock MinIO 客户端"""
    class MockMinIOClient:
        def __init__(self):
            self.buckets = set()
            self.objects = {}

        def bucket_exists(self, bucket):
            return bucket in self.buckets

        def make_bucket(self, bucket):
            self.buckets.add(bucket)

        def put_object(self, bucket, name, data, *args, **kwargs):
            if bucket not in self.objects:
                self.objects[bucket] = {}
            self.objects[bucket][name] = data.read()

        def get_object(self, bucket, name):
            if bucket in self.objects and name in self.objects[bucket]:
                class MockResponse:
                    def __init__(self, data):
                        self.data = data
                    def read(self):
                        return self.data.encode() if isinstance(self.data, str) else self.data
                    def close(self):
                        pass
                    def release_conn(self):
                        pass
                return MockResponse(self.objects[bucket][name])
            raise Exception("Object not found")

        def remove_object(self, bucket, name):
            if bucket in self.objects and name in self.objects[bucket]:
                del self.objects[bucket][name]

    return MockMinIOClient()


# ==================== API Client Fixtures ====================

@pytest.fixture
def api_client_base_url():
    """API 基础 URL"""
    return os.getenv('API_BASE_URL', 'http://localhost:8081')


@pytest.fixture
def bisheng_api_client(api_client_base_url):
    """Bisheng API 客户端"""
    import requests

    class BishengAPIClient:
        def __init__(self, base_url):
            self.base_url = base_url
            self.session = requests.Session()

        def get(self, path, **kwargs):
            return self.session.get(f"{self.base_url}{path}", **kwargs)

        def post(self, path, **kwargs):
            return self.session.post(f"{self.base_url}{path}", **kwargs)

        def put(self, path, **kwargs):
            return self.session.put(f"{self.base_url}{path}", **kwargs)

        def delete(self, path, **kwargs):
            return self.session.delete(f"{self.base_url}{path}", **kwargs)

        def health(self):
            return self.get("/api/v1/health")

        def list_workflows(self):
            return self.get("/api/v1/workflows")

        def create_workflow(self, data):
            return self.post("/api/v1/workflows", json=data)

        def create_conversation(self, title):
            return self.post("/api/v1/conversations", json={"title": title})

        def list_conversations(self):
            return self.get("/api/v1/conversations")

    return BishengAPIClient(api_client_base_url)
