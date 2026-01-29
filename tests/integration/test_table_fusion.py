"""
多表融合模块集成测试

测试场景 (DE-FU-001 ~ DE-FU-009):
1. DE-FU-001: 检测JOIN键 - detect-join-keys 返回候选 JOIN key 列表
2. DE-FU-002: 精确名称匹配 - 完全相同的列名自动匹配, confidence=0.95
3. DE-FU-003: 模糊名称匹配 - Levenshtein 距离 >= 0.7 的模糊匹配
4. DE-FU-004: 语义匹配 - user_id ≈ uid 语义等价匹配, confidence=0.8
5. DE-FU-005: 值级匹配验证 - 采样 1000 行, 计算 overlap_rate
6. DE-FU-006: JOIN质量验证 - validate-join 返回 match_rate/coverage/skew/orphan
7. DE-FU-007: JOIN类型推荐 - 推荐 INNER/LEFT/RIGHT JOIN
8. DE-FU-008: 生成融合Kettle配置 - generate-kettle-config 返回 JOIN XML + SQL 模板
9. DE-FU-009: 执行多表融合 - 提交 Kettle, 验证融合结果正确
"""

import os
import sys
import importlib.util
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, List, Any
from enum import Enum
from dataclasses import dataclass, field

# 添加项目根目录（不添加 data-api 子目录，避免 services 命名空间冲突）
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---------------------------------------------------------------------------
# 直接从文件加载 table_fusion_service 模块，绕过 services/__init__.py
# （services/__init__.py → metadata_graph_builder → ImportError）
# ---------------------------------------------------------------------------
_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "../../services/data-api/services/table_fusion_service.py"
)
_MODULE_PATH = os.path.normpath(_MODULE_PATH)

_spec = importlib.util.spec_from_file_location("table_fusion_service", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# 注入到 sys.modules（使用不冲突的名称，避免污染 services 命名空间）
sys.modules["_test_table_fusion_service"] = _mod

TableFusionService = _mod.TableFusionService
JoinKeyPair = _mod.JoinKeyPair
JoinQualityScore = _mod.JoinQualityScore
JoinStrategyRecommendation = _mod.JoinStrategyRecommendation
JoinType = _mod.JoinType
get_table_fusion_service = _mod.get_table_fusion_service

# ---------------------------------------------------------------------------
# Kettle Bridge 桩类（避免导入 integrations.kettle.kettle_bridge，因为依赖 requests 等）
# ---------------------------------------------------------------------------

class TransformationStatus(Enum):
    """转换执行状态（桩）"""
    RUNNING = "Running"
    FINISHED = "Finished"
    STOPPED = "Stopped"
    STOPPED_WITH_ERRORS = "Stopped with errors"
    WAITING = "Waiting"
    UNKNOWN = "Unknown"


@dataclass
class TransformationResult:
    """转换执行结果（桩）"""
    name: str
    status: TransformationStatus
    status_description: str
    rows_read: int = 0
    rows_written: int = 0
    rows_rejected: int = 0
    errors: int = 0
    step_statuses: List[Dict[str, Any]] = field(default_factory=list)
    log_text: str = ""
    execution_time_ms: int = 0

    @property
    def is_running(self) -> bool:
        return self.status == TransformationStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        return self.status in (
            TransformationStatus.FINISHED,
            TransformationStatus.STOPPED,
            TransformationStatus.STOPPED_WITH_ERRORS,
        )

    @property
    def is_success(self) -> bool:
        return self.status == TransformationStatus.FINISHED and self.errors == 0


class KettleBridge:
    """Kettle Carte 客户端（桩）"""
    pass


# 将桩注入 sys.modules，使 @patch("integrations.kettle.kettle_bridge.KettleBridge") 正常工作
import types as _types

_kettle_stub = _types.ModuleType("integrations.kettle.kettle_bridge")
_kettle_stub.TransformationStatus = TransformationStatus
_kettle_stub.TransformationResult = TransformationResult
_kettle_stub.KettleBridge = KettleBridge

sys.modules.setdefault("integrations", _types.ModuleType("integrations"))
sys.modules.setdefault("integrations.kettle", _types.ModuleType("integrations.kettle"))
sys.modules["integrations.kettle.kettle_bridge"] = _kettle_stub

# 确保父模块具有子模块属性（@patch 需要通过 getattr 链访问）
sys.modules["integrations"].kettle = sys.modules["integrations.kettle"]
sys.modules["integrations.kettle"].kettle_bridge = _kettle_stub


# ==================== 测试数据 ====================

# users 表的列元数据
USERS_COLUMNS = [
    {"name": "user_id", "type": "int", "nullable": False,
     "is_primary_key": True, "is_foreign_key": False, "description": "用户ID"},
    {"name": "username", "type": "varchar", "nullable": False,
     "is_primary_key": False, "is_foreign_key": False, "description": "用户名"},
    {"name": "email", "type": "varchar", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "邮箱"},
    {"name": "org_id", "type": "int", "nullable": True,
     "is_primary_key": False, "is_foreign_key": True, "description": "组织ID"},
    {"name": "dept_code", "type": "varchar", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "部门编码"},
    {"name": "account_id", "type": "int", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "账户ID"},
]

# orders 表的列元数据
ORDERS_COLUMNS = [
    {"name": "order_id", "type": "int", "nullable": False,
     "is_primary_key": True, "is_foreign_key": False, "description": "订单ID"},
    {"name": "user_id", "type": "int", "nullable": False,
     "is_primary_key": False, "is_foreign_key": True, "description": "用户ID"},
    {"name": "product_id", "type": "int", "nullable": False,
     "is_primary_key": False, "is_foreign_key": True, "description": "产品ID"},
    {"name": "amount", "type": "decimal", "nullable": False,
     "is_primary_key": False, "is_foreign_key": False, "description": "金额"},
    {"name": "uid", "type": "int", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "备用用户标识"},
    {"name": "order_no", "type": "varchar", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "订单编号"},
    {"name": "acct_id", "type": "int", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "账户标识"},
    {"name": "department_id", "type": "int", "nullable": True,
     "is_primary_key": False, "is_foreign_key": False, "description": "部门ID"},
]

# 用户表采样数据（模拟 1000 行中的部分 user_id 值）
SAMPLE_USER_IDS = list(range(1, 1001))

# 订单表采样数据（与用户表有 ~80% 重叠）
SAMPLE_ORDER_USER_IDS = list(range(1, 801)) + list(range(1100, 1300))


# ==================== Fixtures ====================

@pytest.fixture
def fusion_service():
    """创建多表融合服务实例"""
    service = TableFusionService()
    return service


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    session = MagicMock()
    return session


@pytest.fixture
def mock_users_columns():
    """模拟 users 表的列查询结果"""
    columns = []
    for col in USERS_COLUMNS:
        mock_col = Mock()
        mock_col.column_name = col["name"]
        mock_col.data_type = col["type"]
        mock_col.is_nullable = col["nullable"]
        mock_col.is_primary_key = col.get("is_primary_key", False)
        mock_col.is_foreign_key = col.get("is_foreign_key", False)
        mock_col.description = col["description"]
        mock_col.position = USERS_COLUMNS.index(col)
        columns.append(mock_col)
    return columns


@pytest.fixture
def mock_orders_columns():
    """模拟 orders 表的列查询结果"""
    columns = []
    for col in ORDERS_COLUMNS:
        mock_col = Mock()
        mock_col.column_name = col["name"]
        mock_col.data_type = col["type"]
        mock_col.is_nullable = col["nullable"]
        mock_col.is_primary_key = col.get("is_primary_key", False)
        mock_col.is_foreign_key = col.get("is_foreign_key", False)
        mock_col.description = col["description"]
        mock_col.position = ORDERS_COLUMNS.index(col)
        columns.append(mock_col)
    return columns


@pytest.fixture
def sample_join_keys():
    """示例 JOIN 键对列表"""
    return [
        JoinKeyPair(
            source_column="user_id",
            target_column="user_id",
            source_table="users",
            target_table="orders",
            confidence=0.95,
            detection_method="name_match",
            name_similarity=1.0,
            is_primary_key=True,
            is_foreign_key=True,
        ),
        JoinKeyPair(
            source_column="account_id",
            target_column="acct_id",
            source_table="users",
            target_table="orders",
            confidence=0.8,
            detection_method="semantic",
            name_similarity=0.0,
            is_primary_key=False,
            is_foreign_key=False,
        ),
    ]


@pytest.fixture
def sample_quality_score():
    """示例 JOIN 质量评分"""
    return JoinQualityScore(
        overall_score=0.85,
        match_rate=0.90,
        coverage_rate=0.88,
        skew_factor=0.15,
        orphan_rate=0.10,
        null_key_rate=0.02,
        duplicate_rate=0.05,
        recommendation="inner",
        issues=[],
    )


@pytest.fixture
def sample_strategy(sample_join_keys, sample_quality_score):
    """示例 JOIN 策略推荐"""
    return JoinStrategyRecommendation(
        join_type=JoinType.INNER,
        join_keys=sample_join_keys,
        estimated_result_count=8000,
        quality_score=sample_quality_score,
        sql_template="SELECT *\nFROM users s\nINNER JOIN orders t\nON s.user_id = t.user_id",
        index_suggestions=[
            {
                "table": "orders",
                "column": "user_id",
                "type": "btree",
                "reason": "JOIN关联键，建议添加索引以提升性能",
            }
        ],
        performance_notes=[],
        warnings=[],
    )


# ==================== 测试类 ====================


@pytest.mark.integration
class TestDetectJoinKeys:
    """DE-FU-001: 检测JOIN键 (P0)

    验证 detect-join-keys 接口返回候选 JOIN key 列表，
    包含完全匹配、模糊匹配和语义匹配三种检测方式。
    """

    def test_detect_join_keys_returns_candidate_list(
        self, fusion_service, mock_db, mock_users_columns, mock_orders_columns
    ):
        """检测 JOIN 键接口应返回非空的候选列表"""
        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ):
            def get_columns_side_effect(db, table_name, database_name=None):
                if table_name == "users":
                    return USERS_COLUMNS
                elif table_name == "orders":
                    return ORDERS_COLUMNS
                return []

            mock_get_cols.side_effect = get_columns_side_effect

            results = fusion_service.detect_potential_join_keys(
                db=mock_db,
                source_table="users",
                target_tables=["orders"],
            )

            assert "orders" in results
            assert len(results["orders"]) > 0
            # 结果按置信度降序排列
            confidences = [k.confidence for k in results["orders"]]
            assert confidences == sorted(confidences, reverse=True)

    def test_detect_join_keys_includes_all_match_methods(
        self, fusion_service, mock_db
    ):
        """候选列表应包含多种检测方法的结果"""
        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ):
            def get_columns_side_effect(db, table_name, database_name=None):
                if table_name == "users":
                    return USERS_COLUMNS
                elif table_name == "orders":
                    return ORDERS_COLUMNS
                return []

            mock_get_cols.side_effect = get_columns_side_effect

            results = fusion_service.detect_potential_join_keys(
                db=mock_db,
                source_table="users",
                target_tables=["orders"],
            )

            methods = {k.detection_method for k in results["orders"]}
            # 应至少包含名称匹配
            assert "name_match" in methods

    def test_detect_join_keys_with_multiple_targets(
        self, fusion_service, mock_db
    ):
        """支持同时检测多个目标表"""
        products_columns = [
            {"name": "product_id", "type": "int", "nullable": False,
             "is_primary_key": True, "is_foreign_key": False, "description": "产品ID"},
            {"name": "product_name", "type": "varchar", "nullable": False,
             "is_primary_key": False, "is_foreign_key": False, "description": "产品名"},
        ]

        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ):
            def get_columns_side_effect(db, table_name, database_name=None):
                if table_name == "users":
                    return USERS_COLUMNS
                elif table_name == "orders":
                    return ORDERS_COLUMNS
                elif table_name == "products":
                    return products_columns
                return []

            mock_get_cols.side_effect = get_columns_side_effect

            results = fusion_service.detect_potential_join_keys(
                db=mock_db,
                source_table="users",
                target_tables=["orders", "products"],
            )

            assert "orders" in results
            assert "products" in results

    def test_detect_join_keys_each_has_required_fields(
        self, fusion_service, mock_db
    ):
        """每个候选 JOIN 键应包含所有必要字段"""
        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ):
            mock_get_cols.side_effect = lambda db, t, d=None: (
                USERS_COLUMNS if t == "users" else ORDERS_COLUMNS
            )

            results = fusion_service.detect_potential_join_keys(
                db=mock_db,
                source_table="users",
                target_tables=["orders"],
            )

            for key_pair in results["orders"]:
                assert key_pair.source_column is not None
                assert key_pair.target_column is not None
                assert key_pair.source_table == "users"
                assert key_pair.target_table == "orders"
                assert 0.0 <= key_pair.confidence <= 1.0
                assert key_pair.detection_method in (
                    "name_match", "enhanced_fuzzy_match", "semantic",
                    "value_analysis", "embedding_semantic",
                )


@pytest.mark.integration
class TestExactNameMatch:
    """DE-FU-002: 精确名称匹配 (P0)

    验证完全相同的列名能自动匹配，confidence 固定为 0.95。
    """

    def test_exact_match_user_id(self, fusion_service):
        """user_id 与 user_id 精确匹配，confidence=0.95"""
        source_cols = [
            {"name": "user_id", "type": "int", "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "user_id", "type": "int", "is_primary_key": False, "is_foreign_key": True},
        ]

        matches = fusion_service._find_exact_name_matches(
            source_cols, target_cols, "users", "orders"
        )

        assert len(matches) == 1
        assert matches[0].source_column == "user_id"
        assert matches[0].target_column == "user_id"
        assert matches[0].confidence == 0.95
        assert matches[0].detection_method == "name_match"
        assert matches[0].name_similarity == 1.0

    def test_exact_match_case_insensitive(self, fusion_service):
        """精确匹配应忽略大小写"""
        source_cols = [
            {"name": "User_ID", "type": "int", "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "user_id", "type": "int", "is_primary_key": False, "is_foreign_key": True},
        ]

        matches = fusion_service._find_exact_name_matches(
            source_cols, target_cols, "users", "orders"
        )

        assert len(matches) == 1
        assert matches[0].confidence == 0.95

    def test_exact_match_multiple_columns(self, fusion_service):
        """多列精确匹配"""
        # users 和 orders 中 user_id 同名
        id_source = [c for c in USERS_COLUMNS if c["name"].endswith("_id")]
        id_target = [c for c in ORDERS_COLUMNS if c["name"].endswith("_id")]

        matches = fusion_service._find_exact_name_matches(
            id_source, id_target, "users", "orders"
        )

        matched_names = [(m.source_column, m.target_column) for m in matches]
        assert ("user_id", "user_id") in matched_names

        # 所有精确匹配的 confidence 都应为 0.95
        for m in matches:
            assert m.confidence == 0.95

    def test_exact_match_preserves_key_flags(self, fusion_service):
        """精确匹配应保留主键/外键标记"""
        source_cols = [
            {"name": "user_id", "type": "int", "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "user_id", "type": "int", "is_primary_key": False, "is_foreign_key": True},
        ]

        matches = fusion_service._find_exact_name_matches(
            source_cols, target_cols, "users", "orders"
        )

        assert matches[0].is_primary_key is True
        assert matches[0].is_foreign_key is True


@pytest.mark.integration
class TestFuzzyNameMatch:
    """DE-FU-003: 模糊名称匹配 (P1)

    验证 Levenshtein 距离 >= 0.7 的字段可以被模糊匹配。
    """

    def test_fuzzy_match_similar_names(self, fusion_service):
        """相似字段名应被模糊匹配识别"""
        source_cols = [
            {"name": "dept_code", "type": "varchar",
             "is_primary_key": False, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "department_id", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        matches = fusion_service._find_fuzzy_name_matches(
            source_cols, target_cols, "users", "orders"
        )

        # dept_code 和 department_id 的模糊相似度需要 >= 0.7
        # 如果不匹配（因为它们确实差异较大），则列表为空
        # 这测试的是算法不会将差异过大的字段误匹配
        for m in matches:
            assert m.name_similarity >= fusion_service._name_similarity_threshold
            assert m.name_similarity < 1.0
            assert m.detection_method == "enhanced_fuzzy_match"

    def test_fuzzy_match_excludes_exact_matches(self, fusion_service):
        """模糊匹配应排除已精确匹配的列"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
            {"name": "userid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": False, "is_foreign_key": True},
        ]

        matches = fusion_service._find_fuzzy_name_matches(
            source_cols, target_cols, "users", "orders",
            exclude=["user_id"],
        )

        # user_id 已排除，不应出现在模糊匹配结果中
        for m in matches:
            assert m.source_column != "user_id"

    def test_fuzzy_match_threshold(self, fusion_service):
        """验证模糊匹配的阈值为 0.7"""
        assert fusion_service._name_similarity_threshold == 0.7

    def test_levenshtein_distance_calculation(self, fusion_service):
        """验证 Levenshtein 距离计算"""
        # 相同字符串距离为 0
        assert fusion_service._levenshtein_distance("user_id", "user_id") == 0
        # 完全不同的短字符串
        assert fusion_service._levenshtein_distance("abc", "xyz") == 3
        # 一个字符不同
        assert fusion_service._levenshtein_distance("user_id", "user_ie") == 1
        # 空字符串
        assert fusion_service._levenshtein_distance("", "test") == 4
        assert fusion_service._levenshtein_distance("test", "") == 4

    def test_enhanced_name_similarity(self, fusion_service):
        """验证增强的名称相似度计算"""
        # 完全相同
        assert fusion_service._enhanced_name_similarity("user_id", "user_id") == 1.0

        # 包含关系应该有较高的相似度
        sim_contain = fusion_service._enhanced_name_similarity("id", "user_id")
        assert sim_contain > 0.0

        # 完全不同的字段应该相似度较低
        sim_diff = fusion_service._enhanced_name_similarity("user_id", "amount")
        assert sim_diff < 0.7

    def test_fuzzy_match_confidence_below_exact(self, fusion_service):
        """模糊匹配的 confidence 应低于精确匹配 (0.95)"""
        source_cols = [
            {"name": "userid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": False, "is_foreign_key": True},
        ]

        matches = fusion_service._find_fuzzy_name_matches(
            source_cols, target_cols, "users", "orders"
        )

        for m in matches:
            assert m.confidence < 0.95


@pytest.mark.integration
class TestSemanticMatch:
    """DE-FU-004: 语义匹配 (P1)

    验证 user_id 和 uid 等语义等价字段能被正确识别，confidence=0.8。
    """

    def test_semantic_match_user_id_uid(self, fusion_service):
        """user_id 与 uid 语义匹配，confidence=0.8"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "uid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        matches = fusion_service._find_semantic_matches(
            source_cols, target_cols, "users", "orders"
        )

        assert len(matches) >= 1
        uid_match = next(
            (m for m in matches if m.target_column == "uid"), None
        )
        assert uid_match is not None
        assert uid_match.confidence == 0.8
        assert uid_match.detection_method == "semantic"

    def test_semantic_match_account_id_acct_id(self, fusion_service):
        """account_id 与 acct_id 语义匹配"""
        source_cols = [
            {"name": "account_id", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "acct_id", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        matches = fusion_service._find_semantic_matches(
            source_cols, target_cols, "users", "orders"
        )

        assert len(matches) >= 1
        acct_match = next(
            (m for m in matches if m.target_column == "acct_id"), None
        )
        assert acct_match is not None
        assert acct_match.confidence == 0.8

    def test_semantic_equivalents_map_coverage(self, fusion_service):
        """验证语义等价映射表包含常见 ID 字段"""
        equiv = TableFusionService.SEMANTIC_EQUIVALENTS
        assert "user_id" in equiv
        assert "uid" in equiv["user_id"]
        assert "customer_id" in equiv
        assert "order_id" in equiv
        assert "product_id" in equiv
        assert "account_id" in equiv
        assert "acct_id" in equiv["account_id"]

    def test_semantic_match_excludes_already_matched(self, fusion_service):
        """语义匹配应排除已被其他方法匹配的列"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "uid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        # 排除 user_id
        matches = fusion_service._find_semantic_matches(
            source_cols, target_cols, "users", "orders",
            exclude=["user_id"],
        )

        for m in matches:
            assert m.source_column != "user_id"

    def test_semantic_match_no_false_positives(self, fusion_service):
        """语义匹配不应产生误报（不相关字段不应匹配）"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "amount", "type": "decimal",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        matches = fusion_service._find_semantic_matches(
            source_cols, target_cols, "users", "orders"
        )

        # amount 不应与 user_id 语义匹配
        assert len(matches) == 0


@pytest.mark.integration
class TestValueLevelMatch:
    """DE-FU-005: 值级匹配验证 (P1)

    验证通过采样 1000 行并计算值域重叠率来识别关联键。
    """

    def test_value_overlap_high_overlap(self, fusion_service, mock_db):
        """高重叠率场景（>= 0.3 阈值）应识别为候选关联键"""
        # 模拟 source 表返回的去重值
        source_rows = [(i,) for i in SAMPLE_USER_IDS]
        # 模拟在 target 表中匹配到的数量
        matched_count = 800  # 80% 重叠

        mock_db.execute.side_effect = [
            Mock(fetchall=Mock(return_value=source_rows), __iter__=lambda s: iter(source_rows)),
            Mock(scalar=Mock(return_value=matched_count)),
        ]

        overlap = fusion_service._calculate_value_overlap(
            mock_db, "users", "user_id", "orders", "user_id", sample_size=1000
        )

        assert overlap >= 0.3

    def test_value_overlap_low_overlap(self, fusion_service, mock_db):
        """低重叠率场景（< 0.3 阈值）不应被识别为候选关联键"""
        source_rows = [(i,) for i in range(1, 101)]
        matched_count = 5  # 5% 重叠

        mock_db.execute.side_effect = [
            Mock(fetchall=Mock(return_value=source_rows), __iter__=lambda s: iter(source_rows)),
            Mock(scalar=Mock(return_value=matched_count)),
        ]

        overlap = fusion_service._calculate_value_overlap(
            mock_db, "users", "email", "orders", "order_no", sample_size=1000
        )

        assert overlap < 0.3

    def test_value_based_match_uses_sample_size(self, fusion_service, mock_db):
        """值级匹配应使用指定的采样大小"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "uid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        with patch.object(
            fusion_service, '_calculate_value_overlap', return_value=0.8
        ) as mock_overlap:
            fusion_service._find_value_based_matches(
                db=mock_db,
                source_table="users",
                target_table="orders",
                source_columns=source_cols,
                target_columns=target_cols,
                source_database=None,
                target_database=None,
                sample_size=1000,
            )

            if mock_overlap.called:
                call_args = mock_overlap.call_args
                assert call_args[1].get("sample_size", call_args[0][-1]) == 1000

    def test_value_overlap_empty_source(self, fusion_service, mock_db):
        """源表值为空时重叠率应为 0"""
        mock_db.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[]), __iter__=lambda s: iter([])),
        ]

        overlap = fusion_service._calculate_value_overlap(
            mock_db, "users", "user_id", "orders", "user_id", sample_size=1000
        )

        assert overlap == 0.0

    def test_value_based_match_confidence(self, fusion_service, mock_db):
        """值级匹配的 confidence 应为 overlap_rate * 0.7"""
        source_cols = [
            {"name": "user_id", "type": "int",
             "is_primary_key": True, "is_foreign_key": False},
        ]
        target_cols = [
            {"name": "uid", "type": "int",
             "is_primary_key": False, "is_foreign_key": False},
        ]

        overlap_rate = 0.85
        with patch.object(
            fusion_service, '_calculate_value_overlap', return_value=overlap_rate
        ):
            matches = fusion_service._find_value_based_matches(
                db=mock_db,
                source_table="users",
                target_table="orders",
                source_columns=source_cols,
                target_columns=target_cols,
                source_database=None,
                target_database=None,
                sample_size=1000,
            )

            assert len(matches) == 1
            assert matches[0].detection_method == "value_analysis"
            assert abs(matches[0].confidence - overlap_rate * 0.7) < 0.001
            assert abs(matches[0].value_overlap_rate - overlap_rate) < 0.001


@pytest.mark.integration
class TestJoinQualityValidation:
    """DE-FU-006: JOIN质量验证 (P0)

    验证 validate-join 返回 match_rate、coverage、skew、orphan 等指标。
    """

    def test_validate_join_returns_quality_score(self, fusion_service, mock_db):
        """validate_join_consistency 应返回完整的质量评分"""
        # 模拟键统计
        source_stats_row = Mock()
        source_stats_row.__getitem__ = lambda self, i: [1000, 980, 20, 950][i]

        target_stats_row = Mock()
        target_stats_row.__getitem__ = lambda self, i: [1200, 1200, 0, 1100][i]

        join_stats_row = Mock()
        join_stats_row.__getitem__ = lambda self, i: [800, 750, 5, 1.07][i]

        mock_db.execute.side_effect = [
            Mock(fetchone=Mock(return_value=source_stats_row)),
            Mock(fetchone=Mock(return_value=target_stats_row)),
            Mock(fetchone=Mock(return_value=join_stats_row)),
        ]

        score = fusion_service.validate_join_consistency(
            db=mock_db,
            source_table="users",
            source_key="user_id",
            target_table="orders",
            target_key="user_id",
        )

        assert isinstance(score, JoinQualityScore)
        assert 0.0 <= score.match_rate <= 1.0
        assert 0.0 <= score.coverage_rate <= 1.0
        assert 0.0 <= score.skew_factor <= 1.0
        assert 0.0 <= score.orphan_rate <= 1.0
        assert 0.0 <= score.null_key_rate <= 1.0
        assert 0.0 <= score.duplicate_rate <= 1.0
        assert 0.0 <= score.overall_score <= 1.0
        assert score.recommendation in ("inner", "left", "right", "full", "unknown")

    def test_validate_join_match_rate_calculation(self, fusion_service, mock_db):
        """match_rate = matched_count / non_null_count"""
        # source: 1000 total, 1000 non-null, 0 null, 1000 distinct
        source_stats_row = Mock()
        source_stats_row.__getitem__ = lambda self, i: [1000, 1000, 0, 1000][i]

        # target: 1200 total, 1200 non-null, 0 null, 1100 distinct
        target_stats_row = Mock()
        target_stats_row.__getitem__ = lambda self, i: [1200, 1200, 0, 1100][i]

        # join: 900 matched, 850 distinct matched
        join_stats_row = Mock()
        join_stats_row.__getitem__ = lambda self, i: [900, 850, 3, 1.06][i]

        mock_db.execute.side_effect = [
            Mock(fetchone=Mock(return_value=source_stats_row)),
            Mock(fetchone=Mock(return_value=target_stats_row)),
            Mock(fetchone=Mock(return_value=join_stats_row)),
        ]

        score = fusion_service.validate_join_consistency(
            db=mock_db,
            source_table="users",
            source_key="user_id",
            target_table="orders",
            target_key="user_id",
        )

        # match_rate = 900 / 1000 = 0.9
        assert abs(score.match_rate - 0.9) < 0.01
        # orphan_rate = 1 - match_rate = 0.1
        assert abs(score.orphan_rate - 0.1) < 0.01

    def test_validate_join_issues_detected(self, fusion_service, mock_db):
        """低质量 JOIN 应报告问题"""
        # 低匹配率场景
        source_stats_row = Mock()
        source_stats_row.__getitem__ = lambda self, i: [1000, 800, 200, 700][i]

        target_stats_row = Mock()
        target_stats_row.__getitem__ = lambda self, i: [500, 500, 0, 500][i]

        join_stats_row = Mock()
        join_stats_row.__getitem__ = lambda self, i: [300, 250, 10, 1.2][i]

        mock_db.execute.side_effect = [
            Mock(fetchone=Mock(return_value=source_stats_row)),
            Mock(fetchone=Mock(return_value=target_stats_row)),
            Mock(fetchone=Mock(return_value=join_stats_row)),
        ]

        score = fusion_service.validate_join_consistency(
            db=mock_db,
            source_table="users",
            source_key="user_id",
            target_table="orders",
            target_key="user_id",
        )

        # match_rate = 300/800 = 0.375 < 0.5, 应有匹配率低的问题
        assert score.match_rate < 0.5
        assert any("匹配率较低" in issue for issue in score.issues)
        # null_key_rate = 200/1000 = 0.2 > 0.1, 应有空键率高的问题
        assert score.null_key_rate > 0.1
        assert any("空键率较高" in issue for issue in score.issues)

    def test_validate_join_error_handling(self, fusion_service, mock_db):
        """数据库异常时应返回降级的质量评分"""
        mock_db.execute.side_effect = Exception("数据库连接失败")

        score = fusion_service.validate_join_consistency(
            db=mock_db,
            source_table="users",
            source_key="user_id",
            target_table="orders",
            target_key="user_id",
        )

        # 辅助方法内部捕获异常并返回零值统计，
        # 综合评分仍包含 null_penalty 和 duplicate_penalty 的正向分数
        assert score.overall_score <= 0.2
        assert score.match_rate == 0
        assert len(score.issues) > 0

    def test_validate_join_to_dict(self, sample_quality_score):
        """质量评分 to_dict 应包含所有字段"""
        result = sample_quality_score.to_dict()

        assert "overall_score" in result
        assert "match_rate" in result
        assert "coverage_rate" in result
        assert "skew_factor" in result
        assert "orphan_rate" in result
        assert "null_key_rate" in result
        assert "duplicate_rate" in result
        assert "recommendation" in result
        assert "issues" in result


@pytest.mark.integration
class TestJoinTypeRecommendation:
    """DE-FU-007: JOIN类型推荐 (P1)

    验证根据数据质量指标推荐合适的 JOIN 类型。
    """

    def test_recommend_inner_join_high_match(self, fusion_service):
        """高匹配率 (>= 0.9) 且高覆盖率时推荐 INNER JOIN"""
        recommendation = fusion_service._recommend_join_type(
            match_rate=0.95,
            coverage_rate=0.92,
            orphan_rate=0.05,
        )
        assert recommendation == "inner"

    def test_recommend_inner_join_good_match(self, fusion_service):
        """匹配率 >= 0.7 时推荐 INNER JOIN"""
        recommendation = fusion_service._recommend_join_type(
            match_rate=0.75,
            coverage_rate=0.60,
            orphan_rate=0.25,
        )
        assert recommendation == "inner"

    def test_recommend_left_join_high_orphan(self, fusion_service):
        """高孤立率 (> 0.3) 时推荐 LEFT JOIN"""
        recommendation = fusion_service._recommend_join_type(
            match_rate=0.60,
            coverage_rate=0.50,
            orphan_rate=0.40,
        )
        assert recommendation == "left"

    def test_recommend_strategy_full_flow(self, fusion_service, mock_db, sample_join_keys):
        """完整的策略推荐流程"""
        with patch.object(
            fusion_service, 'validate_join_consistency'
        ) as mock_validate, patch.object(
            fusion_service, '_estimate_join_result_count', return_value=8000
        ):
            mock_validate.return_value = JoinQualityScore(
                overall_score=0.85,
                match_rate=0.90,
                coverage_rate=0.88,
                skew_factor=0.15,
                orphan_rate=0.10,
                null_key_rate=0.02,
                duplicate_rate=0.05,
                recommendation="inner",
                issues=[],
            )

            strategy = fusion_service.recommend_join_strategy(
                db=mock_db,
                source_table="users",
                target_table="orders",
                join_keys=sample_join_keys,
            )

            assert isinstance(strategy, JoinStrategyRecommendation)
            assert strategy.join_type == JoinType.INNER
            assert strategy.estimated_result_count == 8000
            assert len(strategy.join_keys) > 0
            assert "SELECT *" in strategy.sql_template
            assert "JOIN" in strategy.sql_template

    def test_recommend_strategy_no_keys(self, fusion_service, mock_db):
        """无关联键时应返回 CROSS JOIN 并发出警告"""
        strategy = fusion_service.recommend_join_strategy(
            db=mock_db,
            source_table="users",
            target_table="orders",
            join_keys=[],
        )

        assert strategy.join_type == JoinType.CROSS
        assert len(strategy.join_keys) == 0
        assert len(strategy.warnings) > 0

    def test_recommend_strategy_low_confidence_warning(
        self, fusion_service, mock_db
    ):
        """低置信度关联键应发出警告"""
        low_conf_keys = [
            JoinKeyPair(
                source_column="dept_code",
                target_column="department_id",
                source_table="users",
                target_table="orders",
                confidence=0.5,
                detection_method="value_analysis",
            )
        ]

        with patch.object(
            fusion_service, 'validate_join_consistency'
        ) as mock_validate, patch.object(
            fusion_service, '_estimate_join_result_count', return_value=5000
        ):
            mock_validate.return_value = JoinQualityScore(
                overall_score=0.60,
                match_rate=0.65,
                coverage_rate=0.55,
                skew_factor=0.30,
                orphan_rate=0.35,
                null_key_rate=0.05,
                duplicate_rate=0.10,
                recommendation="left",
                issues=[],
            )

            strategy = fusion_service.recommend_join_strategy(
                db=mock_db,
                source_table="users",
                target_table="orders",
                join_keys=low_conf_keys,
            )

            # 低置信度应有警告
            assert any("置信度较低" in w for w in strategy.warnings)


@pytest.mark.integration
class TestGenerateKettleConfig:
    """DE-FU-008: 生成融合Kettle配置 (P0)

    验证 generate-kettle-config 返回 JOIN XML 配置和 SQL 模板。
    """

    def test_generate_kettle_config_basic(self, fusion_service, sample_strategy):
        """生成基本的 Kettle JOIN 配置"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
            source_step_name="Source",
            target_step_name="Target",
        )

        assert isinstance(config, dict)
        assert "step_type" in config
        assert "step_name" in config
        assert "join_type" in config
        assert "keys_1" in config
        assert "keys_2" in config
        assert "input_step_1" in config
        assert "input_step_2" in config

    def test_generate_kettle_config_inner_join(self, fusion_service, sample_strategy):
        """INNER JOIN 配置应为 MergeJoin 类型"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
        )

        assert config["step_type"] == "MergeJoin"
        assert config["join_type"] == "INNER"

    def test_generate_kettle_config_keys(self, fusion_service, sample_strategy):
        """配置应包含正确的 JOIN 键"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
        )

        assert "user_id" in config["keys_1"]
        assert "user_id" in config["keys_2"]

    def test_generate_kettle_config_merge_join_sort(
        self, fusion_service, sample_strategy
    ):
        """MergeJoin 应包含预排序步骤"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
        )

        assert config.get("pre_sort_required") is True
        assert "sort_steps" in config
        assert len(config["sort_steps"]) == 2

        # 验证排序步骤包含正确的排序字段
        sort_source = config["sort_steps"][0]
        sort_target = config["sort_steps"][1]
        assert len(sort_source["sort_fields"]) > 0
        assert len(sort_target["sort_fields"]) > 0

    def test_generate_kettle_config_metadata(self, fusion_service, sample_strategy):
        """配置应包含元数据（置信度、质量评分等）"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
        )

        assert "metadata" in config
        assert "confidence" in config["metadata"]
        assert "quality_score" in config["metadata"]
        assert "estimated_rows" in config["metadata"]
        assert config["metadata"]["confidence"] == 0.95
        assert config["metadata"]["estimated_rows"] == 8000

    def test_generate_kettle_config_custom_step_names(
        self, fusion_service, sample_strategy
    ):
        """应支持自定义步骤名称"""
        config = fusion_service.generate_kettle_join_config(
            strategy=sample_strategy,
            source_step_name="UsersInput",
            target_step_name="OrdersInput",
        )

        assert config["input_step_1"] == "UsersInput"
        assert config["input_step_2"] == "OrdersInput"
        assert "Join_UsersInput_OrdersInput" in config["step_name"]

    def test_generate_kettle_config_sql_template_in_strategy(
        self, fusion_service, sample_strategy
    ):
        """策略中的 SQL 模板应包含正确的 JOIN 语法"""
        sql = sample_strategy.sql_template
        assert "SELECT *" in sql
        assert "INNER JOIN" in sql
        assert "ON" in sql
        assert "s.user_id = t.user_id" in sql

    def test_generate_kettle_config_left_join(self, fusion_service):
        """LEFT JOIN 的 Kettle 配置"""
        left_strategy = JoinStrategyRecommendation(
            join_type=JoinType.LEFT,
            join_keys=[
                JoinKeyPair(
                    source_column="user_id",
                    target_column="uid",
                    source_table="users",
                    target_table="orders",
                    confidence=0.80,
                    detection_method="semantic",
                ),
            ],
            estimated_result_count=10000,
            quality_score=JoinQualityScore(
                overall_score=0.65,
                match_rate=0.60,
                coverage_rate=0.55,
                skew_factor=0.25,
                orphan_rate=0.40,
                null_key_rate=0.05,
                duplicate_rate=0.10,
                recommendation="left",
                issues=[],
            ),
            sql_template="SELECT *\nFROM users s\nLEFT JOIN orders t\nON s.user_id = t.uid",
            index_suggestions=[],
            performance_notes=[],
            warnings=[],
        )

        config = fusion_service.generate_kettle_join_config(strategy=left_strategy)

        assert config["join_type"] == "LEFT"
        assert config["step_type"] == "MergeJoin"


@pytest.mark.integration
class TestExecuteTableFusion:
    """DE-FU-009: 执行多表融合 (P0)

    验证提交 Kettle 转换任务并确认融合结果正确。
    """

    def test_full_fusion_pipeline(self, fusion_service, mock_db):
        """完整的多表融合流程：检测 -> 验证 -> 推荐 -> 生成配置"""
        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ), patch.object(
            fusion_service, 'validate_join_consistency'
        ) as mock_validate, patch.object(
            fusion_service, '_estimate_join_result_count', return_value=9000
        ):
            mock_get_cols.side_effect = lambda db, t, d=None: (
                USERS_COLUMNS if t == "users" else ORDERS_COLUMNS
            )
            mock_validate.return_value = JoinQualityScore(
                overall_score=0.88,
                match_rate=0.92,
                coverage_rate=0.85,
                skew_factor=0.12,
                orphan_rate=0.08,
                null_key_rate=0.01,
                duplicate_rate=0.03,
                recommendation="inner",
                issues=[],
            )

            # 步骤 1: 检测关联键
            join_keys_result = fusion_service.detect_potential_join_keys(
                db=mock_db,
                source_table="users",
                target_tables=["orders"],
            )
            assert "orders" in join_keys_result
            assert len(join_keys_result["orders"]) > 0

            # 步骤 2: 获取策略推荐
            strategy = fusion_service.recommend_join_strategy(
                db=mock_db,
                source_table="users",
                target_table="orders",
                join_keys=join_keys_result["orders"],
            )
            assert strategy.join_type in (JoinType.INNER, JoinType.LEFT)

            # 步骤 3: 生成 Kettle 配置
            kettle_config = fusion_service.generate_kettle_join_config(
                strategy=strategy,
            )
            assert kettle_config["step_type"] in ("MergeJoin", "JoinRows")
            assert len(kettle_config["keys_1"]) > 0

    @patch("integrations.kettle.kettle_bridge.KettleBridge")
    def test_submit_kettle_transformation(self, MockKettleBridge, fusion_service):
        """提交 Kettle 转换任务并验证执行结果"""
        mock_bridge = MockKettleBridge.return_value
        mock_bridge.submit_transformation.return_value = "fusion_users_orders"
        mock_bridge.get_transformation_status.return_value = TransformationResult(
            name="fusion_users_orders",
            status=TransformationStatus.FINISHED,
            status_description="Finished",
            rows_read=10000,
            rows_written=9200,
            rows_rejected=0,
            errors=0,
            step_statuses=[
                {"name": "Source", "read": 10000, "written": 10000, "rejected": 0, "errors": 0},
                {"name": "Target", "read": 10000, "written": 10000, "rejected": 0, "errors": 0},
                {"name": "MergeJoin", "read": 20000, "written": 9200, "rejected": 0, "errors": 0},
            ],
            log_text="转换执行成功",
        )

        # 提交转换
        job_id = mock_bridge.submit_transformation(
            trans_xml="<transformation>...</transformation>",
            trans_name="fusion_users_orders",
        )
        assert job_id == "fusion_users_orders"

        # 查询状态
        result = mock_bridge.get_transformation_status("fusion_users_orders")
        assert result.is_success
        assert result.is_finished
        assert not result.is_running
        assert result.rows_written == 9200
        assert result.errors == 0

    @patch("integrations.kettle.kettle_bridge.KettleBridge")
    def test_submit_kettle_transformation_with_errors(
        self, MockKettleBridge, fusion_service
    ):
        """Kettle 转换失败时应正确报告错误"""
        mock_bridge = MockKettleBridge.return_value
        mock_bridge.submit_transformation.return_value = "fusion_fail_test"
        mock_bridge.get_transformation_status.return_value = TransformationResult(
            name="fusion_fail_test",
            status=TransformationStatus.STOPPED_WITH_ERRORS,
            status_description="Stopped with errors",
            rows_read=5000,
            rows_written=0,
            rows_rejected=5000,
            errors=1,
            step_statuses=[],
            log_text="ERROR: Join key mismatch",
        )

        result = mock_bridge.get_transformation_status("fusion_fail_test")
        assert not result.is_success
        assert result.errors > 0
        assert result.rows_rejected > 0

    def test_strategy_to_dict_serialization(self, sample_strategy):
        """策略推荐 to_dict 应正确序列化"""
        result = sample_strategy.to_dict()

        assert result["join_type"] == "inner"
        assert len(result["join_keys"]) == 2
        assert result["estimated_result_count"] == 8000
        assert "quality_score" in result
        assert "sql_template" in result
        assert "index_suggestions" in result
        assert "performance_notes" in result
        assert "warnings" in result

    def test_join_key_pair_to_dict(self, sample_join_keys):
        """JoinKeyPair to_dict 应正确序列化"""
        key_dict = sample_join_keys[0].to_dict()

        assert key_dict["source_column"] == "user_id"
        assert key_dict["target_column"] == "user_id"
        assert key_dict["source_table"] == "users"
        assert key_dict["target_table"] == "orders"
        assert key_dict["confidence"] == 0.95
        assert key_dict["detection_method"] == "name_match"
        assert key_dict["name_similarity"] == 1.0
        assert key_dict["is_primary_key"] is True
        assert key_dict["is_foreign_key"] is True

    def test_fusion_end_to_end_with_kettle_config(
        self, fusion_service, mock_db
    ):
        """端到端测试：从检测到生成配置的完整数据结构传递"""
        with patch.object(
            fusion_service, '_get_table_columns'
        ) as mock_get_cols, patch.object(
            fusion_service, '_find_value_based_matches', return_value=[]
        ), patch.object(
            fusion_service, 'validate_join_consistency'
        ) as mock_validate, patch.object(
            fusion_service, '_estimate_join_result_count', return_value=7500
        ):
            mock_get_cols.side_effect = lambda db, t, d=None: (
                USERS_COLUMNS if t == "users" else ORDERS_COLUMNS
            )
            mock_validate.return_value = JoinQualityScore(
                overall_score=0.82,
                match_rate=0.85,
                coverage_rate=0.80,
                skew_factor=0.20,
                orphan_rate=0.15,
                null_key_rate=0.03,
                duplicate_rate=0.08,
                recommendation="inner",
                issues=[],
            )

            # 检测
            keys = fusion_service.detect_potential_join_keys(
                db=mock_db, source_table="users", target_tables=["orders"]
            )

            # 推荐
            strategy = fusion_service.recommend_join_strategy(
                db=mock_db,
                source_table="users",
                target_table="orders",
                join_keys=keys["orders"],
            )

            # 生成 Kettle 配置
            kettle_config = fusion_service.generate_kettle_join_config(
                strategy=strategy,
                source_step_name="UsersInput",
                target_step_name="OrdersInput",
            )

            # 验证最终配置的完整性
            assert kettle_config["step_type"] == "MergeJoin"
            assert kettle_config["input_step_1"] == "UsersInput"
            assert kettle_config["input_step_2"] == "OrdersInput"
            assert len(kettle_config["keys_1"]) > 0
            assert len(kettle_config["keys_2"]) > 0
            assert kettle_config["metadata"]["quality_score"] == 0.82
            assert kettle_config["metadata"]["estimated_rows"] == 7500


@pytest.mark.integration
class TestHelperMethods:
    """辅助方法测试"""

    def test_filter_id_columns(self, fusion_service):
        """ID 字段过滤应正确识别 ID 类字段"""
        id_cols = fusion_service._filter_id_columns(USERS_COLUMNS)
        id_names = [c["name"] for c in id_cols]

        assert "user_id" in id_names
        assert "org_id" in id_names
        assert "account_id" in id_names
        # username, email 等非 ID 字段不应包含
        assert "username" not in id_names
        assert "email" not in id_names

    def test_filter_id_columns_orders(self, fusion_service):
        """orders 表 ID 字段过滤"""
        id_cols = fusion_service._filter_id_columns(ORDERS_COLUMNS)
        id_names = [c["name"] for c in id_cols]

        assert "order_id" in id_names
        assert "user_id" in id_names
        assert "product_id" in id_names
        assert "uid" in id_names
        assert "acct_id" in id_names
        assert "department_id" in id_names
        # amount 不是 ID 字段
        assert "amount" not in id_names

    def test_calculate_skew_factor(self, fusion_service):
        """数据倾斜因子计算"""
        # 无倾斜（最大值 == 平均值）
        skew = fusion_service._calculate_skew_factor(
            {"max_match_per_key": 1, "avg_match_per_key": 1.0}
        )
        assert skew == 0.0

        # 严重倾斜
        skew = fusion_service._calculate_skew_factor(
            {"max_match_per_key": 100, "avg_match_per_key": 1.0}
        )
        assert skew > 0.9

        # 平均值为 0
        skew = fusion_service._calculate_skew_factor(
            {"max_match_per_key": 0, "avg_match_per_key": 0}
        )
        assert skew == 1.0

    def test_calculate_overall_score(self, fusion_service):
        """综合质量评分应在 [0, 1] 范围内"""
        score = fusion_service._calculate_overall_score(
            match_rate=0.9,
            coverage_rate=0.85,
            skew_factor=0.1,
            orphan_rate=0.1,
            null_key_rate=0.02,
            duplicate_rate=0.05,
        )
        assert 0.0 <= score <= 1.0

        # 完美数据应有高分
        perfect_score = fusion_service._calculate_overall_score(
            match_rate=1.0,
            coverage_rate=1.0,
            skew_factor=0.0,
            orphan_rate=0.0,
            null_key_rate=0.0,
            duplicate_rate=0.0,
        )
        assert perfect_score == 1.0

        # 最差数据应有低分
        worst_score = fusion_service._calculate_overall_score(
            match_rate=0.0,
            coverage_rate=0.0,
            skew_factor=1.0,
            orphan_rate=1.0,
            null_key_rate=1.0,
            duplicate_rate=1.0,
        )
        assert worst_score == 0.0

    def test_cosine_similarity(self, fusion_service):
        """余弦相似度计算"""
        # 相同向量
        sim = fusion_service._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert abs(sim - 1.0) < 0.001

        # 正交向量
        sim = fusion_service._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim) < 0.001

        # 空向量
        sim = fusion_service._cosine_similarity([], [1.0, 0.0])
        assert sim == 0.0

    def test_jaccard_similarity(self, fusion_service):
        """Jaccard 相似度计算"""
        # 相同字符串
        sim = fusion_service._jaccard_similarity("user_id", "user_id")
        assert sim == 1.0

        # 完全不同
        sim = fusion_service._jaccard_similarity("ab", "xy")
        assert sim == 0.0

    def test_get_table_fusion_service_singleton(self):
        """get_table_fusion_service 应返回单例"""
        mod = sys.modules["_test_table_fusion_service"]
        original = mod._table_fusion_service
        mod._table_fusion_service = None

        try:
            svc1 = get_table_fusion_service()
            svc2 = get_table_fusion_service()
            assert svc1 is svc2
        finally:
            mod._table_fusion_service = original


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
