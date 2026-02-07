"""
用户全生命周期集成测试
测试用例编号: LC-ON-I-001 ~ LC-OF-I-005

覆盖用户在 DataOps 平台的完整生命周期流程：
- 阶段1: 入职准备（创建账户、分配角色、发送激活通知）
- 阶段2: 首次激活（登录验证、修改密码）
- 阶段3: 熟练使用（各角色功能验证）
- 阶段4: 角色演进（权限升级/降级）
- 阶段5: 离职处理（权限回收、停用、归档）
"""

import pytest
import json
import uuid
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

import sys
import os

_project_root = os.path.join(os.path.dirname(__file__), "../..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ==================== Fixtures ====================

@pytest.fixture
def user_lifecycle_service():
    """用户生命周期服务"""

    class UserLifecycleService:
        """模拟用户生命周期管理服务"""

        def __init__(self):
            self._users = {}
            self._roles = self._init_roles()
            self._user_roles = {}
            self._audit_logs = []
            self._init_default_users()

        def _init_roles(self):
            """初始化系统角色"""
            return {
                'system_admin': {
                    'role_id': 'role-sa',
                    'name': 'system_admin',
                    'display_name': '系统管理员',
                    'permissions': ['*']
                },
                'data_admin': {
                    'role_id': 'role-da',
                    'name': 'data_admin',
                    'display_name': '数据管理员',
                    'permissions': ['datasource:*', 'metadata:*', 'standard:*']
                },
                'data_engineer': {
                    'role_id': 'role-de',
                    'name': 'data_engineer',
                    'display_name': '数据工程师',
                    'permissions': ['etl:*', 'quality:*', 'feature:*']
                },
                'ai_engineer': {
                    'role_id': 'role-ae',
                    'name': 'ai_engineer',
                    'display_name': '算法工程师',
                    'permissions': ['model:*', 'training:*', 'notebook:*']
                },
                'ai_developer': {
                    'role_id': 'role-ad',
                    'name': 'ai_developer',
                    'display_name': 'AI 开发者',
                    'permissions': ['workflow:*', 'prompt:*', 'knowledge:*', 'agent:*']
                },
                'data_analyst': {
                    'role_id': 'role-an',
                    'name': 'data_analyst',
                    'display_name': '数据分析师',
                    'permissions': ['bi:*', 'metrics:*', 'sql:*']
                },
                'business_user': {
                    'role_id': 'role-bu',
                    'name': 'business_user',
                    'display_name': '业务用户',
                    'permissions': ['query:execute', 'bi:read', 'metrics:read']
                }
            }

        def _init_default_users(self):
            """初始化默认管理员"""
            admin_user = {
                'user_id': 'admin-001',
                'username': 'admin',
                'email': 'admin@example.com',
                'display_name': '系统管理员',
                'status': 'active',
                'roles': ['system_admin'],
                'created_at': datetime.utcnow().isoformat()
            }
            self._users['admin-001'] = admin_user
            self._user_roles['admin-001'] = ['role-sa']

        def create_user(self, user_data: Dict) -> Dict:
            """创建新用户"""
            username = user_data.get('username')
            email = user_data.get('email')

            # 检查用户名和邮箱唯一性
            for u in self._users.values():
                if u['username'] == username:
                    return {'success': False, 'error': '用户名已存在'}
                if u['email'] == email:
                    return {'success': False, 'error': '邮箱已存在'}

            user_id = f"user-{str(uuid.uuid4())[:8]}"
            now = datetime.utcnow().isoformat()

            # 生成初始密码
            initial_password = f"Init{str(uuid.uuid4())[:8]}@"

            user = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'display_name': user_data.get('display_name', username),
                'phone': user_data.get('phone'),
                'department': user_data.get('department'),
                'position': user_data.get('position'),
                'status': 'pending',  # 初始状态为待激活
                'initial_password': initial_password,
                'roles': [],
                'created_at': now,
                'updated_at': now
            }

            self._users[user_id] = user

            # 记录审计日志
            self._audit_logs.append({
                'action': 'create_user',
                'user_id': user_id,
                'actor': 'admin',
                'timestamp': now
            })

            return {
                'success': True,
                'user_id': user_id,
                'initial_password': initial_password,
                'user': user
            }

        def send_activation_notification(self, user_id: str) -> Dict:
            """发送激活通知"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            # 模拟发送邮件
            notification = {
                'to': user['email'],
                'subject': '激活您的 DataOps 平台账户',
                'body': f'您的初始密码: {user["initial_password"]}',
                'sent_at': datetime.utcnow().isoformat()
            }

            self._audit_logs.append({
                'action': 'send_activation',
                'user_id': user_id,
                'timestamp': notification['sent_at']
            })

            return {'success': True, 'notification': notification}

        def activate_user(self, user_id: str, new_password: str) -> Dict:
            """激活用户（首次登录修改密码）"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            if user['status'] == 'active':
                return {'success': False, 'error': '用户已激活'}

            user['status'] = 'active'
            user['password'] = new_password
            user.pop('initial_password', None)
            user['activated_at'] = datetime.utcnow().isoformat()
            user['updated_at'] = datetime.utcnow().isoformat()

            self._audit_logs.append({
                'action': 'activate_user',
                'user_id': user_id,
                'timestamp': user['activated_at']
            })

            # 返回用户信息时移除敏感字段
            safe_user = {k: v for k, v in user.items() if k not in ('password', 'initial_password')}
            return {'success': True, 'user': safe_user}

        def assign_role(self, user_id: str, role_name: str) -> Dict:
            """分配角色"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            if role_name not in self._roles:
                return {'success': False, 'error': '角色不存在'}

            role = self._roles[role_name]
            role_id = role['role_id']

            if role_id in self._user_roles.get(user_id, []):
                return {'success': False, 'error': '用户已拥有该角色'}

            self._user_roles.setdefault(user_id, []).append(role_id)
            user['roles'].append(role)
            user['updated_at'] = datetime.utcnow().isoformat()

            self._audit_logs.append({
                'action': 'assign_role',
                'user_id': user_id,
                'role': role_name,
                'timestamp': user['updated_at']
            })

            return {'success': True, 'user': user}

        def revoke_role(self, user_id: str, role_name: str) -> Dict:
            """撤销角色"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            role = self._roles.get(role_name)
            if not role:
                return {'success': False, 'error': '角色不存在'}

            role_id = role['role_id']
            if role_id not in self._user_roles.get(user_id, []):
                return {'success': False, 'error': '用户未拥有该角色'}

            self._user_roles[user_id].remove(role_id)
            user['roles'] = [r for r in user['roles'] if r['role_id'] != role_id]
            user['updated_at'] = datetime.utcnow().isoformat()

            self._audit_logs.append({
                'action': 'revoke_role',
                'user_id': user_id,
                'role': role_name,
                'timestamp': user['updated_at']
            })

            return {'success': True, 'user': user}

        def disable_user(self, user_id: str) -> Dict:
            """停用用户"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            user['status'] = 'inactive'
            user['updated_at'] = datetime.utcnow().isoformat()

            self._audit_logs.append({
                'action': 'disable_user',
                'user_id': user_id,
                'timestamp': user['updated_at']
            })

            return {'success': True, 'user': user}

        def enable_user(self, user_id: str) -> Dict:
            """启用用户"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            user['status'] = 'active'
            user['updated_at'] = datetime.utcnow().isoformat()

            self._audit_logs.append({
                'action': 'enable_user',
                'user_id': user_id,
                'timestamp': user['updated_at']
            })

            return {'success': True, 'user': user}

        def delete_user(self, user_id: str) -> Dict:
            """删除用户（软删除）"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}

            user['status'] = 'deleted'
            user['deleted_at'] = datetime.utcnow().isoformat()
            user['updated_at'] = user['deleted_at']

            self._audit_logs.append({
                'action': 'delete_user',
                'user_id': user_id,
                'timestamp': user['deleted_at']
            })

            return {'success': True, 'user': user}

        def transfer_ownership(self, from_user_id: str, to_user_id: str, resource_type: str) -> Dict:
            """转移资源所有权"""
            from_user = self._users.get(from_user_id)
            to_user = self._users.get(to_user_id)

            if not from_user or not to_user:
                return {'success': False, 'error': '用户不存在'}

            self._audit_logs.append({
                'action': 'transfer_ownership',
                'from_user': from_user_id,
                'to_user': to_user_id,
                'resource_type': resource_type,
                'timestamp': datetime.utcnow().isoformat()
            })

            return {'success': True, 'transferred': resource_type}

        def get_user(self, user_id: str) -> Dict:
            """获取用户信息"""
            user = self._users.get(user_id)
            if not user:
                return {'success': False, 'error': '用户不存在'}
            return {'success': True, 'user': user}

        def get_audit_logs(self, user_id: str = None) -> List[Dict]:
            """获取审计日志"""
            if user_id:
                return [log for log in self._audit_logs if log.get('user_id') == user_id]
            return self._audit_logs

        def check_permission(self, user_id: str, permission: str) -> bool:
            """检查用户权限"""
            user = self._users.get(user_id)
            if not user:
                return False

            # 检查用户状态，只有 active 用户才有权限
            if user.get('status') != 'active':
                return False

            role_ids = self._user_roles.get(user_id, [])
            for role_id in role_ids:
                role = next((r for r in self._roles.values() if r['role_id'] == role_id), None)
                if role and '*' in role['permissions']:
                    return True
                if role and permission in role['permissions']:
                    return True
            return False

    return UserLifecycleService()


# ==================== 阶段1: 入职准备测试 ====================

@pytest.mark.integration
class TestOnboardingPhase:
    """阶段1: 入职准备流程测试

    测试用例：
    - LC-ON-I-001: 创建账户并分配初始角色
    - LC-ON-I-002: 生成初始密码
    - LC-ON-I-003: 发送激活通知
    """

    def test_create_user_account(self, user_lifecycle_service):
        """LC-ON-I-001: 创建用户账户"""
        user_data = {
            'username': f'test_user_{str(uuid.uuid4())[:8]}',
            'email': f'test_{str(uuid.uuid4())[:8]}@example.com',
            'display_name': '测试用户',
            'department': '数据工程部',
            'position': '数据工程师'
        }

        result = user_lifecycle_service.create_user(user_data)

        assert result['success'] is True
        assert 'user_id' in result
        assert result['user']['status'] == 'pending'

    def test_create_user_with_initial_role(self, user_lifecycle_service):
        """LC-ON-I-001: 创建用户并分配初始角色"""
        user_data = {
            'username': f'eng_{str(uuid.uuid4())[:8]}',
            'email': f'eng_{str(uuid.uuid4())[:8]}@example.com',
            'display_name': '数据工程师'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 分配数据工程师角色
        role_result = user_lifecycle_service.assign_role(user_id, 'data_engineer')

        assert role_result['success'] is True
        assert len(role_result['user']['roles']) == 1

    def test_generate_initial_password(self, user_lifecycle_service):
        """LC-ON-I-002: 生成初始密码"""
        user_data = {
            'username': f'newbie_{str(uuid.uuid4())[:8]}',
            'email': f'newbie_{str(uuid.uuid4())[:8]}@example.com'
        }

        result = user_lifecycle_service.create_user(user_data)

        assert result['success'] is True
        assert 'initial_password' in result
        assert len(result['initial_password']) >= 9

    def test_send_activation_notification(self, user_lifecycle_service):
        """LC-ON-I-003: 发送激活通知"""
        user_data = {
            'username': f'pending_{str(uuid.uuid4())[:8]}',
            'email': f'pending_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        notify_result = user_lifecycle_service.send_activation_notification(user_id)

        assert notify_result['success'] is True
        assert 'notification' in notify_result
        assert notify_result['notification']['to'] == user_data['email']


# ==================== 阶段2: 首次激活测试 ====================

@pytest.mark.integration
class TestActivationPhase:
    """阶段2: 首次激活流程测试

    测试用例：
    - LC-AC-I-001: 首次登录验证
    - LC-AC-I-002: 修改初始密码
    - LC-AC-I-003: 状态转换 pending→active
    """

    def test_first_login_authentication(self, user_lifecycle_service):
        """LC-AC-I-001: 首次登录验证"""
        user_data = {
            'username': f'login_{str(uuid.uuid4())[:8]}',
            'email': f'login_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']
        initial_password = create_result['initial_password']

        # 验证初始密码存在
        get_result = user_lifecycle_service.get_user(user_id)
        assert get_result['user']['initial_password'] == initial_password

    def test_change_initial_password(self, user_lifecycle_service):
        """LC-AC-I-002: 修改初始密码"""
        user_data = {
            'username': f'chpwd_{str(uuid.uuid4())[:8]}',
            'email': f'chpwd_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        new_password = 'NewSecure@123456'
        activate_result = user_lifecycle_service.activate_user(user_id, new_password)

        assert activate_result['success'] is True
        assert 'password' not in activate_result['user']  # 密码不应返回
        assert 'initial_password' not in activate_result['user']

    def test_status_transition_to_active(self, user_lifecycle_service):
        """LC-AC-I-003: 状态转换 pending→active"""
        user_data = {
            'username': f'status_{str(uuid.uuid4())[:8]}',
            'email': f'status_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 验证初始状态
        assert create_result['user']['status'] == 'pending'

        # 激活用户
        user_lifecycle_service.activate_user(user_id, 'NewPass@123')

        # 验证状态转换
        get_result = user_lifecycle_service.get_user(user_id)
        assert get_result['user']['status'] == 'active'
        assert 'activated_at' in get_result['user']


# ==================== 阶段4: 角色演进测试 ====================

@pytest.mark.integration
class TestRoleProgressionPhase:
    """阶段4: 角色演进流程测试

    测试用例：
    - LC-RP-I-001: 权限升级（角色添加）
    - LC-RP-I-002: 权限降级（角色撤销）
    - LC-RP-I-003: 跨角色权限验证
    """

    def test_permission_upgrade(self, user_lifecycle_service):
        """LC-RP-I-001: 权限升级"""
        user_data = {
            'username': f'upgrade_{str(uuid.uuid4())[:8]}',
            'email': f'upgrade_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 激活用户
        user_lifecycle_service.activate_user(user_id, 'TestPass@123')

        # 初始角色：业务用户
        user_lifecycle_service.assign_role(user_id, 'business_user')

        # 升级为数据分析师
        upgrade_result = user_lifecycle_service.assign_role(user_id, 'data_analyst')

        assert upgrade_result['success'] is True
        assert len(upgrade_result['user']['roles']) == 2

        # 验证权限
        assert user_lifecycle_service.check_permission(user_id, 'bi:*') is True

    def test_permission_downgrade(self, user_lifecycle_service):
        """LC-RP-I-002: 权限降级"""
        user_data = {
            'username': f'downgrade_{str(uuid.uuid4())[:8]}',
            'email': f'downgrade_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 激活用户
        user_lifecycle_service.activate_user(user_id, 'TestPass@123')

        # 初始角色：数据管理员
        user_lifecycle_service.assign_role(user_id, 'data_admin')

        # 验证有权限
        assert user_lifecycle_service.check_permission(user_id, 'datasource:*') is True

        # 降级
        revoke_result = user_lifecycle_service.revoke_role(user_id, 'data_admin')

        assert revoke_result['success'] is True
        assert len(revoke_result['user']['roles']) == 0

        # 验证权限撤销
        assert user_lifecycle_service.check_permission(user_id, 'datasource:*') is False

    def test_cross_role_permission_isolation(self, user_lifecycle_service):
        """LC-RP-I-003: 跨角色权限隔离"""
        # 创建数据工程师
        de_data = {
            'username': f'de_{str(uuid.uuid4())[:8]}',
            'email': f'de_{str(uuid.uuid4())[:8]}@example.com'
        }
        de_result = user_lifecycle_service.create_user(de_data)
        de_user_id = de_result['user_id']
        user_lifecycle_service.activate_user(de_user_id, 'TestPass@123')
        user_lifecycle_service.assign_role(de_user_id, 'data_engineer')

        # 创建AI开发者
        ad_data = {
            'username': f'ad_{str(uuid.uuid4())[:8]}',
            'email': f'ad_{str(uuid.uuid4())[:8]}@example.com'
        }
        ad_result = user_lifecycle_service.create_user(ad_data)
        ad_user_id = ad_result['user_id']
        user_lifecycle_service.activate_user(ad_user_id, 'TestPass@123')
        user_lifecycle_service.assign_role(ad_user_id, 'ai_developer')

        # 数据工程师有 ETL 权限，没有工作流权限
        assert user_lifecycle_service.check_permission(de_user_id, 'etl:*') is True
        assert user_lifecycle_service.check_permission(de_user_id, 'workflow:*') is False

        # AI开发者有工作流权限，没有 ETL 权限
        assert user_lifecycle_service.check_permission(ad_user_id, 'workflow:*') is True
        assert user_lifecycle_service.check_permission(ad_user_id, 'etl:*') is False


# ==================== 阶段5: 离职处理测试 ====================

@pytest.mark.integration
class TestOffboardingPhase:
    """阶段5: 离职处理流程测试

    测试用例：
    - LC-OF-I-001: 正常离职（权限降级）
    - LC-OF-I-002: 紧急离职（立即停用）
    - LC-OF-I-003: 用户删除
    - LC-OF-I-004: 资源所有权转移
    """

    def test_normal_offboarding_permission_revoke(self, user_lifecycle_service):
        """LC-OF-I-001: 正常离职流程"""
        user_data = {
            'username': f'normal_off_{str(uuid.uuid4())[:8]}',
            'email': f'normal_off_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 分配多个角色
        user_lifecycle_service.assign_role(user_id, 'data_admin')
        user_lifecycle_service.assign_role(user_id, 'data_engineer')

        # 正常离职：先撤销角色
        user_lifecycle_service.revoke_role(user_id, 'data_admin')
        user_lifecycle_service.revoke_role(user_id, 'data_engineer')

        # 再停用账户
        disable_result = user_lifecycle_service.disable_user(user_id)

        assert disable_result['success'] is True
        assert disable_result['user']['status'] == 'inactive'

    def test_emergency_offboarding_immediate_disable(self, user_lifecycle_service):
        """LC-OF-I-002: 紧急离职流程"""
        user_data = {
            'username': f'emergency_{str(uuid.uuid4())[:8]}',
            'email': f'emergency_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 分配角色
        user_lifecycle_service.assign_role(user_id, 'system_admin')

        # 紧急停用
        disable_result = user_lifecycle_service.disable_user(user_id)

        assert disable_result['success'] is True
        assert disable_result['user']['status'] == 'inactive'

        # 验证无法登录（权限失效）
        assert not user_lifecycle_service.check_permission(user_id, '*')

    def test_user_soft_delete(self, user_lifecycle_service):
        """LC-OF-I-003: 用户软删除"""
        user_data = {
            'username': f'delete_{str(uuid.uuid4())[:8]}',
            'email': f'delete_{str(uuid.uuid4())[:8]}@example.com'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 先停用
        user_lifecycle_service.disable_user(user_id)

        # 再删除
        delete_result = user_lifecycle_service.delete_user(user_id)

        assert delete_result['success'] is True
        assert delete_result['user']['status'] == 'deleted'
        assert 'deleted_at' in delete_result['user']

    def test_resource_ownership_transfer(self, user_lifecycle_service):
        """LC-OF-I-004: 资源所有权转移"""
        # 创建离职用户
        leaving_data = {
            'username': f'leaving_{str(uuid.uuid4())[:8]}',
            'email': f'leaving_{str(uuid.uuid4())[:8]}@example.com'
        }
        leaving_result = user_lifecycle_service.create_user(leaving_data)
        leaving_user_id = leaving_result['user_id']

        # 创建接手用户
        replacement_data = {
            'username': f'replace_{str(uuid.uuid4())[:8]}',
            'email': f'replace_{str(uuid.uuid4())[:8]}@example.com'
        }
        replacement_result = user_lifecycle_service.create_user(replacement_data)
        replacement_user_id = replacement_result['user_id']

        # 转移所有权
        transfer_result = user_lifecycle_service.transfer_ownership(
            leaving_user_id,
            replacement_user_id,
            'etl_tasks'
        )

        assert transfer_result['success'] is True
        assert transfer_result['transferred'] == 'etl_tasks'

        # 验证审计日志
        logs = user_lifecycle_service.get_audit_logs()
        transfer_log = [log for log in logs if log['action'] == 'transfer_ownership']
        assert len(transfer_log) > 0


# ==================== 完整生命周期测试 ====================

@pytest.mark.integration
class TestCompleteLifecycle:
    """完整生命周期测试

    测试用例：
    - LC-FULL-I-001: 完整入职到离职流程
    """

    def test_full_lifecycle_flow(self, user_lifecycle_service):
        """LC-FULL-I-001: 完整的用户生命周期流程"""
        # === 阶段1: 入职准备 ===
        user_data = {
            'username': f'full_lc_{str(uuid.uuid4())[:8]}',
            'email': f'full_lc_{str(uuid.uuid4())[:8]}@example.com',
            'display_name': '完整生命周期测试用户',
            'department': '数据工程部',
            'position': '初级数据工程师'
        }

        create_result = user_lifecycle_service.create_user(user_data)
        user_id = create_result['user_id']

        # 分配初始角色
        user_lifecycle_service.assign_role(user_id, 'data_engineer')

        # 发送激活通知
        user_lifecycle_service.send_activation_notification(user_id)

        # === 阶段2: 首次激活 ===
        user_lifecycle_service.activate_user(user_id, 'SecurePass@123')

        get_result = user_lifecycle_service.get_user(user_id)
        assert get_result['user']['status'] == 'active'

        # === 阶段4: 角色演进（晋升） ===
        # 升级为高级工程师，添加数据管理员角色
        user_lifecycle_service.assign_role(user_id, 'data_admin')

        get_result = user_lifecycle_service.get_user(user_id)
        assert len(get_result['user']['roles']) == 2

        # === 阶段5: 离职处理 ===
        # 撤销角色
        user_lifecycle_service.revoke_role(user_id, 'data_admin')
        user_lifecycle_service.revoke_role(user_id, 'data_engineer')

        # 停用账户
        user_lifecycle_service.disable_user(user_id)

        get_result = user_lifecycle_service.get_user(user_id)
        assert get_result['user']['status'] == 'inactive'

        # 删除用户
        user_lifecycle_service.delete_user(user_id)

        final_result = user_lifecycle_service.get_user(user_id)
        assert final_result['user']['status'] == 'deleted'

        # 验证完整的审计日志
        logs = user_lifecycle_service.get_audit_logs(user_id)
        actions = [log['action'] for log in logs]

        expected_actions = [
            'create_user',
            'assign_role',
            'send_activation',
            'activate_user',
            'assign_role',
            'revoke_role',
            'revoke_role',
            'disable_user',
            'delete_user'
        ]

        for expected in expected_actions:
            assert expected in actions, f"审计日志缺少操作: {expected}"
