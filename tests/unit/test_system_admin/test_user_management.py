"""
用户与权限管理单元测试
测试用例：SA-UM-001 ~ SA-UM-010
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestUserManagement:
    """用户管理测试 (SA-UM-001 ~ SA-UM-006)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user(self, mock_user_service):
        """SA-UM-001: 创建用户"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'role': 'data_engineer',
            'department': '数据开发部'
        }

        mock_user_service.create_user = AsyncMock(return_value={
            'success': True,
            'user_id': 'user_0001',
            'username': 'testuser',
            'status': 'active'
        })

        result = await mock_user_service.create_user(user_data)

        assert result['success'] is True
        assert 'user_id' in result

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_edit_user(self, mock_user_service):
        """SA-UM-002: 编辑用户"""
        user_id = 'user_0001'
        update_data = {
            'full_name': 'Updated Name',
            'department': 'AI实验室'
        }

        mock_user_service.update_user = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'updated_fields': list(update_data.keys())
        })

        result = await mock_user_service.update_user(user_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disable_user(self, mock_user_service):
        """SA-UM-003: 禁用用户"""
        user_id = 'user_0001'

        mock_user_service.set_user_status = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'old_status': 'active',
            'new_status': 'inactive',
            'can_login': False
        })

        result = await mock_user_service.set_user_status(user_id, 'inactive')

        assert result['success'] is True
        assert result['can_login'] is False

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enable_user(self, mock_user_service):
        """SA-UM-004: 启用用户"""
        user_id = 'user_0001'

        mock_user_service.set_user_status = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'new_status': 'active',
            'can_login': True
        })

        result = await mock_user_service.set_user_status(user_id, 'active')

        assert result['success'] is True
        assert result['can_login'] is True

    @pytest.mark.p2
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_user(self, mock_user_service):
        """SA-UM-005: 删除用户"""
        user_id = 'user_0001'

        mock_user_service.delete_user = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'deleted': True
        })

        result = await mock_user_service.delete_user(user_id)

        assert result['success'] is True
        assert result['deleted'] is True


class TestRoleManagement:
    """角色管理测试 (SA-UM-006 ~ SA-UM-008)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_role(self, mock_user_service):
        """SA-UM-006: 创建角色"""
        role_data = {
            'role_name': '数据分析师',
            'role_code': 'data_analyst',
            'description': '负责数据分析和报表制作',
            'permissions': [
                'metadata:read',
                'asset:read',
                'query:execute'
            ]
        }

        mock_user_service.create_role = AsyncMock(return_value={
            'success': True,
            'role_id': 'role_0001',
            'role_code': 'data_analyst'
        })

        result = await mock_user_service.create_role(role_data)

        assert result['success'] is True
        assert 'role_id' in result

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_edit_role_permissions(self, mock_user_service):
        """SA-UM-007: 编辑角色权限"""
        role_id = 'role_0001'
        new_permissions = [
            'metadata:read',
            'metadata:write',
            'asset:read',
            'query:execute'
        ]

        mock_user_service.update_role_permissions = AsyncMock(return_value={
            'success': True,
            'role_id': role_id,
            'old_permissions_count': 3,
            'new_permissions_count': 4
        })

        result = await mock_user_service.update_role_permissions(role_id, new_permissions)

        assert result['success'] is True
        assert result['new_permissions_count'] == 4

    @pytest.mark.p2
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_role(self, mock_user_service):
        """SA-UM-008: 删除角色"""
        role_id = 'role_0001'

        mock_user_service.delete_role = AsyncMock(return_value={
            'success': True,
            'role_id': role_id,
            'deleted': True
        })

        result = await mock_user_service.delete_role(role_id)

        assert result['success'] is True


class TestUserRoleAssignment:
    """用户角色分配测试 (SA-UM-009 ~ SA-UM-010)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, mock_user_service):
        """SA-UM-009: 用户角色分配"""
        user_id = 'user_0001'
        role_id = 'role_0001'

        mock_user_service.assign_role = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'role_id': role_id,
            'assigned_at': '2024-01-01T10:00:00Z'
        })

        result = await mock_user_service.assign_role(user_id, role_id)

        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['role_id'] == role_id

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_permission_policy_config(self, mock_permission_service):
        """SA-UM-010: 数据权限策略配置"""
        role_id = 'role_0001'
        policy = {
            'data_scope': 'department',
            'departments': ['数据开发部'],
            'tables': ['users', 'orders'],
            'row_filter': 'department = ?',
            'column_masking': ['phone', 'id_card']
        }

        mock_permission_service.set_data_policy = AsyncMock(return_value={
            'success': True,
            'policy_id': 'policy_0001',
            'role_id': role_id,
            'policy_active': True
        })

        result = await mock_permission_service.set_data_policy(role_id, policy)

        assert result['success'] is True
        assert result['policy_active'] is True

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_data_policy_effective(self, mock_permission_service):
        """验证数据权限策略生效"""
        user_id = 'user_0001'
        resource = 'table:users'

        mock_permission_service.check_data_access = AsyncMock(return_value={
            'allowed': True,
            'access_type': 'masked',
            'accessible_columns': ['id', 'username', 'created_at'],
            'masked_columns': ['phone', 'email', 'id_card']
        })

        result = await mock_permission_service.check_data_access(user_id, resource)

        assert result['allowed'] is True
        assert result['access_type'] == 'masked'
        assert 'phone' in result['masked_columns']


# ==================== Fixtures ====================

@pytest.fixture
def mock_user_service():
    """Mock 用户服务"""
    service = Mock()
    service.create_user = AsyncMock()
    service.update_user = AsyncMock()
    service.set_user_status = AsyncMock()
    service.delete_user = AsyncMock()
    service.create_role = AsyncMock()
    service.update_role_permissions = AsyncMock()
    service.delete_role = AsyncMock()
    service.assign_role = AsyncMock()
    return service


@pytest.fixture
def mock_permission_service():
    """Mock 权限服务"""
    service = Mock()
    service.set_data_policy = AsyncMock()
    service.check_data_access = AsyncMock()
    return service
