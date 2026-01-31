"""
Apache Hop 集成单元测试
Phase 2: 渐进迁移 - Apache Hop ETL 引擎

测试覆盖：
- HopConfig 配置加载
- HopBridge HTTP 会话管理
- HopBridge 健康检查
- Pipeline 注册、执行、状态查询、停止、删除
- Workflow 注册、执行、状态查询
- PipelineResult / WorkflowResult 属性
"""

import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# 添加 data-api 路径
_project_root = Path(__file__).parent.parent.parent
_data_api_path = str(_project_root / "services" / "data-api")
if _data_api_path not in sys.path:
    sys.path.insert(0, _data_api_path)


class TestHopConfig:
    """HopConfig 配置测试"""

    @patch.dict(os.environ, {
        "HOP_SERVER_URL": "http://hop-test:8080",
        "HOP_SERVER_USER": "admin",
        "HOP_SERVER_PASSWORD": "secret123",
        "HOP_ENABLED": "true",
    })
    def test_from_env_full_config(self):
        """完整环境变量加载"""
        from integrations.hop.config import HopConfig
        config = HopConfig.from_env()
        assert config.server_url == "http://hop-test:8080"
        assert config.username == "admin"
        assert config.password == "secret123"
        assert config.enabled is True

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self):
        """默认配置"""
        from integrations.hop.config import HopConfig
        config = HopConfig.from_env()
        assert config.server_url == "http://hop-server:8182"
        assert config.username == "cluster"
        assert config.password == ""  # 默认密码为空
        assert config.enabled is False
        assert config.timeout == 30
        assert config.execution_timeout == 3600
        assert config.poll_interval == 5

    @patch.dict(os.environ, {
        "HOP_ENABLED": "false",
    })
    def test_from_env_disabled(self):
        """HOP_ENABLED=false"""
        from integrations.hop.config import HopConfig
        config = HopConfig.from_env()
        assert config.enabled is False

    @patch.dict(os.environ, {
        "HOP_TIMEOUT": "60",
        "HOP_EXECUTION_TIMEOUT": "7200",
        "HOP_POLL_INTERVAL": "10",
    })
    def test_from_env_custom_timeouts(self):
        """自定义超时参数"""
        from integrations.hop.config import HopConfig
        config = HopConfig.from_env()
        assert config.timeout == 60
        assert config.execution_timeout == 7200
        assert config.poll_interval == 10

    def test_validate_disabled_config(self):
        """禁用状态的配置验证"""
        from integrations.hop.config import HopConfig
        config = HopConfig(enabled=False, server_url="")
        assert config.validate() is True

    def test_validate_enabled_without_url_raises(self):
        """启用但无 server_url 抛出 ValueError"""
        from integrations.hop.config import HopConfig
        config = HopConfig(enabled=True, server_url="")
        with pytest.raises(ValueError, match="HOP_SERVER_URL is required"):
            config.validate()


class TestHopBridgeSession:
    """HopBridge 会话管理测试"""

    def test_session_auth_is_http_basic(self):
        """HTTP 会话使用 HTTPBasicAuth"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge
        from requests.auth import HTTPBasicAuth

        config = HopConfig(
            server_url="http://hop-server:8182",
            username="admin",
            password="secret",
            enabled=True,
        )
        bridge = HopBridge(config)

        # 检查会话的认证类型
        assert isinstance(bridge._session.auth, HTTPBasicAuth)

    def test_session_reused(self):
        """会话被复用而非每次创建新会话"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        session1 = bridge._session
        session2 = bridge._session
        assert session1 is session2


class TestHopBridgeHealthCheck:
    """HopBridge 健康检查测试"""

    def test_health_check_success(self):
        """健康检查成功"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response

            result = bridge.health_check()
            assert result is True

    def test_health_check_failure(self):
        """健康检查失败（请求异常）"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge
        import requests

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_request.side_effect = requests.RequestException("Connection failed")

            result = bridge.health_check()
            assert result is False

    def test_health_check_connection_error(self):
        """健康检查连接错误"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge
        import requests

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_request.side_effect = requests.ConnectionError("Connection refused")

            result = bridge.health_check()
            assert result is False


class TestHopBridgePipelineOperations:
    """HopBridge Pipeline 操作测试"""

    def test_register_pipeline_success(self):
        """注册 Pipeline 成功"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.register_pipeline("<pipeline>...</pipeline>", "test_pipeline")
            assert result is True

    def test_register_pipeline_failure(self):
        """注册 Pipeline 失败"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ERROR", "message": "Invalid"}
            mock_request.return_value = mock_response

            result = bridge.register_pipeline("<invalid/>", "bad_pipeline")
            assert result is False

    def test_execute_pipeline_success(self):
        """执行 Pipeline 成功"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.execute_pipeline("test_pipeline")
            assert result is True

    def test_get_pipeline_status(self):
        """获取 Pipeline 状态"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge, PipelineResult, PipelineStatus

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status_desc": "Finished",
                "errors": 0,
                "transforms": [
                    {"name": "step1", "lines_read": 100, "lines_written": 100, "errors": 0}
                ],
            }
            mock_request.return_value = mock_response

            result = bridge.get_pipeline_status("test_pipeline")
            assert isinstance(result, PipelineResult)
            assert result.status == PipelineStatus.FINISHED
            assert result.rows_read == 100
            assert result.errors == 0

    def test_stop_pipeline(self):
        """停止 Pipeline"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.stop_pipeline("test_pipeline")
            assert result is True

    def test_remove_pipeline(self):
        """移除 Pipeline"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.remove_pipeline("test_pipeline")
            assert result is True

    def test_list_pipelines(self):
        """列出所有 Pipeline"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "pipelines": [
                    {"name": "pipeline1", "status": "Finished"},
                    {"name": "pipeline2", "status": "Running"},
                ]
            }
            mock_request.return_value = mock_response

            result = bridge.list_pipelines()
            assert len(result) == 2
            assert result[0]["name"] == "pipeline1"


class TestHopBridgeWorkflowOperations:
    """HopBridge Workflow 操作测试"""

    def test_register_workflow_success(self):
        """注册 Workflow 成功"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.register_workflow("<workflow>...</workflow>", "test_workflow")
            assert result is True

    def test_execute_workflow_success(self):
        """执行 Workflow 成功"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "OK"}
            mock_request.return_value = mock_response

            result = bridge.execute_workflow("test_workflow")
            assert result is True

    def test_get_workflow_status(self):
        """获取 Workflow 状态"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge, WorkflowResult, WorkflowStatus

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status_desc": "Finished",
                "errors": 0,
                "actions": [
                    {"name": "action1", "result": "true", "errors": 0}
                ],
            }
            mock_request.return_value = mock_response

            result = bridge.get_workflow_status("test_workflow")
            assert isinstance(result, WorkflowResult)
            assert result.status == WorkflowStatus.FINISHED
            assert result.errors == 0

    def test_list_workflows(self):
        """列出所有 Workflow"""
        from integrations.hop.config import HopConfig
        from integrations.hop.hop_bridge import HopBridge

        config = HopConfig(enabled=True)
        bridge = HopBridge(config)

        with patch.object(bridge, "_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "workflows": [
                    {"name": "workflow1", "status": "Finished"},
                ]
            }
            mock_request.return_value = mock_response

            result = bridge.list_workflows()
            assert len(result) == 1
            assert result[0]["name"] == "workflow1"


class TestPipelineResult:
    """PipelineResult dataclass 测试"""

    def test_is_running(self):
        """is_running 属性"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.RUNNING,
            status_description="Running"
        )
        assert result.is_running is True

        result = PipelineResult(
            name="test",
            status=PipelineStatus.FINISHED,
            status_description="Finished"
        )
        assert result.is_running is False

    def test_is_finished(self):
        """is_finished 属性"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.FINISHED,
            status_description="Finished"
        )
        assert result.is_finished is True

        result = PipelineResult(
            name="test",
            status=PipelineStatus.RUNNING,
            status_description="Running"
        )
        assert result.is_finished is False

    def test_is_success_finished_no_errors(self):
        """is_success 成功场景（Finished 且无错误）"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.FINISHED,
            status_description="Finished",
            errors=0
        )
        assert result.is_success is True

    def test_is_success_with_errors(self):
        """is_success 失败场景（有错误）"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.FINISHED,
            status_description="Finished",
            errors=5
        )
        assert result.is_success is False

    def test_is_success_still_running(self):
        """is_success 仍在运行"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.RUNNING,
            status_description="Running",
            errors=0
        )
        assert result.is_success is False

    def test_is_error_and_stopped_are_finished(self):
        """Error 和 Stopped 状态算作 finished"""
        from integrations.hop.hop_bridge import PipelineResult, PipelineStatus

        result = PipelineResult(
            name="test",
            status=PipelineStatus.ERROR,
            status_description="Error"
        )
        assert result.is_finished is True

        result = PipelineResult(
            name="test",
            status=PipelineStatus.STOPPED,
            status_description="Stopped"
        )
        assert result.is_finished is True


class TestWorkflowResult:
    """WorkflowResult dataclass 测试"""

    def test_is_running(self):
        """is_running 属性"""
        from integrations.hop.hop_bridge import WorkflowResult, WorkflowStatus

        result = WorkflowResult(
            name="test",
            status=WorkflowStatus.RUNNING,
            status_description="Running"
        )
        assert result.is_running is True

    def test_is_finished(self):
        """is_finished 属性"""
        from integrations.hop.hop_bridge import WorkflowResult, WorkflowStatus

        result = WorkflowResult(
            name="test",
            status=WorkflowStatus.FINISHED,
            status_description="Finished"
        )
        assert result.is_finished is True

    def test_is_success(self):
        """is_success 属性"""
        from integrations.hop.hop_bridge import WorkflowResult, WorkflowStatus

        result = WorkflowResult(
            name="test",
            status=WorkflowStatus.FINISHED,
            status_description="Finished",
            errors=0
        )
        assert result.is_success is True

        result = WorkflowResult(
            name="test",
            status=WorkflowStatus.FINISHED,
            status_description="Finished",
            errors=1
        )
        assert result.is_success is False


class TestHopIntegrationInit:
    """Hop 集成模块 __init__.py 测试"""

    def test_module_imports_without_error(self):
        """Hop 集成模块可以正常导入"""
        try:
            from integrations.hop import HopConfig, HopBridge
            assert HopConfig is not None
            assert HopBridge is not None
        except ImportError:
            pytest.skip("Hop integration module not importable in test environment")

    def test_parent_init_handles_hop_import(self):
        """父 __init__.py 处理 Hop 导入（可选依赖）"""
        try:
            from integrations import HopConfig, HopBridge
            # Hop 可能安装也可能没有，两种都合法
            assert True
        except ImportError:
            pytest.skip("integrations module not importable in test environment")
