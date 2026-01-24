"""
TLS 配置模块单元测试
Sprint 21: P2 测试覆盖 - Security Hardening
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestTLSConfig:
    """TLS 配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        from services.shared.security.tls import TLSConfig

        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            config = TLSConfig()
            # 在非生产环境下不强制 HTTPS
            assert config.min_tls_version == 'TLSv1.2'

    def test_force_https_in_production(self):
        """测试生产环境强制 HTTPS"""
        from services.shared.security.tls import TLSConfig

        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'SECURITY_FORCE_HTTPS': 'true'
        }):
            config = TLSConfig()
            assert config.force_https is True

    def test_exempt_paths(self):
        """测试豁免路径"""
        from services.shared.security.tls import TLSConfig

        config = TLSConfig()

        assert config.is_exempt('/api/v1/health') is True
        assert config.is_exempt('/metrics') is True
        assert config.is_exempt('/.well-known/acme') is True
        assert config.is_exempt('/api/v1/users') is False

    def test_is_https_direct(self):
        """测试直接 HTTPS 检测"""
        from services.shared.security.tls import TLSConfig

        config = TLSConfig()
        mock_request = MagicMock()
        mock_request.is_secure = True
        mock_request.headers.get.return_value = ''

        assert config.is_https(mock_request) is True

    def test_is_https_via_proxy(self):
        """测试通过代理的 HTTPS 检测"""
        from services.shared.security.tls import TLSConfig

        config = TLSConfig()
        config.trust_proxy = True

        mock_request = MagicMock()
        mock_request.is_secure = False
        mock_request.headers.get.return_value = 'https'

        assert config.is_https(mock_request) is True

    def test_get_https_url(self):
        """测试获取 HTTPS URL"""
        from services.shared.security.tls import TLSConfig

        config = TLSConfig()
        mock_request = MagicMock()
        mock_request.url = 'http://example.com/path'

        https_url = config.get_https_url(mock_request)

        assert https_url == 'https://example.com/path'

    def test_get_https_url_already_https(self):
        """测试已是 HTTPS 的 URL"""
        from services.shared.security.tls import TLSConfig

        config = TLSConfig()
        mock_request = MagicMock()
        mock_request.url = 'https://example.com/path'

        https_url = config.get_https_url(mock_request)

        assert https_url == 'https://example.com/path'


class TestGetTLSConfig:
    """获取 TLS 配置测试"""

    def test_get_tls_config_singleton(self):
        """测试 TLS 配置单例"""
        from services.shared.security.tls import get_tls_config

        config1 = get_tls_config()
        config2 = get_tls_config()

        assert config1 is config2


class TestRequireHTTPS:
    """require_https 中间件测试"""

    def test_require_https_disabled(self):
        """测试禁用 HTTPS 强制"""
        from services.shared.security.tls import require_https, TLSConfig

        mock_app = MagicMock()
        config = TLSConfig()
        config.force_https = False

        require_https(mock_app, config)

        # 不应该注册 before_request
        mock_app.before_request.assert_not_called()

    def test_require_https_enabled(self):
        """测试启用 HTTPS 强制"""
        from services.shared.security.tls import require_https, TLSConfig

        mock_app = MagicMock()
        config = TLSConfig()
        config.force_https = True

        require_https(mock_app, config)

        mock_app.before_request.assert_called_once()


class TestHTTPSRequired:
    """https_required 装饰器测试"""

    def test_https_required_decorator(self):
        """测试 HTTPS 必需装饰器"""
        from services.shared.security.tls import https_required

        @https_required
        def my_endpoint():
            return "OK"

        # 装饰器应该保留函数
        assert callable(my_endpoint)


class TestGenerateNginxTLSConfig:
    """生成 Nginx TLS 配置测试"""

    def test_generate_basic_config(self):
        """测试生成基本配置"""
        from services.shared.security.tls import generate_nginx_tls_config

        config = generate_nginx_tls_config(
            cert_path='/etc/ssl/cert.pem',
            key_path='/etc/ssl/key.pem'
        )

        assert 'ssl_certificate /etc/ssl/cert.pem' in config
        assert 'ssl_certificate_key /etc/ssl/key.pem' in config
        assert 'TLSv1.2' in config
        assert 'ssl_prefer_server_ciphers on' in config

    def test_generate_config_with_dhparam(self):
        """测试生成带 DH 参数的配置"""
        from services.shared.security.tls import generate_nginx_tls_config

        config = generate_nginx_tls_config(
            cert_path='/etc/ssl/cert.pem',
            key_path='/etc/ssl/key.pem',
            dhparam_path='/etc/ssl/dhparam.pem'
        )

        assert 'ssl_dhparam /etc/ssl/dhparam.pem' in config

    def test_generate_config_includes_hsts(self):
        """测试配置包含 HSTS"""
        from services.shared.security.tls import generate_nginx_tls_config

        config = generate_nginx_tls_config(
            cert_path='/etc/ssl/cert.pem',
            key_path='/etc/ssl/key.pem'
        )

        assert 'Strict-Transport-Security' in config


class TestGenerateSSLContext:
    """生成 SSL 上下文测试"""

    def test_generate_ssl_context(self):
        """测试生成 SSL 上下文"""
        from services.shared.security.tls import generate_ssl_context
        import ssl

        context = generate_ssl_context()

        assert isinstance(context, ssl.SSLContext)
        assert context.minimum_version == ssl.TLSVersion.TLSv1_2
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED
