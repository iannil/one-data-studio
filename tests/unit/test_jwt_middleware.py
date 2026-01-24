"""
JWT 中间件单元测试
Sprint 14: P1 测试覆盖
"""

import pytest
import os
import time
import jwt
from unittest.mock import patch, Mock, MagicMock
from flask import Flask, g


class TestExtractTokenFromRequest:
    """Token 提取测试"""

    @pytest.fixture
    def app(self):
        """创建测试 Flask 应用"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def test_extract_from_bearer_header(self, app):
        """测试从 Bearer Header 提取"""
        from services.shared.auth.jwt_middleware import extract_token_from_request

        with app.test_request_context(headers={'Authorization': 'Bearer test_token'}):
            from flask import request
            token = extract_token_from_request(request)
            assert token == 'test_token'

    def test_extract_from_query_parameter(self, app):
        """测试从查询参数提取"""
        from services.shared.auth.jwt_middleware import extract_token_from_request

        with app.test_request_context('/?access_token=query_token'):
            from flask import request
            token = extract_token_from_request(request)
            assert token == 'query_token'

    def test_extract_from_cookie(self, app):
        """测试从 Cookie 提取"""
        from services.shared.auth.jwt_middleware import extract_token_from_request

        with app.test_request_context(headers={'Cookie': 'access_token=cookie_token'}):
            from flask import request
            token = extract_token_from_request(request)
            assert token == 'cookie_token'

    def test_extract_priority_bearer_first(self, app):
        """测试 Bearer Header 优先级最高"""
        from services.shared.auth.jwt_middleware import extract_token_from_request

        with app.test_request_context(
            '/?access_token=query',
            headers={
                'Authorization': 'Bearer bearer_token',
                'Cookie': 'access_token=cookie'
            }
        ):
            from flask import request
            token = extract_token_from_request(request)
            assert token == 'bearer_token'

    def test_extract_returns_none_when_no_token(self, app):
        """测试无 Token 返回 None"""
        from services.shared.auth.jwt_middleware import extract_token_from_request

        with app.test_request_context():
            from flask import request
            token = extract_token_from_request(request)
            assert token is None


class TestGetUserRoles:
    """用户角色提取测试"""

    def test_extract_realm_roles(self):
        """测试提取 Realm 角色"""
        from services.shared.auth.jwt_middleware import get_user_roles

        payload = {
            "realm_access": {
                "roles": ["admin", "user"]
            }
        }
        roles = get_user_roles(payload)
        assert "admin" in roles
        assert "user" in roles

    def test_extract_resource_roles(self):
        """测试提取资源角色"""
        from services.shared.auth.jwt_middleware import get_user_roles

        payload = {
            "resource_access": {
                "web-frontend": {
                    "roles": ["viewer", "editor"]
                }
            }
        }
        roles = get_user_roles(payload)
        assert "viewer" in roles
        assert "editor" in roles

    def test_extract_combined_roles(self):
        """测试合并角色"""
        from services.shared.auth.jwt_middleware import get_user_roles

        payload = {
            "realm_access": {
                "roles": ["admin"]
            },
            "resource_access": {
                "client": {
                    "roles": ["viewer"]
                }
            }
        }
        roles = get_user_roles(payload)
        assert "admin" in roles
        assert "viewer" in roles

    def test_empty_payload_returns_empty_list(self):
        """测试空 Payload 返回空列表"""
        from services.shared.auth.jwt_middleware import get_user_roles

        roles = get_user_roles({})
        assert roles == []


class TestDecodeJwtToken:
    """JWT Token 解码测试"""

    @patch('services.shared.auth.jwt_middleware.get_keycloak_public_key')
    def test_returns_none_when_no_public_key(self, mock_get_key):
        """测试无公钥时返回 None"""
        from services.shared.auth.jwt_middleware import decode_jwt_token

        mock_get_key.return_value = None
        result = decode_jwt_token("test_token")
        assert result is None

    @patch('services.shared.auth.jwt_middleware.get_keycloak_public_key')
    def test_returns_none_on_expired_token(self, mock_get_key):
        """测试过期 Token 返回 None"""
        from services.shared.auth.jwt_middleware import decode_jwt_token

        # 生成测试密钥对
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        mock_get_key.return_value = pem

        # 创建过期的 Token
        expired_token = jwt.encode(
            {"exp": int(time.time()) - 3600, "sub": "test"},
            private_key,
            algorithm="RS256"
        )

        result = decode_jwt_token(expired_token)
        assert result is None

    @patch('services.shared.auth.jwt_middleware.get_keycloak_public_key')
    def test_returns_none_on_invalid_token(self, mock_get_key):
        """测试无效 Token 返回 None"""
        from services.shared.auth.jwt_middleware import decode_jwt_token

        mock_get_key.return_value = "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"
        result = decode_jwt_token("invalid_token")
        assert result is None


class TestGetKeycloakPublicKey:
    """Keycloak 公钥获取测试"""

    @patch('services.shared.auth.jwt_middleware.requests.get')
    def test_fetches_and_caches_public_key(self, mock_get):
        """测试获取并缓存公钥"""
        from services.shared.auth.jwt_middleware import get_keycloak_public_key, _public_key_cache

        # Mock Keycloak 响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
                    "e": "AQAB"
                }
            ]
        }
        mock_get.return_value = mock_response

        # 清除缓存
        import services.shared.auth.jwt_middleware as module
        module._public_key_cache = None
        module._public_key_cache_time = 0

        result = get_keycloak_public_key()
        assert result is not None
        assert "-----BEGIN PUBLIC KEY-----" in result

    @patch('services.shared.auth.jwt_middleware.requests.get')
    def test_returns_cached_key_within_ttl(self, mock_get):
        """测试在 TTL 内返回缓存"""
        import services.shared.auth.jwt_middleware as module

        # 设置缓存
        cached_key = "-----BEGIN PUBLIC KEY-----\nCACHED\n-----END PUBLIC KEY-----"
        module._public_key_cache = cached_key
        module._public_key_cache_time = time.time()

        result = get_keycloak_public_key()
        assert result == cached_key
        mock_get.assert_not_called()

    @patch('services.shared.auth.jwt_middleware.requests.get')
    def test_returns_cached_on_error(self, mock_get):
        """测试获取失败时返回缓存"""
        import services.shared.auth.jwt_middleware as module

        module._public_key_cache = "cached_key"
        module._public_key_cache_time = 0  # 缓存过期

        mock_get.side_effect = Exception("Network error")

        result = get_keycloak_public_key()
        assert result == "cached_key"


class TestRequireJwtDecorator:
    """require_jwt 装饰器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from services.shared.auth.jwt_middleware import require_jwt

        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/protected')
        @require_jwt()
        def protected():
            return {"user": g.user}

        @app.route('/optional')
        @require_jwt(optional=True)
        def optional():
            return {"user": g.user if hasattr(g, 'user') else None}

        return app

    def test_returns_401_without_token(self, app):
        """测试无 Token 返回 401"""
        with app.test_client() as client:
            response = client.get('/protected')
            assert response.status_code == 401

    def test_optional_allows_unauthenticated(self, app):
        """测试可选认证允许未认证请求"""
        with app.test_client() as client:
            response = client.get('/optional')
            assert response.status_code == 200

    @patch('services.shared.auth.jwt_middleware.decode_jwt_token')
    def test_sets_user_info_on_valid_token(self, mock_decode, app):
        """测试有效 Token 设置用户信息"""
        mock_decode.return_value = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "name": "Test User",
            "realm_access": {"roles": ["user"]}
        }

        with app.test_client() as client:
            response = client.get('/protected', headers={
                'Authorization': 'Bearer valid_token'
            })
            assert response.status_code == 200

    @patch('services.shared.auth.jwt_middleware.decode_jwt_token')
    def test_returns_401_on_invalid_token(self, mock_decode, app):
        """测试无效 Token 返回 401"""
        mock_decode.return_value = None

        with app.test_client() as client:
            response = client.get('/protected', headers={
                'Authorization': 'Bearer invalid_token'
            })
            assert response.status_code == 401


class TestRequireRoleDecorator:
    """require_role 装饰器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from services.shared.auth.jwt_middleware import require_jwt, require_role

        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/admin')
        @require_jwt()
        @require_role("admin")
        def admin():
            return {"status": "ok"}

        @app.route('/multi-role')
        @require_jwt()
        @require_role("admin", "super_admin")
        def multi_role():
            return {"status": "ok"}

        return app

    @patch('services.shared.auth.jwt_middleware.decode_jwt_token')
    def test_allows_user_with_role(self, mock_decode, app):
        """测试有角色的用户通过"""
        mock_decode.return_value = {
            "sub": "user-123",
            "realm_access": {"roles": ["admin"]}
        }

        with app.test_client() as client:
            response = client.get('/admin', headers={
                'Authorization': 'Bearer token'
            })
            assert response.status_code == 200

    @patch('services.shared.auth.jwt_middleware.decode_jwt_token')
    def test_denies_user_without_role(self, mock_decode, app):
        """测试无角色的用户被拒绝"""
        mock_decode.return_value = {
            "sub": "user-123",
            "realm_access": {"roles": ["user"]}
        }

        with app.test_client() as client:
            response = client.get('/admin', headers={
                'Authorization': 'Bearer token'
            })
            assert response.status_code == 403

    @patch('services.shared.auth.jwt_middleware.decode_jwt_token')
    def test_allows_user_with_any_required_role(self, mock_decode, app):
        """测试有任一所需角色的用户通过"""
        mock_decode.return_value = {
            "sub": "user-123",
            "realm_access": {"roles": ["super_admin"]}
        }

        with app.test_client() as client:
            response = client.get('/multi-role', headers={
                'Authorization': 'Bearer token'
            })
            assert response.status_code == 200


class TestGetCurrentUser:
    """get_current_user 测试"""

    def test_returns_none_without_payload(self):
        """测试无 Payload 返回 None"""
        from services.shared.auth.jwt_middleware import get_current_user

        app = Flask(__name__)
        with app.test_request_context():
            result = get_current_user()
            assert result is None

    def test_returns_user_info_with_payload(self):
        """测试有 Payload 返回用户信息"""
        from services.shared.auth.jwt_middleware import get_current_user

        app = Flask(__name__)
        with app.test_request_context():
            g.payload = {"sub": "user-123"}
            g.user_id = "user-123"
            g.user = "testuser"
            g.email = "test@example.com"
            g.name = "Test User"
            g.roles = ["user"]

            result = get_current_user()
            assert result is not None
            assert result["user_id"] == "user-123"
            assert result["username"] == "testuser"
            assert result["email"] == "test@example.com"


class TestHealthCheckEndpoint:
    """健康检查端点判断测试"""

    def test_identifies_health_check_endpoints(self):
        """测试识别健康检查端点"""
        from services.shared.auth.jwt_middleware import is_health_check_endpoint

        app = Flask(__name__)

        with app.test_request_context('/health'):
            from flask import request
            assert is_health_check_endpoint(request) is True

        with app.test_request_context('/readiness'):
            from flask import request
            assert is_health_check_endpoint(request) is True

        with app.test_request_context('/metrics'):
            from flask import request
            assert is_health_check_endpoint(request) is True

    def test_identifies_non_health_endpoints(self):
        """测试识别非健康检查端点"""
        from services.shared.auth.jwt_middleware import is_health_check_endpoint

        app = Flask(__name__)

        with app.test_request_context('/api/v1/users'):
            from flask import request
            assert is_health_check_endpoint(request) is False
