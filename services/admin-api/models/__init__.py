"""
Admin API Models
导出所有模型
"""

from .base import Base, SessionLocal, init_db, engine
from .user import User, user_roles, user_groups
from .role import Role, Permission, role_permissions
from .group import UserGroup
from .audit import AuditLog
from .settings import SystemSettings, NotificationChannel, NotificationRule
from .notification import NotificationTemplate, NotificationLog
from .portal import UserNotification, UserTodo, UserActivityLog, Announcement

__all__ = [
    # Base
    'Base',
    'SessionLocal',
    'init_db',
    'engine',

    # User
    'User',
    'user_roles',
    'user_groups',

    # Role
    'Role',
    'Permission',
    'role_permissions',

    # Group
    'UserGroup',

    # Audit
    'AuditLog',

    # Settings
    'SystemSettings',
    'NotificationChannel',
    'NotificationRule',

    # Notification
    'NotificationTemplate',
    'NotificationLog',

    # Portal
    'UserNotification',
    'UserTodo',
    'UserActivityLog',
    'Announcement',
]
