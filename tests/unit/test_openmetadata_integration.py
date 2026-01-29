"""
OpenMetadata 集成层单元测试

测试覆盖:
- OpenMetadataConfig: 配置加载、验证
- OpenMetadataClient: API 调用（mock）
- MetadataSyncService: 元数据同步逻辑
- OpenLineageService: 血缘推送与获取
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass


# ==================== Config Tests ====================

class TestOpenMetadataConfig:
    """OpenMetadataConfig 配置测试"""

    def test_from_env_defaults(self, monkeypatch):
        """测试默认环境变量加载"""
        # 清除可能存在的环境变量
        monkeypatch.delenv("OPENMETADATA_ENABLED", raising=False)
        monkeypatch.delenv("OPENMETADATA_HOST", raising=False)
        monkeypatch.delenv("OPENMETADATA_PORT", raising=False)

        from integrations.openmetadata.config import OpenMetadataConfig

        # 重置全局单例
        import integrations.openmetadata.config as cfg_module
        cfg_module._config = None

        config = OpenMetadataConfig.from_env()

        assert config.host == "localhost"
        assert config.port == 8585
        assert config.enabled is False
        assert config.api_version == "v1"
        assert config.timeout == 30
        assert config.jwt_token is None

    def test_from_env_enabled(self, monkeypatch):
        """测试启用状态的环境变量"""
        monkeypatch.setenv("OPENMETADATA_ENABLED", "true")
        monkeypatch.setenv("OPENMETADATA_HOST", "om-server")
        monkeypatch.setenv("OPENMETADATA_PORT", "9585")
        monkeypatch.setenv("OPENMETADATA_API_VERSION", "v2")
        monkeypatch.setenv("OPENMETADATA_TIMEOUT", "60")
        monkeypatch.setenv("OPENMETADATA_JWT_TOKEN", "test-token-123")

        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig.from_env()

        assert config.host == "om-server"
        assert config.port == 9585
        assert config.enabled is True
        assert config.api_version == "v2"
        assert config.timeout == 60
        assert config.jwt_token == "test-token-123"

    def test_from_env_enabled_variants(self, monkeypatch):
        """测试各种启用值"""
        from integrations.openmetadata.config import OpenMetadataConfig

        for val in ("true", "1", "yes", "True", "YES"):
            monkeypatch.setenv("OPENMETADATA_ENABLED", val)
            config = OpenMetadataConfig.from_env()
            assert config.enabled is True, f"Expected enabled=True for '{val}'"

        for val in ("false", "0", "no", "anything"):
            monkeypatch.setenv("OPENMETADATA_ENABLED", val)
            config = OpenMetadataConfig.from_env()
            assert config.enabled is False, f"Expected enabled=False for '{val}'"

    def test_base_url(self):
        """测试 base_url 属性"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(
            host="myhost",
            port=8585,
            enabled=True,
            api_version="v1",
        )
        assert config.base_url == "http://myhost:8585/api/v1"

    def test_health_url(self):
        """测试 health_url 属性"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(
            host="myhost",
            port=8585,
            enabled=True,
        )
        assert config.health_url == "http://myhost:8585/api/v1/system/version"

    def test_validate_disabled(self):
        """测试禁用时验证通过"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(host="", port=0, enabled=False)
        assert config.validate() is True

    def test_validate_valid(self):
        """测试有效配置验证"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(host="localhost", port=8585, enabled=True)
        assert config.validate() is True

    def test_validate_missing_host(self):
        """测试缺少 host 验证失败"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(host="", port=8585, enabled=True)
        assert config.validate() is False

    def test_validate_invalid_port(self):
        """测试无效端口验证失败"""
        from integrations.openmetadata.config import OpenMetadataConfig

        config = OpenMetadataConfig(host="localhost", port=0, enabled=True)
        assert config.validate() is False

        config = OpenMetadataConfig(host="localhost", port=70000, enabled=True)
        assert config.validate() is False

    def test_get_config_singleton(self, monkeypatch):
        """测试配置单例"""
        monkeypatch.setenv("OPENMETADATA_HOST", "singleton-test")

        import integrations.openmetadata.config as cfg_module
        cfg_module._config = None

        config1 = cfg_module.get_config()
        config2 = cfg_module.get_config()
        assert config1 is config2

        # 清理
        cfg_module._config = None

    def test_is_enabled(self, monkeypatch):
        """测试 is_enabled 函数"""
        import integrations.openmetadata.config as cfg_module
        cfg_module._config = None

        monkeypatch.setenv("OPENMETADATA_ENABLED", "false")
        assert cfg_module.is_enabled() is False

        cfg_module._config = None
        monkeypatch.setenv("OPENMETADATA_ENABLED", "true")
        assert cfg_module.is_enabled() is True

        # 清理
        cfg_module._config = None


# ==================== Client Tests ====================

class TestOpenMetadataClient:
    """OpenMetadataClient 测试（使用 mock）"""

    def _make_client(self, enabled=True):
        """创建一个测试用客户端"""
        from integrations.openmetadata.config import OpenMetadataConfig
        from integrations.openmetadata.client import OpenMetadataClient

        config = OpenMetadataConfig(
            host="test-host",
            port=8585,
            enabled=enabled,
            jwt_token="test-token",
        )
        client = OpenMetadataClient(config=config)
        return client

    def test_health_check_disabled(self):
        """测试禁用时健康检查返回 False"""
        client = self._make_client(enabled=False)
        assert client.health_check() is False

    @patch("requests.Session.get")
    def test_health_check_success(self, mock_get):
        """测试健康检查成功"""
        mock_get.return_value = MagicMock(status_code=200)
        client = self._make_client()
        assert client.health_check() is True

    @patch("requests.Session.get")
    def test_health_check_failure(self, mock_get):
        """测试健康检查失败"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        client = self._make_client()
        assert client.health_check() is False

    def test_session_headers(self):
        """测试会话头设置"""
        client = self._make_client()
        session = client.session
        assert session.headers["Content-Type"] == "application/json"
        assert session.headers["Accept"] == "application/json"
        assert session.headers["Authorization"] == "Bearer test-token"

    def test_session_no_token(self):
        """测试无 token 时会话头"""
        from integrations.openmetadata.config import OpenMetadataConfig
        from integrations.openmetadata.client import OpenMetadataClient

        config = OpenMetadataConfig(host="test", port=8585, enabled=True, jwt_token=None)
        client = OpenMetadataClient(config=config)
        session = client.session
        assert "Authorization" not in session.headers

    @patch("requests.Session.request")
    def test_list_database_services(self, mock_request):
        """测试列出数据库服务"""
        mock_request.return_value = MagicMock(
            status_code=200,
            text='{"data": [{"name": "svc1"}]}',
        )
        mock_request.return_value.json.return_value = {"data": [{"name": "svc1"}]}
        mock_request.return_value.raise_for_status = MagicMock()

        client = self._make_client()
        result = client.list_database_services(limit=50)
        assert result == [{"name": "svc1"}]

    @patch("requests.Session.request")
    def test_create_database_service(self, mock_request):
        """测试创建数据库服务"""
        mock_request.return_value = MagicMock(
            status_code=201,
            text='{"name": "data-service"}',
        )
        mock_request.return_value.json.return_value = {"name": "data-service"}
        mock_request.return_value.raise_for_status = MagicMock()

        client = self._make_client()
        result = client.create_database_service(
            name="data-service",
            service_type="Mysql",
            description="Test service",
        )
        assert result["name"] == "data-service"

    @patch("requests.Session.request")
    def test_get_database_service_not_found(self, mock_request):
        """测试获取不存在的数据库服务"""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        mock_request.return_value = mock_response

        client = self._make_client()
        result = client.get_database_service("nonexistent")
        assert result is None

    @patch("requests.Session.request")
    def test_create_table(self, mock_request):
        """测试创建表"""
        mock_request.return_value = MagicMock(
            status_code=201,
            text='{"name": "users"}',
        )
        mock_request.return_value.json.return_value = {"name": "users"}
        mock_request.return_value.raise_for_status = MagicMock()

        client = self._make_client()
        result = client.create_table(
            name="users",
            database_fqn="data-service.mydb",
            columns=[{"name": "id", "dataType": "INT"}],
            description="Users table",
        )
        assert result["name"] == "users"

    @patch("requests.Session.request")
    def test_add_lineage(self, mock_request):
        """测试添加血缘"""
        mock_request.return_value = MagicMock(
            status_code=200,
            text='{"entity": {"id": "123"}}',
        )
        mock_request.return_value.json.return_value = {"entity": {"id": "123"}}
        mock_request.return_value.raise_for_status = MagicMock()

        client = self._make_client()
        result = client.add_lineage(
            from_entity_type="table",
            from_entity_fqn="svc.db.source",
            to_entity_type="table",
            to_entity_fqn="svc.db.target",
            description="ETL transform",
        )
        assert result["entity"]["id"] == "123"

    @patch("requests.Session.request")
    def test_search(self, mock_request):
        """测试搜索"""
        mock_request.return_value = MagicMock(
            status_code=200,
            text='{"hits": {"total": 5}}',
        )
        mock_request.return_value.json.return_value = {"hits": {"total": 5}}
        mock_request.return_value.raise_for_status = MagicMock()

        client = self._make_client()
        result = client.search("users", limit=5)
        assert result["hits"]["total"] == 5

    @patch("requests.Session.request")
    def test_request_error(self, mock_request):
        """测试请求失败异常"""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = self._make_client()
        with pytest.raises(requests.exceptions.ConnectionError):
            client.list_database_services()


# ==================== SyncService Tests ====================

class TestMetadataSyncService:
    """MetadataSyncService 测试"""

    def _make_service(self, is_available=True):
        """创建测试用同步服务"""
        from integrations.openmetadata.config import OpenMetadataConfig
        from integrations.openmetadata.sync_service import MetadataSyncService

        config = OpenMetadataConfig(host="test", port=8585, enabled=True)
        mock_client = MagicMock()
        mock_client.health_check.return_value = is_available

        service = MetadataSyncService(client=mock_client, config=config)
        return service, mock_client

    def test_is_available_true(self):
        """测试服务可用"""
        service, mock_client = self._make_service(is_available=True)
        assert service.is_available() is True

    def test_is_available_false(self):
        """测试服务不可用"""
        service, mock_client = self._make_service(is_available=False)
        assert service.is_available() is False

    def test_is_available_disabled(self):
        """测试服务禁用"""
        from integrations.openmetadata.config import OpenMetadataConfig
        from integrations.openmetadata.sync_service import MetadataSyncService

        config = OpenMetadataConfig(host="test", port=8585, enabled=False)
        service = MetadataSyncService(client=MagicMock(), config=config)
        assert service.is_available() is False

    def test_ensure_database_service_exists(self):
        """测试确保数据库服务存在（已存在）"""
        service, mock_client = self._make_service()
        mock_client.get_database_service.return_value = {"name": "data-service"}

        result = service.ensure_database_service()
        assert result["name"] == "data-service"
        mock_client.create_database_service.assert_not_called()

    def test_ensure_database_service_creates(self):
        """测试确保数据库服务存在（需要创建）"""
        service, mock_client = self._make_service()
        mock_client.get_database_service.return_value = None
        mock_client.create_database_service.return_value = {"name": "data-service"}

        result = service.ensure_database_service()
        assert result["name"] == "data-service"
        mock_client.create_database_service.assert_called_once()

    def test_sync_database_not_available(self):
        """测试不可用时跳过同步"""
        service, _ = self._make_service(is_available=False)
        result = service.sync_database("testdb")
        assert result == {}

    def test_sync_database_existing(self):
        """测试同步已存在的数据库"""
        service, mock_client = self._make_service()
        mock_client.get_database_service.return_value = {"name": "data-service"}
        mock_client.get_database.return_value = {"name": "testdb"}

        result = service.sync_database("testdb")
        assert result["name"] == "testdb"
        mock_client.create_database.assert_not_called()

    def test_sync_database_new(self):
        """测试同步新数据库"""
        service, mock_client = self._make_service()
        mock_client.get_database_service.return_value = {"name": "data-service"}
        mock_client.get_database.return_value = None
        mock_client.create_database.return_value = {"name": "testdb"}

        result = service.sync_database("testdb")
        assert result["name"] == "testdb"
        mock_client.create_database.assert_called_once()

    def test_sync_table_not_available(self):
        """测试不可用时跳过表同步"""
        service, _ = self._make_service(is_available=False)
        result = service.sync_table("db", "table", [])
        assert result == {}

    def test_sync_table_new(self):
        """测试同步新表"""
        service, mock_client = self._make_service()
        mock_client.get_database_service.return_value = {"name": "data-service"}
        mock_client.get_database.return_value = {"name": "testdb"}
        mock_client.get_table.return_value = None
        mock_client.create_table.return_value = {"name": "users"}

        columns = [
            {"name": "id", "data_type": "int"},
            {"name": "name", "data_type": "varchar", "length": 100},
        ]
        result = service.sync_table("testdb", "users", columns, description="User table")
        assert result["name"] == "users"
        mock_client.create_table.assert_called_once()

    def test_convert_columns_basic(self):
        """测试列转换（基本类型）"""
        service, _ = self._make_service()

        columns = [
            {"name": "id", "data_type": "int"},
            {"name": "name", "data_type": "varchar", "length": 100, "description": "User name"},
            {"name": "score", "data_type": "double"},
            {"name": "data", "data_type": "json"},
        ]

        result = service._convert_columns(columns)
        assert len(result) == 4
        assert result[0]["name"] == "id"
        assert result[0]["dataType"] == "INT"
        assert result[1]["dataType"] == "VARCHAR"
        assert result[1]["dataLength"] == 100
        assert result[1]["description"] == "User name"
        assert result[2]["dataType"] == "DOUBLE"
        assert result[3]["dataType"] == "JSON"

    def test_convert_columns_with_sensitivity(self):
        """测试列转换（含敏感性标签）"""
        service, _ = self._make_service()

        columns = [
            {
                "name": "phone",
                "data_type": "varchar",
                "sensitivity_level": "confidential",
                "sensitivity_type": "phone_number",
            },
        ]

        result = service._convert_columns(columns)
        assert len(result) == 1
        assert len(result[0]["tags"]) == 2
        assert result[0]["tags"][0]["tagFQN"] == "Sensitivity.confidential"
        assert result[0]["tags"][1]["tagFQN"] == "PII.PHONE_NUMBER"

    def test_convert_columns_with_ai_description(self):
        """测试列转换（含 AI 描述）"""
        service, _ = self._make_service()

        columns = [
            {
                "name": "status",
                "data_type": "int",
                "description": "Order status",
                "ai_description": "1=pending, 2=shipped, 3=delivered",
            },
        ]

        result = service._convert_columns(columns)
        assert "AI:" in result[0]["description"]
        assert "Order status" in result[0]["description"]
        assert "1=pending" in result[0]["description"]

    def test_convert_columns_unknown_type(self):
        """测试未知类型默认为 VARCHAR"""
        service, _ = self._make_service()

        columns = [{"name": "col", "data_type": "custom_type"}]
        result = service._convert_columns(columns)
        assert result[0]["dataType"] == "VARCHAR"

    def test_convert_columns_type_with_length(self):
        """测试带长度的类型（如 varchar(255)）"""
        service, _ = self._make_service()

        columns = [{"name": "col", "data_type": "varchar(255)"}]
        result = service._convert_columns(columns)
        assert result[0]["dataType"] == "VARCHAR"

    def test_sync_all_metadata_not_available(self):
        """测试不可用时批量同步全部跳过"""
        service, _ = self._make_service(is_available=False)
        tables = [MagicMock(), MagicMock(), MagicMock()]
        stats = service.sync_all_metadata(tables)
        assert stats["skipped"] == 3
        assert stats["synced"] == 0
        assert stats["failed"] == 0

    def test_sync_all_metadata_with_failures(self):
        """测试批量同步（部分失败）"""
        service, mock_client = self._make_service()

        # 设置 mock
        mock_client.get_database_service.return_value = {"name": "data-service"}
        mock_client.get_database.return_value = {"name": "db"}

        # 创建 mock 表
        mock_table1 = MagicMock()
        mock_table1.name = "table1"
        mock_table1.database.name = "db"
        mock_table1.columns = []
        mock_table1.description = "Table 1"
        mock_table1.comment = None

        mock_table2 = MagicMock()
        mock_table2.name = "table2"
        mock_table2.database.name = "db"
        mock_table2.columns = []
        mock_table2.description = None
        mock_table2.comment = None

        # 第一个成功，第二个失败
        mock_client.get_table.side_effect = [None, Exception("API error")]
        mock_client.create_table.return_value = {"name": "table1"}

        stats = service.sync_all_metadata([mock_table1, mock_table2])
        assert stats["synced"] == 1
        assert stats["failed"] == 1


# ==================== LineageService Tests ====================

class TestOpenLineageService:
    """OpenLineageService 测试"""

    def _make_service(self, is_available=True):
        """创建测试用血缘服务"""
        from integrations.openmetadata.config import OpenMetadataConfig
        from integrations.openmetadata.lineage_service import OpenLineageService

        config = OpenMetadataConfig(host="test", port=8585, enabled=True)
        mock_client = MagicMock()
        mock_client.health_check.return_value = is_available

        service = OpenLineageService(client=mock_client, config=config)
        return service, mock_client

    def test_is_available(self):
        """测试服务可用性"""
        service, _ = self._make_service(is_available=True)
        assert service.is_available() is True

        service, _ = self._make_service(is_available=False)
        assert service.is_available() is False

    def test_push_lineage_not_available(self):
        """测试不可用时推送返回空"""
        service, _ = self._make_service(is_available=False)
        result = service.push_lineage("db1", "t1", "db2", "t2")
        assert result == {}

    def test_push_lineage_success(self):
        """测试推送血缘成功"""
        service, mock_client = self._make_service()
        mock_client.add_lineage.return_value = {"entity": {"id": "123"}}

        result = service.push_lineage(
            source_db="source_db",
            source_table="source_table",
            target_db="target_db",
            target_table="target_table",
            description="ETL pipeline",
            transformation="SELECT * FROM source",
        )

        assert result["entity"]["id"] == "123"
        mock_client.add_lineage.assert_called_once()

        # 验证 FQN 格式
        call_args = mock_client.add_lineage.call_args
        assert call_args.kwargs["from_entity_fqn"] == "data-service.source_db.source_table"
        assert call_args.kwargs["to_entity_fqn"] == "data-service.target_db.target_table"

    def test_push_pipeline_lineage(self):
        """测试推送 Pipeline 血缘"""
        service, mock_client = self._make_service()
        mock_client.add_lineage.return_value = {"entity": {"id": "1"}}

        results = service.push_pipeline_lineage(
            pipeline_name="etl_job",
            input_tables=[("db1", "input1"), ("db1", "input2")],
            output_tables=[("db2", "output1")],
            description="Merge tables",
        )

        # 2 inputs × 1 output = 2 lineage edges
        assert len(results) == 2
        assert mock_client.add_lineage.call_count == 2

    def test_push_pipeline_lineage_not_available(self):
        """测试不可用时 Pipeline 血缘返回空列表"""
        service, _ = self._make_service(is_available=False)
        results = service.push_pipeline_lineage("job", [("db", "t1")], [("db", "t2")])
        assert results == []

    def test_get_table_lineage_not_available(self):
        """测试不可用时获取血缘返回空"""
        service, _ = self._make_service(is_available=False)
        result = service.get_table_lineage("db", "table")
        assert result == {}

    def test_get_table_lineage_success(self):
        """测试获取表血缘成功"""
        service, mock_client = self._make_service()
        mock_client.get_lineage.return_value = {
            "entity": {"name": "table"},
            "upstreamEdges": [{"fromEntity": {"type": "table", "name": "src"}}],
            "downstreamEdges": [{"toEntity": {"type": "table", "name": "dst"}}],
        }

        result = service.get_table_lineage("db", "table", upstream_depth=2, downstream_depth=1)
        assert "upstreamEdges" in result
        assert "downstreamEdges" in result
        mock_client.get_lineage.assert_called_once_with(
            entity_type="table",
            entity_fqn="data-service.db.table",
            upstream_depth=2,
            downstream_depth=1,
        )

    def test_get_upstream_tables(self):
        """测试获取上游表"""
        service, mock_client = self._make_service()
        mock_client.get_lineage.return_value = {
            "upstreamEdges": [
                {"fromEntity": {"type": "table", "fqn": "svc.db.src1", "name": "src1", "description": "Source 1"}},
                {"fromEntity": {"type": "table", "fqn": "svc.db.src2", "name": "src2", "description": "Source 2"}},
            ],
        }

        upstream = service.get_upstream_tables("db", "target")
        assert len(upstream) == 2
        assert upstream[0]["name"] == "src1"
        assert upstream[1]["name"] == "src2"

    def test_get_downstream_tables(self):
        """测试获取下游表"""
        service, mock_client = self._make_service()
        mock_client.get_lineage.return_value = {
            "downstreamEdges": [
                {"toEntity": {"type": "table", "fqn": "svc.db.dst1", "name": "dst1", "description": "Dest 1"}},
            ],
        }

        downstream = service.get_downstream_tables("db", "source")
        assert len(downstream) == 1
        assert downstream[0]["name"] == "dst1"

    def test_convert_node_type(self):
        """测试节点类型转换"""
        service, _ = self._make_service()

        assert service._convert_node_type("table") == "table"
        assert service._convert_node_type("database") == "table"
        assert service._convert_node_type("column") == "table"
        assert service._convert_node_type("job") == "pipeline"
        assert service._convert_node_type("model") == "mlmodel"
        assert service._convert_node_type("unknown") == "table"

    def test_build_fqn_table(self):
        """测试构建表 FQN"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "table"
        node.database_name = "mydb"
        node.table_name = "mytable"

        fqn = service._build_fqn(node)
        assert fqn == "data-service.mydb.mytable"

    def test_build_fqn_table_no_db(self):
        """测试构建表 FQN（无数据库名）"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "table"
        node.database_name = None
        node.table_name = "mytable"

        fqn = service._build_fqn(node)
        assert fqn == "data-service.default.mytable"

    def test_build_fqn_table_use_name(self):
        """测试构建表 FQN（使用 name 替代 table_name）"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "table"
        node.database_name = "mydb"
        node.table_name = None
        node.name = "alt_name"

        fqn = service._build_fqn(node)
        assert fqn == "data-service.mydb.alt_name"

    def test_build_fqn_table_no_name(self):
        """测试构建表 FQN（无任何名称）"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "table"
        node.database_name = "mydb"
        node.table_name = None
        node.name = None

        fqn = service._build_fqn(node)
        assert fqn is None

    def test_build_fqn_job(self):
        """测试构建 Job FQN"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "job"
        node.name = "etl_task_1"

        fqn = service._build_fqn(node)
        assert fqn == "data-pipelines.etl_task_1"

    def test_build_fqn_unknown_type(self):
        """测试构建未知类型 FQN"""
        service, _ = self._make_service()

        node = MagicMock()
        node.node_type = "unknown_type"

        fqn = service._build_fqn(node)
        assert fqn is None

    def test_sync_all_lineage_not_available(self):
        """测试不可用时批量同步全部跳过"""
        service, _ = self._make_service(is_available=False)
        edges = [MagicMock(), MagicMock()]
        stats = service.sync_all_lineage(edges)
        assert stats["skipped"] == 2
        assert stats["synced"] == 0

    def test_sync_all_lineage_partial_success(self):
        """测试批量同步部分成功"""
        service, mock_client = self._make_service()

        edge1 = MagicMock()
        edge1.source_node = MagicMock()
        edge1.source_node.node_type = "table"
        edge1.source_node.database_name = "db"
        edge1.source_node.table_name = "t1"
        edge1.target_node = MagicMock()
        edge1.target_node.node_type = "table"
        edge1.target_node.database_name = "db"
        edge1.target_node.table_name = "t2"
        edge1.description = "test"

        edge2 = MagicMock()
        edge2.source_node = None
        edge2.target_node = MagicMock()

        # edge1 成功（返回 {}，因为 source_node 的 push 返回空）
        # edge2 跳过（source_node is None）
        mock_client.add_lineage.return_value = {"id": "1"}

        stats = service.sync_all_lineage([edge1, edge2])
        # edge1: push_lineage_edge 调用后会返回结果 → synced
        # edge2: source_node is None → 返回 {} → skipped
        assert stats["synced"] + stats["skipped"] + stats["failed"] == 2

    def test_push_etl_task_lineage(self):
        """测试从 ETL 任务推送血缘"""
        service, mock_client = self._make_service()
        mock_client.add_lineage.return_value = {"id": "1"}

        etl_task = MagicMock()
        etl_task.name = "daily_etl"
        etl_task.description = "Daily ETL job"
        etl_task.config = {
            "source_tables": [
                {"database": "raw", "table": "orders"},
                {"database": "raw", "table": "products"},
            ],
            "target_tables": [
                {"database": "warehouse", "table": "order_summary"},
            ],
        }

        results = service.push_etl_task_lineage(etl_task)
        # 2 inputs × 1 output = 2 lineage edges
        assert len(results) == 2

    def test_push_etl_task_lineage_no_tables(self):
        """测试 ETL 任务无输入输出表"""
        service, _ = self._make_service()

        etl_task = MagicMock()
        etl_task.name = "empty_etl"
        etl_task.config = {}

        results = service.push_etl_task_lineage(etl_task)
        assert results == []

    def test_push_etl_task_lineage_not_available(self):
        """测试不可用时 ETL 任务返回空"""
        service, _ = self._make_service(is_available=False)
        results = service.push_etl_task_lineage(MagicMock())
        assert results == []
