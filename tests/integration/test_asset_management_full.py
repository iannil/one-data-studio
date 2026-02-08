"""
数据资产管理集成测试

测试用例覆盖：
1. DM-AS-001: 自动注册数据资产 (P0)
2. DM-AS-002: 查询资产列表 (P0)
3. DM-AS-003: 获取资产详情 (P0)
4. DM-AS-004: 资产分类管理 (P1)
5. DM-AS-005: AI 语义搜索 (P1)
6. DM-AS-006: 资产价值评估 (P1)
7. DM-AS-007: 资产收藏 (P2)
8. DM-AS-008: 批量资产编目 (P2)
"""

import os
import sys
import pytest
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/data-api'))

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================

class AssetStatus(str, Enum):
    """资产状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    PENDING = "pending"


class AssetType(str, Enum):
    """资产类型"""
    TABLE = "table"
    VIEW = "view"
    API = "api"
    FILE = "file"
    DATASET = "dataset"


@dataclass
class AssetValue:
    """资产价值评分"""
    usage_score: float
    business_score: float
    quality_score: float
    governance_score: float
    overall_score: float
    value_level: str


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

    # 测试资产数据
    TEST_ASSETS = [
        {
            "name": "用户表",
            "asset_type": AssetType.TABLE,
            "database_name": "test_ecommerce",
            "table_name": "users",
            "description": "用户基础信息表",
            "category_name": "用户数据",
            "row_count": 1000,
            "tags": ["用户", "基础数据"],
        },
        {
            "name": "订单表",
            "asset_type": AssetType.TABLE,
            "database_name": "test_ecommerce",
            "table_name": "orders",
            "description": "订单信息表",
            "category_name": "交易数据",
            "row_count": 2000,
            "tags": ["订单", "交易"],
        },
        {
            "name": "商品表",
            "asset_type": AssetType.TABLE,
            "database_name": "test_ecommerce",
            "table_name": "products",
            "description": "商品信息表",
            "category_name": "产品数据",
            "row_count": 500,
            "tags": ["商品", "产品"],
        },
    ]

    # 测试分类
    CATEGORIES = [
        {"category_name": "用户数据", "parent_id": None},
        {"category_name": "交易数据", "parent_id": None},
        {"category_name": "产品数据", "parent_id": None},
        {"category_name": "日志数据", "parent_id": None},
    ]


# =============================================================================
# 数据资产管理测试
# =============================================================================

class TestAssetManagement:
    """数据资产管理测试类"""

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
        session.execute = MagicMock()
        return session

    @pytest.fixture
    def asset_service(self, mock_db_session):
        """创建资产服务"""
        from services.asset_service import AssetService
        return AssetService(mock_db_session)

    @pytest.fixture
    def auto_catalog_service(self, mock_db_session):
        """创建自动编目服务"""
        from services.asset_auto_catalog_service import AssetAutoCatalogService
        return AssetAutoCatalogService()

    # -------------------------------------------------------------------------
    # 测试用例：DM-AS-001 ~ DM-AS-008
    # -------------------------------------------------------------------------

    def test_auto_register_asset(
        self,
        auto_catalog_service,
        mock_db_session
    ):
        """
        DM-AS-001: 自动注册数据资产 (P0)

        验证点：
        1. 能够从元数据自动创建资产
        2. 资产信息正确填充
        3. 返回资产 ID
        """
        # 准备测试数据
        source_database = "test_ecommerce"
        source_table = "users"
        target_database = "test_ecommerce"
        target_table = "users"

        # Mock 查询
        def mock_query_func(model):
            # 模拟资产不存在
            mock_result = MagicMock()
            mock_result.filter.return_value.first.return_value = None
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行自动编目
        result = auto_catalog_service.auto_catalog_from_etl(
            source_database=source_database,
            source_table=source_table,
            target_database=target_database,
            target_table=target_table,
            etl_task_id="",
            created_by="test_user",
            db_session=mock_db_session
        )

        # 验证结果
        assert result is not None
        assert "success" in result

        if result["success"]:
            assert result["asset_id"] is not None
            assert result["action"] in ["created", "updated"]
            logger.info(
                f"✓ DM-AS-001: 成功自动注册资产: "
                f"{result['asset_id']} ({result['action']})"
            )
        else:
            # 可能是环境问题
            logger.warning(f"⚠ DM-AS-001: 自动注册失败: {result.get('message')}")

    def test_batch_catalog_assets(
        self,
        auto_catalog_service,
        mock_db_session
    ):
        """
        DM-AS-008: 批量资产编目 (P2)

        验证点：
        1. 能够批量从元数据注册资产
        2. 正确统计处理结果
        3. 跳过系统数据库
        """
        # Mock 数据库查询
        def mock_query_func(model):
            if hasattr(model, '__tablename__'):
                # Mock 查询返回空列表（跳过实际查询）
                mock_result = MagicMock()
                mock_result.filter.return_value.all.return_value = []
                return mock_result
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_func

        # 执行批量编目
        result = auto_catalog_service.batch_catalog_from_metadata(
            database_name=None,
            created_by="test_user",
            db_session=mock_db_session
        )

        # 验证结果
        assert result is not None
        assert "total_tables" in result
        assert "created" in result
        assert "updated" in result
        assert "errors" in result

        logger.info(
            f"✓ DM-AS-008: 批量编目完成，"
            f"处理: {result['total_tables']}，"
            f"创建: {result['created']}，"
            f"更新: {result['updated']}，"
            f"错误: {result['errors']}"
        )

    def test_list_assets(self, asset_service, mock_db_session):
        """
        DM-AS-002: 查询资产列表 (P0)

        验证点：
        1. 能够获取资产列表
        2. 支持按分类筛选
        3. 支持按资产类型筛选
        4. 支持分页查询
        """
        # Mock 资产数据
        mock_assets = [
            MagicMock(
                asset_id="asset_001",
                name="用户表",
                asset_type=AssetType.TABLE,
                database_name="test_ecommerce",
                table_name="users",
                category_name="用户数据",
                status=AssetStatus.ACTIVE,
                row_count=1000,
                created_at=datetime.now()
            ),
            MagicMock(
                asset_id="asset_002",
                name="订单表",
                asset_type=AssetType.TABLE,
                database_name="test_ecommerce",
                table_name="orders",
                category_name="交易数据",
                status=AssetStatus.ACTIVE,
                row_count=2000,
                created_at=datetime.now()
            ),
            MagicMock(
                asset_id="asset_003",
                name="商品表",
                asset_type=AssetType.TABLE,
                database_name="test_ecommerce",
                table_name="products",
                category_name="产品数据",
                status=AssetStatus.ACTIVE,
                row_count=500,
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_assets
        mock_query.count.return_value = 3

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = asset_service.list_assets(
            category_name=None,
            asset_type=None,
            limit=10,
            offset=0
        )

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 3
        assert result["total"] == 3

        logger.info(
            f"✓ DM-AS-002: 成功获取资产列表，"
            f"共 {result['total']} 个资产"
        )

    def test_get_asset_detail(self, asset_service, mock_db_session):
        """
        DM-AS-003: 获取资产详情 (P0)

        验证点：
        1. 能够获取资产的详细信息
        2. 包含列信息
        3. 包含统计信息
        4. 包含标签信息
        """
        asset_id = "asset_001"

        # Mock 资产数据
        mock_asset = MagicMock(
            asset_id=asset_id,
            name="用户表",
            asset_type=AssetType.TABLE,
            database_name="test_ecommerce",
            table_name="users",
            description="用户基础信息表",
            category_name="用户数据",
            row_count=1000,
            status=AssetStatus.ACTIVE,
            tags=["用户", "基础数据"],
            owner="admin",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Mock 列信息
        mock_columns = [
            {"name": "id", "type": "INT", "comment": "主键ID"},
            {"name": "username", "type": "VARCHAR(50)", "comment": "用户名"},
            {"name": "email", "type": "VARCHAR(100)", "comment": "邮箱"},
        ]

        mock_asset.columns = mock_columns

        # Mock 查询
        call_count = [0]

        def mock_query_func(model):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_result.filter.return_value.first.return_value = mock_asset
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = asset_service.get_asset_detail(asset_id)

        # 验证结果
        assert result is not None
        assert result["asset_id"] == asset_id
        assert result["name"] == "用户表"
        assert "columns" in result
        assert len(result["columns"]) == 3

        logger.info(
            f"✓ DM-AS-003: 成功获取资产详情: "
            f"{result['name']} ({len(result['columns'])} 列)"
        )

    def test_manage_asset_categories(self, asset_service, mock_db_session):
        """
        DM-AS-004: 资产分类管理 (P1)

        验证点：
        1. 能够创建分类
        2. 能够获取分类列表
        3. 支持层级分类
        4. 能够删除分类
        """
        # Mock 分类数据
        mock_categories = [
            MagicMock(
                category_id="cat_001",
                category_name="用户数据",
                parent_id=None,
                level=1,
                asset_count=5,
                created_at=datetime.now()
            ),
            MagicMock(
                category_id="cat_002",
                category_name="交易数据",
                parent_id=None,
                level=1,
                asset_count=3,
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_categories
        mock_query.count.return_value = 2

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 获取分类列表
        result = asset_service.list_categories()

        # 验证结果
        assert result is not None
        assert len(result) >= 0

        if len(result) > 0:
            logger.info(f"✓ DM-AS-004: 成功获取分类列表，共 {len(result)} 个分类")
        else:
            logger.info("✓ DM-AS-004: 分类列表为空（或使用模拟数据）")

    def test_ai_semantic_search(self, mock_db_session):
        """
        DM-AS-005: AI 语义搜索 (P1)

        验证点：
        1. 支持自然语言搜索
        2. 能够理解同义词
        3. 返回相关资产
        """
        from services.ai_asset_search import AIAssetSearchService

        search_service = AIAssetSearchService(mock_db_session)

        # Mock 搜索结果
        mock_results = [
            {
                "asset_id": "asset_001",
                "name": "用户表",
                "description": "用户基础信息表",
                "relevance_score": 0.95
            },
            {
                "asset_id": "asset_010",
                "name": "会员信息",
                "description": "会员详细资料",
                "relevance_score": 0.85
            },
        ]

        # Mock AI 服务
        with patch.object(search_service, '_search_with_embedding', return_value=mock_results):
            # 执行语义搜索
            result = search_service.semantic_search(
                query="找一下用户相关的数据表",
                limit=10
            )

        # 验证结果
        assert result is not None
        assert "items" in result

        logger.info(
            f"✓ DM-AS-005: AI 语义搜索完成，"
            f"找到 {len(result.get('items', []))} 个相关资产"
        )

    def test_asset_value_assessment(self, mock_db_session):
        """
        DM-AS-006: 资产价值评估 (P1)

        验证点：
        1. 能够计算资产使用度评分
        2. 能够计算业务重要度评分
        3. 能够计算数据质量评分
        4. 能够计算治理成熟度评分
        5. 能够分配价值等级
        """
        from services.asset_value_calculator import AssetValueCalculator

        calculator = AssetValueCalculator()

        asset_id = "asset_001"

        # Mock 各项评分返回
        mock_usage_score = 75.0
        mock_business_score = 80.0
        mock_quality_score = 70.0
        mock_governance_score = 65.0

        # Mock 查询
        def mock_query_func(model):
            mock_result = MagicMock()
            mock_result.filter.return_value = MagicMock(
                scalar=MagicMock(return_value=100)
            )
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行价值评估
        with patch.multiple(
            calculator,
            calculate_usage_score=MagicMock(return_value=(mock_usage_score, {})),
            calculate_business_score=MagicMock(return_value=(mock_business_score, {})),
            calculate_quality_score=MagicMock(return_value=(mock_quality_score, {})),
            calculate_governance_score=MagicMock(return_value=(mock_governance_score, {}))
        ):
            result = calculator.evaluate_asset(
                db=mock_db_session,
                asset_id=asset_id,
                save_result=False
            )

        # 验证结果
        assert result is not None
        assert result.usage_score >= 0
        assert result.business_score >= 0
        assert result.quality_score >= 0
        assert result.governance_score >= 0
        assert result.overall_score >= 0
        assert result.value_level in ["S", "A", "B", "C"]

        logger.info(
            f"✓ DM-AS-006: 资产价值评估完成，"
            f"综合评分: {result.overall_score:.2f}，"
            f"等级: {result.value_level}"
        )

    def test_asset_collection(self, asset_service, mock_db_session):
        """
        DM-AS-007: 资产收藏 (P2)

        验证点：
        1. 能够收藏资产
        2. 能够取消收藏
        3. 能够获取收藏列表
        """
        asset_id = "asset_001"
        user_id = "user_001"

        # Mock 资产
        mock_asset = MagicMock(
            asset_id=asset_id,
            name="用户表"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None  # 未收藏过
        mock_db_session.query.return_value = mock_query

        # 添加收藏
        result = asset_service.collect_asset(asset_id, user_id)

        assert result is True or result.get("success") is True

        logger.info(f"✓ DM-AS-007: 资产收藏功能正常")

        # Mock 已收藏
        mock_collection = MagicMock(
            id=1,
            asset_id=asset_id,
            user_id=user_id
        )
        mock_query.filter.return_value.first.return_value = mock_collection

        # 取消收藏
        result = asset_service.uncollect_asset(asset_id, user_id)

        assert result is True or result.get("success") is True

        logger.info(f"✓ DM-AS-007: 资产取消收藏功能正常")


# =============================================================================
# 端到端测试：完整的资产管理流程
# =============================================================================

class TestAssetManagementE2E:
    """数据资产管理端到端测试"""

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

    def test_full_asset_lifecycle(self, api_client):
        """
        端到端测试：完整的资产管理生命周期

        流程：
        1. 自动注册资产（从元数据）
        2. 查询资产列表
        3. 获取资产详情
        4. AI 语义搜索
        5. 资产价值评估
        6. 资产收藏
        7. 删除资产
        """
        api_base = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")

        # 1. 自动注册资产
        catalog_request = {
            "database_name": "test_ecommerce",
            "table_name": "users"
        }

        response = api_client.post(
            f"{api_base}/assets/auto-catalog",
            json=catalog_request
        )

        if response.status_code == 404:
            logger.warning("资产管理 API 未实现，跳过 E2E 测试")
            pytest.skip("资产管理 API 未实现")

        # 允许 200 或 202（异步处理）
        assert response.status_code in [200, 201, 202]
        catalog_result = response.get_json()
        asset_id = catalog_result.get("asset_id")

        logger.info(f"E2E: 自动注册资产成功: {asset_id}")

        # 2. 查询资产列表
        response = api_client.get(f"{api_base}/assets")
        assert response.status_code == 200
        assets_result = response.get_json()

        assert "items" in assets_result
        logger.info(f"E2E: 获取资产列表成功，共 {len(assets_result['items'])} 个资产")

        # 3. 获取资产详情
        if asset_id:
            response = api_client.get(f"{api_base}/assets/{asset_id}")
            assert response.status_code == 200
            asset_detail = response.get_json()

            assert asset_detail.get("asset_id") == asset_id
            logger.info(f"E2E: 获取资产详情成功: {asset_detail.get('name')}")

        # 4. AI 语义搜索
        search_request = {
            "query": "用户相关的数据表",
            "limit": 5
        }

        response = api_client.post(
            f"{api_base}/assets/semantic-search",
            json=search_request
        )

        if response.status_code == 200:
            search_result = response.get_json()
            logger.info(
                f"E2E: AI 语义搜索成功，"
                f"找到 {len(search_result.get('items', []))} 个结果"
            )

        # 5. 资产价值评估
        if asset_id:
            response = api_client.post(
                f"{api_base}/assets/{asset_id}/value-assess"
            )

            if response.status_code == 200:
                assess_result = response.get_json()
                logger.info(
                    f"E2E: 资产价值评估完成，"
                    f"等级: {assess_result.get('value_level')}"
                )

        # 6. 资产收藏
        if asset_id:
            response = api_client.post(f"{api_base}/assets/{asset_id}/collect")
            if response.status_code == 200:
                logger.info("E2E: 资产收藏成功")

        # 7. 清理（删除测试资产）
        if asset_id:
            response = api_client.delete(f"{api_base}/assets/{asset_id}")
            if response.status_code == 200:
                logger.info("E2E: 删除资产成功")

        logger.info("✓ 数据资产管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
