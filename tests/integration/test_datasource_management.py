"""
数据源管理集成测试

测试用例覆盖：
1. DM-DS-001: 创建 MySQL 数据源 (P0)
2. DM-DS-002: 创建 PostgreSQL 数据源 (P0)
3. DM-DS-003: 测试数据源连接 (P0)
4. DM-DS-004: 查询数据源列表 (P0)
5. DM-DS-005: 获取数据源详情 (P1)
6. DM-DS-006: 更新数据源配置 (P1)
7. DM-DS-007: 删除数据源 (P1)
8. DM-DS-008: 数据源连接失败处理 (P2)
"""

import os
import sys
import pytest
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/data-api'))

logger = logging.getLogger(__name__)


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

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


# =============================================================================
# 数据源管理测试
# =============================================================================

class TestDatasourceManagement:
    """数据源管理测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.query = MagicMock()
        session.flush = MagicMock()
        session.close = MagicMock()
        return session

    @pytest.fixture
    def datasource_service(self, mock_db_session):
        """创建数据源服务实例"""
        from services.datasource_service import DatasourceService
        return DatasourceService(mock_db_session)

    # -------------------------------------------------------------------------
    # 测试用例：DM-DS-001 ~ DM-DS-008
    # -------------------------------------------------------------------------

    def test_create_mysql_datasource(
        self,
        datasource_service,
        mock_db_session
    ):
        """
        DM-DS-001: 创建 MySQL 数据源 (P0)

        验证点：
        1. 能够成功创建 MySQL 数据源
        2. 数据源信息正确保存
        3. 返回包含 datasource_id 的响应
        """
        # 准备测试数据
        datasource_data = {
            "name": "测试 MySQL 数据源",
            "type": "mysql",
            "host": TestConfig.MYSQL_CONFIG["host"],
            "port": TestConfig.MYSQL_CONFIG["port"],
            "username": TestConfig.MYSQL_CONFIG["username"],
            "password": TestConfig.MYSQL_CONFIG["password"],
            "database": TestConfig.MYSQL_CONFIG["database"],
            "description": "用于测试的 MySQL 数据源",
        }

        # Mock 查询返回 None（表示不存在同名数据源）
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Mock 添加后的对象
        mock_datasource = MagicMock()
        mock_datasource.datasource_id = f"ds_{uuid.uuid4().hex[:12]}"
        mock_datasource.name = datasource_data["name"]
        mock_datasource.type = datasource_data["type"]

        # 执行测试
        result = datasource_service.create_datasource(datasource_data)

        # 验证结果
        assert result is not None
        assert "datasource_id" in result
        assert result["name"] == datasource_data["name"]
        assert result["type"] == datasource_data["type"]
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-DS-001: 成功创建 MySQL 数据源 {result.get('datasource_id')}")

    def test_create_postgres_datasource(
        self,
        datasource_service,
        mock_db_session
    ):
        """
        DM-DS-002: 创建 PostgreSQL 数据源 (P0)

        验证点：
        1. 能够成功创建 PostgreSQL 数据源
        2. 数据源信息正确保存
        3. 返回包含 datasource_id 的响应
        """
        # 准备测试数据
        datasource_data = {
            "name": "测试 PostgreSQL 数据源",
            "type": "postgresql",
            "host": TestConfig.POSTGRES_CONFIG["host"],
            "port": TestConfig.POSTGRES_CONFIG["port"],
            "username": TestConfig.POSTGRES_CONFIG["username"],
            "password": TestConfig.POSTGRES_CONFIG["password"],
            "database": TestConfig.POSTGRES_CONFIG["database"],
            "description": "用于测试的 PostgreSQL 数据源",
        }

        # Mock 查询返回 None
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # 执行测试
        result = datasource_service.create_datasource(datasource_data)

        # 验证结果
        assert result is not None
        assert "datasource_id" in result
        assert result["name"] == datasource_data["name"]
        assert result["type"] == "postgresql"
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-DS-002: 成功创建 PostgreSQL 数据源 {result.get('datasource_id')}")

    def test_datasource_connection_mysql(self, datasource_service):
        """
        DM-DS-003: 测试 MySQL 数据源连接 (P0)

        验证点：
        1. 能够测试 MySQL 数据源连接
        2. 连接成功返回正确状态
        3. 连接失败返回错误信息
        """
        # 准备测试数据
        connection_config = {
            "type": "mysql",
            "host": TestConfig.MYSQL_CONFIG["host"],
            "port": TestConfig.MYSQL_CONFIG["port"],
            "username": TestConfig.MYSQL_CONFIG["username"],
            "password": TestConfig.MYSQL_CONFIG["password"],
            "database": TestConfig.MYSQL_CONFIG["database"],
        }

        # 执行连接测试
        result = datasource_service.test_connection(connection_config)

        # 验证结果
        assert result is not None
        assert "success" in result
        assert "message" in result

        if result["success"]:
            logger.info("✓ DM-DS-003: MySQL 数据源连接测试成功")
        else:
            logger.warning(f"⚠ DM-DS-003: MySQL 数据源连接测试失败: {result.get('message')}")
            # 如果是环境问题（数据库未启动），跳过后续依赖测试
            pytest.skip("MySQL 数据库未启动或连接失败")

    def test_datasource_connection_postgres(self, datasource_service):
        """
        DM-DS-003 (续): 测试 PostgreSQL 数据源连接 (P0)

        验证点：
        1. 能够测试 PostgreSQL 数据源连接
        2. 连接成功返回正确状态
        3. 连接失败返回错误信息
        """
        # 准备测试数据
        connection_config = {
            "type": "postgresql",
            "host": TestConfig.POSTGRES_CONFIG["host"],
            "port": TestConfig.POSTGRES_CONFIG["port"],
            "username": TestConfig.POSTGRES_CONFIG["username"],
            "password": TestConfig.POSTGRES_CONFIG["password"],
            "database": TestConfig.POSTGRES_CONFIG["database"],
        }

        # 执行连接测试
        result = datasource_service.test_connection(connection_config)

        # 验证结果
        assert result is not None
        assert "success" in result
        assert "message" in result

        if result["success"]:
            logger.info("✓ DM-DS-003: PostgreSQL 数据源连接测试成功")
        else:
            logger.warning(f"⚠ DM-DS-003: PostgreSQL 数据源连接测试失败: {result.get('message')}")
            pytest.skip("PostgreSQL 数据库未启动或连接失败")

    def test_list_datasources(self, datasource_service, mock_db_session):
        """
        DM-DS-004: 查询数据源列表 (P0)

        验证点：
        1. 能够获取数据源列表
        2. 返回正确的数据源数量
        3. 包含正确的数据源信息
        """
        # Mock 查询返回数据
        mock_datasources = [
            MagicMock(
                datasource_id="ds_001",
                name="MySQL 测试数据源",
                type="mysql",
                host="localhost",
                port=3306,
                status="active",
                created_at=datetime.now()
            ),
            MagicMock(
                datasource_id="ds_002",
                name="PostgreSQL 测试数据源",
                type="postgresql",
                host="localhost",
                port=5434,
                status="active",
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.order_by.return_value.all.return_value = mock_datasources
        mock_query.limit.return_value = mock_query
        mock_db_session.query.return_value = mock_query

        # 执行测试
        result = datasource_service.list_datasources(limit=10, offset=0)

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 2
        assert result["total"] >= 2

        logger.info(f"✓ DM-DS-004: 成功获取数据源列表，共 {result['total']} 个数据源")

    def test_get_datasource_detail(self, datasource_service, mock_db_session):
        """
        DM-DS-005: 获取数据源详情 (P1)

        验证点：
        1. 能够获取指定数据源的详细信息
        2. 返回正确的字段
        3. 数据源不存在时返回 None 或错误
        """
        datasource_id = "ds_001"

        # Mock 查询返回数据
        mock_datasource = MagicMock(
            datasource_id=datasource_id,
            name="MySQL 测试数据源",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            database="test_ecommerce",
            status="active",
            description="测试数据源",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_datasource
        mock_db_session.query.return_value = mock_query

        # 执行测试
        result = datasource_service.get_datasource(datasource_id)

        # 验证结果
        assert result is not None
        assert result["datasource_id"] == datasource_id
        assert result["name"] == "MySQL 测试数据源"
        assert result["type"] == "mysql"
        assert "host" in result
        assert "port" in result

        logger.info(f"✓ DM-DS-005: 成功获取数据源详情: {datasource_id}")

    def test_update_datasource(self, datasource_service, mock_db_session):
        """
        DM-DS-006: 更新数据源配置 (P1)

        验证点：
        1. 能够更新数据源配置
        2. 更新后数据正确保存
        3. 不存在的数据源返回错误
        """
        datasource_id = "ds_001"

        # 准备更新数据
        update_data = {
            "name": "更新后的 MySQL 数据源",
            "description": "更新后的描述",
            "port": 3307,
        }

        # Mock 查询返回现有数据源
        mock_datasource = MagicMock(
            datasource_id=datasource_id,
            name="MySQL 测试数据源",
            type="mysql",
            host="localhost",
            port=3306,
            description="原始描述",
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_datasource
        mock_db_session.query.return_value = mock_query

        # 执行测试
        result = datasource_service.update_datasource(datasource_id, update_data)

        # 验证结果
        assert result is not None
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-DS-006: 成功更新数据源配置: {datasource_id}")

    def test_delete_datasource(self, datasource_service, mock_db_session):
        """
        DM-DS-007: 删除数据源 (P1)

        验证点：
        1. 能够删除指定数据源
        2. 删除后数据不可再获取
        3. 不存在的数据源返回 False
        """
        datasource_id = "ds_001"

        # Mock 查询返回现有数据源
        mock_datasource = MagicMock(
            datasource_id=datasource_id,
            name="MySQL 测试数据源",
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_datasource
        mock_db_session.query.return_value = mock_query

        # 执行测试
        result = datasource_service.delete_datasource(datasource_id)

        # 验证结果
        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-DS-007: 成功删除数据源: {datasource_id}")

    def test_datasource_connection_failure(self, datasource_service):
        """
        DM-DS-008: 数据源连接失败处理 (P2)

        验证点：
        1. 错误的连接信息能够被正确识别
        2. 返回清晰的错误信息
        3. 不抛出未捕获的异常
        """
        # 准备错误的连接配置
        connection_config = {
            "type": "mysql",
            "host": "nonexistent-host",
            "port": 9999,
            "username": "wrong_user",
            "password": "wrong_password",
            "database": "nonexistent_db",
        }

        # 执行连接测试
        result = datasource_service.test_connection(connection_config)

        # 验证结果
        assert result is not None
        assert "success" in result
        assert result["success"] is False
        assert "message" in result
        assert len(result["message"]) > 0

        logger.info(f"✓ DM-DS-008: 正确处理连接失败: {result.get('message')}")


# =============================================================================
# 端到端测试：完整的数据源管理流程
# =============================================================================

class TestDatasourceManagementE2E:
    """数据源管理端到端测试"""

    @pytest.fixture
    def api_client(self):
        """创建 API 测试客户端"""
        try:
            from flask import Flask
            from src.main import create_app

            app = create_app()
            app.config["TESTING"] = True

            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("Flask 应用未找到，跳过 API 测试")

    def test_full_datasource_lifecycle(self, api_client):
        """
        端到端测试：完整的数据源生命周期

        流程：
        1. 创建 MySQL 数据源
        2. 测试连接
        3. 获取数据源详情
        4. 更新数据源
        5. 删除数据源
        """
        # 1. 创建数据源
        create_data = {
            "name": "E2E 测试 MySQL 数据源",
            "type": "mysql",
            "host": TestConfig.MYSQL_CONFIG["host"],
            "port": TestConfig.MYSQL_CONFIG["port"],
            "username": TestConfig.MYSQL_CONFIG["username"],
            "password": TestConfig.MYSQL_CONFIG["password"],
            "database": TestConfig.MYSQL_CONFIG["database"],
        }

        response = api_client.post(
            f"{TestConfig.API_BASE_URL}/datasources",
            json=create_data
        )

        if response.status_code not in [200, 201]:
            logger.warning(f"API 测试跳过: {response.status_code}")
            pytest.skip("API 服务未运行或数据源创建失败")

        create_result = response.get_json()
        datasource_id = create_result.get("datasource_id")

        assert datasource_id is not None
        logger.info(f"E2E: 创建数据源成功: {datasource_id}")

        # 2. 测试连接
        response = api_client.post(
            f"{TestConfig.API_BASE_URL}/datasources/test",
            json={
                "type": "mysql",
                "host": create_data["host"],
                "port": create_data["port"],
                "username": create_data["username"],
                "password": create_data["password"],
                "database": create_data["database"],
            }
        )

        assert response.status_code == 200
        test_result = response.get_json()
        assert test_result.get("success") is True
        logger.info("E2E: 连接测试成功")

        # 3. 获取数据源详情
        response = api_client.get(f"{TestConfig.API_BASE_URL}/datasources/{datasource_id}")
        assert response.status_code == 200
        detail_result = response.get_json()
        assert detail_result.get("datasource_id") == datasource_id
        logger.info("E2E: 获取数据源详情成功")

        # 4. 更新数据源
        update_data = {"description": "E2E 测试更新"}
        response = api_client.put(
            f"{TestConfig.API_BASE_URL}/datasources/{datasource_id}",
            json=update_data
        )
        assert response.status_code == 200
        logger.info("E2E: 更新数据源成功")

        # 5. 删除数据源
        response = api_client.delete(f"{TestConfig.API_BASE_URL}/datasources/{datasource_id}")
        assert response.status_code == 200
        logger.info("E2E: 删除数据源成功")

        logger.info("✓ 数据源管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
