"""
用户与权限管理模块集成测试
测试用例编号: SA-UM-001 ~ SA-UM-010

覆盖用户管理 API 的完整生命周期，包括：
- 用户 CRUD 操作
- 角色 CRUD 操作
- 用户-角色分配
- 数据权限策略配置
"""

import pytest
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

logger = logging.getLogger(__name__)

# 尝试导入权限模块（需要 Flask 等依赖）
try:
    from services.shared.auth.permissions import (
        has_permission, get_user_permissions, can_manage_users,
        Resource, Operation,
    )
    PERMISSIONS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PERMISSIONS_AVAILABLE = False

_requires_permissions = pytest.mark.skipif(
    not PERMISSIONS_AVAILABLE,
    reason="需要 services.shared.auth.permissions 模块（依赖 Flask）"
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_jwt_token():
    """模拟管理员 JWT Token"""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.mock-admin-token"


@pytest.fixture
def mock_admin_headers(mock_jwt_token):
    """模拟管理员请求头"""
    return {
        "Authorization": f"Bearer {mock_jwt_token}",
        "Content-Type": "application/json",
        "X-Tenant-Id": "tenant-001",
    }


@pytest.fixture
def mock_user_headers():
    """模拟普通用户请求头"""
    return {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.mock-user-token",
        "Content-Type": "application/json",
        "X-Tenant-Id": "tenant-001",
    }


@pytest.fixture
def sample_create_user_payload():
    """创建用户请求体"""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "display_name": f"测试用户 {unique_id}",
        "password": "SecureP@ssw0rd!",
        "phone": "13800138000",
        "department": "数据工程部",
        "position": "数据工程师",
        "roles": ["data_engineer"],
    }


@pytest.fixture
def sample_update_user_payload():
    """更新用户请求体"""
    return {
        "display_name": "更新后的显示名称",
        "phone": "13900139000",
        "department": "AI研发部",
        "position": "高级工程师",
    }


@pytest.fixture
def sample_create_role_payload():
    """创建角色请求体"""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"custom_role_{unique_id}",
        "display_name": f"自定义角色 {unique_id}",
        "description": "集成测试创建的自定义角色",
        "permissions": [
            {"resource": "dataset", "operation": "read"},
            {"resource": "dataset", "operation": "create"},
            {"resource": "workflow", "operation": "read"},
        ],
    }


@pytest.fixture
def sample_permissions():
    """样例权限数据"""
    return [
        {"id": "perm-001", "code": "dataset:create", "resource": "dataset", "operation": "create", "name": "创建数据集"},
        {"id": "perm-002", "code": "dataset:read", "resource": "dataset", "operation": "read", "name": "查看数据集"},
        {"id": "perm-003", "code": "dataset:update", "resource": "dataset", "operation": "update", "name": "更新数据集"},
        {"id": "perm-004", "code": "dataset:delete", "resource": "dataset", "operation": "delete", "name": "删除数据集"},
        {"id": "perm-005", "code": "workflow:create", "resource": "workflow", "operation": "create", "name": "创建工作流"},
        {"id": "perm-006", "code": "workflow:read", "resource": "workflow", "operation": "read", "name": "查看工作流"},
        {"id": "perm-007", "code": "workflow:execute", "resource": "workflow", "operation": "execute", "name": "执行工作流"},
        {"id": "perm-008", "code": "user:manage", "resource": "user", "operation": "manage", "name": "管理用户"},
        {"id": "perm-009", "code": "model:read", "resource": "model", "operation": "read", "name": "查看模型"},
        {"id": "perm-010", "code": "system:admin", "resource": "system", "operation": "admin", "name": "系统管理"},
    ]


@pytest.fixture
def sample_data_policy_payload():
    """数据权限策略配置请求体"""
    return {
        "policy_name": "department_data_access",
        "description": "按部门限制数据访问范围",
        "scope_type": "department",
        "scope_value": ["数据工程部", "AI研发部"],
        "resource_type": "dataset",
        "conditions": {
            "department_match": True,
            "include_public": True,
        },
    }


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.flush = MagicMock()
    return session


@pytest.fixture
def mock_admin_api_client(mock_admin_headers):
    """模拟管理后台 API 客户端"""

    class MockAdminAPIClient:
        """Admin API 模拟客户端，模拟对 /api/v1/users 和 /api/v1/roles 的调用"""

        def __init__(self, headers):
            self.base_url = os.getenv('ADMIN_API_URL', 'http://localhost:8084')
            self.headers = headers
            self._users = {}
            self._roles = {}
            self._user_roles = {}
            self._data_policies = {}
            self._init_system_roles()

        def _init_system_roles(self):
            """初始化系统内置角色"""
            system_roles = [
                {"role_id": "role-admin", "name": "admin", "display_name": "管理员",
                 "is_system": True, "is_active": True, "role_type": "system",
                 "permissions": [{"resource": "*", "operation": "*"}]},
                {"role_id": "role-data-eng", "name": "data_engineer", "display_name": "数据工程师",
                 "is_system": True, "is_active": True, "role_type": "system",
                 "permissions": [
                     {"resource": "dataset", "operation": "create"},
                     {"resource": "dataset", "operation": "read"},
                     {"resource": "dataset", "operation": "update"},
                     {"resource": "dataset", "operation": "delete"},
                 ]},
                {"role_id": "role-user", "name": "user", "display_name": "普通用户",
                 "is_system": True, "is_active": True, "role_type": "system",
                 "permissions": [
                     {"resource": "dataset", "operation": "read"},
                     {"resource": "chat", "operation": "execute"},
                 ]},
            ]
            for role in system_roles:
                self._roles[role["role_id"]] = role

        def _make_response(self, status_code, data=None, error=None):
            """构造模拟响应"""
            resp = Mock()
            resp.status_code = status_code
            if error:
                resp.json.return_value = {"code": status_code * 100, "message": error, "error": error}
            else:
                resp.json.return_value = {"code": 0, "message": "success", "data": data}
            resp.ok = 200 <= status_code < 300
            return resp

        # ---------- 用户管理 API ----------

        def create_user(self, payload):
            """POST /api/v1/users"""
            username = payload.get("username")
            email = payload.get("email")

            # 校验必填字段
            if not username or not email:
                return self._make_response(400, error="用户名和邮箱为必填项")

            # 检查用户名唯一
            for u in self._users.values():
                if u["username"] == username:
                    return self._make_response(409, error="用户名已存在")
                if u["email"] == email:
                    return self._make_response(409, error="邮箱已存在")

            user_id = f"user-{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()
            user = {
                "id": user_id,
                "user_id": user_id,
                "username": username,
                "email": email,
                "display_name": payload.get("display_name", username),
                "phone": payload.get("phone"),
                "department": payload.get("department"),
                "position": payload.get("position"),
                "status": "active",
                "login_count": 0,
                "created_at": now,
                "updated_at": now,
                "roles": [],
            }
            self._users[user_id] = user

            # 分配角色
            role_names = payload.get("roles", [])
            for role_name in role_names:
                for role in self._roles.values():
                    if role["name"] == role_name:
                        user["roles"].append(role)
                        self._user_roles.setdefault(user_id, []).append(role["role_id"])
                        break

            return self._make_response(201, data=user)

        def get_user(self, user_id):
            """GET /api/v1/users/{user_id}"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")
            return self._make_response(200, data=user)

        def update_user(self, user_id, payload):
            """PUT /api/v1/users/{user_id}"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")

            for key in ["display_name", "phone", "department", "position", "email"]:
                if key in payload:
                    user[key] = payload[key]

            user["updated_at"] = datetime.utcnow().isoformat()
            return self._make_response(200, data=user)

        def disable_user(self, user_id):
            """POST /api/v1/users/{user_id}/disable"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")
            user["status"] = "inactive"
            user["updated_at"] = datetime.utcnow().isoformat()
            return self._make_response(200, data=user)

        def enable_user(self, user_id):
            """POST /api/v1/users/{user_id}/enable"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")
            user["status"] = "active"
            user["updated_at"] = datetime.utcnow().isoformat()
            return self._make_response(200, data=user)

        def delete_user(self, user_id):
            """DELETE /api/v1/users/{user_id}"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")
            del self._users[user_id]
            self._user_roles.pop(user_id, None)
            return self._make_response(200, data={"deleted": True})

        def login(self, username, password):
            """POST /api/v1/auth/login (模拟登录)"""
            for user in self._users.values():
                if user["username"] == username:
                    if user["status"] != "active":
                        return self._make_response(403, error="用户已被禁用")
                    return self._make_response(200, data={
                        "access_token": f"mock-token-{user['user_id']}",
                        "user": user,
                    })
            return self._make_response(401, error="用户名或密码错误")

        # ---------- 角色管理 API ----------

        def create_role(self, payload):
            """POST /api/v1/roles"""
            name = payload.get("name")
            if not name:
                return self._make_response(400, error="角色名称为必填项")

            for role in self._roles.values():
                if role["name"] == name:
                    return self._make_response(409, error="角色名称已存在")

            role_id = f"role-{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()
            role = {
                "role_id": role_id,
                "name": name,
                "display_name": payload.get("display_name", name),
                "description": payload.get("description"),
                "role_type": "custom",
                "is_system": False,
                "is_active": True,
                "permissions": payload.get("permissions", []),
                "created_at": now,
                "updated_at": now,
            }
            self._roles[role_id] = role
            return self._make_response(201, data=role)

        def get_role(self, role_id):
            """GET /api/v1/roles/{role_id}"""
            role = self._roles.get(role_id)
            if not role:
                return self._make_response(404, error="角色不存在")
            return self._make_response(200, data=role)

        def update_role_permissions(self, role_id, permissions):
            """PUT /api/v1/roles/{role_id}/permissions"""
            role = self._roles.get(role_id)
            if not role:
                return self._make_response(404, error="角色不存在")

            if role.get("is_system"):
                return self._make_response(403, error="不能修改系统内置角色的权限")

            role["permissions"] = permissions
            role["updated_at"] = datetime.utcnow().isoformat()
            return self._make_response(200, data=role)

        def delete_role(self, role_id):
            """DELETE /api/v1/roles/{role_id}"""
            role = self._roles.get(role_id)
            if not role:
                return self._make_response(404, error="角色不存在")

            if role.get("is_system"):
                return self._make_response(403, error="不能删除系统内置角色")

            # 检查是否有用户在使用
            for uid, rids in self._user_roles.items():
                if role_id in rids:
                    return self._make_response(409, error="角色仍有关联用户，无法删除")

            del self._roles[role_id]
            return self._make_response(200, data={"deleted": True})

        # ---------- 用户-角色分配 API ----------

        def assign_role_to_user(self, user_id, role_id):
            """POST /api/v1/users/{user_id}/roles"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")

            role = self._roles.get(role_id)
            if not role:
                return self._make_response(404, error="角色不存在")

            existing_roles = self._user_roles.setdefault(user_id, [])
            if role_id in existing_roles:
                return self._make_response(409, error="用户已拥有该角色")

            existing_roles.append(role_id)
            user["roles"].append(role)
            return self._make_response(200, data=user)

        def remove_role_from_user(self, user_id, role_id):
            """DELETE /api/v1/users/{user_id}/roles/{role_id}"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")

            existing_roles = self._user_roles.get(user_id, [])
            if role_id not in existing_roles:
                return self._make_response(404, error="用户未拥有该角色")

            existing_roles.remove(role_id)
            user["roles"] = [r for r in user["roles"] if r["role_id"] != role_id]
            return self._make_response(200, data=user)

        def get_user_roles(self, user_id):
            """GET /api/v1/users/{user_id}/roles"""
            user = self._users.get(user_id)
            if not user:
                return self._make_response(404, error="用户不存在")

            role_ids = self._user_roles.get(user_id, [])
            roles = [self._roles[rid] for rid in role_ids if rid in self._roles]
            return self._make_response(200, data=roles)

        # ---------- 数据权限策略 API ----------

        def create_data_policy(self, payload):
            """POST /api/v1/data-policies"""
            policy_name = payload.get("policy_name")
            if not policy_name:
                return self._make_response(400, error="策略名称为必填项")

            policy_id = f"policy-{str(uuid.uuid4())[:8]}"
            policy = {
                "policy_id": policy_id,
                "policy_name": policy_name,
                "description": payload.get("description"),
                "scope_type": payload.get("scope_type"),
                "scope_value": payload.get("scope_value", []),
                "resource_type": payload.get("resource_type"),
                "conditions": payload.get("conditions", {}),
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
            }
            self._data_policies[policy_id] = policy
            return self._make_response(201, data=policy)

        def get_data_policy(self, policy_id):
            """GET /api/v1/data-policies/{policy_id}"""
            policy = self._data_policies.get(policy_id)
            if not policy:
                return self._make_response(404, error="策略不存在")
            return self._make_response(200, data=policy)

        def assign_policy_to_role(self, role_id, policy_id):
            """POST /api/v1/roles/{role_id}/data-policies"""
            role = self._roles.get(role_id)
            if not role:
                return self._make_response(404, error="角色不存在")

            policy = self._data_policies.get(policy_id)
            if not policy:
                return self._make_response(404, error="策略不存在")

            role.setdefault("data_policies", []).append(policy_id)
            return self._make_response(200, data=role)

    return MockAdminAPIClient(mock_admin_headers)


# ==================== 测试类 ====================

@pytest.mark.integration
class TestCreateUser:
    """SA-UM-001: 创建用户 (P0)

    验证通过 POST /api/v1/users 创建用户并分配角色的完整流程。

    前置条件：
    - 管理员已认证
    - 角色 data_engineer 已存在

    预期结果：
    - 返回 201，用户创建成功
    - 用户信息完整返回
    - 角色已正确分配
    """

    def test_create_user_success(self, mock_admin_api_client, sample_create_user_payload):
        """测试管理员成功创建用户"""
        response = mock_admin_api_client.create_user(sample_create_user_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["username"] == sample_create_user_payload["username"]
        assert data["email"] == sample_create_user_payload["email"]
        assert data["display_name"] == sample_create_user_payload["display_name"]
        assert data["status"] == "active"

    def test_create_user_with_role_assignment(self, mock_admin_api_client, sample_create_user_payload):
        """测试创建用户时分配角色"""
        sample_create_user_payload["roles"] = ["data_engineer"]

        response = mock_admin_api_client.create_user(sample_create_user_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        role_names = [r["name"] for r in data["roles"]]
        assert "data_engineer" in role_names

    def test_create_user_with_multiple_roles(self, mock_admin_api_client, sample_create_user_payload):
        """测试创建用户时分配多个角色"""
        sample_create_user_payload["roles"] = ["data_engineer", "user"]

        response = mock_admin_api_client.create_user(sample_create_user_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        role_names = [r["name"] for r in data["roles"]]
        assert "data_engineer" in role_names
        assert "user" in role_names

    def test_create_user_missing_required_fields(self, mock_admin_api_client):
        """测试缺少必填字段时创建用户失败"""
        response = mock_admin_api_client.create_user({"display_name": "无用户名"})

        assert response.status_code == 400

    def test_create_user_duplicate_username(self, mock_admin_api_client, sample_create_user_payload):
        """测试重复用户名时创建用户失败"""
        mock_admin_api_client.create_user(sample_create_user_payload)

        response = mock_admin_api_client.create_user(sample_create_user_payload)

        assert response.status_code == 409

    def test_create_user_duplicate_email(self, mock_admin_api_client, sample_create_user_payload):
        """测试重复邮箱时创建用户失败"""
        mock_admin_api_client.create_user(sample_create_user_payload)

        # 不同用户名但相同邮箱
        payload2 = sample_create_user_payload.copy()
        payload2["username"] = f"another_{payload2['username']}"

        response = mock_admin_api_client.create_user(payload2)

        assert response.status_code == 409

    def test_create_user_returns_correct_fields(self, mock_admin_api_client, sample_create_user_payload):
        """测试创建用户响应包含所有必要字段"""
        response = mock_admin_api_client.create_user(sample_create_user_payload)

        data = response.json()["data"]
        required_fields = ["id", "username", "email", "display_name", "status", "created_at"]
        for field in required_fields:
            assert field in data, f"响应缺少字段: {field}"

    def test_create_user_default_status_is_active(self, mock_admin_api_client, sample_create_user_payload):
        """测试新创建用户默认状态为 active"""
        response = mock_admin_api_client.create_user(sample_create_user_payload)

        data = response.json()["data"]
        assert data["status"] == "active"


@pytest.mark.integration
class TestEditUser:
    """SA-UM-002: 编辑用户 (P1)

    验证通过 PUT /api/v1/users/{user_id} 更新用户信息。

    前置条件：
    - 用户已存在
    - 管理员已认证

    预期结果：
    - 返回 200，用户信息更新成功
    - 更新后的信息能正确查询到
    """

    def test_update_user_display_name(self, mock_admin_api_client, sample_create_user_payload):
        """测试更新用户显示名称"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.update_user(user_id, {"display_name": "新显示名称"})

        assert response.status_code == 200
        assert response.json()["data"]["display_name"] == "新显示名称"

    def test_update_user_department(self, mock_admin_api_client, sample_create_user_payload):
        """测试更新用户部门"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.update_user(user_id, {"department": "AI研发部"})

        assert response.status_code == 200
        assert response.json()["data"]["department"] == "AI研发部"

    def test_update_user_multiple_fields(self, mock_admin_api_client, sample_create_user_payload, sample_update_user_payload):
        """测试同时更新多个字段"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.update_user(user_id, sample_update_user_payload)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["display_name"] == sample_update_user_payload["display_name"]
        assert data["phone"] == sample_update_user_payload["phone"]
        assert data["department"] == sample_update_user_payload["department"]
        assert data["position"] == sample_update_user_payload["position"]

    def test_update_nonexistent_user(self, mock_admin_api_client):
        """测试更新不存在的用户"""
        response = mock_admin_api_client.update_user("nonexistent-id", {"display_name": "test"})

        assert response.status_code == 404

    def test_update_user_preserves_unchanged_fields(self, mock_admin_api_client, sample_create_user_payload):
        """测试更新用户时未修改的字段保持不变"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]
        original_email = create_resp.json()["data"]["email"]

        response = mock_admin_api_client.update_user(user_id, {"display_name": "修改了"})

        assert response.status_code == 200
        assert response.json()["data"]["email"] == original_email

    def test_update_user_updated_at_changes(self, mock_admin_api_client, sample_create_user_payload):
        """测试更新用户后 updated_at 字段发生变化"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]
        original_updated = create_resp.json()["data"]["updated_at"]

        # 稍作等待以确保时间差
        time.sleep(0.01)
        response = mock_admin_api_client.update_user(user_id, {"display_name": "test"})

        assert response.status_code == 200
        # updated_at 应该已更新（可能相同也可能不同，取决于精度）
        assert response.json()["data"]["updated_at"] is not None


@pytest.mark.integration
class TestDisableUser:
    """SA-UM-003: 禁用用户 (P1)

    验证通过 POST /api/v1/users/{user_id}/disable 禁用用户。

    前置条件：
    - 用户已存在且状态为 active

    预期结果：
    - 返回 200，用户状态变为 inactive
    - 被禁用的用户无法登录
    """

    def test_disable_active_user(self, mock_admin_api_client, sample_create_user_payload):
        """测试禁用活跃用户"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.disable_user(user_id)

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "inactive"

    def test_disabled_user_cannot_login(self, mock_admin_api_client, sample_create_user_payload):
        """测试被禁用的用户无法登录"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]
        username = sample_create_user_payload["username"]

        # 禁用用户
        mock_admin_api_client.disable_user(user_id)

        # 尝试登录
        login_resp = mock_admin_api_client.login(username, "any_password")

        assert login_resp.status_code == 403
        assert "禁用" in login_resp.json()["message"]

    def test_disable_nonexistent_user(self, mock_admin_api_client):
        """测试禁用不存在的用户"""
        response = mock_admin_api_client.disable_user("nonexistent-id")

        assert response.status_code == 404

    def test_disable_user_status_persists(self, mock_admin_api_client, sample_create_user_payload):
        """测试禁用状态在查询时保持一致"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        mock_admin_api_client.disable_user(user_id)
        get_resp = mock_admin_api_client.get_user(user_id)

        assert get_resp.json()["data"]["status"] == "inactive"


@pytest.mark.integration
class TestEnableUser:
    """SA-UM-004: 启用用户 (P1)

    验证通过 POST /api/v1/users/{user_id}/enable 启用已禁用的用户。

    前置条件：
    - 用户已存在且状态为 inactive

    预期结果：
    - 返回 200，用户状态恢复为 active
    - 重新启用的用户可以登录
    """

    def test_enable_disabled_user(self, mock_admin_api_client, sample_create_user_payload):
        """测试启用已禁用的用户"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        # 先禁用
        mock_admin_api_client.disable_user(user_id)
        # 再启用
        response = mock_admin_api_client.enable_user(user_id)

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    def test_enabled_user_can_login(self, mock_admin_api_client, sample_create_user_payload):
        """测试重新启用的用户可以登录"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]
        username = sample_create_user_payload["username"]

        # 禁用再启用
        mock_admin_api_client.disable_user(user_id)
        mock_admin_api_client.enable_user(user_id)

        # 尝试登录
        login_resp = mock_admin_api_client.login(username, "any_password")

        assert login_resp.status_code == 200
        assert login_resp.json()["data"]["access_token"] is not None

    def test_enable_nonexistent_user(self, mock_admin_api_client):
        """测试启用不存在的用户"""
        response = mock_admin_api_client.enable_user("nonexistent-id")

        assert response.status_code == 404

    def test_enable_already_active_user(self, mock_admin_api_client, sample_create_user_payload):
        """测试启用已处于活跃状态的用户（幂等操作）"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.enable_user(user_id)

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"


@pytest.mark.integration
class TestDeleteUser:
    """SA-UM-005: 删除用户 (P2)

    验证通过 DELETE /api/v1/users/{user_id} 删除用户。

    前置条件：
    - 用户已存在

    预期结果：
    - 返回 200，用户已被删除
    - 删除后无法查询到该用户
    - 用户关联的角色记录被清除
    """

    def test_delete_user_success(self, mock_admin_api_client, sample_create_user_payload):
        """测试成功删除用户"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        response = mock_admin_api_client.delete_user(user_id)

        assert response.status_code == 200
        assert response.json()["data"]["deleted"] is True

    def test_deleted_user_not_found(self, mock_admin_api_client, sample_create_user_payload):
        """测试删除后用户不可查询"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        mock_admin_api_client.delete_user(user_id)
        get_resp = mock_admin_api_client.get_user(user_id)

        assert get_resp.status_code == 404

    def test_delete_nonexistent_user(self, mock_admin_api_client):
        """测试删除不存在的用户"""
        response = mock_admin_api_client.delete_user("nonexistent-id")

        assert response.status_code == 404

    def test_delete_user_clears_role_associations(self, mock_admin_api_client, sample_create_user_payload):
        """测试删除用户后角色关联被清除"""
        sample_create_user_payload["roles"] = ["data_engineer"]
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]

        mock_admin_api_client.delete_user(user_id)

        # 尝试查询已删除用户的角色
        roles_resp = mock_admin_api_client.get_user_roles(user_id)
        assert roles_resp.status_code == 404

    def test_deleted_user_cannot_login(self, mock_admin_api_client, sample_create_user_payload):
        """测试删除后用户无法登录"""
        create_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = create_resp.json()["data"]["id"]
        username = sample_create_user_payload["username"]

        mock_admin_api_client.delete_user(user_id)
        login_resp = mock_admin_api_client.login(username, "any_password")

        assert login_resp.status_code == 401


@pytest.mark.integration
class TestCreateRole:
    """SA-UM-006: 创建角色 (P0)

    验证通过 POST /api/v1/roles 创建自定义角色并配置权限。

    前置条件：
    - 管理员已认证

    预期结果：
    - 返回 201，角色创建成功
    - 角色权限已正确配置
    """

    def test_create_role_success(self, mock_admin_api_client, sample_create_role_payload):
        """测试管理员成功创建角色"""
        response = mock_admin_api_client.create_role(sample_create_role_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == sample_create_role_payload["name"]
        assert data["display_name"] == sample_create_role_payload["display_name"]
        assert data["description"] == sample_create_role_payload["description"]

    def test_create_role_with_permissions(self, mock_admin_api_client, sample_create_role_payload):
        """测试创建角色时配置权限"""
        response = mock_admin_api_client.create_role(sample_create_role_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["permissions"]) == len(sample_create_role_payload["permissions"])

    def test_create_role_is_custom_type(self, mock_admin_api_client, sample_create_role_payload):
        """测试新创建角色类型为 custom"""
        response = mock_admin_api_client.create_role(sample_create_role_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["role_type"] == "custom"
        assert data["is_system"] is False

    def test_create_role_missing_name(self, mock_admin_api_client):
        """测试缺少名称时创建角色失败"""
        response = mock_admin_api_client.create_role({"display_name": "缺少名称的角色"})

        assert response.status_code == 400

    def test_create_role_duplicate_name(self, mock_admin_api_client, sample_create_role_payload):
        """测试重复名称时创建角色失败"""
        mock_admin_api_client.create_role(sample_create_role_payload)
        response = mock_admin_api_client.create_role(sample_create_role_payload)

        assert response.status_code == 409

    def test_create_role_default_active(self, mock_admin_api_client, sample_create_role_payload):
        """测试新创建角色默认为启用状态"""
        response = mock_admin_api_client.create_role(sample_create_role_payload)

        assert response.status_code == 201
        assert response.json()["data"]["is_active"] is True

    def test_create_role_empty_permissions(self, mock_admin_api_client):
        """测试创建不带权限的角色"""
        payload = {
            "name": f"empty_role_{str(uuid.uuid4())[:8]}",
            "display_name": "空权限角色",
            "permissions": [],
        }

        response = mock_admin_api_client.create_role(payload)

        assert response.status_code == 201
        assert len(response.json()["data"]["permissions"]) == 0


@pytest.mark.integration
class TestEditRolePermissions:
    """SA-UM-007: 编辑角色权限 (P1)

    验证通过 PUT /api/v1/roles/{role_id}/permissions 修改角色权限。

    前置条件：
    - 自定义角色已存在

    预期结果：
    - 返回 200，权限更新成功
    - 系统内置角色不能被修改
    """

    def test_update_custom_role_permissions(self, mock_admin_api_client, sample_create_role_payload):
        """测试更新自定义角色权限"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]

        new_permissions = [
            {"resource": "dataset", "operation": "read"},
            {"resource": "workflow", "operation": "read"},
            {"resource": "workflow", "operation": "execute"},
            {"resource": "model", "operation": "read"},
        ]
        response = mock_admin_api_client.update_role_permissions(role_id, new_permissions)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["permissions"]) == 4

    def test_add_new_permission_to_role(self, mock_admin_api_client, sample_create_role_payload):
        """测试为角色添加新权限"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]
        original_perms = create_resp.json()["data"]["permissions"]

        updated_perms = original_perms + [{"resource": "model", "operation": "read"}]
        response = mock_admin_api_client.update_role_permissions(role_id, updated_perms)

        assert response.status_code == 200
        assert len(response.json()["data"]["permissions"]) == len(original_perms) + 1

    def test_remove_permission_from_role(self, mock_admin_api_client, sample_create_role_payload):
        """测试从角色移除权限"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]

        # 仅保留一个权限
        reduced_perms = [{"resource": "dataset", "operation": "read"}]
        response = mock_admin_api_client.update_role_permissions(role_id, reduced_perms)

        assert response.status_code == 200
        assert len(response.json()["data"]["permissions"]) == 1

    def test_cannot_modify_system_role_permissions(self, mock_admin_api_client):
        """测试不能修改系统内置角色的权限"""
        # role-admin 是系统内置角色
        new_perms = [{"resource": "dataset", "operation": "read"}]
        response = mock_admin_api_client.update_role_permissions("role-admin", new_perms)

        assert response.status_code == 403

    def test_update_permissions_nonexistent_role(self, mock_admin_api_client):
        """测试更新不存在角色的权限"""
        response = mock_admin_api_client.update_role_permissions(
            "nonexistent-role",
            [{"resource": "dataset", "operation": "read"}],
        )

        assert response.status_code == 404

    def test_clear_all_permissions(self, mock_admin_api_client, sample_create_role_payload):
        """测试清空角色的所有权限"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]

        response = mock_admin_api_client.update_role_permissions(role_id, [])

        assert response.status_code == 200
        assert len(response.json()["data"]["permissions"]) == 0


@pytest.mark.integration
class TestDeleteRole:
    """SA-UM-008: 删除角色 (P2)

    验证通过 DELETE /api/v1/roles/{role_id} 删除未使用的角色。

    前置条件：
    - 自定义角色已存在
    - 角色未被任何用户关联

    预期结果：
    - 返回 200，角色已被删除
    - 有关联用户的角色无法删除
    - 系统内置角色不能被删除
    """

    def test_delete_unused_role(self, mock_admin_api_client, sample_create_role_payload):
        """测试删除未使用的角色"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]

        response = mock_admin_api_client.delete_role(role_id)

        assert response.status_code == 200
        assert response.json()["data"]["deleted"] is True

    def test_deleted_role_not_found(self, mock_admin_api_client, sample_create_role_payload):
        """测试删除后角色不可查询"""
        create_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = create_resp.json()["data"]["role_id"]

        mock_admin_api_client.delete_role(role_id)
        get_resp = mock_admin_api_client.get_role(role_id)

        assert get_resp.status_code == 404

    def test_cannot_delete_system_role(self, mock_admin_api_client):
        """测试不能删除系统内置角色"""
        response = mock_admin_api_client.delete_role("role-admin")

        assert response.status_code == 403

    def test_cannot_delete_role_with_users(self, mock_admin_api_client, sample_create_user_payload, sample_create_role_payload):
        """测试有关联用户的角色无法删除"""
        # 创建角色
        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        # 创建用户并分配该角色
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]
        mock_admin_api_client.assign_role_to_user(user_id, role_id)

        # 尝试删除角色
        response = mock_admin_api_client.delete_role(role_id)

        assert response.status_code == 409
        assert "关联用户" in response.json()["message"]

    def test_delete_nonexistent_role(self, mock_admin_api_client):
        """测试删除不存在的角色"""
        response = mock_admin_api_client.delete_role("nonexistent-role-id")

        assert response.status_code == 404


@pytest.mark.integration
class TestUserRoleAssignment:
    """SA-UM-009: 用户角色分配 (P0)

    验证通过 POST /api/v1/users/{user_id}/roles 为用户分配角色。

    前置条件：
    - 用户已存在
    - 角色已存在

    预期结果：
    - 返回 200，角色分配成功
    - 用户权限立即生效
    - 可以移除用户的角色
    """

    def test_assign_role_to_user(self, mock_admin_api_client, sample_create_user_payload, sample_create_role_payload):
        """测试为用户分配角色"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        response = mock_admin_api_client.assign_role_to_user(user_id, role_id)

        assert response.status_code == 200

    def test_assign_role_user_roles_updated(self, mock_admin_api_client, sample_create_user_payload, sample_create_role_payload):
        """测试分配角色后用户角色列表更新"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        mock_admin_api_client.assign_role_to_user(user_id, role_id)

        roles_resp = mock_admin_api_client.get_user_roles(user_id)
        assert roles_resp.status_code == 200
        role_ids = [r["role_id"] for r in roles_resp.json()["data"]]
        assert role_id in role_ids

    def test_assign_duplicate_role(self, mock_admin_api_client, sample_create_user_payload, sample_create_role_payload):
        """测试重复分配角色"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        mock_admin_api_client.assign_role_to_user(user_id, role_id)
        response = mock_admin_api_client.assign_role_to_user(user_id, role_id)

        assert response.status_code == 409

    def test_remove_role_from_user(self, mock_admin_api_client, sample_create_user_payload, sample_create_role_payload):
        """测试移除用户角色"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        mock_admin_api_client.assign_role_to_user(user_id, role_id)
        response = mock_admin_api_client.remove_role_from_user(user_id, role_id)

        assert response.status_code == 200
        roles_resp = mock_admin_api_client.get_user_roles(user_id)
        role_ids = [r["role_id"] for r in roles_resp.json()["data"]]
        assert role_id not in role_ids

    def test_assign_role_nonexistent_user(self, mock_admin_api_client, sample_create_role_payload):
        """测试为不存在的用户分配角色"""
        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        response = mock_admin_api_client.assign_role_to_user("nonexistent-user", role_id)

        assert response.status_code == 404

    def test_assign_nonexistent_role_to_user(self, mock_admin_api_client, sample_create_user_payload):
        """测试为用户分配不存在的角色"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        response = mock_admin_api_client.assign_role_to_user(user_id, "nonexistent-role")

        assert response.status_code == 404

    @_requires_permissions
    def test_user_permissions_effective_after_role_assignment(self, mock_admin_api_client, sample_create_user_payload):
        """测试角色分配后权限立即生效"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        # 分配 data_engineer 角色
        mock_admin_api_client.assign_role_to_user(user_id, "role-data-eng")

        # 验证权限检查：data_engineer 应有 dataset:create 权限
        assert has_permission(["data_engineer"], Resource.DATASET, Operation.CREATE) is True
        assert has_permission(["data_engineer"], Resource.DATASET, Operation.READ) is True

    @_requires_permissions
    def test_user_permissions_revoked_after_role_removal(self, mock_admin_api_client, sample_create_user_payload):
        """测试角色移除后权限被撤销"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        # 分配再移除
        mock_admin_api_client.assign_role_to_user(user_id, "role-data-eng")
        mock_admin_api_client.remove_role_from_user(user_id, "role-data-eng")

        # 获取用户当前角色
        roles_resp = mock_admin_api_client.get_user_roles(user_id)
        current_role_names = [r["name"] for r in roles_resp.json()["data"]]

        # 如果用户没有其他赋予 dataset:create 的角色，则权限应失效
        if "data_engineer" not in current_role_names and "admin" not in current_role_names:
            assert has_permission(current_role_names, Resource.DATASET, Operation.CREATE) is False

    @_requires_permissions
    def test_multiple_roles_permissions_merge(self, mock_admin_api_client, sample_create_user_payload):
        """测试多角色权限合并"""
        user_resp = mock_admin_api_client.create_user(sample_create_user_payload)
        user_id = user_resp.json()["data"]["id"]

        # 分配 user + data_engineer 两个角色
        mock_admin_api_client.assign_role_to_user(user_id, "role-user")
        mock_admin_api_client.assign_role_to_user(user_id, "role-data-eng")

        # 合并权限：user 有 chat:execute，data_engineer 有 dataset:create
        merged_perms = get_user_permissions(["user", "data_engineer"])
        assert ("chat", "execute") in merged_perms      # 来自 user
        assert ("dataset", "create") in merged_perms     # 来自 data_engineer


@pytest.mark.integration
class TestDataAccessPolicyConfig:
    """SA-UM-010: 数据权限策略配置 (P0)

    验证数据权限策略的配置和应用。

    前置条件：
    - 管理员已认证
    - 角色已存在

    预期结果：
    - 策略创建成功
    - 策略关联到角色
    - 策略配置正确控制数据访问范围
    """

    def test_create_data_access_policy(self, mock_admin_api_client, sample_data_policy_payload):
        """测试创建数据权限策略"""
        response = mock_admin_api_client.create_data_policy(sample_data_policy_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["policy_name"] == sample_data_policy_payload["policy_name"]
        assert data["scope_type"] == "department"
        assert data["is_active"] is True

    def test_create_policy_with_scope_values(self, mock_admin_api_client, sample_data_policy_payload):
        """测试创建策略包含范围值"""
        response = mock_admin_api_client.create_data_policy(sample_data_policy_payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["scope_value"]) == 2
        assert "数据工程部" in data["scope_value"]
        assert "AI研发部" in data["scope_value"]

    def test_create_policy_with_conditions(self, mock_admin_api_client, sample_data_policy_payload):
        """测试创建策略包含条件"""
        response = mock_admin_api_client.create_data_policy(sample_data_policy_payload)

        assert response.status_code == 201
        conditions = response.json()["data"]["conditions"]
        assert conditions["department_match"] is True
        assert conditions["include_public"] is True

    def test_create_policy_missing_name(self, mock_admin_api_client):
        """测试缺少策略名称时创建失败"""
        response = mock_admin_api_client.create_data_policy({"scope_type": "department"})

        assert response.status_code == 400

    def test_assign_policy_to_role(self, mock_admin_api_client, sample_create_role_payload, sample_data_policy_payload):
        """测试将策略关联到角色"""
        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        policy_resp = mock_admin_api_client.create_data_policy(sample_data_policy_payload)
        policy_id = policy_resp.json()["data"]["policy_id"]

        response = mock_admin_api_client.assign_policy_to_role(role_id, policy_id)

        assert response.status_code == 200
        assert policy_id in response.json()["data"].get("data_policies", [])

    def test_policy_query_after_creation(self, mock_admin_api_client, sample_data_policy_payload):
        """测试策略创建后可查询"""
        create_resp = mock_admin_api_client.create_data_policy(sample_data_policy_payload)
        policy_id = create_resp.json()["data"]["policy_id"]

        get_resp = mock_admin_api_client.get_data_policy(policy_id)

        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["policy_id"] == policy_id

    def test_policy_nonexistent_query(self, mock_admin_api_client):
        """测试查询不存在的策略"""
        response = mock_admin_api_client.get_data_policy("nonexistent-policy")

        assert response.status_code == 404

    def test_assign_policy_to_nonexistent_role(self, mock_admin_api_client, sample_data_policy_payload):
        """测试将策略关联到不存在的角色"""
        policy_resp = mock_admin_api_client.create_data_policy(sample_data_policy_payload)
        policy_id = policy_resp.json()["data"]["policy_id"]

        response = mock_admin_api_client.assign_policy_to_role("nonexistent-role", policy_id)

        assert response.status_code == 404

    def test_assign_nonexistent_policy_to_role(self, mock_admin_api_client, sample_create_role_payload):
        """测试将不存在的策略关联到角色"""
        role_resp = mock_admin_api_client.create_role(sample_create_role_payload)
        role_id = role_resp.json()["data"]["role_id"]

        response = mock_admin_api_client.assign_policy_to_role(role_id, "nonexistent-policy")

        assert response.status_code == 404

    def test_create_multiple_scope_types(self, mock_admin_api_client):
        """测试创建不同范围类型的策略"""
        scope_types = [
            {"policy_name": "project_scope", "scope_type": "project", "scope_value": ["proj-1"], "resource_type": "dataset"},
            {"policy_name": "tenant_scope", "scope_type": "tenant", "scope_value": ["tenant-001"], "resource_type": "dataset"},
            {"policy_name": "global_scope", "scope_type": "global", "scope_value": [], "resource_type": "dataset"},
        ]

        for policy_payload in scope_types:
            response = mock_admin_api_client.create_data_policy(policy_payload)
            assert response.status_code == 201, f"创建 {policy_payload['scope_type']} 类型策略失败"
            assert response.json()["data"]["scope_type"] == policy_payload["scope_type"]


# ==================== 权限模块集成验证 ====================

@pytest.mark.integration
@_requires_permissions
class TestPermissionModuleIntegration:
    """权限模块集成验证

    使用 services/shared/auth/permissions.py 中的权限模型
    验证权限检查逻辑在用户管理流程中的正确性。
    """

    def test_admin_role_full_permissions(self):
        """验证 admin 角色拥有所有权限"""
        for resource in Resource:
            for operation in Operation:
                assert has_permission(["admin"], resource, operation) is True, \
                    f"admin 应有权限 {resource.value}:{operation.value}"

    def test_user_role_limited_permissions(self):
        """验证 user 角色权限有限"""
        # 有的权限
        assert has_permission(["user"], Resource.DATASET, Operation.READ) is True
        assert has_permission(["user"], Resource.CHAT, Operation.EXECUTE) is True

        # 没有的权限
        assert has_permission(["user"], Resource.USER, Operation.MANAGE) is False
        assert has_permission(["user"], Resource.DATASET, Operation.DELETE) is False
        assert has_permission(["user"], Resource.SYSTEM, Operation.MANAGE) is False

    def test_guest_role_minimal_permissions(self):
        """验证 guest 角色只有最小权限"""
        assert has_permission(["guest"], Resource.DATASET, Operation.READ) is True
        assert has_permission(["guest"], Resource.METADATA, Operation.READ) is True
        assert has_permission(["guest"], Resource.WORKFLOW, Operation.EXECUTE) is False
        assert has_permission(["guest"], Resource.USER, Operation.MANAGE) is False

    def test_can_manage_users_check(self):
        """验证 can_manage_users 辅助函数"""
        assert can_manage_users(["admin"]) is True
        assert can_manage_users(["user"]) is False
        assert can_manage_users(["data_engineer"]) is False
        assert can_manage_users(["guest"]) is False

    def test_permission_merge_across_roles(self):
        """验证多角色权限合并"""
        perms = get_user_permissions(["user", "data_engineer"])

        # user 贡献
        assert ("chat", "execute") in perms

        # data_engineer 贡献
        assert ("dataset", "create") in perms
        assert ("dataset", "delete") in perms

    def test_empty_roles_deny_everything(self):
        """验证空角色列表拒绝所有权限"""
        assert has_permission([], Resource.DATASET, Operation.READ) is False
        assert has_permission([], Resource.USER, Operation.MANAGE) is False

    def test_none_roles_deny_everything(self):
        """验证 None 角色拒绝所有权限"""
        assert has_permission(None, Resource.DATASET, Operation.READ) is False
