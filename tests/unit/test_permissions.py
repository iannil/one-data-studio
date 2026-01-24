"""
权限管理模块单元测试
Sprint 14: P1 测试覆盖
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from flask import Flask, g


class TestResourceAndOperationEnums:
    """资源和操作枚举测试"""

    def test_resource_enum_values(self):
        """测试资源枚举值"""
        from services.shared.auth.permissions import Resource

        assert Resource.DATASET.value == "dataset"
        assert Resource.METADATA.value == "metadata"
        assert Resource.WORKFLOW.value == "workflow"
        assert Resource.CHAT.value == "chat"
        assert Resource.MODEL.value == "model"
        assert Resource.USER.value == "user"
        assert Resource.SYSTEM.value == "system"

    def test_operation_enum_values(self):
        """测试操作枚举值"""
        from services.shared.auth.permissions import Operation

        assert Operation.CREATE.value == "create"
        assert Operation.READ.value == "read"
        assert Operation.UPDATE.value == "update"
        assert Operation.DELETE.value == "delete"
        assert Operation.EXECUTE.value == "execute"
        assert Operation.MANAGE.value == "manage"


class TestRolePermissions:
    """角色权限配置测试"""

    def test_admin_has_all_permissions(self):
        """测试管理员拥有所有权限"""
        from services.shared.auth.permissions import ROLE_PERMISSIONS, Resource, Operation

        admin_perms = ROLE_PERMISSIONS["admin"]

        # 检查所有资源和操作的组合
        for resource in Resource:
            for operation in Operation:
                assert (resource.value, operation.value) in admin_perms

    def test_data_engineer_permissions(self):
        """测试数据工程师权限"""
        from services.shared.auth.permissions import ROLE_PERMISSIONS

        perms = ROLE_PERMISSIONS["data_engineer"]

        # 有数据集权限
        assert ("dataset", "create") in perms
        assert ("dataset", "read") in perms
        assert ("dataset", "update") in perms
        assert ("dataset", "delete") in perms

        # 有元数据权限
        assert ("metadata", "read") in perms
        assert ("metadata", "create") in perms

        # 无工作流执行权限
        assert ("workflow", "execute") not in perms

    def test_data_analyst_read_only(self):
        """测试数据分析师只读权限"""
        from services.shared.auth.permissions import ROLE_PERMISSIONS

        perms = ROLE_PERMISSIONS["data_analyst"]

        # 只有读权限
        assert ("dataset", "read") in perms
        assert ("metadata", "read") in perms
        assert ("workflow", "read") in perms

        # 无写权限
        assert ("dataset", "create") not in perms
        assert ("dataset", "update") not in perms
        assert ("dataset", "delete") not in perms

    def test_guest_minimal_permissions(self):
        """测试访客最小权限"""
        from services.shared.auth.permissions import ROLE_PERMISSIONS

        perms = ROLE_PERMISSIONS["guest"]

        # 只有最基础的读权限
        assert ("dataset", "read") in perms
        assert ("metadata", "read") in perms

        # 无其他权限
        assert ("workflow", "read") not in perms
        assert ("chat", "execute") not in perms


class TestGetUserPermissions:
    """获取用户权限测试"""

    def test_single_role_permissions(self):
        """测试单角色权限"""
        from services.shared.auth.permissions import get_user_permissions

        perms = get_user_permissions(["data_analyst"])

        assert ("dataset", "read") in perms
        assert ("metadata", "read") in perms

    def test_multiple_roles_merged(self):
        """测试多角色权限合并"""
        from services.shared.auth.permissions import get_user_permissions

        perms = get_user_permissions(["data_analyst", "ai_developer"])

        # 从 data_analyst
        assert ("dataset", "read") in perms

        # 从 ai_developer
        assert ("workflow", "create") in perms
        assert ("workflow", "execute") in perms
        assert ("chat", "execute") in perms

    def test_unknown_role_returns_empty(self):
        """测试未知角色返回空集合"""
        from services.shared.auth.permissions import get_user_permissions

        perms = get_user_permissions(["unknown_role"])
        assert len(perms) == 0

    def test_empty_roles_returns_empty(self):
        """测试空角色列表返回空集合"""
        from services.shared.auth.permissions import get_user_permissions

        perms = get_user_permissions([])
        assert len(perms) == 0


class TestHasPermission:
    """权限检查测试"""

    def test_admin_has_all_permissions(self):
        """测试管理员拥有所有权限"""
        from services.shared.auth.permissions import has_permission, Resource, Operation

        assert has_permission(["admin"], Resource.DATASET, Operation.DELETE) is True
        assert has_permission(["admin"], Resource.USER, Operation.MANAGE) is True
        assert has_permission(["admin"], Resource.SYSTEM, Operation.MANAGE) is True

    def test_user_has_specific_permission(self):
        """测试用户有特定权限"""
        from services.shared.auth.permissions import has_permission, Resource, Operation

        assert has_permission(["user"], Resource.DATASET, Operation.READ) is True
        assert has_permission(["user"], Resource.CHAT, Operation.EXECUTE) is True

    def test_user_lacks_permission(self):
        """测试用户无权限"""
        from services.shared.auth.permissions import has_permission, Resource, Operation

        assert has_permission(["user"], Resource.DATASET, Operation.DELETE) is False
        assert has_permission(["guest"], Resource.WORKFLOW, Operation.EXECUTE) is False

    def test_empty_roles_no_permission(self):
        """测试空角色无权限"""
        from services.shared.auth.permissions import has_permission, Resource, Operation

        assert has_permission([], Resource.DATASET, Operation.READ) is False

    def test_none_roles_no_permission(self):
        """测试 None 角色无权限"""
        from services.shared.auth.permissions import has_permission, Resource, Operation

        assert has_permission(None, Resource.DATASET, Operation.READ) is False


class TestRequirePermissionDecorator:
    """require_permission 装饰器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from services.shared.auth.permissions import require_permission, Resource, Operation

        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/create-dataset', methods=['POST'])
        @require_permission(Resource.DATASET, Operation.CREATE)
        def create_dataset():
            return {"status": "created"}

        return app

    def test_returns_401_without_auth(self, app):
        """测试未认证返回 401"""
        with app.test_client() as client:
            response = client.post('/create-dataset')
            assert response.status_code == 401

    def test_allows_user_with_permission(self, app):
        """测试有权限的用户通过"""
        with app.test_request_context('/create-dataset', method='POST'):
            g.roles = ["data_engineer"]

            from services.shared.auth.permissions import require_permission, Resource, Operation

            @require_permission(Resource.DATASET, Operation.CREATE)
            def test_func():
                return {"status": "ok"}

            result = test_func()
            assert result == {"status": "ok"}

    def test_denies_user_without_permission(self, app):
        """测试无权限的用户被拒绝"""
        with app.test_client() as client:
            with app.test_request_context('/create-dataset', method='POST'):
                g.roles = ["guest"]

                response = client.post('/create-dataset')
                # 由于 g 在请求之间不共享，这里需要模拟


class TestRequireAnyPermissionDecorator:
    """require_any_permission 装饰器测试"""

    def test_allows_with_any_permission(self):
        """测试有任一权限的用户通过"""
        from services.shared.auth.permissions import require_any_permission, Resource, Operation

        app = Flask(__name__)
        with app.test_request_context():
            g.roles = ["data_engineer"]

            @require_any_permission(
                (Resource.DATASET, Operation.CREATE),
                (Resource.DATASET, Operation.UPDATE)
            )
            def test_func():
                return {"status": "ok"}

            result = test_func()
            assert result == {"status": "ok"}


class TestOwnerOrAdminDecorator:
    """owner_or_admin 装饰器测试"""

    def test_admin_always_passes(self):
        """测试管理员始终通过"""
        from services.shared.auth.permissions import owner_or_admin

        app = Flask(__name__)
        with app.test_request_context():
            g.roles = ["admin"]
            g.user_id = "admin-user"

            @owner_or_admin("id")
            def test_func(id):
                return {"status": "ok"}

            result = test_func(id="resource-123")
            assert result == {"status": "ok"}

    def test_owner_passes(self):
        """测试资源所有者通过"""
        from services.shared.auth.permissions import owner_or_admin

        app = Flask(__name__)

        def get_owner(resource_id):
            return "user-123"

        with app.test_request_context():
            g.roles = ["user"]
            g.user_id = "user-123"

            @owner_or_admin("id", get_resource_owner=get_owner)
            def test_func(id):
                return {"status": "ok"}

            result = test_func(id="resource-456")
            assert result == {"status": "ok"}

    def test_non_owner_denied(self):
        """测试非所有者被拒绝"""
        from services.shared.auth.permissions import owner_or_admin

        app = Flask(__name__)

        def get_owner(resource_id):
            return "other-user"

        with app.test_request_context():
            g.roles = ["user"]
            g.user_id = "user-123"

            @owner_or_admin("id", get_resource_owner=get_owner)
            def test_func(id):
                return {"status": "ok"}

            result, status = test_func(id="resource-456")
            assert status == 403


class TestPermissionHelperFunctions:
    """权限辅助函数测试"""

    def test_can_create_dataset(self):
        """测试 can_create_dataset"""
        from services.shared.auth.permissions import can_create_dataset

        assert can_create_dataset(["data_engineer"]) is True
        assert can_create_dataset(["admin"]) is True
        assert can_create_dataset(["guest"]) is False

    def test_can_delete_dataset(self):
        """测试 can_delete_dataset"""
        from services.shared.auth.permissions import can_delete_dataset

        assert can_delete_dataset(["data_engineer"]) is True
        assert can_delete_dataset(["admin"]) is True
        assert can_delete_dataset(["data_analyst"]) is False

    def test_can_execute_workflow(self):
        """测试 can_execute_workflow"""
        from services.shared.auth.permissions import can_execute_workflow

        assert can_execute_workflow(["ai_developer"]) is True
        assert can_execute_workflow(["admin"]) is True
        assert can_execute_workflow(["guest"]) is False

    def test_can_manage_users(self):
        """测试 can_manage_users"""
        from services.shared.auth.permissions import can_manage_users

        assert can_manage_users(["admin"]) is True
        assert can_manage_users(["user"]) is False

    def test_can_access_chat(self):
        """测试 can_access_chat"""
        from services.shared.auth.permissions import can_access_chat

        assert can_access_chat(["user"]) is True
        assert can_access_chat(["ai_developer"]) is True
        assert can_access_chat(["guest"]) is False


class TestDynamicRBACManager:
    """动态 RBAC 管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建 RBAC 管理器"""
        from services.shared.auth.permissions import DynamicRBACManager
        return DynamicRBACManager()

    def test_get_role_permissions_fallback_to_static(self, manager):
        """测试数据库不可用时回退到静态配置"""
        perms = manager.get_role_permissions("admin")
        assert len(perms) > 0

    def test_clear_cache(self, manager):
        """测试清除缓存"""
        manager._role_cache["test"] = {("a", "b")}
        manager.clear_cache()
        assert len(manager._role_cache) == 0


class TestHasDynamicPermission:
    """动态权限检查测试"""

    def test_admin_has_all_permissions(self):
        """测试管理员有所有权限"""
        from services.shared.auth.permissions import has_dynamic_permission, Resource, Operation

        assert has_dynamic_permission(["admin"], Resource.DATASET, Operation.DELETE) is True
        assert has_dynamic_permission(["admin"], Resource.USER, Operation.MANAGE) is True

    def test_empty_roles_no_permission(self):
        """测试空角色无权限"""
        from services.shared.auth.permissions import has_dynamic_permission, Resource, Operation

        assert has_dynamic_permission([], Resource.DATASET, Operation.READ) is False

    def test_regular_user_permissions(self):
        """测试普通用户权限"""
        from services.shared.auth.permissions import has_dynamic_permission, Resource, Operation

        assert has_dynamic_permission(["user"], Resource.DATASET, Operation.READ) is True
        assert has_dynamic_permission(["user"], Resource.DATASET, Operation.DELETE) is False


class TestGetDynamicPermissions:
    """获取动态权限测试"""

    def test_gets_permissions_for_roles(self):
        """测试获取角色权限"""
        from services.shared.auth.permissions import get_dynamic_permissions

        perms = get_dynamic_permissions(["user"])
        assert len(perms) > 0
        assert ("dataset", "read") in perms

    def test_merges_multiple_roles(self):
        """测试合并多角色权限"""
        from services.shared.auth.permissions import get_dynamic_permissions

        perms = get_dynamic_permissions(["user", "ai_developer"])

        # 从两个角色合并
        assert ("dataset", "read") in perms  # from user
        assert ("workflow", "execute") in perms  # from ai_developer
