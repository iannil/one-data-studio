"""
用户生命周期测试 - pytest 扩展 fixtures
提供测试角色用户、API 客户端、数据管理等公共 fixtures。

在 conftest.py 中自动加载，或通过 pytest_plugins 导入。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# ==================== 测试角色用户 ====================

TEST_USERS = {
    "admin": {
        "username": "seed_admin",
        "email": "seed_admin@test.local",
        "password": "Admin1234!",
        "roles": ["admin"],
    },
    "data_admin": {
        "username": "seed_da",
        "email": "seed_da@test.local",
        "password": "Da1234!",
        "roles": ["data_analyst"],
    },
    "data_engineer": {
        "username": "seed_de",
        "email": "seed_de@test.local",
        "password": "De1234!",
        "roles": ["data_engineer"],
    },
    "algorithm_engineer": {
        "username": "seed_ai",
        "email": "seed_ai@test.local",
        "password": "Ai1234!",
        "roles": ["ai_developer"],
    },
    "business_user": {
        "username": "seed_user",
        "email": "seed_user@test.local",
        "password": "User1234!",
        "roles": ["user"],
    },
}


@pytest.fixture
def test_user_admin():
    """系统管理员测试用户"""
    return TEST_USERS["admin"]


@pytest.fixture
def test_user_data_admin():
    """数据管理员测试用户"""
    return TEST_USERS["data_admin"]


@pytest.fixture
def test_user_data_engineer():
    """数据工程师测试用户"""
    return TEST_USERS["data_engineer"]


@pytest.fixture
def test_user_algorithm_engineer():
    """算法工程师测试用户"""
    return TEST_USERS["algorithm_engineer"]


@pytest.fixture
def test_user_business():
    """业务用户测试用户"""
    return TEST_USERS["business_user"]


# ==================== 测试数据源 ====================

@pytest.fixture
def mysql_datasource_config():
    """MySQL 测试数据源配置"""
    return {
        "name": "test_mysql",
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "username": "root",
        "password": "test123",
        "database": "test_db",
    }


@pytest.fixture
def postgres_datasource_config():
    """PostgreSQL 测试数据源配置"""
    return {
        "name": "test_postgres",
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "username": "postgres",
        "password": "test123",
        "database": "test_db",
    }


@pytest.fixture
def oracle_datasource_config():
    """Oracle 测试数据源配置"""
    return {
        "name": "test_oracle",
        "type": "oracle",
        "host": "localhost",
        "port": 1521,
        "username": "system",
        "password": "test123",
        "database": "ORCL",
    }


# ==================== 测试数据 ====================

@pytest.fixture
def sample_users_data():
    """用户表样本数据（含缺失值和敏感字段）"""
    return {
        "columns": ["id", "username", "phone", "id_card", "email", "bank_card", "age", "salary"],
        "data": [
            {"id": 1, "username": "张三", "phone": "13812345678", "id_card": "110101199001011234", "email": "zhangsan@example.com", "bank_card": "6222021234567890", "age": 30, "salary": 15000},
            {"id": 2, "username": "李四", "phone": "15098765432", "id_card": "320102198512150012", "email": "lisi@example.com", "bank_card": "6228480000000001", "age": 35, "salary": 20000},
            {"id": 3, "username": "王五", "phone": "18600001111", "id_card": "440106199203200045", "email": "wangwu@company.cn", "bank_card": "6217001234567890", "age": None, "salary": None},
            {"id": 4, "username": "赵六", "phone": None, "id_card": None, "email": "zhaoliu@test.io", "bank_card": None, "age": 28, "salary": 12000},
            {"id": 5, "username": "钱七", "phone": "13900009999", "id_card": "510105199507080123", "email": None, "bank_card": "6222031234567890", "age": None, "salary": 18000},
        ],
    }


@pytest.fixture
def sample_orders_data():
    """订单表样本数据"""
    return {
        "columns": ["id", "user_id", "order_no", "amount", "status", "order_date"],
        "data": [
            {"id": 1, "user_id": 1, "order_no": "ORD20240101001", "amount": 299.00, "status": "completed", "order_date": "2024-01-01"},
            {"id": 2, "user_id": 1, "order_no": "ORD20240115002", "amount": 1599.00, "status": "completed", "order_date": "2024-01-15"},
            {"id": 3, "user_id": 2, "order_no": "ORD20240201003", "amount": 88.50, "status": "completed", "order_date": "2024-02-01"},
            {"id": 4, "user_id": 3, "order_no": "ORD20240301004", "amount": 4500.00, "status": "pending", "order_date": "2024-03-01"},
            {"id": 5, "user_id": 2, "order_no": "ORD20240315005", "amount": 199.00, "status": "cancelled", "order_date": "2024-03-15"},
        ],
    }


@pytest.fixture
def sample_timeseries_data():
    """时序样本数据（含缺失值）"""
    return {
        "columns": ["date", "value"],
        "data": [
            {"date": "2024-01-01", "value": 100},
            {"date": "2024-01-02", "value": None},
            {"date": "2024-01-03", "value": None},
            {"date": "2024-01-04", "value": 120},
            {"date": "2024-01-05", "value": 130},
        ],
    }


# ==================== 脱敏规则 ====================

@pytest.fixture
def masking_rules():
    """预定义脱敏规则"""
    return [
        {"column": "phone", "strategy": "partial_mask", "type": "phone"},
        {"column": "id_card", "strategy": "partial_mask", "type": "id_card"},
        {"column": "email", "strategy": "partial_mask", "type": "email"},
        {"column": "bank_card", "strategy": "partial_mask", "type": "bank_card"},
        {"column": "password", "strategy": "hash", "type": "sha256"},
    ]


# ==================== Mock 外部服务 ====================

@pytest.fixture
def mock_kettle_service():
    """Mock Kettle ETL 服务"""
    mock = MagicMock()
    mock.submit_job.return_value = {"job_id": "test_job_001", "status": "submitted"}
    mock.get_job_status.return_value = {"job_id": "test_job_001", "status": "running", "progress": 50}
    mock.get_job_result.return_value = {
        "job_id": "test_job_001",
        "status": "completed",
        "rows_processed": 1000,
        "duration_ms": 5000,
    }
    return mock


@pytest.fixture
def mock_openmetadata_client():
    """Mock OpenMetadata 客户端"""
    mock = MagicMock()
    mock.get_tables.return_value = [
        {"name": "test_users", "columns": 8, "rows": 5},
        {"name": "test_orders", "columns": 6, "rows": 7},
    ]
    mock.get_lineage.return_value = {
        "nodes": [
            {"id": "test_users", "type": "table"},
            {"id": "test_orders", "type": "table"},
        ],
        "edges": [
            {"from": "test_users", "to": "test_orders", "type": "foreign_key"},
        ],
    }
    return mock


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes 客户端"""
    mock = MagicMock()
    mock.create_pod.return_value = {"name": "test-pod", "status": "Running"}
    mock.get_pod_status.return_value = {"name": "test-pod", "status": "Running", "ready": True}
    mock.delete_pod.return_value = True
    return mock


@pytest.fixture
def mock_vllm_service():
    """Mock vLLM 推理服务"""
    mock = MagicMock()
    mock.chat_completions.return_value = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "这是一个测试响应"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    return mock
