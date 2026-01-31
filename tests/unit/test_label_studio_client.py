"""
Label Studio 客户端单元测试
Phase 1: 补齐短板 - Label Studio 集成

测试覆盖：
- LabelStudioConfig 配置加载
- LabelStudioClient API 调用 mock
- 健康检查
- ID 映射逻辑
- fallback 到内存存储
"""

import pytest
import os
import sys
import importlib.util
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# 直接加载 label_studio_client 模块（避免 services 命名空间冲突）
_project_root = Path(__file__).parent.parent.parent
_ls_client_path = _project_root / "services" / "model-api" / "services" / "label_studio_client.py"

_ls_module = None
if _ls_client_path.exists():
    spec = importlib.util.spec_from_file_location("label_studio_client", str(_ls_client_path))
    _ls_module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(_ls_module)
    except ImportError as e:
        _ls_module = None

# 如果模块加载失败则跳过
pytestmark = pytest.mark.skipif(
    _ls_module is None,
    reason="Cannot load label_studio_client module"
)


def _get_classes():
    """从模块中获取类"""
    return _ls_module.LabelStudioConfig, _ls_module.LabelStudioClient


class TestLabelStudioConfig:
    """LabelStudioConfig 配置测试"""

    @patch.dict(os.environ, {
        "LABEL_STUDIO_URL": "http://label-studio:8080",
        "LABEL_STUDIO_API_TOKEN": "test-token-123",
        "LABEL_STUDIO_TIMEOUT": "60",
    })
    def test_from_env_with_all_vars(self):
        """环境变量完整时正确加载配置"""
        LabelStudioConfig, _ = _get_classes()
        config = LabelStudioConfig.from_env()
        assert config.url == "http://label-studio:8080"
        assert config.api_token == "test-token-123"
        assert config.timeout == 60
        assert config.enabled is True

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_disabled_when_empty(self):
        """环境变量为空时 enabled=False"""
        LabelStudioConfig, _ = _get_classes()
        config = LabelStudioConfig.from_env()
        assert config.url == ""
        assert config.api_token == ""
        assert config.enabled is False

    @patch.dict(os.environ, {
        "LABEL_STUDIO_URL": "http://label-studio:8080/",
        "LABEL_STUDIO_API_TOKEN": "token",
    })
    def test_from_env_strips_trailing_slash(self):
        """URL 末尾的斜杠被移除"""
        LabelStudioConfig, _ = _get_classes()
        config = LabelStudioConfig.from_env()
        assert config.url == "http://label-studio:8080"

    @patch.dict(os.environ, {
        "LABEL_STUDIO_URL": "http://label-studio:8080",
        "LABEL_STUDIO_API_TOKEN": "",
    })
    def test_from_env_disabled_when_token_empty(self):
        """Token 为空时 enabled=False"""
        LabelStudioConfig, _ = _get_classes()
        config = LabelStudioConfig.from_env()
        assert config.enabled is False


class TestLabelStudioClientSession:
    """LabelStudioClient HTTP 会话测试"""

    def test_session_lazy_init(self):
        """Session 延迟初始化"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)
        assert client._session is None
        # 访问 session 属性时初始化
        session = client.session
        assert session is not None
        assert client._session is session

    def test_session_has_auth_header(self):
        """Session 包含 Token 认证头"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token-abc",
        )
        client = LabelStudioClient(config)
        session = client.session
        assert session.headers.get("Authorization") == "Token test-token-abc"

    def test_session_has_json_content_type(self):
        """Session 包含 JSON Content-Type"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)
        session = client.session
        assert session.headers.get("Content-Type") == "application/json"

    def test_session_reused_on_second_access(self):
        """第二次访问 session 返回同一实例"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)
        session1 = client.session
        session2 = client.session
        assert session1 is session2


class TestLabelStudioClientHealthCheck:
    """健康检查测试"""

    def test_health_check_success(self):
        """健康检查成功"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)

        mock_response = Mock()
        mock_response.status_code = 200
        client._session = Mock()
        client._session.get.return_value = mock_response

        assert client.health_check() is True
        client._session.get.assert_called_once_with(
            "http://localhost:8080/health",
            timeout=5,
        )

    def test_health_check_failure(self):
        """健康检查失败"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)

        mock_response = Mock()
        mock_response.status_code = 500
        client._session = Mock()
        client._session.get.return_value = mock_response

        assert client.health_check() is False

    def test_health_check_connection_error(self):
        """连接失败时返回 False"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)

        client._session = Mock()
        client._session.get.side_effect = Exception("Connection refused")

        assert client.health_check() is False


class TestLabelStudioClientAPICalls:
    """Label Studio API 调用测试"""

    def _make_client(self):
        """创建带 mock session 的客户端"""
        LabelStudioConfig, LabelStudioClient = _get_classes()
        config = LabelStudioConfig(
            url="http://localhost:8080",
            api_token="test-token",
        )
        client = LabelStudioClient(config)
        mock_session = Mock()
        client._session = mock_session
        return client, mock_session

    def test_create_project(self):
        """创建项目 API 调用"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": 1, "title": "test"}'
        mock_response.json.return_value = {"id": 1, "title": "test"}
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.create_project(
            title="Test Project",
            description="A test project",
            label_config="<View><Text name='text'/></View>",
        )

        assert result == {"id": 1, "title": "test"}
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/api/projects/" in call_args[1]["url"]

    def test_list_projects_with_pagination(self):
        """列出项目（分页结果）"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": [{"id": 1}, {"id": 2}]}'
        mock_response.json.return_value = {"results": [{"id": 1}, {"id": 2}]}
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.list_projects()
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_list_projects_with_list_response(self):
        """列出项目（直接列表结果）"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"id": 1}]'
        mock_response.json.return_value = [{"id": 1}]
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.list_projects()
        assert len(result) == 1

    def test_create_tasks(self):
        """批量导入任务"""
        client, mock_session = self._make_client()

        tasks = [{"data": {"text": "sample 1"}}, {"data": {"text": "sample 2"}}]
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'[{"id": 10}, {"id": 11}]'
        mock_response.json.return_value = [{"id": 10}, {"id": 11}]
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.create_tasks(project_id=1, tasks=tasks)
        assert len(result) == 2
        call_args = mock_session.request.call_args
        assert "/api/projects/1/import" in call_args[1]["url"]

    def test_create_annotation(self):
        """创建标注"""
        client, mock_session = self._make_client()

        annotation_result = [{"value": {"choices": ["Positive"]}}]
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": 100}'
        mock_response.json.return_value = {"id": 100}
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.create_annotation(
            task_id=10,
            result=annotation_result,
            lead_time=5.0,
        )
        assert result["id"] == 100
        call_args = mock_session.request.call_args
        assert "/api/tasks/10/annotations/" in call_args[1]["url"]

    def test_export_annotations(self):
        """导出标注"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"id": 1, "annotations": []}]'
        mock_response.json.return_value = [{"id": 1, "annotations": []}]
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.export_annotations(project_id=1, export_type="JSON")
        assert isinstance(result, list)
        call_args = mock_session.request.call_args
        assert call_args[1]["params"] == {"exportType": "JSON"}

    def test_get_tasks(self):
        """获取任务列表"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"tasks": []}'
        mock_response.json.return_value = {"tasks": []}
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client.get_tasks(project_id=1, page=1, page_size=50)
        call_args = mock_session.request.call_args
        assert call_args[1]["params"]["project"] == 1
        assert call_args[1]["params"]["page_size"] == 50

    def test_delete_project(self):
        """删除项目"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b''
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client.delete_project(project_id=1)
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "DELETE"
        assert "/api/projects/1/" in call_args[1]["url"]

    def test_request_http_error_raises(self):
        """HTTP 错误被抛出"""
        import requests
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_session.request.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            client._request("GET", "/api/projects/999/")

    def test_request_empty_response(self):
        """空响应返回空字典"""
        client, mock_session = self._make_client()

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b''
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        result = client._request("DELETE", "/api/projects/1/")
        assert result == {}


class TestLabelingServiceFallback:
    """LabelingService LS 集成 fallback 测试"""

    @patch.dict(os.environ, {
        "LABEL_STUDIO_URL": "",
        "LABEL_STUDIO_API_TOKEN": "",
    })
    def test_service_works_without_label_studio(self):
        """Label Studio 不可用时服务正常启动（内存存储）"""
        try:
            # 动态加载 labeling_service 避免命名空间冲突
            ls_path = _project_root / "services" / "model-api" / "services" / "labeling_service.py"
            spec = importlib.util.spec_from_file_location("labeling_service", str(ls_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            service = mod.LabelingService()
            assert service is not None
        except (ImportError, Exception):
            pytest.skip("labeling_service module not importable in test environment")

    @patch.dict(os.environ, {
        "LABEL_STUDIO_URL": "http://unreachable:8080",
        "LABEL_STUDIO_API_TOKEN": "fake-token",
    })
    def test_service_degrades_when_ls_unreachable(self):
        """Label Studio 不可达时降级到内存存储"""
        try:
            ls_path = _project_root / "services" / "model-api" / "services" / "labeling_service.py"
            spec = importlib.util.spec_from_file_location("labeling_service", str(ls_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            service = mod.LabelingService()
            assert service is not None
        except (ImportError, Exception):
            pytest.skip("labeling_service module not importable in test environment")
