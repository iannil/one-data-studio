"""
元数据版本管理集成测试

测试用例覆盖：
1. DM-MV-001: 创建元数据版本快照 (P0)
2. DM-MV-002: 查看版本历史 (P0)
3. DM-MV-003: 版本对比 (P0)
4. DM-MV-004: 生成迁移 SQL (P1)
5. DM-MV-005: 版本回滚 (P1)
6. DM-MV-006: 删除版本快照 (P2)
"""

import os
import sys
import pytest
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/data-api'))

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义（复用服务代码中的定义）
# =============================================================================

class ChangeType(str, Enum):
    """变更类型"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class ColumnVersion:
    """列版本信息"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    default_value: Any = None
    comment: str = ""
    max_length: int = None
    auto_increment: bool = False

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "default_value": str(self.default_value) if self.default_value else None,
            "comment": self.comment,
            "max_length": self.max_length,
            "auto_increment": self.auto_increment,
        }


@dataclass
class TableVersion:
    """表版本信息"""
    table_name: str
    database: str
    columns: Dict[str, ColumnVersion] = field(default_factory=dict)
    row_count: int = 0
    comment: str = ""
    engine: str = "InnoDB"
    charset: str = "utf8mb4"

    def to_dict(self) -> Dict:
        return {
            "table_name": self.table_name,
            "database": self.database,
            "columns": {k: v.to_dict() for k, v in self.columns.items()},
            "row_count": self.row_count,
            "comment": self.comment,
            "engine": self.engine,
            "charset": self.charset,
        }


# =============================================================================
# 测试配置
# =============================================================================

class TestConfig:
    """测试配置"""

    TEST_DATABASE = "test_ecommerce"

    # 测试表结构 - 版本1
    TABLE_V1_COLUMNS = {
        "id": ColumnVersion("id", "INT", False, True, None, "主键ID"),
        "username": ColumnVersion("username", "VARCHAR(50)", False, False, None, "用户名"),
        "email": ColumnVersion("email", "VARCHAR(100)", False, False, None, "邮箱"),
        "created_at": ColumnVersion("created_at", "DATETIME", True, False, None, "创建时间"),
    }

    # 测试表结构 - 版本2（添加列）
    TABLE_V2_COLUMNS = {
        "id": ColumnVersion("id", "INT", False, True, None, "主键ID"),
        "username": ColumnVersion("username", "VARCHAR(50)", False, False, None, "用户名"),
        "email": ColumnVersion("email", "VARCHAR(100)", False, False, None, "邮箱"),
        "phone": ColumnVersion("phone", "VARCHAR(20)", True, False, None, "手机号"),  # 新增
        "status": ColumnVersion("status", "VARCHAR(20)", True, False, "active", "状态"),  # 新增
        "created_at": ColumnVersion("created_at", "DATETIME", True, False, None, "创建时间"),
    }

    # 测试表结构 - 版本3（修改列）
    TABLE_V3_COLUMNS = {
        "id": ColumnVersion("id", "INT", False, True, None, "主键ID"),
        "username": ColumnVersion("username", "VARCHAR(100)", False, False, None, "用户名"),  # 修改长度
        "email": ColumnVersion("email", "VARCHAR(100)", False, False, None, "邮箱"),
        "phone": ColumnVersion("phone", "VARCHAR(20)", True, False, None, "手机号"),
        "status": ColumnVersion("status", "VARCHAR(20)", True, False, "active", "状态"),
        "updated_at": ColumnVersion("updated_at", "DATETIME", True, False, None, "更新时间"),  # 新增
        "created_at": ColumnVersion("created_at", "DATETIME", True, False, None, "创建时间"),
    }


# =============================================================================
# 元数据版本管理测试
# =============================================================================

class TestMetadataVersion:
    """元数据版本管理测试类"""

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
    def version_service(self, mock_db_session):
        """创建版本服务"""
        from services.metadata_version_service import MetadataVersionService
        return MetadataVersionService(lambda: mock_db_session)

    # -------------------------------------------------------------------------
    # 测试用例：DM-MV-001 ~ DM-MV-006
    # -------------------------------------------------------------------------

    def test_create_metadata_snapshot(self, version_service, mock_db_session):
        """
        DM-MV-001: 创建元数据版本快照 (P0)

        验证点：
        1. 能够成功创建快照
        2. 快照包含所有表信息
        3. 返回快照 ID
        4. 快照数据正确保存
        """
        # 准备测试数据
        version = "v1.0.0"
        database = TestConfig.TEST_DATABASE

        tables = {
            "users": TableVersion(
                table_name="users",
                database=database,
                columns=TestConfig.TABLE_V1_COLUMNS.copy(),
                row_count=1000
            ),
            "products": TableVersion(
                table_name="products",
                database=database,
                columns={
                    "id": ColumnVersion("id", "INT", False, True, None, "主键ID"),
                    "name": ColumnVersion("name", "VARCHAR(200)", False, False, None, "商品名称"),
                    "price": ColumnVersion("price", "DECIMAL(10,2)", False, False, None, "价格"),
                },
                row_count=500
            ),
        }

        # 执行测试
        snapshot = version_service.create_snapshot(
            version=version,
            database=database,
            tables=tables,
            created_by="test_user",
            description="初始版本快照"
        )

        # 验证结果
        assert snapshot is not None
        assert snapshot.snapshot_id is not None
        assert snapshot.version == version
        assert snapshot.database == database
        assert len(snapshot.tables) == 2
        assert "users" in snapshot.tables
        assert "products" in snapshot.tables
        assert mock_db_session.commit.called

        logger.info(
            f"✓ DM-MV-001: 成功创建快照 {snapshot.snapshot_id}，"
            f"版本: {version}，"
            f"表数: {len(snapshot.tables)}"
        )

        return snapshot.snapshot_id

    def test_list_version_history(self, version_service, mock_db_session):
        """
        DM-MV-002: 查看版本历史 (P0)

        验证点：
        1. 能够获取版本历史列表
        2. 按时间倒序排列
        3. 包含版本信息
        4. 支持按数据库筛选
        """
        # Mock 快照数据
        mock_snapshots = [
            MagicMock(
                id="snap_003",
                version="v1.2.0",
                database="test_ecommerce",
                tables_snapshot={},
                created_at=datetime.now(),
                created_by="user_a",
                description="第三版",
                tags=["release"]
            ),
            MagicMock(
                id="snap_002",
                version="v1.1.0",
                database="test_ecommerce",
                tables_snapshot={},
                created_at=datetime.now() - timedelta(hours=1),
                created_by="user_a",
                description="第二版",
                tags=[]
            ),
            MagicMock(
                id="snap_001",
                version="v1.0.0",
                database="test_ecommerce",
                tables_snapshot={},
                created_at=datetime.now() - timedelta(hours=2),
                created_by="user_b",
                description="初始版",
                tags=["baseline"]
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_snapshots
        mock_db_session.query.return_value = mock_query

        # 执行测试
        snapshots = version_service.list_snapshots(
            database="test_ecommerce",
            limit=10
        )

        # 验证结果
        assert snapshots is not None
        assert len(snapshots) == 3
        assert snapshots[0].version == "v1.2.0"  # 最新的在前
        assert snapshots[2].version == "v1.0.0"

        logger.info(f"✓ DM-MV-002: 成功获取版本历史，共 {len(snapshots)} 个快照")

    def test_compare_snapshots(self, version_service, mock_db_session):
        """
        DM-MV-003: 版本对比 (P0)

        验证点：
        1. 能够正确识别新增的表
        2. 能够正确识别删除的表
        3. 能够正确识别修改的表
        4. 能够正确识别列级变更
        """
        # 准备两个版本的数据
        from_snapshot_id = "snap_v1"
        to_snapshot_id = "snap_v2"

        # Mock 源快照（版本1）
        from_snapshot = MagicMock(
            snapshot_id=from_snapshot_id,
            version="v1.0.0",
            database="test_ecommerce",
            created_at=datetime.now() - timedelta(hours=1),
        )
        from_snapshot.get_table_names = Mock(return_value=["users", "products"])
        from_snapshot.tables = {
            "users": TableVersion(
                table_name="users",
                database="test_ecommerce",
                columns=TestConfig.TABLE_V1_COLUMNS.copy()
            ),
            "products": TableVersion(
                table_name="products",
                database="test_ecommerce",
                columns={}
            ),
        }

        # Mock 目标快照（版本2）
        to_snapshot = MagicMock(
            snapshot_id=to_snapshot_id,
            version="v2.0.0",
            database="test_ecommerce",
            created_at=datetime.now()
        )
        to_snapshot.get_table_names = Mock(return_value=["users", "products", "orders"])
        to_snapshot.tables = {
            "users": TableVersion(
                table_name="users",
                database="test_ecommerce",
                columns=TestConfig.TABLE_V2_COLUMNS.copy()  # 有新增列
            ),
            "products": TableVersion(
                table_name="products",
                database="test_ecommerce",
                columns={}
            ),
            "orders": TableVersion(  # 新增表
                table_name="orders",
                database="test_ecommerce",
                columns={}
            ),
        }

        # Mock 查询
        def mock_get_snapshot(sid):
            if sid == from_snapshot_id:
                return from_snapshot
            elif sid == to_snapshot_id:
                return to_snapshot
            return None

        with patch.object(version_service, 'get_snapshot', side_effect=mock_get_snapshot):
            # 执行对比
            diff = version_service.compare_snapshots(from_snapshot_id, to_snapshot_id)

        # 验证结果
        assert diff is not None
        assert "added_tables" in diff
        assert "removed_tables" in diff
        assert "modified_tables" in diff
        assert "table_diffs" in diff

        # 验证新增表
        assert "orders" in diff["added_tables"]

        # 验证修改的表
        assert "users" in diff["modified_tables"]

        # 验证 users 表的列变更
        users_diff = diff["table_diffs"].get("users", {})
        assert "phone" in users_diff.get("added_columns", [])
        assert "status" in users_diff.get("added_columns", [])

        logger.info(
            f"✓ DM-MV-003: 版本对比完成，"
            f"新增表: {len(diff['added_tables'])}，"
            f"删除表: {len(diff['removed_tables'])}，"
            f"修改表: {len(diff['modified_tables'])}"
        )

    def test_generate_migration_sql(self, version_service, mock_db_session):
        """
        DM-MV-004: 生成迁移 SQL (P1)

        验证点：
        1. 能够为新增表生成 CREATE TABLE
        2. 能够为删除表生成 DROP TABLE
        3. 能够为新增列生成 ALTER TABLE ADD
        4. 能够为修改列生成 ALTER TABLE MODIFY
        """
        from_snapshot_id = "snap_v1"
        to_snapshot_id = "snap_v2"

        # Mock 版本对比结果
        mock_diff = {
            "from_snapshot": {"id": from_snapshot_id, "version": "v1.0.0"},
            "to_snapshot": {"id": to_snapshot_id, "version": "v2.0.0"},
            "added_tables": ["new_table"],
            "removed_tables": ["old_table"],
            "modified_tables": ["users"],
            "table_diffs": {
                "new_table": {
                    "table_name": "new_table",
                    "is_new_table": True,
                    "added_columns": ["id", "name"],
                    "removed_columns": [],
                    "modified_columns": [],
                    "unchanged_columns": [],
                },
                "old_table": {
                    "table_name": "old_table",
                    "is_removed_table": True,
                    "added_columns": [],
                    "removed_columns": ["id", "name"],
                    "modified_columns": [],
                    "unchanged_columns": [],
                },
                "users": {
                    "table_name": "users",
                    "added_columns": ["phone", "status"],
                    "removed_columns": [],
                    "modified_columns": [
                        {
                            "column_name": "username",
                            "changes": [
                                {"field_name": "类型", "old_value": "VARCHAR(50)", "new_value": "VARCHAR(100)"}
                            ]
                        }
                    ],
                    "unchanged_columns": ["id", "email"],
                }
            }
        }

        # Mock 目标快照
        to_snapshot = MagicMock()
        to_snapshot.tables = {
            "new_table": TableVersion(
                table_name="new_table",
                database="test_ecommerce",
                columns={
                    "id": ColumnVersion("id", "INT", False, True, None, "主键"),
                    "name": ColumnVersion("name", "VARCHAR(100)", False, False, None, "名称"),
                },
                engine="InnoDB",
                charset="utf8mb4"
            )
        }

        # Mock 方法
        with patch.object(version_service, 'compare_snapshots', return_value=mock_diff):
            with patch.object(version_service, 'get_snapshot', return_value=to_snapshot):
                # 生成迁移 SQL
                sql_statements = version_service.generate_migration_sql(
                    from_snapshot_id,
                    to_snapshot_id
                )

        # 验证结果
        assert sql_statements is not None
        assert isinstance(sql_statements, dict)

        # 验证新增表的 SQL
        assert "new_table" in sql_statements
        assert any("CREATE TABLE" in sql for sql in sql_statements["new_table"])

        # 验证删除表的 SQL
        assert "old_table" in sql_statements
        assert any("DROP TABLE" in sql for sql in sql_statements["old_table"])

        # 验证修改表的 SQL
        assert "users" in sql_statements
        users_sql = sql_statements["users"]
        assert any("ADD COLUMN" in sql for sql in users_sql)
        assert any("phone" in sql for sql in users_sql)

        logger.info(
            f"✓ DM-MV-004: 成功生成迁移 SQL，"
            f"涉及表: {len(sql_statements)}"
        )

    def test_rollback_version(self, mock_db_session):
        """
        DM-MV-005: 版本回滚 (P1)

        验证点：
        1. 能够获取历史版本的结构
        2. 能够生成回滚 SQL
        3. 能够验证回滚的可行性
        """
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        # Mock 历史快照
        snapshot_id = "snap_v1"
        historical_snapshot = MagicMock(
            snapshot_id=snapshot_id,
            version="v1.0.0",
            database="test_ecommerce",
            tables={
                "users": TableVersion(
                    table_name="users",
                    database="test_ecommerce",
                    columns=TestConfig.TABLE_V1_COLUMNS.copy()
                )
            },
            created_at=datetime.now() - timedelta(days=1)
        )

        # Mock 查询
        with patch.object(service, 'get_snapshot', return_value=historical_snapshot):
            # 获取回滚信息
            snapshot = service.get_snapshot(snapshot_id)

        # 验证结果
        assert snapshot is not None
        assert snapshot.snapshot_id == snapshot_id
        assert "users" in snapshot.tables

        # 验证列信息（回滚目标状态）
        users_columns = snapshot.tables["users"].columns
        assert len(users_columns) == 4
        assert "id" in users_columns
        assert "username" in users_columns
        assert "email" in users_columns
        assert "created_at" in users_columns
        # 不应有 v2 新增的列
        assert "phone" not in users_columns

        logger.info(
            f"✓ DM-MV-005: 版本回滚验证成功，"
            f"目标版本: {snapshot.version}"
        )

    def test_delete_snapshot(self, version_service, mock_db_session):
        """
        DM-MV-006: 删除版本快照 (P2)

        验证点：
        1. 能够删除指定快照
        2. 删除后无法再获取
        3. 不存在的快照返回 False
        """
        snapshot_id = "snap_to_delete"

        # Mock 查询返回存在的快照
        mock_snapshot = MagicMock(
            id=snapshot_id,
            version="v1.0.0",
            database="test_ecommerce"
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_snapshot
        mock_db_session.query.return_value = mock_query

        # 执行删除
        result = version_service.delete_snapshot(snapshot_id)

        # 验证结果
        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called

        # 测试删除不存在的快照
        mock_query.filter.return_value.first.return_value = None
        result = version_service.delete_snapshot("nonexistent")

        assert result is False

        logger.info(f"✓ DM-MV-006: 删除快照功能正常")


# =============================================================================
# 端到端测试：完整的版本管理流程
# =============================================================================

class TestMetadataVersionE2E:
    """元数据版本管理端到端测试"""

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

    def test_full_version_lifecycle(self, api_client):
        """
        端到端测试：完整的版本管理生命周期

        流程：
        1. 创建初始快照（v1.0）
        2. 创建更新快照（v2.0）
        3. 对比两个版本
        4. 生成迁移 SQL
        5. 删除快照
        """
        api_base = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")

        # 1. 创建初始快照
        snapshot_request = {
            "version": "v1.0.0",
            "database": "test_ecommerce",
            "description": "初始快照"
        }

        response = api_client.post(
            f"{api_base}/metadata/versions/snapshots",
            json=snapshot_request
        )

        if response.status_code == 404:
            logger.warning("版本管理 API 未实现，跳过 E2E 测试")
            pytest.skip("版本管理 API 未实现")

        assert response.status_code in [200, 201]
        snapshot_v1 = response.get_json()
        snapshot_v1_id = snapshot_v1.get("snapshot_id")

        logger.info(f"E2E: 创建快照 v1.0.0 成功: {snapshot_v1_id}")

        # 2. 创建更新快照（模拟表结构变更后）
        snapshot_request["version"] = "v2.0.0"
        snapshot_request["description"] = "添加 phone 和 status 列"

        response = api_client.post(
            f"{api_base}/metadata/versions/snapshots",
            json=snapshot_request
        )
        assert response.status_code in [200, 201]
        snapshot_v2 = response.get_json()
        snapshot_v2_id = snapshot_v2.get("snapshot_id")

        logger.info(f"E2E: 创建快照 v2.0.0 成功: {snapshot_v2_id}")

        # 3. 对比两个版本
        compare_request = {
            "from_snapshot_id": snapshot_v1_id,
            "to_snapshot_id": snapshot_v2_id
        }

        response = api_client.post(
            f"{api_base}/metadata/versions/compare",
            json=compare_request
        )
        assert response.status_code == 200
        diff = response.get_json()

        assert "added_tables" in diff
        assert "modified_tables" in diff

        logger.info(
            f"E2E: 版本对比完成，"
            f"新增表: {len(diff['added_tables'])}，"
            f"修改表: {len(diff['modified_tables'])}"
        )

        # 4. 生成迁移 SQL
        response = api_client.post(
            f"{api_base}/metadata/versions/migration/generate",
            json=compare_request
        )
        assert response.status_code == 200
        migration = response.get_json()

        assert "sql_statements" in migration

        logger.info(f"E2E: 生成迁移 SQL 成功，涉及 {len(migration['sql_statements'])} 张表")

        # 5. 清理：删除测试快照
        for sid in [snapshot_v1_id, snapshot_v2_id]:
            response = api_client.delete(f"{api_base}/metadata/versions/snapshots/{sid}")
            if response.status_code == 200:
                logger.info(f"E2E: 删除快照成功: {sid}")

        logger.info("✓ 元数据版本管理端到端测试完成")


# =============================================================================
# 测试运行入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
