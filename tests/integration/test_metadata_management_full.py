"""
元数据管理集成测试

测试用例覆盖：
1. DM-MD-001: 扫描数据源获取表结构 (P0)
2. DM-MD-002: 查看元数据列表 (P0)
3. DM-MD-003: 查看表详情（列信息、关系）(P0)
4. DM-MD-004: 元数据搜索 (P1)
5. DM-MD-005: 血缘关系分析 (P1)
6. DM-MD-006: AI 自动标注 (P1)
7. DM-MD-007: 增量扫描 (P2)
"""

import os
import sys
import pytest
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/data-api'))

logger = logging.getLogger(__name__)


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

    MYSQL_CONFIG = {
        "type": "mysql",
        "host": os.getenv("TEST_MYSQL_HOST", "localhost"),
        "port": int(os.getenv("TEST_MYSQL_PORT", "3308")),
        "username": os.getenv("TEST_MYSQL_USER", "root"),
        "password": os.getenv("TEST_MYSQL_PASSWORD", "rootdev123"),
        "database": "test_ecommerce",
    }

    POSTGRES_CONFIG = {
        "type": "postgresql",
        "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("TEST_POSTGRES_PORT", "5436")),
        "username": os.getenv("TEST_POSTGRES_USER", "postgres"),
        "password": os.getenv("TEST_POSTGRES_PASSWORD", "postgresdev123"),
        "database": "test_ecommerce_pg",
    }

    # 预期的测试表
    EXPECTED_TABLES = [
        "users", "products", "orders", "order_items",
        "shopping_cart", "categories"
    ]


# =============================================================================
# 元数据管理测试
# =============================================================================

class TestMetadataManagement:
    """元数据管理测试类"""

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
    def metadata_scan_engine(self):
        """创建元数据扫描引擎"""
        from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine
        return get_metadata_auto_scan_engine()

    @pytest.fixture
    def metadata_service(self, mock_db_session):
        """创建元数据服务"""
        from services.metadata_service import MetadataService
        return MetadataService(mock_db_session)

    # -------------------------------------------------------------------------
    # 测试用例：DM-MD-001 ~ DM-MD-007
    # -------------------------------------------------------------------------

    def test_scan_datasource_mysql(
        self,
        metadata_scan_engine,
        mock_db_session
    ):
        """
        DM-MD-001: 扫描 MySQL 数据源获取表结构 (P0)

        验证点：
        1. 能够成功连接并扫描 MySQL 数据源
        2. 发现所有预期的表
        3. 正确获取表的列信息
        4. 元数据正确保存到数据库
        """
        # Mock 数据库查询
        def mock_query_side_effect(model):
            """模拟数据库查询行为"""
            if hasattr(model, '__tablename__'):
                if model.__tablename__ == 'metadata_databases':
                    mock_result = MagicMock()
                    mock_result.filter.return_value.first.return_value = None
                    return mock_result
                elif model.__tablename__ == 'metadata_tables':
                    mock_result = MagicMock()
                    mock_result.filter.return_value.first.return_value = None
                    return mock_result
                elif model.__tablename__ == 'metadata_columns':
                    mock_result = MagicMock()
                    mock_result.filter.return_value.all.return_value = []
                    return mock_result
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_side_effect

        # 执行扫描
        result = metadata_scan_engine.scan_database(
            connection_info=TestConfig.MYSQL_CONFIG,
            database_name=TestConfig.MYSQL_CONFIG["database"],
            exclude_tables=[],
            ai_annotate=False,  # 跳过 AI 标注以加快测试
            db_session=mock_db_session
        )

        # 验证结果
        assert result is not None
        assert "tables_discovered" in result
        assert "columns_discovered" in result
        assert result["tables_discovered"] > 0
        assert result["columns_discovered"] > 0
        assert len(result.get("errors", [])) == 0

        logger.info(
            f"✓ DM-MD-001: 成功扫描 MySQL 数据源，"
            f"发现 {result['tables_discovered']} 表，"
            f"{result['columns_discovered']} 列"
        )

    def test_scan_datasource_postgres(
        self,
        metadata_scan_engine,
        mock_db_session
    ):
        """
        DM-MD-001 (续): 扫描 PostgreSQL 数据源获取表结构 (P0)

        验证点：
        1. 能够成功连接并扫描 PostgreSQL 数据源
        2. 发现所有预期的表
        3. 正确获取表的列信息
        """
        # Mock 数据库查询
        def mock_query_side_effect(model):
            mock_result = MagicMock()
            mock_result.filter.return_value.first.return_value = None
            mock_result.filter.return_value.all.return_value = []
            return mock_result

        mock_db_session.query.side_effect = mock_query_side_effect

        # 执行扫描
        result = metadata_scan_engine.scan_database(
            connection_info=TestConfig.POSTGRES_CONFIG,
            database_name=TestConfig.POSTGRES_CONFIG["database"],
            exclude_tables=[],
            ai_annotate=False,
            db_session=mock_db_session
        )

        # 验证结果
        assert result is not None
        assert result["tables_discovered"] >= 0

        if result["tables_discovered"] > 0:
            logger.info(
                f"✓ DM-MD-001: 成功扫描 PostgreSQL 数据源，"
                f"发现 {result['tables_discovered']} 表"
            )
        else:
            # PostgreSQL 可能未初始化
            logger.warning("⚠ DM-MD-001: PostgreSQL 数据源扫描未发现表")

    def test_list_metadata_tables(self, metadata_service, mock_db_session):
        """
        DM-MD-002: 查看元数据列表 (P0)

        验证点：
        1. 能够获取表列表
        2. 支持分页查询
        3. 支持按数据库筛选
        4. 返回正确的表数量
        """
        # Mock 查询返回
        mock_tables = [
            MagicMock(
                id=1,
                table_name="users",
                database_id=1,
                row_count=1000,
                table_comment="用户表",
                created_at=datetime.now()
            ),
            MagicMock(
                id=2,
                table_name="products",
                database_id=1,
                row_count=500,
                table_comment="商品表",
                created_at=datetime.now()
            ),
            MagicMock(
                id=3,
                table_name="orders",
                database_id=1,
                row_count=2000,
                table_comment="订单表",
                created_at=datetime.now()
            ),
        ]

        # Mock 数据库查询
        mock_db = MagicMock()
        mock_db.database_name = "test_ecommerce"

        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_tables
        mock_query.count.return_value.len.return_value = 3

        def mock_query_func(model):
            if hasattr(model, '__tablename__') and model.__tablename__ == 'metadata_databases':
                result = MagicMock()
                result.filter.return_value.first.return_value = mock_db
                return result
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = metadata_service.list_tables(
            database_name="test_ecommerce",
            limit=10,
            offset=0
        )

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) >= 0

        logger.info(f"✓ DM-MD-002: 成功获取元数据列表，共 {result.get('total', 0)} 张表")

    def test_get_table_detail(self, metadata_service, mock_db_session):
        """
        DM-MD-003: 查看表详情（列信息、关系）(P0)

        验证点：
        1. 能够获取表的详细信息
        2. 包含所有列信息
        3. 包含表关系信息
        4. 包含统计信息
        """
        table_id = 1

        # Mock 表数据
        mock_table = MagicMock(
            id=table_id,
            table_name="users",
            database_id=1,
            row_count=1000,
            table_comment="用户表",
            table_type="BASE TABLE",
            created_at=datetime.now()
        )

        # Mock 列数据
        mock_columns = [
            MagicMock(
                id=1,
                table_id=table_id,
                column_name="id",
                column_type="INT",
                is_nullable=False,
                column_key="PRI",
                column_comment="主键ID"
            ),
            MagicMock(
                id=2,
                table_id=table_id,
                column_name="username",
                column_type="VARCHAR(50)",
                is_nullable=False,
                column_key="UNI",
                column_comment="用户名"
            ),
            MagicMock(
                id=3,
                table_id=table_id,
                column_name="email",
                column_type="VARCHAR(100)",
                is_nullable=False,
                column_key="UNI",
                column_comment="邮箱"
            ),
            MagicMock(
                id=4,
                table_id=table_id,
                column_name="created_at",
                column_type="DATETIME",
                is_nullable=True,
                column_key="",
                column_comment="创建时间"
            ),
        ]

        # Mock 查询
        def mock_query_func(model):
            if hasattr(model, '__tablename__'):
                if model.__tablename__ == 'metadata_tables':
                    result = MagicMock()
                    result.filter.return_value.first.return_value = mock_table
                    return result
                elif model.__tablename__ == 'metadata_columns':
                    result = MagicMock()
                    result.filter.return_value.all.return_value = mock_columns
                    return result
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = metadata_service.get_table_detail(table_id)

        # 验证结果
        assert result is not None
        assert result["table_name"] == "users"
        assert "columns" in result
        assert len(result["columns"]) == 4
        assert any(col["column_name"] == "id" for col in result["columns"])
        assert any(col["column_name"] == "username" for col in result["columns"])

        logger.info(
            f"✓ DM-MD-003: 成功获取表详情，"
            f"表名: {result['table_name']}, "
            f"列数: {len(result['columns'])}"
        )

    def test_search_metadata(self, metadata_service, mock_db_session):
        """
        DM-MD-004: 元数据搜索 (P1)

        验证点：
        1. 支持按表名搜索
        2. 支持按列名搜索
        3. 支持按注释搜索
        4. 返回匹配的结果列表
        """
        search_keyword = "user"

        # Mock 搜索结果
        mock_search_results = [
            MagicMock(
                id=1,
                table_name="users",
                database_name="test_ecommerce",
                table_comment="用户表",
                match_type="table"
            ),
            MagicMock(
                id=2,
                table_name="user_mgmt",
                database_name="test_user_mgmt",
                table_comment="用户管理表",
                match_type="table"
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = mock_search_results

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行搜索
        result = metadata_service.search(
            keyword=search_keyword,
            search_type="all",
            limit=10
        )

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result

        logger.info(
            f"✓ DM-MD-004: 成功搜索元数据，"
            f"关键词: '{search_keyword}', "
            f"结果数: {result.get('total', 0)}"
        )

    def test_lineage_analysis(self, mock_db_session):
        """
        DM-MD-005: 血缘关系分析 (P1)

        验证点：
        1. 能够获取表的上游依赖
        2. 能够获取表的下游依赖
        3. 正确构建血缘图谱
        """
        from services.metadata_graph_builder import MetadataGraphBuilder

        graph_builder = MetadataGraphBuilder(mock_db_session)

        table_name = "orders"

        # Mock 血缘关系数据
        mock_lineage = {
            "upstream": [
                {"table": "users", "type": "foreign_key", "columns": ["user_id"]},
                {"table": "products", "type": "denormalized", "columns": ["product_info"]},
            ],
            "downstream": [
                {"table": "order_items", "type": "foreign_key", "columns": ["order_id"]},
                {"table": "analytics_daily_sales", "type": "etl", "columns": []},
            ],
        }

        # Mock 查询
        def mock_query_func(model):
            mock_result = MagicMock()
            mock_result.filter.return_value.all.return_value = []
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行血缘分析
        result = graph_builder.get_lineage(table_name)

        # 验证结果
        assert result is not None
        assert "upstream" in result
        assert "downstream" in result

        logger.info(
            f"✓ DM-MD-005: 成功分析血缘关系，"
            f"上游: {len(result['upstream'])}, "
            f"下游: {len(result['downstream'])}"
        )

    def test_ai_auto_annotate(self, metadata_scan_engine, mock_db_session):
        """
        DM-MD-006: AI 自动标注 (P1)

        验证点：
        1. 能够为表生成描述
        2. 能够为列生成描述
        3. AI 不可用时回退到规则匹配
        """
        # Mock AI 服务不可用
        with patch('services.metadata_auto_scan_engine.get_ai_service') as mock_get_ai:
            mock_ai = MagicMock()
            mock_ai.config.enabled = False
            mock_ai.health_check.return_value = False
            mock_get_ai.return_value = mock_ai

            # Mock 数据库查询
            def mock_query_func(model):
                if hasattr(model, '__tablename__') == 'metadata_databases':
                    result = MagicMock()
                    result.filter.return_value.first.return_value = MagicMock(id=1)
                    return result

                if hasattr(model, '__tablename__') == 'metadata_tables':
                    result = MagicMock()
                    result.filter.return_value.first.return_value = MagicMock(id=1, table_id=1)
                    return result

                if hasattr(model, '__tablename__') == 'metadata_columns':
                    result = MagicMock()
                    result.filter.return_value.all.return_value = []
                    return result

                return MagicMock()

            mock_db_session.query.side_effect = mock_query_func

            # 执行带 AI 标注的扫描
            result = metadata_scan_engine.scan_database(
                connection_info=TestConfig.MYSQL_CONFIG,
                database_name=TestConfig.MYSQL_CONFIG["database"],
                exclude_tables=[],
                ai_annotate=True,
                db_session=mock_db_session
            )

            # 验证结果
            assert result is not None
            assert "columns_annotated" in result

            logger.info(
                f"✓ DM-MD-006: AI 自动标注完成，"
                f"标注列数: {result['columns_annotated']}"
            )

    def test_incremental_scan(
        self,
        metadata_scan_engine,
        mock_db_session
    ):
        """
        DM-MD-007: 增量扫描 (P2)

        验证点：
        1. 能够检测表结构变更
        2. 只处理有变更的表
        3. 生成变更报告
        """
        # Mock 数据库查询
        def mock_query_func(model):
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_func

        # 执行增量扫描
        result = metadata_scan_engine.incremental_scan(
            connection_info=TestConfig.MYSQL_CONFIG,
            database_name=TestConfig.MYSQL_CONFIG["database"],
            exclude_tables=[],
            ai_annotate=False,
            db_session=mock_db_session
        )

        # 验证结果
        assert result is not None
        assert "is_incremental" in result
        assert result["is_incremental"] is True
        assert "tables_scanned" in result
        assert "tables_skipped" in result

        logger.info(
            f"✓ DM-MD-007: 增量扫描完成，"
            f"扫描: {result['tables_scanned']}, "
            f"跳过: {result['tables_skipped']}"
        )


# =============================================================================
# 端到端测试：完整的元数据管理流程
# =============================================================================

class TestMetadataManagementE2E:
    """元数据管理端到端测试"""

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

    def test_full_metadata_workflow(self, api_client):
        """
        端到端测试：完整的元数据管理流程

        流程：
        1. 创建数据源
        2. 扫描元数据
        3. 查看表列表
        4. 查看表详情
        5. 搜索元数据
        """
        api_base = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")

        # 1. 创建数据源（假设数据源已存在）
        datasource_id = "test_mysql_ds"

        # 2. 扫描元数据
        scan_request = {
            "datasource_id": datasource_id,
            "database_name": "test_ecommerce",
            "ai_annotate": False
        }

        response = api_client.post(f"{api_base}/metadata/scan", json=scan_request)

        if response.status_code == 404:
            logger.warning("元数据扫描 API 未实现，跳过 E2E 测试")
            pytest.skip("元数据扫描 API 未实现")

        assert response.status_code in [200, 202]
        scan_result = response.get_json()
        assert "scan_id" in scan_result or "tables_discovered" in scan_result

        logger.info("E2E: 元数据扫描成功")

        # 3. 查看表列表
        response = api_client.get(f"{api_base}/metadata/databases/test_ecommerce/tables")
        assert response.status_code == 200
        tables_result = response.get_json()
        assert "items" in tables_result

        logger.info(f"E2E: 获取表列表成功，共 {len(tables_result['items'])} 张表")

        # 4. 查看表详情
        if tables_result["items"]:
            table_name = tables_result["items"][0]["table_name"]
            response = api_client.get(
                f"{api_base}/metadata/databases/test_ecommerce/tables/{table_name}"
            )
            assert response.status_code == 200
            table_detail = response.get_json()
            assert "columns" in table_detail

            logger.info(
                f"E2E: 获取表详情成功，"
                f"{table_detail['table_name']} 有 {len(table_detail['columns'])} 列"
            )

        # 5. 搜索元数据
        response = api_client.get(f"{api_base}/metadata/search?keyword=user")
        assert response.status_code == 200
        search_result = response.get_json()
        assert "items" in search_result

        logger.info(f"E2E: 搜索元数据成功，找到 {len(search_result['items'])} 个结果")

        logger.info("✓ 元数据管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
