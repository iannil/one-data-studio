"""
配置模块单元测试
Sprint 9: 测试覆盖
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from services.shared.config import (
    Config,
    DatabaseConfig,
    MinIOConfig,
    MilvusConfig,
    OpenAIConfig,
    KeycloakConfig,
    ServiceConfig,
    LoggingConfig,
    RedisConfig,
    CeleryConfig,
    get_config,
    reload_config
)


class TestDatabaseConfig:
    """数据库配置测试"""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_values(self):
        """测试默认值"""
        # Clear environment to test actual defaults
        for key in ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_DATABASE',
                    'DB_POOL_SIZE', 'DB_MAX_OVERFLOW']:
            os.environ.pop(key, None)
        config = DatabaseConfig()
        assert config.host == "mysql.one-data-infra.svc.cluster.local"
        assert config.port == 3306
        assert config.user == "one_data"
        assert config.database == "one_data_studio"
        assert config.pool_size == 10
        assert config.max_overflow == 20

    def test_url_generation(self):
        """测试 URL 生成"""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            user="root",
            password="pass",
            database="test"
        )
        url = config.url
        assert "mysql+pymysql://" in url
        assert "root:pass" in url
        assert "localhost:3306" in url
        assert "test" in url

    @patch.dict(os.environ, {
        "MYSQL_HOST": "custom-host",
        "MYSQL_PORT": "3307",
        "MYSQL_USER": "custom-user"
    })
    def test_env_override(self):
        """测试环境变量覆盖"""
        config = DatabaseConfig()
        assert config.host == "custom-host"
        assert config.port == 3307
        assert config.user == "custom-user"


class TestRedisConfig:
    """Redis 配置测试 - Sprint 8"""

    def test_default_values(self):
        """测试默认值"""
        config = RedisConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.max_connections == 50

    def test_ttl_defaults(self):
        """测试 TTL 默认值"""
        config = RedisConfig()
        assert config.metadata_ttl == 300
        assert config.model_list_ttl == 600
        assert config.workflow_ttl == 180
        assert config.search_result_ttl == 60

    def test_url_generation_without_password(self):
        """测试无密码 URL 生成"""
        config = RedisConfig(host="localhost", port=6379, db=0, password=None)
        assert config.url == "redis://localhost:6379/0"

    def test_url_generation_with_password(self):
        """测试带密码 URL 生成"""
        config = RedisConfig(host="localhost", port=6379, db=0, password="secret")
        assert config.url == "redis://:secret@localhost:6379/0"

    @patch.dict(os.environ, {"REDIS_ENABLED": "false"})
    def test_disabled(self):
        """测试 Redis 禁用状态"""
        config = RedisConfig()
        assert not config.enabled


class TestCeleryConfig:
    """Celery 配置测试 - Sprint 8"""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_values(self):
        """测试默认值"""
        # Clear environment to test actual defaults
        for key in ['CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND', 'CELERY_TASK_TIME_LIMIT']:
            os.environ.pop(key, None)
        config = CeleryConfig()
        assert "redis://localhost:6379/1" in config.broker_url
        assert "redis://localhost:6379/2" in config.result_backend
        assert config.task_track_started is True
        assert config.task_time_limit == 3600


class TestConfig:
    """统一配置测试"""

    @patch("services.shared.config.Config._validate_production_config")
    @patch("services.shared.config.LoggingConfig.setup")
    def test_init(self, mock_setup, mock_validate):
        """测试初始化"""
        config = Config()
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.minio, MinIOConfig)
        assert isinstance(config.milvus, MilvusConfig)
        assert isinstance(config.openai, OpenAIConfig)
        assert isinstance(config.keycloak, KeycloakConfig)
        assert isinstance(config.service, ServiceConfig)
        assert isinstance(config.redis, RedisConfig)  # Sprint 8
        assert isinstance(config.celery, CeleryConfig)  # Sprint 8
        assert isinstance(config.logging, LoggingConfig)
        mock_setup.assert_called_once()

    def test_to_dict_hides_passwords(self):
        """测试导出时隐藏密码"""
        config = Config()
        data = config.to_dict()
        assert data["database"]["password"] == "***HIDDEN***"
        assert data["minio"]["secret_key"] == "***HIDDEN***"
        assert data["openai"]["api_key"] == "***HIDDEN***" or data["openai"]["api_key"] is None

    def test_get_service_url(self):
        """测试获取服务 URL"""
        config = Config()
        assert config.get_service_url("data") == config.service.data_api_url
        assert config.get_service_url("agent") == config.service.agent_api_url
        assert config.get_service_url("model") == config.service.model_api_url
        assert config.get_service_url("invalid") is None


class TestConfigSingleton:
    """配置单例测试"""

    def test_get_config_singleton(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_config(self):
        """测试重新加载"""
        config1 = get_config()
        config2 = reload_config()
        assert config1 is not config2
        assert isinstance(config2, Config)
