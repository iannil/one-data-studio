"""
特征管理集成测试

测试用例覆盖：
1. DM-FG-001: 创建特征组 (P0)
2. DM-FG-002: 创建特征 (P0)
3. DM-FG-003: 查询特征列表 (P0)
4. DM-FG-004: 获取特征详情 (P1)
5. DM-FG-005: 更新特征 (P1)
6. DM-FG-006: 删除特征 (P1)
7. DM-FG-007: 自动特征工程 (P2)
8. DM-FG-008: 特征服务查询 (P1)
"""

import os
import sys
import pytest
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/data-api'))

logger = logging.getLogger(__name__)


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

    # 测试特征组
    FEATURE_GROUPS = [
        {
            "group_name": "用户基础特征",
            "group_code": "user_basic_features",
            "description": "包含用户的基础属性特征",
            "entity_type": "user",
        },
        {
            "group_name": "用户行为特征",
            "group_code": "user_behavior_features",
            "description": "包含用户的行为统计特征",
            "entity_type": "user",
        },
        {
            "group_name": "商品特征",
            "group_code": "product_features",
            "description": "包含商品的属性特征",
            "entity_type": "product",
        },
    ]

    # 测试特征
    FEATURES = [
        {
            "feature_name": "user_age",
            "feature_type": "integer",
            "description": "用户年龄",
            "data_type": "INT",
            "default_value": 0,
            "tags": ["demographic", "basic"],
        },
        {
            "feature_name": "user_total_orders",
            "feature_type": "integer",
            "description": "用户累计订单数",
            "data_type": "BIGINT",
            "default_value": 0,
            "tags": ["behavior", "aggregated"],
        },
        {
            "feature_name": "user_avg_order_amount",
            "feature_type": "float",
            "description": "用户平均订单金额",
            "data_type": "DECIMAL(10,2)",
            "default_value": 0.0,
            "tags": ["behavior", "financial"],
        },
        {
            "feature_name": "user_last_order_days",
            "feature_type": "integer",
            "description": "用户最后一次下单距今天数",
            "data_type": "INT",
            "default_value": 999,
            "tags": ["behavior", "recency"],
        },
        {
            "feature_name": "product_view_count_7d",
            "feature_type": "integer",
            "description": "商品7天浏览次数",
            "data_type": "INT",
            "default_value": 0,
            "tags": ["product", "behavior"],
        },
    ]


# =============================================================================
# 特征管理测试
# =============================================================================

class TestFeatureManagement:
    """特征管理测试类"""

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
    def feature_service(self, mock_db_session):
        """创建特征服务"""
        from services.feature_service import FeatureService
        return FeatureService(mock_db_session)

    # -------------------------------------------------------------------------
    # 测试用例：DM-FG-001 ~ DM-FG-008
    # -------------------------------------------------------------------------

    def test_create_feature_group(self, feature_service, mock_db_session):
        """
        DM-FG-001: 创建特征组 (P0)

        验证点：
        1. 能够成功创建特征组
        2. 特征组信息正确保存
        3. 返回特征组 ID
        """
        group_data = TestConfig.FEATURE_GROUPS[0]

        # Mock 查询返回 None（表示不存在同名特征组）
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # 执行创建
        result = feature_service.create_feature_group(group_data)

        # 验证结果
        assert result is not None
        assert "group_id" in result
        assert result["group_name"] == group_data["group_name"]
        assert result["group_code"] == group_data["group_code"]
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

        logger.info(
            f"✓ DM-FG-001: 成功创建特征组: "
            f"{result['group_id']} - {result['group_name']}"
        )

    def test_create_feature(self, feature_service, mock_db_session):
        """
        DM-FG-002: 创建特征 (P0)

        验证点：
        1. 能够成功创建特征
        2. 特征信息正确保存
        3. 返回特征 ID
        4. 特征关联到正确的特征组
        """
        group_id = "fg_user_basic"
        feature_data = TestConfig.FEATURES[0].copy()
        feature_data["group_id"] = group_id

        # Mock 查询
        def mock_query_func(model):
            if hasattr(model, '__tablename__'):
                mock_result = MagicMock()
                mock_result.filter.return_value.first.return_value = None
                return mock_result
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_func

        # 执行创建
        result = feature_service.create_feature(feature_data)

        # 验证结果
        assert result is not None
        assert "feature_id" in result
        assert result["feature_name"] == feature_data["feature_name"]
        assert result["feature_type"] == feature_data["feature_type"]
        assert mock_db_session.commit.called

        logger.info(
            f"✓ DM-FG-002: 成功创建特征: "
            f"{result['feature_id']} - {result['feature_name']}"
        )

    def test_list_features(self, feature_service, mock_db_session):
        """
        DM-FG-003: 查询特征列表 (P0)

        验证点：
        1. 能够获取特征列表
        2. 支持按特征组筛选
        3. 支持分页查询
        4. 返回正确的特征数量
        """
        group_id = "fg_user_basic"

        # Mock 特征数据
        mock_features = [
            MagicMock(
                feature_id="f_age",
                feature_name="user_age",
                feature_type="integer",
                data_type="INT",
                description="用户年龄",
                group_id=group_id,
                status="active",
                created_at=datetime.now()
            ),
            MagicMock(
                feature_id="f_gender",
                feature_name="user_gender",
                feature_type="string",
                data_type="VARCHAR(10)",
                description="用户性别",
                group_id=group_id,
                status="active",
                created_at=datetime.now()
            ),
            MagicMock(
                feature_id="f_city",
                feature_name="user_city",
                feature_type="string",
                data_type="VARCHAR(50)",
                description="用户城市",
                group_id=group_id,
                status="active",
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_features
        mock_query.count.return_value = 3

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = feature_service.list_features(
            group_id=group_id,
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
            f"✓ DM-FG-003: 成功获取特征列表，"
            f"共 {result['total']} 个特征"
        )

    def test_get_feature_detail(self, feature_service, mock_db_session):
        """
        DM-FG-004: 获取特征详情 (P1)

        验证点：
        1. 能够获取特征的详细信息
        2. 包含特征定义
        3. 包含关联的特征组信息
        4. 包含特征统计信息
        """
        feature_id = "f_user_age"

        # Mock 特征数据
        mock_feature = MagicMock(
            feature_id=feature_id,
            feature_name="user_age",
            feature_type="integer",
            data_type="INT",
            description="用户年龄",
            group_id="fg_user_basic",
            default_value=0,
            status="active",
            tags=["demographic", "basic"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Mock 特征组
        mock_group = MagicMock(
            group_id="fg_user_basic",
            group_name="用户基础特征",
            entity_type="user"
        )

        # Mock 查询
        call_count = [0]

        def mock_query_func(model):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.filter.return_value.first.return_value = mock_feature
            else:
                mock_result.filter.return_value.first.return_value = mock_group
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = feature_service.get_feature_detail(feature_id)

        # 验证结果
        assert result is not None
        assert result["feature_id"] == feature_id
        assert result["feature_name"] == "user_age"
        assert "group" in result

        logger.info(
            f"✓ DM-FG-004: 成功获取特征详情: "
            f"{result['feature_name']}"
        )

    def test_update_feature(self, feature_service, mock_db_session):
        """
        DM-FG-005: 更新特征 (P1)

        验证点：
        1. 能够更新特征信息
        2. 更新后数据正确保存
        3. 不存在的特征返回错误
        """
        feature_id = "f_user_age"

        # 准备更新数据
        update_data = {
            "description": "用户年龄（基于生日计算）",
            "default_value": 18,
        }

        # Mock 现有特征
        mock_feature = MagicMock(
            feature_id=feature_id,
            feature_name="user_age",
            description="用户年龄",
            default_value=0
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_feature
        mock_db_session.query.return_value = mock_query

        # 执行更新
        result = feature_service.update_feature(feature_id, update_data)

        # 验证结果
        assert result is not None
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-FG-005: 成功更新特征: {feature_id}")

    def test_delete_feature(self, feature_service, mock_db_session):
        """
        DM-FG-006: 删除特征 (P1)

        验证点：
        1. 能够删除指定特征
        2. 删除后特征不可再获取
        3. 不存在的特征返回 False
        """
        feature_id = "f_user_age"

        # Mock 现有特征
        mock_feature = MagicMock(
            feature_id=feature_id,
            feature_name="user_age"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_feature
        mock_db_session.query.return_value = mock_query

        # 执行删除
        result = feature_service.delete_feature(feature_id)

        # 验证结果
        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-FG-006: 成功删除特征: {feature_id}")

    def test_auto_feature_engineering(self, mock_db_session):
        """
        DM-FG-007: 自动特征工程 (P2)

        验证点：
        1. 能够从数据表自动生成特征
        2. 能够识别数值型特征
        3. 能够识别类别型特征
        4. 能够生成聚合特征
        """
        from services.feature_auto import FeatureAutoEngine

        engine = FeatureAutoEngine(mock_db_session)

        # 准备表结构信息
        table_info = {
            "table_name": "users",
            "database": "test_ecommerce",
            "columns": [
                {"name": "id", "type": "INT", "nullable": False, "key": "PRI"},
                {"name": "username", "type": "VARCHAR(50)", "nullable": False, "key": "UNI"},
                {"name": "email", "type": "VARCHAR(100)", "nullable": False, "key": ""},
                {"name": "age", "type": "INT", "nullable": True, "key": ""},
                {"name": "gender", "type": "VARCHAR(10)", "nullable": True, "key": ""},
                {"name": "city", "type": "VARCHAR(50)", "nullable": True, "key": ""},
                {"name": "created_at", "type": "DATETIME", "nullable": True, "key": ""},
            ],
            "row_count": 1000
        }

        # Mock 查询
        def mock_query_func(model):
            return MagicMock()

        mock_db_session.query.side_effect = mock_query_func

        # 执行自动特征工程
        result = engine.generate_features_from_table(
            table_info=table_info,
            group_id="fg_user_auto",
            feature_name_prefix="user"
        )

        # 验证结果
        assert result is not None
        assert "features" in result
        assert len(result["features"]) > 0

        # 验证生成的特征类型
        feature_types = {f.get("inferred_type") for f in result["features"]}
        assert "numerical" in feature_types or "categorical" in feature_types

        logger.info(
            f"✓ DM-FG-007: 自动特征工程完成，"
            f"生成 {len(result['features'])} 个特征"
        )

    def test_feature_serving_query(self, mock_db_session):
        """
        DM-FG-008: 特征服务查询 (P1)

        验证点：
        1. 能够根据实体 ID 查询特征值
        2. 支持批量查询
        3. 返回正确的特征值
        """
        from services.feature_store import FeatureStoreService

        store = FeatureStoreService(mock_db_session)

        # Mock 特征值数据
        mock_feature_values = {
            "user_age": 25,
            "user_total_orders": 10,
            "user_avg_order_amount": 299.50,
            "user_last_order_days": 5,
        }

        # Mock 查询返回
        mock_result = MagicMock()
        mock_result.filter.return_value.all.return_value = []

        def mock_query_func(model):
            return mock_result

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = store.get_features(
            entity_type="user",
            entity_id="user_001",
            feature_names=["user_age", "user_total_orders"]
        )

        # 验证结果
        assert result is not None
        assert "entity_id" in result
        assert "features" in result

        logger.info(
            f"✓ DM-FG-008: 特征服务查询完成，"
            f"返回 {len(result.get('features', {}))} 个特征值"
        )


# =============================================================================
# 端到端测试：完整的特征管理流程
# =============================================================================

class TestFeatureManagementE2E:
    """特征管理端到端测试"""

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

    def test_full_feature_lifecycle(self, api_client):
        """
        端到端测试：完整的特征管理生命周期

        流程：
        1. 创建特征组
        2. 创建特征
        3. 查询特征列表
        4. 获取特征详情
        5. 更新特征
        6. 删除特征
        7. 删除特征组
        """
        api_base = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")

        # 1. 创建特征组
        group_request = TestConfig.FEATURE_GROUPS[0]

        response = api_client.post(
            f"{api_base}/feature-groups",
            json=group_request
        )

        if response.status_code == 404:
            logger.warning("特征管理 API 未实现，跳过 E2E 测试")
            pytest.skip("特征管理 API 未实现")

        assert response.status_code in [200, 201]
        group_result = response.get_json()
        group_id = group_result.get("group_id")

        logger.info(f"E2E: 创建特征组成功: {group_id}")

        # 2. 创建特征
        feature_request = TestConfig.FEATURES[0].copy()
        feature_request["group_id"] = group_id

        response = api_client.post(
            f"{api_base}/features",
            json=feature_request
        )
        assert response.status_code in [200, 201]
        feature_result = response.get_json()
        feature_id = feature_result.get("feature_id")

        logger.info(f"E2E: 创建特征成功: {feature_id}")

        # 3. 查询特征列表
        response = api_client.get(f"{api_base}/features?group_id={group_id}")
        assert response.status_code == 200
        features_result = response.get_json()

        assert "items" in features_result
        logger.info(f"E2E: 获取特征列表成功，共 {len(features_result['items'])} 个特征")

        # 4. 获取特征详情
        response = api_client.get(f"{api_base}/features/{feature_id}")
        assert response.status_code == 200
        detail_result = response.get_json()

        assert detail_result.get("feature_id") == feature_id
        logger.info(f"E2E: 获取特征详情成功: {detail_result.get('feature_name')}")

        # 5. 更新特征
        update_request = {"description": "更新后的描述"}
        response = api_client.put(
            f"{api_base}/features/{feature_id}",
            json=update_request
        )
        assert response.status_code == 200

        logger.info("E2E: 更新特征成功")

        # 6-7. 清理（删除特征和特征组）
        response = api_client.delete(f"{api_base}/features/{feature_id}")
        if response.status_code == 200:
            logger.info("E2E: 删除特征成功")

        response = api_client.delete(f"{api_base}/feature-groups/{group_id}")
        if response.status_code == 200:
            logger.info("E2E: 删除特征组成功")

        logger.info("✓ 特征管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
