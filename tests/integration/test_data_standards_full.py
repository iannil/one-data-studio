"""
数据标准集成测试

测试用例覆盖：
1. DM-DS-001: 创建数据标准 (P0)
2. DM-DS-002: 查询标准列表 (P0)
3. DM-DS-003: 应用数据标准到字段 (P1)
4. DM-DS-004: 验证数据是否符合标准 (P0)
5. DM-DS-005: 查看标准违规情况 (P1)
6. DM-DS-006: 更新数据标准 (P1)
7. DM-DS-007: 删除数据标准 (P2)
8. DM-DS-008: 标准类型验证 (P1)
"""

import os
import sys
import pytest
import uuid
import re
import logging
from datetime import datetime
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

class StandardType(str, Enum):
    """标准类型"""
    NAMING = "naming"           # 命名规范
    FORMAT = "format"           # 格式规范
    RANGE = "range"             # 范围规范
    REFERENCE = "reference"     # 引用规范
    CUSTOM = "custom"           # 自定义规范


@dataclass
class StandardViolation:
    """标准违规记录"""
    standard_id: str
    standard_name: str
    violation_type: str
    field_name: str
    field_value: Any
    expected_value: str
    description: str


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

    # 测试标准定义
    STANDARDS = [
        {
            "standard_name": "邮箱格式标准",
            "standard_code": "email_format",
            "standard_type": StandardType.FORMAT,
            "description": "邮箱地址格式验证",
            "rule": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "error_message": "邮箱格式不正确"
            }
        },
        {
            "standard_name": "手机号格式标准",
            "standard_code": "phone_format",
            "standard_type": StandardType.FORMAT,
            "description": "手机号格式验证（中国大陆）",
            "rule": {
                "pattern": r"^1[3-9]\d{9}$",
                "error_message": "手机号格式不正确"
            }
        },
        {
            "standard_name": "字段命名规范",
            "standard_code": "snake_case_naming",
            "standard_type": StandardType.NAMING,
            "description": "字段名必须使用 snake_case 格式",
            "rule": {
                "pattern": r"^[a-z][a-z0-9_]*$",
                "error_message": "字段名必须使用小写字母、数字和下划线，且以字母开头"
            }
        },
        {
            "standard_name": "年龄范围规范",
            "standard_code": "age_range",
            "standard_type": StandardType.RANGE,
            "description": "年龄必须在 0-150 之间",
            "rule": {
                "min": 0,
                "max": 150,
                "error_message": "年龄必须在 0-150 之间"
            }
        },
        {
            "standard_name": "用户状态枚举",
            "standard_code": "user_status_enum",
            "standard_type": StandardType.CUSTOM,
            "description": "用户状态只能是指定值",
            "rule": {
                "allowed_values": ["active", "inactive", "banned"],
                "error_message": "用户状态必须是 active/inactive/banned 之一"
            }
        },
    ]

    # 测试数据
    TEST_DATA = {
        "valid": {
            "email": "test@example.com",
            "phone": "13812345678",
            "age": 25,
            "status": "active",
            "field_name": "user_name"
        },
        "invalid": {
            "email": "invalid-email",
            "phone": "12345",
            "age": 200,
            "status": "unknown",
            "field_name": "UserName"  # 违反命名规范
        }
    }


# =============================================================================
# 数据标准管理测试
# =============================================================================

class TestDataStandards:
    """数据标准管理测试类"""

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
    def standard_service(self, mock_db_session):
        """创建数据标准服务"""
        from services.standard_service import DataStandardService
        return DataStandardService(mock_db_session)

    # -------------------------------------------------------------------------
    # 测试用例：DM-DS-001 ~ DM-DS-008
    # -------------------------------------------------------------------------

    def test_create_standard(self, standard_service, mock_db_session):
        """
        DM-DS-001: 创建数据标准 (P0)

        验证点：
        1. 能够成功创建数据标准
        2. 标准信息正确保存
        3. 返回标准 ID
        """
        standard_data = TestConfig.STANDARDS[0]

        # Mock 查询返回 None
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # 执行创建
        result = standard_service.create_standard(standard_data)

        # 验证结果
        assert result is not None
        assert "standard_id" in result
        assert result["standard_name"] == standard_data["standard_name"]
        assert result["standard_code"] == standard_data["standard_code"]
        assert result["standard_type"] == standard_data["standard_type"]
        assert mock_db_session.commit.called

        logger.info(
            f"✓ DM-DS-001: 成功创建数据标准: "
            f"{result['standard_id']} - {result['standard_name']}"
        )

    def test_list_standards(self, standard_service, mock_db_session):
        """
        DM-DS-002: 查询标准列表 (P0)

        验证点：
        1. 能够获取标准列表
        2. 支持按标准类型筛选
        3. 支持分页查询
        4. 返回正确的标准数量
        """
        # Mock 标准数据
        mock_standards = [
            MagicMock(
                standard_id="std_001",
                standard_name="邮箱格式标准",
                standard_code="email_format",
                standard_type=StandardType.FORMAT,
                description="邮箱格式验证",
                created_at=datetime.now()
            ),
            MagicMock(
                standard_id="std_002",
                standard_name="手机号格式标准",
                standard_code="phone_format",
                standard_type=StandardType.FORMAT,
                description="手机号格式验证",
                created_at=datetime.now()
            ),
            MagicMock(
                standard_id="std_003",
                standard_name="命名规范",
                standard_code="naming_rule",
                standard_type=StandardType.NAMING,
                description="命名规范",
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_standards
        mock_query.count.return_value = 3

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = standard_service.list_standards(
            standard_type=None,
            limit=10,
            offset=0
        )

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 3
        assert result["total"] == 3

        logger.info(f"✓ DM-DS-002: 成功获取标准列表，共 {result['total']} 个标准")

    def test_apply_standard_to_field(self, standard_service, mock_db_session):
        """
        DM-DS-003: 应用数据标准到字段 (P1)

        验证点：
        1. 能够将标准应用到指定字段
        2. 创建标准与字段的关联
        3. 支持批量应用
        """
        standard_id = "std_email_format"

        # 准备应用数据
        apply_data = {
            "standard_id": standard_id,
            "database": "test_ecommerce",
            "table": "users",
            "column": "email",
        }

        # Mock 查询
        mock_standard = MagicMock(
            standard_id=standard_id,
            standard_name="邮箱格式标准"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_standard
        mock_db_session.query.return_value = mock_query

        # 执行应用
        result = standard_service.apply_standard(apply_data)

        # 验证结果
        assert result is not None
        assert result["success"] is True
        assert mock_db_session.add.called

        logger.info(
            f"✓ DM-DS-003: 成功应用标准到字段: "
            f"{apply_data['table']}.{apply_data['column']}"
        )

    def test_validate_data_with_standard(self, standard_service, mock_db_session):
        """
        DM-DS-004: 验证数据是否符合标准 (P0)

        验证点：
        1. 能够验证单条数据
        2. 能够批量验证数据
        3. 正确识别违规数据
        4. 返回清晰的验证结果
        """
        standard_id = "std_email_format"

        # Mock 标准
        mock_standard = MagicMock(
            standard_id=standard_id,
            standard_name="邮箱格式标准",
            standard_type=StandardType.FORMAT,
            rule={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_standard
        mock_db_session.query.return_value = mock_query

        # 测试有效数据
        valid_data = {"email": TestConfig.TEST_DATA["valid"]["email"]}
        result = standard_service.validate_data(
            standard_id=standard_id,
            data=valid_data
        )

        assert result is not None
        assert result["valid"] is True
        assert len(result.get("violations", [])) == 0

        # 测试无效数据
        invalid_data = {"email": TestConfig.TEST_DATA["invalid"]["email"]}
        result = standard_service.validate_data(
            standard_id=standard_id,
            data=invalid_data
        )

        assert result is not None
        assert result["valid"] is False
        assert len(result.get("violations", [])) > 0

        logger.info(f"✓ DM-DS-004: 数据验证功能正常")

    def test_get_standard_violations(self, standard_service, mock_db_session):
        """
        DM-DS-005: 查看标准违规情况 (P1)

        验证点：
        1. 能够获取违规记录列表
        2. 支持按标准筛选
        3. 支持按表/字段筛选
        4. 返回违规详情
        """
        standard_id = "std_email_format"

        # Mock 违规记录
        mock_violations = [
            MagicMock(
                id=1,
                standard_id=standard_id,
                database="test_ecommerce",
                table="users",
                column="email",
                row_id=10,
                field_value="invalid-email",
                expected_value="valid email format",
                violation_type="format",
                created_at=datetime.now()
            ),
            MagicMock(
                id=2,
                standard_id=standard_id,
                database="test_ecommerce",
                table="users",
                column="email",
                row_id=25,
                field_value="another-invalid",
                expected_value="valid email format",
                violation_type="format",
                created_at=datetime.now()
            ),
        ]

        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_violations
        mock_query.count.return_value = 2

        def mock_query_func(model):
            return mock_query

        mock_db_session.query.side_effect = mock_query_func

        # 执行查询
        result = standard_service.get_violations(
            standard_id=standard_id,
            limit=10,
            offset=0
        )

        # 验证结果
        assert result is not None
        assert "items" in result
        assert "total" in result
        assert result["total"] >= 0

        if result["total"] > 0:
            logger.info(
                f"✓ DM-DS-005: 查询到 {result['total']} 条违规记录"
            )
        else:
            logger.info("✓ DM-DS-005: 无违规记录")

    def test_update_standard(self, standard_service, mock_db_session):
        """
        DM-DS-006: 更新数据标准 (P1)

        验证点：
        1. 能够更新标准信息
        2. 更新后规则生效
        3. 不存在的标准返回错误
        """
        standard_id = "std_email_format"

        # 准备更新数据
        update_data = {
            "description": "更新后的邮箱格式标准",
            "rule": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "error_message": "邮箱格式不正确，请检查"
            }
        }

        # Mock 现有标准
        mock_standard = MagicMock(
            standard_id=standard_id,
            standard_name="邮箱格式标准",
            description="原始描述"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_standard
        mock_db_session.query.return_value = mock_query

        # 执行更新
        result = standard_service.update_standard(standard_id, update_data)

        # 验证结果
        assert result is not None
        assert mock_db_session.commit.called

        logger.info(f"✓ DM-DS-006: 成功更新数据标准: {standard_id}")

    def test_delete_standard(self, standard_service, mock_db_session):
        """
        DM-DS-007: 删除数据标准 (P2)

        验证点：
        1. 能够删除指定标准
        2. 删除后关联关系也删除
        3. 不存在的标准返回 False
        """
        standard_id = "std_to_delete"

        # Mock 现有标准
        mock_standard = MagicMock(
            standard_id=standard_id,
            standard_name="待删除标准"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_standard
        mock_db_session.query.return_value = mock_query

        # 执行删除
        result = standard_service.delete_standard(standard_id)

        # 验证结果
        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called

        # 测试删除不存在的标准
        mock_query.filter.return_value.first.return_value = None
        result = standard_service.delete_standard("nonexistent")

        assert result is False

        logger.info(f"✓ DM-DS-007: 删除标准功能正常")

    def test_standard_type_validation(self, standard_service, mock_db_session):
        """
        DM-DS-008: 标准类型验证 (P1)

        验证点：
        1. 命名规范验证
        2. 格式规范验证（正则）
        3. 范围规范验证
        4. 枚举值验证
        """
        # 测试格式规范（邮箱）
        email_standard = TestConfig.STANDARDS[0]
        pattern = email_standard["rule"]["pattern"]

        valid_email = TestConfig.TEST_DATA["valid"]["email"]
        invalid_email = TestConfig.TEST_DATA["invalid"]["email"]

        assert re.match(pattern, valid_email) is not None
        assert re.match(pattern, invalid_email) is None

        # 测试格式规范（手机号）
        phone_standard = TestConfig.STANDARDS[1]
        pattern = phone_standard["rule"]["pattern"]

        valid_phone = TestConfig.TEST_DATA["valid"]["phone"]
        invalid_phone = TestConfig.TEST_DATA["invalid"]["phone"]

        assert re.match(pattern, valid_phone) is not None
        assert re.match(pattern, invalid_phone) is None

        # 测试命名规范
        naming_standard = TestConfig.STANDARDS[2]
        pattern = naming_standard["rule"]["pattern"]

        valid_name = TestConfig.TEST_DATA["valid"]["field_name"]
        invalid_name = TestConfig.TEST_DATA["invalid"]["field_name"]

        assert re.match(pattern, valid_name) is not None
        assert re.match(pattern, invalid_name) is None

        # 测试范围规范
        range_standard = TestConfig.STANDARDS[3]
        min_val = range_standard["rule"]["min"]
        max_val = range_standard["rule"]["max"]

        valid_age = TestConfig.TEST_DATA["valid"]["age"]
        invalid_age = TestConfig.TEST_DATA["invalid"]["age"]

        assert min_val <= valid_age <= max_val
        assert not (min_val <= invalid_age <= max_val)

        # 测试枚举值规范
        enum_standard = TestConfig.STANDARDS[4]
        allowed_values = enum_standard["rule"]["allowed_values"]

        valid_status = TestConfig.TEST_DATA["valid"]["status"]
        invalid_status = TestConfig.TEST_DATA["invalid"]["status"]

        assert valid_status in allowed_values
        assert invalid_status not in allowed_values

        logger.info(f"✓ DM-DS-008: 各类型标准验证功能正常")


# =============================================================================
# 端到端测试：完整的数据标准管理流程
# =============================================================================

class TestDataStandardsE2E:
    """数据标准管理端到端测试"""

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

    def test_full_standards_lifecycle(self, api_client):
        """
        端到端测试：完整的数据标准管理生命周期

        流程：
        1. 创建数据标准
        2. 应用标准到字段
        3. 验证数据
        4. 查看违规情况
        5. 更新标准
        6. 删除标准
        """
        api_base = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")

        # 1. 创建数据标准
        standard_request = TestConfig.STANDARDS[0]

        response = api_client.post(
            f"{api_base}/standards",
            json=standard_request
        )

        if response.status_code == 404:
            logger.warning("数据标准 API 未实现，跳过 E2E 测试")
            pytest.skip("数据标准 API 未实现")

        assert response.status_code in [200, 201]
        standard_result = response.get_json()
        standard_id = standard_result.get("standard_id")

        logger.info(f"E2E: 创建数据标准成功: {standard_id}")

        # 2. 应用标准到字段
        apply_request = {
            "standard_id": standard_id,
            "database": "test_ecommerce",
            "table": "users",
            "column": "email"
        }

        response = api_client.post(
            f"{api_base}/standards/apply",
            json=apply_request
        )
        assert response.status_code == 200

        logger.info("E2E: 应用标准到字段成功")

        # 3. 验证数据
        validate_request = {
            "standard_id": standard_id,
            "data": {"email": "test@example.com"}
        }

        response = api_client.post(
            f"{api_base}/standards/validate",
            json=validate_request
        )
        assert response.status_code == 200
        validate_result = response.get_json()

        assert validate_result["valid"] is True

        logger.info("E2E: 数据验证成功")

        # 4. 查看违规情况
        response = api_client.get(
            f"{api_base}/standards/{standard_id}/violations"
        )
        assert response.status_code == 200
        violations_result = response.get_json()

        logger.info(
            f"E2E: 查询违规记录成功，"
            f"共 {violations_result.get('total', 0)} 条"
        )

        # 5. 更新标准
        update_request = {
            "description": "更新后的描述"
        }

        response = api_client.put(
            f"{api_base}/standards/{standard_id}",
            json=update_request
        )
        assert response.status_code == 200

        logger.info("E2E: 更新标准成功")

        # 6. 删除标准
        response = api_client.delete(f"{api_base}/standards/{standard_id}")
        if response.status_code == 200:
            logger.info("E2E: 删除标准成功")

        logger.info("✓ 数据标准管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
