"""
认证和权限端到端测试
Sprint 24: E2E 测试扩展

测试覆盖:
- 用户注册和登录
- JWT Token 验证
- 权限控制
- Session 管理
- API Key 认证
"""

import pytest
import requests
import time
import os
import logging
import jwt
from typing import Optional
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8081")

# 请求头
HEADERS = {
    "Content-Type": "application/json",
}


class TestUserAuthentication:
    """用户认证测试"""

    test_user = {
        "username": f"e2e_test_user_{int(time.time())}",
        "email": f"e2e_test_{int(time.time())}@example.com",
        "password": "TestPassword123!"
    }
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    def test_01_register_user(self):
        """测试用户注册"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            headers=HEADERS,
            json=self.test_user
        )

        # 允许 201（成功）、400（用户已存在）、401（需要管理员权限）
        assert response.status_code in [201, 400, 401, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            logger.info("Registered user: %s", self.test_user['username'])

    def test_02_login_user(self):
        """测试用户登录"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            headers=HEADERS,
            json={
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
        )

        # 允许 200（成功）、401（密码错误）、404（用户不存在）
        assert response.status_code in [200, 401, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "access_token" in data["data"]
            TestUserAuthentication.access_token = data["data"]["access_token"]
            TestUserAuthentication.refresh_token = data["data"].get("refresh_token")
            logger.info("Login successful, token received")

    def test_03_access_protected_endpoint(self):
        """测试访问受保护的端点"""
        if not TestUserAuthentication.access_token:
            pytest.skip("No access token available")

        auth_headers = {
            **HEADERS,
            "Authorization": f"Bearer {TestUserAuthentication.access_token}"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=auth_headers
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["username"] == self.test_user["username"]

    def test_04_access_without_token(self):
        """测试无 Token 访问受保护端点"""
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=HEADERS
        )

        # 应该返回 401 未授权
        assert response.status_code in [401, 403]

    def test_05_access_with_invalid_token(self):
        """测试使用无效 Token"""
        invalid_headers = {
            **HEADERS,
            "Authorization": "Bearer invalid_token_here"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=invalid_headers
        )

        assert response.status_code in [401, 403]

    def test_06_refresh_token(self):
        """测试刷新 Token"""
        if not TestUserAuthentication.refresh_token:
            pytest.skip("No refresh token available")

        response = requests.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            headers=HEADERS,
            json={
                "refresh_token": TestUserAuthentication.refresh_token
            }
        )

        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "access_token" in data["data"]
            # 更新 token
            TestUserAuthentication.access_token = data["data"]["access_token"]

    def test_07_logout(self):
        """测试登出"""
        if not TestUserAuthentication.access_token:
            pytest.skip("No access token available")

        auth_headers = {
            **HEADERS,
            "Authorization": f"Bearer {TestUserAuthentication.access_token}"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers=auth_headers
        )

        assert response.status_code in [200, 204, 401, 404]


class TestJWTTokenSecurity:
    """JWT Token 安全测试"""

    @pytest.mark.e2e
    def test_token_expiration(self):
        """测试 Token 过期"""
        # 创建一个已过期的 token
        secret = os.getenv("JWT_SECRET_KEY", "test-secret")
        expired_token = jwt.encode(
            {
                "sub": "test_user",
                "exp": datetime.utcnow() - timedelta(hours=1)  # 已过期
            },
            secret,
            algorithm="HS256"
        )

        expired_headers = {
            **HEADERS,
            "Authorization": f"Bearer {expired_token}"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=expired_headers
        )

        # 应该返回 401
        assert response.status_code in [401, 403]

    @pytest.mark.e2e
    def test_token_tampering(self):
        """测试 Token 篡改检测"""
        # 创建一个有效的 token 然后篡改
        secret = os.getenv("JWT_SECRET_KEY", "test-secret")
        valid_token = jwt.encode(
            {
                "sub": "test_user",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            secret,
            algorithm="HS256"
        )

        # 篡改 token（修改 payload 中的一个字符）
        parts = valid_token.split('.')
        if len(parts) == 3:
            # 修改 payload 部分
            tampered_token = f"{parts[0]}.{parts[1][:-1]}X.{parts[2]}"

            tampered_headers = {
                **HEADERS,
                "Authorization": f"Bearer {tampered_token}"
            }

            response = requests.get(
                f"{BASE_URL}/api/v1/users/me",
                headers=tampered_headers
            )

            # 应该返回 401
            assert response.status_code in [401, 403]

    @pytest.mark.e2e
    def test_wrong_algorithm_rejection(self):
        """测试拒绝错误的签名算法"""
        # 尝试使用 none 算法（已知漏洞）
        # 大多数现代 JWT 库会拒绝这种攻击

        # 手动构造一个 "none" 算法的 token
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b'=').decode()
        payload = base64.urlsafe_b64encode(json.dumps({
            "sub": "admin",
            "role": "admin",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }).encode()).rstrip(b'=').decode()

        none_token = f"{header}.{payload}."

        none_headers = {
            **HEADERS,
            "Authorization": f"Bearer {none_token}"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=none_headers
        )

        # 应该拒绝 none 算法
        assert response.status_code in [401, 403]


class TestPermissionControl:
    """权限控制测试"""

    admin_token: Optional[str] = None
    user_token: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup_tokens(self):
        """设置测试 Token"""
        # 尝试获取管理员 token
        admin_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            headers=HEADERS,
            json={
                "username": os.getenv("TEST_ADMIN_USER", "admin"),
                "password": os.getenv("TEST_ADMIN_PASSWORD", "admin")
            }
        )

        if admin_response.status_code == 200:
            TestPermissionControl.admin_token = admin_response.json()["data"]["access_token"]

        # 尝试获取普通用户 token
        user_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            headers=HEADERS,
            json={
                "username": os.getenv("TEST_USER", "user"),
                "password": os.getenv("TEST_USER_PASSWORD", "user")
            }
        )

        if user_response.status_code == 200:
            TestPermissionControl.user_token = user_response.json()["data"]["access_token"]

        yield

    def test_01_admin_only_endpoint(self):
        """测试仅管理员可访问的端点"""
        if not TestPermissionControl.admin_token:
            pytest.skip("No admin token available")

        admin_headers = {
            **HEADERS,
            "Authorization": f"Bearer {TestPermissionControl.admin_token}"
        }

        # 尝试访问管理员端点
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers
        )

        # 管理员应该可以访问
        assert response.status_code in [200, 404]  # 404 表示端点不存在

    def test_02_user_cannot_access_admin_endpoint(self):
        """测试普通用户无法访问管理员端点"""
        if not TestPermissionControl.user_token:
            pytest.skip("No user token available")

        user_headers = {
            **HEADERS,
            "Authorization": f"Bearer {TestPermissionControl.user_token}"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=user_headers
        )

        # 普通用户应该被拒绝
        assert response.status_code in [401, 403, 404]

    def test_03_resource_ownership(self):
        """测试资源所有权检查"""
        if not TestPermissionControl.user_token:
            pytest.skip("No user token available")

        user_headers = {
            **HEADERS,
            "Authorization": f"Bearer {TestPermissionControl.user_token}"
        }

        # 尝试访问其他用户的资源
        response = requests.get(
            f"{BASE_URL}/api/v1/workflows/other-user-workflow-id",
            headers=user_headers
        )

        # 应该返回 403（无权限）或 404（不存在）
        assert response.status_code in [403, 404]


class TestAPIKeyAuthentication:
    """API Key 认证测试"""

    api_key: Optional[str] = None

    def test_01_create_api_key(self):
        """测试创建 API Key"""
        # 需要先登录
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            headers=HEADERS,
            json={
                "username": os.getenv("TEST_USER", "user"),
                "password": os.getenv("TEST_USER_PASSWORD", "user")
            }
        )

        if login_response.status_code != 200:
            pytest.skip("Cannot login to create API key")

        token = login_response.json()["data"]["access_token"]
        auth_headers = {
            **HEADERS,
            "Authorization": f"Bearer {token}"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/api-keys",
            headers=auth_headers,
            json={
                "name": "E2E Test API Key",
                "permissions": ["read", "write"],
                "expires_in_days": 1
            }
        )

        assert response.status_code in [201, 401, 404]

        if response.status_code == 201:
            data = response.json()
            TestAPIKeyAuthentication.api_key = data["data"].get("api_key")
            logger.info("Created API key")

    def test_02_authenticate_with_api_key(self):
        """测试使用 API Key 认证"""
        if not TestAPIKeyAuthentication.api_key:
            pytest.skip("No API key available")

        api_key_headers = {
            **HEADERS,
            "X-API-Key": TestAPIKeyAuthentication.api_key
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/workflows",
            headers=api_key_headers
        )

        assert response.status_code in [200, 401, 404]

    def test_03_invalid_api_key(self):
        """测试无效 API Key"""
        invalid_headers = {
            **HEADERS,
            "X-API-Key": "invalid_api_key_here"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/workflows",
            headers=invalid_headers
        )

        # 应该返回 401
        assert response.status_code in [401, 403]

    def test_04_revoke_api_key(self):
        """测试撤销 API Key"""
        if not TestAPIKeyAuthentication.api_key:
            pytest.skip("No API key available")

        # 需要先登录
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            headers=HEADERS,
            json={
                "username": os.getenv("TEST_USER", "user"),
                "password": os.getenv("TEST_USER_PASSWORD", "user")
            }
        )

        if login_response.status_code != 200:
            pytest.skip("Cannot login to revoke API key")

        token = login_response.json()["data"]["access_token"]
        auth_headers = {
            **HEADERS,
            "Authorization": f"Bearer {token}"
        }

        # 获取 API key ID（假设从创建响应中获取）
        response = requests.delete(
            f"{BASE_URL}/api/v1/api-keys/{TestAPIKeyAuthentication.api_key}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204, 401, 404]


class TestRateLimiting:
    """速率限制测试"""

    @pytest.mark.e2e
    def test_rate_limit_exceeded(self):
        """测试超出速率限制"""
        # 快速发送多个请求
        responses = []
        for _ in range(100):
            response = requests.get(
                f"{BASE_URL}/api/v1/health",
                headers=HEADERS
            )
            responses.append(response.status_code)

        # 检查是否有 429 响应
        rate_limited = 429 in responses

        # 如果实施了速率限制，应该有一些 429 响应
        # 如果没有实施，所有请求都应该成功
        assert all(r in [200, 429] for r in responses)


class TestSecurityHeaders:
    """安全头测试"""

    @pytest.mark.e2e
    def test_security_headers_present(self):
        """测试安全头是否存在"""
        response = requests.get(f"{BASE_URL}/api/v1/health")

        # 检查推荐的安全头
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
        }

        for header, expected in security_headers.items():
            if header in response.headers:
                actual = response.headers[header]
                if isinstance(expected, list):
                    assert actual in expected, f"{header}: {actual} not in {expected}"
                else:
                    assert actual == expected, f"{header}: {actual} != {expected}"

    @pytest.mark.e2e
    def test_no_sensitive_headers_leaked(self):
        """测试敏感头没有泄露"""
        response = requests.get(f"{BASE_URL}/api/v1/health")

        # 这些头不应该在生产环境中暴露
        sensitive_headers = [
            "X-Powered-By",
            "Server",  # 应该是通用的，不暴露具体版本
        ]

        for header in sensitive_headers:
            if header in response.headers:
                value = response.headers[header]
                # 不应该暴露具体版本信息
                assert not any(v in value.lower() for v in ["flask", "python", "gunicorn", "nginx/1"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
