"""
双引擎 ETL 编排服务单元测试
Phase 2: 渐进迁移 - 双引擎编排（Kettle + Hop）

测试覆盖：
- 引擎选择逻辑（auto/kettle/hop）
- Hop 路径编排流程
- Kettle 路径编排流程（保持兼容）
- Fallback 机制
- OrchestrationRequest/OrchestrationResult 字段
"""

import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import importlib.util

# 设置测试环境变量
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# 添加 data-api 路径
_project_root = Path(__file__).parent.parent.parent
_data_api_path = str(_project_root / "services" / "data-api")
if _data_api_path not in sys.path:
    sys.path.insert(0, _data_api_path)


def _import_orchestration_module():
    """直接导入 kettle_orchestration_service 模块，绕过包初始化问题"""
    module_path = _project_root / "services" / "data-api" / "services" / "kettle_orchestration_service.py"
    spec = importlib.util.spec_from_file_location("kettle_orchestration_service", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 导入模块
_orchestration_module = _import_orchestration_module()

# 从模块中获取类
KettleOrchestrationService = _orchestration_module.KettleOrchestrationService
OrchestrationRequest = _orchestration_module.OrchestrationRequest
OrchestrationResult = _orchestration_module.OrchestrationResult
OrchestrationStatus = _orchestration_module.OrchestrationStatus
DataQualityReport = _orchestration_module.DataQualityReport
ETLEngine = _orchestration_module.ETLEngine


class TestEngineSelection:
    """引擎选择逻辑测试"""

    def test_select_engine_explicit_kettle(self):
        """显式指定 Kettle 引擎"""
        service = KettleOrchestrationService()

        # Mock Kettle Bridge 可用
        mock_kettle_bridge = Mock()
        with patch.object(service, "_get_kettle_bridge", return_value=mock_kettle_bridge):
            engine_name, bridge = service._select_engine("kettle")
            assert engine_name == "kettle"
            assert bridge is mock_kettle_bridge

    def test_select_engine_explicit_kettle_unavailable(self):
        """显式指定 Kettle 引擎但不可用"""
        service = KettleOrchestrationService()

        with patch.object(service, "_get_kettle_bridge", return_value=None):
            engine_name, bridge = service._select_engine("kettle")
            assert engine_name is None
            assert bridge is None

    def test_select_engine_explicit_hop(self):
        """显式指定 Hop 引擎"""
        service = KettleOrchestrationService()

        mock_hop_bridge = Mock()
        with patch.object(service, "_get_hop_bridge", return_value=mock_hop_bridge):
            engine_name, bridge = service._select_engine("hop")
            assert engine_name == "hop"
            assert bridge is mock_hop_bridge

    def test_select_engine_hop_unavailable_fallback_to_kettle(self):
        """Hop 不可用时回退到 Kettle"""
        service = KettleOrchestrationService()

        mock_kettle_bridge = Mock()
        with patch.object(service, "_get_hop_bridge", return_value=None):
            with patch.object(service, "_get_kettle_bridge", return_value=mock_kettle_bridge):
                engine_name, bridge = service._select_engine("hop")
                # 当 hop 不可用时，应回退到 kettle
                assert engine_name == "kettle"
                assert bridge is mock_kettle_bridge

    def test_select_engine_hop_and_kettle_unavailable(self):
        """Hop 和 Kettle 都不可用"""
        service = KettleOrchestrationService()

        with patch.object(service, "_get_hop_bridge", return_value=None):
            with patch.object(service, "_get_kettle_bridge", return_value=None):
                engine_name, bridge = service._select_engine("hop")
                assert engine_name is None
                assert bridge is None

    def test_select_engine_auto_prefers_hop_if_available(self):
        """auto 模式优先使用 Hop（如果可用）"""
        service = KettleOrchestrationService()

        mock_hop_bridge = Mock()
        mock_kettle_bridge = Mock()

        with patch.object(service, "_get_hop_bridge", return_value=mock_hop_bridge):
            with patch.object(service, "_get_kettle_bridge", return_value=mock_kettle_bridge):
                engine_name, bridge = service._select_engine("auto")
                assert engine_name == "hop"
                assert bridge is mock_hop_bridge

    def test_select_engine_auto_fallback_to_kettle(self):
        """auto 模式在 Hop 不可用时回退到 Kettle"""
        service = KettleOrchestrationService()

        mock_kettle_bridge = Mock()

        with patch.object(service, "_get_hop_bridge", return_value=None):
            with patch.object(service, "_get_kettle_bridge", return_value=mock_kettle_bridge):
                engine_name, bridge = service._select_engine("auto")
                assert engine_name == "kettle"
                assert bridge is mock_kettle_bridge

    def test_select_engine_case_insensitive(self):
        """引擎类型不区分大小写"""
        service = KettleOrchestrationService()

        mock_kettle_bridge = Mock()
        with patch.object(service, "_get_kettle_bridge", return_value=mock_kettle_bridge):
            engine_name, bridge = service._select_engine("KETTLE")
            assert engine_name == "kettle"

            engine_name, bridge = service._select_engine("Kettle")
            assert engine_name == "kettle"


class TestExecuteViaCarte:
    """远程执行测试"""

    def test_execute_via_carte_no_engine_available(self):
        """没有可用引擎时返回错误"""
        service = KettleOrchestrationService()

        with patch.object(service, "_select_engine", return_value=(None, None)):
            result = service.execute_via_carte(
                trans_xml="<xml/>",
                trans_name="test",
                engine_type="auto",
            )

            assert result["success"] is False
            assert "error" in result
            assert result["error_type"] == "no_engine_available"

    def test_execute_via_carte_health_check_failed(self):
        """健康检查失败时返回错误"""
        service = KettleOrchestrationService()

        mock_bridge = Mock()
        mock_bridge.health_check.return_value = False

        with patch.object(service, "_select_engine", return_value=("hop", mock_bridge)):
            result = service.execute_via_carte(
                trans_xml="<xml/>",
                trans_name="test",
                engine_type="hop",
            )

            assert result["success"] is False
            assert "hop 服务器不可用" in result["error"]
            assert result["error_type"] == "hop_unavailable"

    def test_execute_via_carte_exception_handling(self):
        """执行异常处理"""
        service = KettleOrchestrationService()

        mock_bridge = Mock()
        mock_bridge.health_check.side_effect = Exception("Connection error")

        with patch.object(service, "_select_engine", return_value=("kettle", mock_bridge)):
            result = service.execute_via_carte(
                trans_xml="<xml/>",
                trans_name="test",
                engine_type="kettle",
            )

            assert result["success"] is False
            assert "Connection error" in result["error"]
            assert result["error_type"] == "execution_error"
            assert result["engine_used"] == "kettle"


class TestGetAvailableEngines:
    """获取可用引擎测试"""

    def test_get_available_engines_structure(self):
        """返回结构正确"""
        service = KettleOrchestrationService()

        engines = service.get_available_engines()

        assert "default_engine" in engines
        assert "kettle" in engines
        assert "hop" in engines
        assert "enabled" in engines["kettle"]
        assert "status" in engines["kettle"]
        assert "enabled" in engines["hop"]
        assert "status" in engines["hop"]

    def test_get_available_engines_both_disabled(self):
        """两个引擎都禁用"""
        service = KettleOrchestrationService()

        # Mock config to return enabled=False for both engines
        mock_kettle_config = Mock()
        mock_kettle_config.enabled = False
        mock_hop_config = Mock()
        mock_hop_config.enabled = False

        with patch("integrations.kettle.KettleConfig") as MockKettleConfig:
            with patch("integrations.hop.HopConfig") as MockHopConfig:
                MockKettleConfig.from_env.return_value = mock_kettle_config
                MockHopConfig.from_env.return_value = mock_hop_config

                engines = service.get_available_engines()

                # 当两个引擎都禁用时，enabled=False 且 status="unavailable"
                assert engines["kettle"]["enabled"] is False
                assert engines["kettle"]["status"] == "unavailable"
                assert engines["hop"]["enabled"] is False
                assert engines["hop"]["status"] == "unavailable"


class TestGetHopStatus:
    """获取 Hop 状态测试"""

    def test_get_hop_status_unavailable(self):
        """Hop 不可用状态"""
        service = KettleOrchestrationService()

        with patch.object(service, "_get_hop_bridge", return_value=None):
            status = service.get_hop_status()

            assert status["enabled"] is False
            assert "message" in status

    def test_get_hop_status_available(self):
        """Hop 可用状态"""
        service = KettleOrchestrationService()

        mock_hop_bridge = Mock()
        mock_hop_bridge.get_server_status.return_value = {"status": "running"}
        mock_hop_bridge.list_pipelines.return_value = [{"name": "pipeline1"}]
        mock_hop_bridge.list_workflows.return_value = [{"name": "workflow1"}]

        with patch.object(service, "_get_hop_bridge", return_value=mock_hop_bridge):
            status = service.get_hop_status()

            assert status["enabled"] is True
            assert "server_status" in status
            assert "pipelines" in status
            assert "workflows" in status

    def test_get_hop_status_error(self):
        """Hop 状态查询错误"""
        service = KettleOrchestrationService()

        mock_hop_bridge = Mock()
        mock_hop_bridge.get_server_status.side_effect = Exception("Connection error")

        with patch.object(service, "_get_hop_bridge", return_value=mock_hop_bridge):
            status = service.get_hop_status()

            assert status["enabled"] is True
            assert "error" in status


class TestOrchestrationRequest:
    """OrchestrationRequest 测试"""

    def test_default_values(self):
        """默认值"""
        request = OrchestrationRequest()
        assert request.engine_type == "auto"
        assert request.request_id == ""
        assert request.name == ""
        assert request.enable_ai_cleaning is True
        assert request.enable_ai_masking is True
        assert request.auto_execute is False
        assert request.dry_run is True

    def test_engine_type_explicit(self):
        """显式设置 engine_type"""
        request = OrchestrationRequest(engine_type="hop")
        assert request.engine_type == "hop"

        request = OrchestrationRequest(engine_type="kettle")
        assert request.engine_type == "kettle"

    def test_to_dict(self):
        """to_dict 序列化"""
        request = OrchestrationRequest(
            request_id="test-123",
            name="test-etl",
            source_database="db1",
            source_table="table1",
            engine_type="hop",
        )

        data = request.to_dict()
        assert data["request_id"] == "test-123"
        assert data["name"] == "test-etl"
        assert data["source_database"] == "db1"
        assert data["source_table"] == "table1"
        assert data["engine_type"] == "hop"


class TestOrchestrationResult:
    """OrchestrationResult 测试"""

    def test_default_values(self):
        """默认值"""
        result = OrchestrationResult()
        assert result.request_id == ""
        assert result.status == OrchestrationStatus.PENDING
        assert result.engine_used == ""
        assert result.execution_success is None
        assert result.error_message == ""

    def test_engine_used_field(self):
        """engine_used 字段"""
        result = OrchestrationResult(
            request_id="test-123",
            status=OrchestrationStatus.COMPLETED,
            engine_used="hop",
        )
        assert result.engine_used == "hop"

    def test_to_dict(self):
        """to_dict 序列化"""
        result = OrchestrationResult(
            request_id="test-123",
            status=OrchestrationStatus.COMPLETED,
            engine_used="kettle",
            execution_success=True,
            rows_processed=100,
        )

        data = result.to_dict()
        assert data["request_id"] == "test-123"
        assert data["status"] == "completed"
        assert data["engine_used"] == "kettle"
        assert data["execution_success"] is True
        assert data["rows_processed"] == 100

    def test_duration_seconds_property(self):
        """duration_seconds 计算属性"""
        from datetime import datetime, timedelta

        now = datetime.now()
        result = OrchestrationResult(
            request_id="test-123",
            started_at=now - timedelta(seconds=60),
            completed_at=now,
        )

        # 应该约等于 60 秒
        assert 59 <= result.duration_seconds <= 61


class TestETLEngineEnum:
    """ETLEngine 枚举测试"""

    def test_enum_values(self):
        """枚举值"""
        assert ETLEngine.KETTLE.value == "kettle"
        assert ETLEngine.HOP.value == "hop"
        assert ETLEngine.AUTO.value == "auto"

    def test_enum_string_comparison(self):
        """枚举可以与字符串比较"""
        assert ETLEngine.KETTLE == "kettle"
        assert ETLEngine.HOP == "hop"
        assert ETLEngine.AUTO == "auto"


class TestOrchestrationStatus:
    """OrchestrationStatus 枚举测试"""

    def test_enum_values(self):
        """枚举值"""
        assert OrchestrationStatus.PENDING.value == "pending"
        assert OrchestrationStatus.ANALYZING.value == "analyzing"
        assert OrchestrationStatus.GENERATING.value == "generating"
        assert OrchestrationStatus.EXECUTING.value == "executing"
        assert OrchestrationStatus.COMPLETED.value == "completed"
        assert OrchestrationStatus.FAILED.value == "failed"


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_initialization(self):
        """服务初始化"""
        service = KettleOrchestrationService()

        assert service is not None
        assert service._tasks == {}
        assert service._quality_reports == {}

    def test_default_engine_from_env(self):
        """从环境变量读取默认引擎"""
        service = KettleOrchestrationService()

        # 默认值应该是 kettle 或从环境变量读取
        assert service._default_engine in ["kettle", "auto", "hop"]

    def test_bridges_lazy_init(self):
        """Bridge 懒加载初始化"""
        service = KettleOrchestrationService()

        # 初始化时 bridge 应该为 None
        assert service._kettle_bridge is None
        assert service._hop_bridge is None


class TestDataQualityReport:
    """数据质量报告测试"""

    def test_report_default_values(self):
        """报告默认值"""
        report = DataQualityReport()
        assert report.request_id == ""
        assert report.rows_read == 0
        assert report.rows_written == 0
        assert report.error_rate == 0.0
        assert report.success_rate == 1.0

    def test_calculate_metrics(self):
        """计算质量指标"""
        report = DataQualityReport(
            rows_read=100,
            rows_written=90,
            rows_error=5,
            rows_rejected=5,
        )
        report.calculate_metrics()

        assert report.error_rate == 0.05
        assert report.rejection_rate == 0.05
        assert report.success_rate == 0.9

    def test_to_dict(self):
        """to_dict 序列化"""
        report = DataQualityReport(
            request_id="test-123",
            rows_read=100,
            rows_written=95,
        )

        data = report.to_dict()
        assert data["request_id"] == "test-123"
        assert data["rows_read"] == 100
        assert data["rows_written"] == 95

    def test_to_json(self):
        """to_json 序列化"""
        import json

        report = DataQualityReport(request_id="test-123")
        json_str = report.to_json()

        data = json.loads(json_str)
        assert data["request_id"] == "test-123"
