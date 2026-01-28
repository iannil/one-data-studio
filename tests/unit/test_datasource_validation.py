"""
数据源验证单元测试
用例覆盖: DM-DS-001 ~ DM-DS-007

测试数据源注册、连接测试、编辑和删除的验证逻辑。
"""

import pytest
from unittest.mock import Mock, MagicMock


# ==================== 内联业务逻辑实现 ====================

SUPPORTED_TYPES = {"mysql", "postgresql", "oracle", "sqlserver", "hive"}
REQUIRED_FIELDS = ["name", "type", "host", "port", "username", "password", "database"]


def validate_datasource_config(config):
    """验证数据源配置，返回错误列表。"""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in config or config[field] is None or config[field] == "":
            errors.append(f"缺少必填字段: {field}")
    if "port" in config and config["port"] is not None:
        port = config["port"]
        if not isinstance(port, int) or port <= 0 or port > 65535:
            errors.append(f"port 必须为 1-65535 之间的整数")
    if "type" in config and config["type"] not in SUPPORTED_TYPES:
        errors.append(f"不支持的数据源 type: {config['type']}")
    return errors


def check_datasource_connection(config, _create_connection=None):
    """测试数据源连接，返回结果字典。

    Args:
        config: 数据源配置字典
        _create_connection: 可选的连接创建函数（用于测试注入）
    """
    if _create_connection is None:
        raise NotImplementedError("需要提供 _create_connection 函数")
    try:
        conn = _create_connection(config)
        conn.execute("SELECT 1")
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def can_delete_datasource(ds_id, _get_references=None):
    """检查数据源是否可删除，返回结果字典。

    Args:
        ds_id: 数据源 ID
        _get_references: 可选的引用查询函数（用于测试注入）
    """
    if _get_references is None:
        raise NotImplementedError("需要提供 _get_references 函数")
    references = _get_references(ds_id)
    if not references:
        return {"can_delete": True, "message": "可以删除", "references": []}
    return {
        "can_delete": False,
        "message": "该数据源正在被使用，无法删除",
        "references": references,
    }


# ==================== 测试数据 ====================

MYSQL_DATASOURCE = {
    "name": "test_mysql",
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "test123",
    "database": "test_db",
}

POSTGRES_DATASOURCE = {
    "name": "test_postgres",
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "username": "postgres",
    "password": "test123",
    "database": "test_db",
}

ORACLE_DATASOURCE = {
    "name": "test_oracle",
    "type": "oracle",
    "host": "localhost",
    "port": 1521,
    "username": "system",
    "password": "test123",
    "database": "ORCL",
}

INVALID_DATASOURCE = {
    "name": "invalid_ds",
    "type": "mysql",
    "host": "invalid-host",
    "port": 9999,
    "username": "wrong",
    "password": "wrong",
    "database": "nonexistent",
}


@pytest.mark.unit
class TestDatasourceRegistration:
    """数据源注册测试 - DM-DS-001/002/003"""

    def test_register_mysql_datasource_valid(self):
        """DM-DS-001: 注册 MySQL 数据源 - 有效配置"""
        errors = validate_datasource_config(MYSQL_DATASOURCE)
        assert errors == []

    def test_register_postgresql_datasource_valid(self):
        """DM-DS-002: 注册 PostgreSQL 数据源 - 有效配置"""
        errors = validate_datasource_config(POSTGRES_DATASOURCE)
        assert errors == []

    def test_register_oracle_datasource_valid(self):
        """DM-DS-003: 注册 Oracle 数据源 - 有效配置"""
        errors = validate_datasource_config(ORACLE_DATASOURCE)
        assert errors == []

    def test_register_datasource_missing_name(self):
        """注册数据源 - 缺少名称"""
        config = {**MYSQL_DATASOURCE}
        del config["name"]
        errors = validate_datasource_config(config)
        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)

    def test_register_datasource_missing_host(self):
        """注册数据源 - 缺少主机"""
        config = {**MYSQL_DATASOURCE}
        del config["host"]
        errors = validate_datasource_config(config)
        assert len(errors) > 0
        assert any("host" in e.lower() for e in errors)

    def test_register_datasource_invalid_port(self):
        """注册数据源 - 无效端口"""
        config = {**MYSQL_DATASOURCE, "port": -1}
        errors = validate_datasource_config(config)
        assert len(errors) > 0
        assert any("port" in e.lower() for e in errors)

    def test_register_datasource_invalid_type(self):
        """注册数据源 - 不支持的类型"""
        config = {**MYSQL_DATASOURCE, "type": "unsupported_db"}
        errors = validate_datasource_config(config)
        assert len(errors) > 0
        assert any("type" in e.lower() for e in errors)

    def test_register_datasource_port_out_of_range(self):
        """注册数据源 - 端口超出范围"""
        config = {**MYSQL_DATASOURCE, "port": 70000}
        errors = validate_datasource_config(config)
        assert len(errors) > 0


@pytest.mark.unit
class TestDatasourceConnectionTest:
    """数据源连接测试 - DM-DS-004"""

    def test_connection_test_success(self):
        """DM-DS-004: 连接测试成功"""
        mock_conn = Mock()
        mock_conn.return_value = Mock()
        mock_conn.return_value.execute = Mock(return_value=True)

        result = check_datasource_connection(MYSQL_DATASOURCE, _create_connection=mock_conn)
        assert result["success"] is True
        assert result["message"] == "连接成功"

    def test_connection_test_failure(self):
        """DM-DS-004: 连接测试失败 - 错误连接信息"""
        mock_conn = Mock(side_effect=Exception("Connection refused"))

        result = check_datasource_connection(INVALID_DATASOURCE, _create_connection=mock_conn)
        assert result["success"] is False
        assert "Connection refused" in result["message"]

    def test_connection_test_timeout(self):
        """连接测试超时"""
        mock_conn = Mock(side_effect=TimeoutError("Connection timed out"))

        result = check_datasource_connection(INVALID_DATASOURCE, _create_connection=mock_conn)
        assert result["success"] is False
        assert "timed out" in result["message"].lower()

    def test_connection_test_auth_failure(self):
        """连接测试认证失败"""
        mock_conn = Mock(side_effect=Exception("Access denied for user"))

        result = check_datasource_connection(INVALID_DATASOURCE, _create_connection=mock_conn)
        assert result["success"] is False
        assert "Access denied" in result["message"]


@pytest.mark.unit
class TestDatasourceEdit:
    """数据源编辑测试 - DM-DS-005"""

    def test_edit_datasource_valid_changes(self):
        """DM-DS-005: 编辑数据源 - 有效变更"""
        updated = {**MYSQL_DATASOURCE, "host": "new-host", "port": 3307}
        errors = validate_datasource_config(updated)
        assert errors == []

    def test_edit_datasource_name_change(self):
        """编辑数据源 - 修改名称"""
        updated = {**MYSQL_DATASOURCE, "name": "updated_name"}
        errors = validate_datasource_config(updated)
        assert errors == []


@pytest.mark.unit
class TestDatasourceDelete:
    """数据源删除测试 - DM-DS-006/007"""

    def test_delete_unreferenced_datasource(self):
        """DM-DS-006: 删除未被引用的数据源"""
        mock_refs = Mock(return_value=[])
        result = can_delete_datasource("ds-001", _get_references=mock_refs)
        assert result["can_delete"] is True

    def test_delete_referenced_datasource_blocked(self):
        """DM-DS-007: 删除被引用的数据源被阻止"""
        mock_refs = Mock(return_value=[
            {"type": "etl_task", "id": "etl-001", "name": "Daily ETL"}
        ])
        result = can_delete_datasource("ds-001", _get_references=mock_refs)
        assert result["can_delete"] is False
        assert "正在被使用" in result["message"] or "使用" in result["message"]
        assert len(result["references"]) == 1

    def test_delete_multi_referenced_datasource(self):
        """删除被多个任务引用的数据源"""
        mock_refs = Mock(return_value=[
            {"type": "etl_task", "id": "etl-001", "name": "Daily ETL"},
            {"type": "metadata_scan", "id": "scan-001", "name": "Auto Scan"},
        ])
        result = can_delete_datasource("ds-001", _get_references=mock_refs)
        assert result["can_delete"] is False
        assert len(result["references"]) == 2
