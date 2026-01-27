"""
API密钥管理服务
支持API密钥的生成、验证、权限管理
"""

import secrets
import hashlib
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """权限枚举"""
    READ = "read"               # 只读权限
    WRITE = "write"             # 读写权限
    ADMIN = "admin"             # 管理员权限
    TASK_CREATE = "task:create" # 创建任务
    TASK_READ = "task:read"     # 读取任务
    TASK_DELETE = "task:delete" # 删除任务
    TEMPLATE_MANAGE = "template:manage"  # 模板管理


@dataclass
class APIKey:
    """API密钥"""
    id: str
    key_hash: str              # 密钥哈希值
    name: str                  # 密钥名称
    user_id: str               # 所属用户
    permissions: List[str]     # 权限列表
    rate_limit: Optional[int]  # 速率限制（请求/分钟）
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: datetime = None
    is_active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        if Permission.ADMIN.value in self.permissions:
            return True
        return permission in self.permissions

    def is_expired(self) -> bool:
        """检查是否过期"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self, hide_key: bool = True) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }


class APIKeyManager:
    """API密钥管理器"""

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._hash_index: Dict[str, str] = {}  # key_hash -> key_id

    def create_key(
        self,
        name: str,
        user_id: str,
        permissions: List[str],
        rate_limit: Optional[int] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        创建新的API密钥

        Args:
            name: 密钥名称
            user_id: 所属用户ID
            permissions: 权限列表
            rate_limit: 速率限制（请求/分钟）
            expires_in_days: 有效期（天）

        Returns:
            API密钥（只在创建时返回）
        """
        # 生成密钥
        key_id = secrets.token_hex(16)
        raw_key = f"ocr_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        # 计算过期时间
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # 创建API密钥对象
        api_key = APIKey(
            id=key_id,
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            permissions=permissions,
            rate_limit=rate_limit,
            expires_at=expires_at,
            created_at=datetime.now()
        )

        # 存储密钥
        self._keys[key_id] = api_key
        self._hash_index[key_hash] = key_id

        logger.info(f"Created API key: {key_id} for user: {user_id}")
        return raw_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        验证API密钥

        Args:
            raw_key: 原始密钥

        Returns:
            API密钥对象，如果无效则返回None
        """
        key_hash = self._hash_key(raw_key)
        key_id = self._hash_index.get(key_hash)

        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # 检查密钥状态
        if not api_key.is_active:
            logger.warning(f"API key is inactive: {key_id}")
            return None

        if api_key.is_expired():
            logger.warning(f"API key is expired: {key_id}")
            return None

        # 更新最后使用时间
        api_key.last_used = datetime.now()

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """撤销API密钥"""
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        api_key.is_active = False
        logger.info(f"Revoked API key: {key_id}")
        return True

    def delete_key(self, key_id: str) -> bool:
        """删除API密钥"""
        api_key = self._keys.pop(key_id, None)
        if not api_key:
            return False

        # 删除索引
        if api_key.key_hash in self._hash_index:
            del self._hash_index[api_key.key_hash]

        logger.info(f"Deleted API key: {key_id}")
        return True

    def update_key(
        self,
        key_id: str,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit: Optional[int] = None
    ) -> bool:
        """更新API密钥"""
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        if name is not None:
            api_key.name = name
        if permissions is not None:
            api_key.permissions = permissions
        if rate_limit is not None:
            api_key.rate_limit = rate_limit

        logger.info(f"Updated API key: {key_id}")
        return True

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """获取API密钥"""
        return self._keys.get(key_id)

    def list_keys(self, user_id: Optional[str] = None) -> List[APIKey]:
        """列出API密钥"""
        keys = list(self._keys.values())

        if user_id:
            keys = [k for k in keys if k.user_id == user_id]

        return keys

    def get_user_permissions(self, raw_key: str) -> List[str]:
        """获取用户权限"""
        api_key = self.validate_key(raw_key)
        if not api_key:
            return []
        return api_key.permissions

    def check_permission(self, raw_key: str, permission: str) -> bool:
        """检查是否有指定权限"""
        api_key = self.validate_key(raw_key)
        if not api_key:
            return False
        return api_key.has_permission(permission)

    @staticmethod
    def _hash_key(key: str) -> str:
        """计算密钥哈希"""
        return hashlib.sha256(key.encode()).hexdigest()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self._keys)
        active = sum(1 for k in self._keys.values() if k.is_active)
        expired = sum(1 for k in self._keys.values() if k.is_expired())

        return {
            "total_keys": total,
            "active_keys": active,
            "inactive_keys": total - active,
            "expired_keys": expired
        }


# 全局API密钥管理器实例
_api_key_manager: Optional[APIKeyManager] = None


def init_api_key_manager() -> APIKeyManager:
    """初始化API密钥管理器"""
    global _api_key_manager
    _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_api_key_manager() -> Optional[APIKeyManager]:
    """获取API密钥管理器实例"""
    return _api_key_manager


# 预定义的权限组
class PermissionGroups:
    """预定义权限组"""

    READONLY = [Permission.READ.value, Permission.TASK_READ.value]
    STANDARD = [Permission.READ.value, Permission.WRITE.value,
                Permission.TASK_CREATE.value, Permission.TASK_READ.value]
    FULL = [Permission.ADMIN.value]
    TEMPLATE_USER = [Permission.READ.value, Permission.WRITE.value,
                     Permission.TASK_CREATE.value, Permission.TEMPLATE_MANAGE.value]


# 便捷函数
def create_user_key(
    user_id: str,
    name: str,
    group: str = "standard"
) -> Optional[str]:
    """
    为用户创建API密钥

    Args:
        user_id: 用户ID
        name: 密钥名称
        group: 权限组 (readonly, standard, full, template_user)

    Returns:
        API密钥
    """
    manager = get_api_key_manager()
    if not manager:
        return None

    permissions = getattr(PermissionGroups, group.upper(), PermissionGroups.STANDARD)

    return manager.create_key(
        name=name,
        user_id=user_id,
        permissions=permissions
    )


def validate_request(raw_key: str, required_permission: str) -> Optional[APIKey]:
    """
    验证请求

    Args:
        raw_key: API密钥
        required_permission: 需要的权限

    Returns:
        API密钥对象，如果验证失败则返回None
    """
    manager = get_api_key_manager()
    if not manager:
        return None

    api_key = manager.validate_key(raw_key)
    if not api_key:
        return None

    if required_permission and not api_key.has_permission(required_permission):
        return None

    return api_key


# FastAPI依赖
async def require_permission(permission: str):
    """
    FastAPI权限检查依赖

    Usage:
        @router.get("/api/endpoint")
        async def endpoint(
            api_key: APIKey = Depends(require_permission(Permission.TASK_CREATE.value))
        ):
            pass
    """
    from fastapi import Header, HTTPException

    async def _check(x_api_key: str = Header(...)) -> APIKey:
        api_key = validate_request(x_api_key, permission)
        if not api_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key or insufficient permissions"
            )
        return api_key

    return _check


async def optional_api_key(x_api_key: str = Header(None)) -> Optional[APIKey]:
    """
    可选的API密钥依赖

    如果提供了密钥则验证，但不强制要求
    """
    if not x_api_key:
        return None

    manager = get_api_key_manager()
    if manager:
        return manager.validate_key(x_api_key)
    return None
