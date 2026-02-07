"""
用户和权限生成器

生成：
- 用户（5种角色，23+用户）
- 角色
- 权限
- 用户角色关联
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import (
    BaseGenerator, UserRoles, generate_id, random_date,
    random_chinese_name, random_chinese_department,
    generate_email, generate_phone, hash_password
)
from ..config import GeneratorQuantities, ROLE_PERMISSIONS


class UserGenerator(BaseGenerator):
    """
    用户生成器

    生成用户、角色、权限数据
    """

    # 角色中文名称映射
    ROLE_NAMES = {
        UserRoles.DATA_ADMINISTRATOR: "数据管理员",
        UserRoles.DATA_ENGINEER: "数据工程师",
        UserRoles.AI_DEVELOPER: "AI开发者",
        UserRoles.DATA_ANALYST: "数据分析师",
        UserRoles.SYSTEM_ADMINISTRATOR: "系统管理员",
    }

    # 部门列表
    DEPARTMENTS = [
        "数据治理部",
        "数据工程部",
        "AI研发部",
        "数据分析部",
        "系统运维部",
        "产品部",
        "市场部",
        "财务部",
    ]

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有用户相关数据

        Returns:
            包含users, roles, permissions, user_roles的字典
        """
        self.log("Generating users and permissions...", "info")

        # 生成权限
        permissions = self._generate_permissions()
        self.store_data("permissions", permissions)

        # 生成角色
        roles = self._generate_roles(permissions)
        self.store_data("roles", roles)

        # 生成用户
        users = self._generate_users()
        self.store_data("users", users)

        # 生成用户角色关联
        user_roles = self._generate_user_roles(users, roles)
        self.store_data("user_roles", user_roles)

        self.log(f"Generated {len(users)} users, {len(roles)} roles, {len(permissions)} permissions", "success")

        return self.get_all_data()

    def _generate_permissions(self) -> List[Dict[str, Any]]:
        """生成所有权限"""
        permissions = []
        permission_id = 1

        for role_config in ROLE_PERMISSIONS.values():
            for perm_code in role_config.permissions:
                # 解析权限代码
                resource, action = perm_code.split(":") if ":" in perm_code else (perm_code, "*")

                permission = {
                    "permission_id": f"perm_{permission_id:04d}",
                    "permission_code": perm_code,
                    "permission_name": f"{resource} {action}",
                    "resource": resource,
                    "action": action,
                    "description": f"{resource}资源的{action}权限",
                    "created_at": random_date(90),
                }
                permissions.append(permission)
                permission_id += 1

        return permissions

    def _generate_roles(self, permissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成角色"""
        roles = []
        perm_map = {p["permission_code"]: p["permission_id"] for p in permissions}

        for role_code, role_config in ROLE_PERMISSIONS.items():
            # 获取权限ID列表
            permission_ids = [perm_map.get(p, "") for p in role_config.permissions]
            permission_ids = [pid for pid in permission_ids if pid]

            role = {
                "role_id": f"role_{role_code}",
                "role_code": role_code,
                "role_name": role_config.role_name,
                "description": role_config.description,
                "permissions": ",".join(permission_ids),
                "created_at": random_date(90),
            }
            roles.append(role)

        return roles

    def _generate_users(self) -> List[Dict[str, Any]]:
        """生成用户"""
        users = []

        # 为每个角色生成用户
        role_counts = {
            UserRoles.DATA_ADMINISTRATOR: self.quantities.data_administrator_count,
            UserRoles.DATA_ENGINEER: self.quantities.data_engineer_count,
            UserRoles.AI_DEVELOPER: self.quantities.ai_developer_count,
            UserRoles.DATA_ANALYST: self.quantities.data_analyst_count,
            UserRoles.SYSTEM_ADMINISTRATOR: self.quantities.system_administrator_count,
        }

        user_id = 1

        for role, count in role_counts.items():
            for i in range(count):
                is_active = random.random() > 0.1  # 90%活跃
                user = self._create_user(user_id, role, i + 1, is_active)
                users.append(user)
                user_id += 1

        return users

    def _create_user(
        self,
        index: int,
        role: str,
        role_index: int,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """创建单个用户"""
        role_suffix = f"{role[:3].lower()}_{role_index:02d}"
        user_id = generate_id("user_", 8)

        # 生成中文姓名
        name = random_chinese_name()

        # 生成用户名
        username_map = {
            UserRoles.DATA_ADMINISTRATOR: f"da_admin_{role_index}",
            UserRoles.DATA_ENGINEER: f"de_engineer_{role_index}",
            UserRoles.AI_DEVELOPER: f"ai_dev_{role_index}",
            UserRoles.DATA_ANALYST: f"analyst_{role_index}",
            UserRoles.SYSTEM_ADMINISTRATOR: f"sys_admin_{role_index}",
        }
        username = username_map.get(role, f"user_{index}")

        # 生成邮箱
        email = generate_email(name)

        # 生成手机号
        phone = generate_phone()

        # 选择部门
        department_map = {
            UserRoles.DATA_ADMINISTRATOR: "数据治理部",
            UserRoles.DATA_ENGINEER: "数据工程部",
            UserRoles.AI_DEVELOPER: "AI研发部",
            UserRoles.DATA_ANALYST: "数据分析部",
            UserRoles.SYSTEM_ADMINISTRATOR: "系统运维部",
        }
        department = department_map.get(role, random.choice(self.DEPARTMENTS))

        # 状态
        status = "active" if is_active else random.choice(["inactive", "locked"])

        # 创建时间
        created_at = random_date(90)

        user = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "full_name": name,
            "phone": phone,
            "password": hash_password("Test123456"),  # 默认测试密码
            "role": role,
            "role_name": self.ROLE_NAMES.get(role, role),
            "department": department,
            "status": status,
            "is_active": is_active,
            "last_login": random_date(30) if is_active else None,
            "created_at": created_at,
            "updated_at": random_date(30),
        }

        return user

    def _generate_user_roles(self, users: List[Dict], roles: List[Dict]) -> List[Dict[str, Any]]:
        """生成用户角色关联"""
        user_roles = []

        for user in users:
            role_code = user["role"]
            role_id = f"role_{role_code}"

            user_role = {
                "user_role_id": generate_id("ur_", 8),
                "user_id": user["user_id"],
                "role_id": role_id,
                "granted_at": user["created_at"],
                "granted_by": "system",
            }
            user_roles.append(user_role)

        return user_roles

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving users to database...", "info")

        # 保存角色
        roles = self.get_data("roles")
        if roles and self.storage.table_exists("roles"):
            self.storage.batch_insert(
                "roles",
                ["role_id", "role_code", "role_name", "description", "permissions", "created_at"],
                roles,
                idempotent=True,
                idempotent_columns=["role_id"]
            )
            self.log(f"Saved {len(roles)} roles", "success")

        # 保存权限
        permissions = self.get_data("permissions")
        if permissions and self.storage.table_exists("permissions"):
            self.storage.batch_insert(
                "permissions",
                ["permission_id", "permission_code", "permission_name", "resource", "action", "description", "created_at"],
                permissions,
                idempotent=True,
                idempotent_columns=["permission_code"]
            )
            self.log(f"Saved {len(permissions)} permissions", "success")

        # 保存用户
        users = self.get_data("users")
        if users and self.storage.table_exists("users"):
            self.storage.batch_insert(
                "users",
                ["user_id", "username", "email", "full_name", "phone", "password", "role", "role_name",
                 "department", "status", "is_active", "last_login", "created_at", "updated_at"],
                users,
                idempotent=True,
                idempotent_columns=["user_id", "username"]
            )
            self.log(f"Saved {len(users)} users", "success")

        # 保存用户角色关联
        user_roles = self.get_data("user_roles")
        if user_roles and self.storage.table_exists("user_roles"):
            self.storage.batch_insert(
                "user_roles",
                ["user_role_id", "user_id", "role_id", "granted_at", "granted_by"],
                user_roles,
                idempotent=True,
                idempotent_columns=["user_id", "role_id"]
            )
            self.log(f"Saved {len(user_roles)} user roles", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up user data...", "info")

        if self.storage.table_exists("user_roles"):
            self.storage.cleanup_by_prefix("user_roles", "user_role_id", "ur_")

        if self.storage.table_exists("users"):
            self.storage.cleanup_by_prefix("users", "user_id", "user_")

        if self.storage.table_exists("roles"):
            # 不删除角色，因为可能被其他地方使用
            pass


def generate_user_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成用户数据

    Args:
        config: 生成配置

    Returns:
        用户数据字典
    """
    generator = UserGenerator(config)
    return generator.generate()


def generate_test_users() -> List[Dict[str, Any]]:
    """
    生成测试用户（默认配置）

    Returns:
        用户列表
    """
    generator = UserGenerator()
    data = generator.generate()
    return data["users"]
