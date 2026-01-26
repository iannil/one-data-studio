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
from .user_profile import (
    UserProfile,
    UserSegment,
    UserTag,
    BehaviorAnomaly,
    generate_profile_id,
    generate_segment_id,
)
from .content import (
    ContentCategory,
    ContentTag,
    Article,
    ArticleVersion,
    ContentApproval,
    generate_content_id,
    generate_category_id,
    generate_tag_id,
)
from .api_call_log import (
    ApiEndpoint,
    ApiCallLog,
    generate_api_endpoint_id,
    generate_api_call_id,
)

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

    # User Profile
    'UserProfile',
    'UserSegment',
    'UserTag',
    'BehaviorAnomaly',
    'generate_profile_id',
    'generate_segment_id',

    # Content Management
    'ContentCategory',
    'ContentTag',
    'Article',
    'ArticleVersion',
    'ContentApproval',
    'generate_content_id',
    'generate_category_id',
    'generate_tag_id',

    # API Management
    'ApiEndpoint',
    'ApiCallLog',
    'generate_api_endpoint_id',
    'generate_api_call_id',
]
