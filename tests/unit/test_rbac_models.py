"""
RBAC 数据模型单元测试
Sprint 30: P1 测试覆盖 - API 成熟度提升
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestRoleModel:
    """角色模型测试"""

    def test_role_default_values(self):
        """测试角色默认值"""
        from services.shared.models.rbac import Role

        role = Role(name='test_role')

        assert role.name == 'test_role'
        assert role.role_type == 'custom'
        assert role.is_active is True
        assert role.is_system is False
        assert role.priority == 0

    def test_role_to_dict(self):
        """测试角色转字典"""
        from services.shared.models.rbac import Role

        role = Role(
            id='role-123',
            name='admin',
            display_name='管理员',
            description='系统管理员',
            role_type='system',
            is_active=True,
            is_system=True,
            priority=100
        )
        role.created_at = datetime(2024, 1, 1, 12, 0, 0)
        role.updated_at = datetime(2024, 1, 1, 12, 0, 0)

        data = role.to_dict()

        assert data['id'] == 'role-123'
        assert data['name'] == 'admin'
        assert data['display_name'] == '管理员'
        assert data['is_system'] is True
        assert data['priority'] == 100
        assert 'created_at' in data

    def test_role_to_dict_with_permissions(self):
        """测试角色转字典包含权限"""
        from services.shared.models.rbac import Role, Permission, RolePermission

        role = Role(
            id='role-123',
            name='admin'
        )
        role.created_at = datetime.utcnow()
        role.updated_at = datetime.utcnow()

        # 模拟权限关系
        permission = Permission(
            id='perm-1',
            name='user:read',
            resource='user',
            operation='read'
        )
        permission.created_at = datetime.utcnow()
        permission.updated_at = datetime.utcnow()

        role_permission = MagicMock()
        role_permission.permission = permission
        role.permissions = [role_permission]

        data = role.to_dict(include_permissions=True)

        assert 'permissions' in data
        assert len(data['permissions']) == 1

    def test_role_repr(self):
        """测试角色字符串表示"""
        from services.shared.models.rbac import Role

        role = Role(id='role-123', name='admin')

        repr_str = repr(role)

        assert 'role-123' in repr_str
        assert 'admin' in repr_str


class TestRoleHasPermission:
    """角色权限检查测试"""

    def test_has_permission_direct(self):
        """测试直接权限检查"""
        from services.shared.models.rbac import Role, Permission, RolePermission

        role = Role(id='role-1', name='viewer')
        permission = Permission(
            id='perm-1',
            name='dataset:read',
            resource='dataset',
            operation='read'
        )

        rp = MagicMock()
        rp.permission = permission
        role.permissions = [rp]
        role.parent_role = None

        assert role.has_permission('dataset', 'read') is True
        assert role.has_permission('dataset', 'write') is False

    def test_has_permission_wildcard_resource(self):
        """测试通配符资源权限"""
        from services.shared.models.rbac import Role, Permission

        role = Role(id='role-1', name='superadmin')
        permission = Permission(
            id='perm-1',
            name='all:read',
            resource='*',
            operation='read'
        )

        rp = MagicMock()
        rp.permission = permission
        role.permissions = [rp]
        role.parent_role = None

        assert role.has_permission('dataset', 'read') is True
        assert role.has_permission('workflow', 'read') is True

    def test_has_permission_wildcard_operation(self):
        """测试通配符操作权限"""
        from services.shared.models.rbac import Role, Permission

        role = Role(id='role-1', name='dataset_admin')
        permission = Permission(
            id='perm-1',
            name='dataset:all',
            resource='dataset',
            operation='*'
        )

        rp = MagicMock()
        rp.permission = permission
        role.permissions = [rp]
        role.parent_role = None

        assert role.has_permission('dataset', 'read') is True
        assert role.has_permission('dataset', 'write') is True
        assert role.has_permission('dataset', 'delete') is True


class TestPermissionModel:
    """权限模型测试"""

    def test_permission_default_values(self):
        """测试权限默认值"""
        from services.shared.models.rbac import Permission

        permission = Permission(
            name='test:read',
            resource='test',
            operation='read'
        )

        assert permission.scope == 'all'
        assert permission.is_active is True
        assert permission.is_system is False

    def test_permission_to_dict(self):
        """测试权限转字典"""
        from services.shared.models.rbac import Permission

        permission = Permission(
            id='perm-123',
            name='user:create',
            display_name='创建用户',
            description='允许创建新用户',
            resource='user',
            operation='create',
            scope='tenant',
            is_active=True,
            is_system=True
        )
        permission.created_at = datetime(2024, 1, 1, 12, 0, 0)
        permission.updated_at = datetime(2024, 1, 1, 12, 0, 0)

        data = permission.to_dict()

        assert data['id'] == 'perm-123'
        assert data['name'] == 'user:create'
        assert data['resource'] == 'user'
        assert data['operation'] == 'create'
        assert data['scope'] == 'tenant'

    def test_permission_string(self):
        """测试权限字符串表示"""
        from services.shared.models.rbac import Permission

        permission = Permission(
            name='user:create',
            resource='user',
            operation='create'
        )

        assert permission.permission_string == 'user:create'

    def test_permission_repr(self):
        """测试权限字符串表示"""
        from services.shared.models.rbac import Permission

        permission = Permission(id='perm-123', name='user:read')

        repr_str = repr(permission)

        assert 'perm-123' in repr_str
        assert 'user:read' in repr_str


class TestRolePermissionModel:
    """角色权限关联模型测试"""

    def test_role_permission_repr(self):
        """测试角色权限关联字符串表示"""
        from services.shared.models.rbac import RolePermission

        rp = RolePermission(
            role_id='role-1',
            permission_id='perm-1'
        )

        repr_str = repr(rp)

        assert 'role-1' in repr_str
        assert 'perm-1' in repr_str

    def test_role_permission_granted_at(self):
        """测试授权时间默认值"""
        from services.shared.models.rbac import RolePermission

        rp = RolePermission(
            role_id='role-1',
            permission_id='perm-1',
            granted_by='admin'
        )

        assert rp.granted_by == 'admin'
        # granted_at 会在插入时自动设置


class TestSystemPermissions:
    """系统权限预定义测试"""

    def test_system_permissions_exist(self):
        """测试系统权限存在"""
        from services.shared.models.rbac import SYSTEM_PERMISSIONS

        assert len(SYSTEM_PERMISSIONS) > 0

    def test_dataset_permissions_exist(self):
        """测试数据集权限存在"""
        from services.shared.models.rbac import SYSTEM_PERMISSIONS

        dataset_perms = [p for p in SYSTEM_PERMISSIONS if p['resource'] == 'dataset']

        assert len(dataset_perms) >= 4  # create, read, update, delete
        operations = {p['operation'] for p in dataset_perms}
        assert 'create' in operations
        assert 'read' in operations
        assert 'update' in operations
        assert 'delete' in operations

    def test_workflow_permissions_exist(self):
        """测试工作流权限存在"""
        from services.shared.models.rbac import SYSTEM_PERMISSIONS

        workflow_perms = [p for p in SYSTEM_PERMISSIONS if p['resource'] == 'workflow']

        assert len(workflow_perms) >= 5  # create, read, update, delete, execute
        operations = {p['operation'] for p in workflow_perms}
        assert 'execute' in operations

    def test_system_admin_permissions_exist(self):
        """测试系统管理权限存在"""
        from services.shared.models.rbac import SYSTEM_PERMISSIONS

        system_perms = [p for p in SYSTEM_PERMISSIONS if p['resource'] == 'system']

        assert len(system_perms) >= 1


class TestSystemRoles:
    """系统角色预定义测试"""

    def test_system_roles_exist(self):
        """测试系统角色存在"""
        from services.shared.models.rbac import SYSTEM_ROLES

        assert len(SYSTEM_ROLES) > 0

    def test_admin_role_exists(self):
        """测试管理员角色存在"""
        from services.shared.models.rbac import SYSTEM_ROLES

        admin_role = next((r for r in SYSTEM_ROLES if r['name'] == 'admin'), None)

        assert admin_role is not None
        assert admin_role['is_system'] is True
        assert admin_role['priority'] == 100

    def test_user_role_exists(self):
        """测试普通用户角色存在"""
        from services.shared.models.rbac import SYSTEM_ROLES

        user_role = next((r for r in SYSTEM_ROLES if r['name'] == 'user'), None)

        assert user_role is not None
        assert user_role['is_system'] is True

    def test_guest_role_has_lowest_priority(self):
        """测试访客角色优先级最低"""
        from services.shared.models.rbac import SYSTEM_ROLES

        guest_role = next((r for r in SYSTEM_ROLES if r['name'] == 'guest'), None)

        assert guest_role is not None
        assert guest_role['priority'] == 0

    def test_all_system_roles_are_system(self):
        """测试所有系统角色标记为系统角色"""
        from services.shared.models.rbac import SYSTEM_ROLES

        for role in SYSTEM_ROLES:
            assert role['is_system'] is True
            assert role['role_type'] == 'system'


class TestRoleInheritance:
    """角色继承测试"""

    def test_get_all_permissions_includes_parent(self):
        """测试获取所有权限包含父角色权限"""
        from services.shared.models.rbac import Role, Permission

        # 创建父角色
        parent_role = Role(id='parent', name='parent_role')
        parent_permission = Permission(
            id='parent-perm',
            name='parent:read',
            resource='parent',
            operation='read'
        )
        parent_rp = MagicMock()
        parent_rp.permission = parent_permission
        parent_role.permissions = [parent_rp]
        parent_role.parent_role = None

        # 创建子角色
        child_role = Role(id='child', name='child_role')
        child_permission = Permission(
            id='child-perm',
            name='child:read',
            resource='child',
            operation='read'
        )
        child_rp = MagicMock()
        child_rp.permission = child_permission
        child_role.permissions = [child_rp]
        child_role.parent_role = parent_role

        all_permissions = child_role.get_all_permissions()

        assert len(all_permissions) == 2
        resources = {p.resource for p in all_permissions}
        assert 'parent' in resources
        assert 'child' in resources


class TestTableArgs:
    """表参数测试"""

    def test_role_table_args(self):
        """测试角色表参数"""
        from services.shared.models.rbac import Role

        table_args = Role.__table_args__

        assert isinstance(table_args, tuple)
        # 最后一个元素应该是字典
        config = table_args[-1]
        assert config.get('mysql_engine') == 'InnoDB'
        assert config.get('mysql_charset') == 'utf8mb4'

    def test_permission_table_args(self):
        """测试权限表参数"""
        from services.shared.models.rbac import Permission

        table_args = Permission.__table_args__

        assert isinstance(table_args, tuple)
        config = table_args[-1]
        assert config.get('mysql_engine') == 'InnoDB'

    def test_role_permission_table_args(self):
        """测试角色权限表参数"""
        from services.shared.models.rbac import RolePermission

        table_args = RolePermission.__table_args__

        assert isinstance(table_args, tuple)
        config = table_args[-1]
        assert config.get('mysql_engine') == 'InnoDB'
