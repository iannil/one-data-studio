"""
Admin API - 管理平台服务
提供用户管理、角色管理、用户组管理、审计日志、系统设置等功能

功能：
- 用户 CRUD 管理
- 角色和权限管理
- 用户组管理
- 审计日志查询
- 系统设置管理
- 通知渠道管理
- 成本统计
- 平台统计概览
"""

import os
import sys
import logging
import uuid
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from sqlalchemy import func

# 添加项目路径
sys.path.insert(0, '/app')
sys.path.insert(1, '/app/shared')

from models import (
    SessionLocal, init_db,
    User, Role, Permission, UserGroup,
    AuditLog, SystemSettings, NotificationChannel, NotificationRule,
    NotificationTemplate, NotificationLog,
    UserNotification, UserTodo, UserActivityLog, Announcement,
    user_roles, role_permissions
)

# 尝试导入认证模块
try:
    from auth import (
        require_jwt,
        require_permission,
        Resource,
        Operation,
        get_current_user
    )
    AUTH_ENABLED = True
except ImportError:
    if os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod'):
        raise ImportError(
            "Authentication module is required in production. "
            "Ensure auth.py is present and all dependencies are installed."
        )

    AUTH_ENABLED = False
    logging.getLogger(__name__).warning(
        "Authentication module not available. Running in development mode without auth."
    )
    def require_jwt(optional=False):
        def decorator(fn):
            return fn
        return decorator
    def require_permission(resource, operation):
        def decorator(fn):
            return fn
        return decorator
    class Resource:
        USER = type('', (), {'value': 'user'})()
        SYSTEM = type('', (), {'value': 'system'})()
    class Operation:
        CREATE = type('', (), {'value': 'create'})()
        READ = type('', (), {'value': 'read'})()
        UPDATE = type('', (), {'value': 'update'})()
        DELETE = type('', (), {'value': 'delete'})()
        MANAGE = type('', (), {'value': 'manage'})()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 配置 CORS
_cors_origins = os.getenv("CORS_ORIGINS", "")
if not _cors_origins:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("CORS_ORIGINS must be explicitly configured in production.")
    logger.warning("CORS_ORIGINS not configured, defaulting to localhost only.")
    _cors_origins = "http://localhost:3000,http://127.0.0.1:3000"

CORS(app, resources={
    r"/*": {
        "origins": _cors_origins.split(","),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


# ==================== 工具函数 ====================

def get_db_session():
    """获取数据库会话"""
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def close_db_session(exception=None):
    """关闭数据库会话"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:16]}"


def hash_password(password: str) -> str:
    """哈希密码"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def log_audit(action: str, resource_type: str, resource_id: str = None,
              resource_name: str = None, success: bool = True, error_message: str = None,
              changes: dict = None):
    """记录审计日志"""
    db = get_db_session()
    try:
        audit = AuditLog(
            audit_id=generate_id("audit_"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            user_id=getattr(g, 'user_id', 'system'),
            username=getattr(g, 'username', 'system'),
            user_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:512],
            success=success,
            error_message=error_message,
            request_id=request.headers.get('X-Request-ID')
        )
        if changes:
            audit.set_changes(changes.get('before'), changes.get('after'))
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
        db.rollback()


# ==================== 健康检查 ====================

@app.route("/health")
@app.route("/api/v1/health")
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "service": "admin-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


# ==================== 用户管理 API ====================

@app.route("/api/v1/users", methods=["GET"])
@require_jwt(optional=True)
def list_users():
    """列出所有用户"""
    db = get_db_session()

    # 查询参数
    status = request.args.get("status")
    department = request.args.get("department")
    search = request.args.get("search")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(User).filter(User.status != 'deleted')

    if status:
        query = query.filter(User.status == status)
    if department:
        query = query.filter(User.department == department)
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.display_name.ilike(f"%{search}%"))
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "users": [u.to_dict(include_roles=True) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/users", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.CREATE)
def create_user():
    """创建用户"""
    db = get_db_session()
    data = request.json

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email:
        return jsonify({"code": 40001, "message": "用户名和邮箱不能为空"}), 400

    # 检查用户名是否存在
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        return jsonify({"code": 40003, "message": "用户名或邮箱已存在"}), 409

    user = User(
        user_id=generate_id("user_"),
        username=username,
        email=email,
        password_hash=hash_password(password) if password else None,
        display_name=data.get("display_name", username),
        phone=data.get("phone"),
        department=data.get("department"),
        position=data.get("position"),
        status="active",
        created_by=getattr(g, 'username', 'system')
    )

    # 分配角色
    role_ids = data.get("role_ids", [])
    if role_ids:
        roles = db.query(Role).filter(Role.role_id.in_(role_ids)).all()
        user.roles = roles

    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit("create", "user", user.user_id, user.username, changes={"after": user.to_dict()})
    logger.info(f"创建用户: {user.user_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": user.to_dict(include_roles=True)
    }), 201


@app.route("/api/v1/users/<user_id>", methods=["GET"])
@require_jwt(optional=True)
def get_user(user_id: str):
    """获取用户详情"""
    db = get_db_session()

    user = db.query(User).filter(User.user_id == user_id, User.status != 'deleted').first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": user.to_dict(include_roles=True, include_groups=True)
    })


@app.route("/api/v1/users/<user_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def update_user(user_id: str):
    """更新用户"""
    db = get_db_session()
    data = request.json

    user = db.query(User).filter(User.user_id == user_id, User.status != 'deleted').first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    old_data = user.to_dict()

    if data.get("display_name"):
        user.display_name = data["display_name"]
    if data.get("phone") is not None:
        user.phone = data["phone"]
    if data.get("department") is not None:
        user.department = data["department"]
    if data.get("position") is not None:
        user.position = data["position"]
    if data.get("avatar_url") is not None:
        user.avatar_url = data["avatar_url"]
    if data.get("status"):
        user.status = data["status"]

    # 更新角色
    if "role_ids" in data:
        roles = db.query(Role).filter(Role.role_id.in_(data["role_ids"])).all()
        user.roles = roles

    db.commit()
    db.refresh(user)

    log_audit("update", "user", user.user_id, user.username, changes={"before": old_data, "after": user.to_dict()})
    logger.info(f"更新用户: {user_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": user.to_dict(include_roles=True)
    })


@app.route("/api/v1/users/<user_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.USER, Operation.DELETE)
def delete_user(user_id: str):
    """删除用户（软删除）"""
    db = get_db_session()

    user = db.query(User).filter(User.user_id == user_id, User.status != 'deleted').first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    user.status = "deleted"
    db.commit()

    log_audit("delete", "user", user.user_id, user.username)
    logger.info(f"删除用户: {user_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/users/<user_id>/reset-password", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def reset_user_password(user_id: str):
    """重置用户密码"""
    db = get_db_session()
    data = request.json

    user = db.query(User).filter(User.user_id == user_id, User.status != 'deleted').first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    new_password = data.get("new_password")
    if not new_password:
        # 生成随机密码
        import secrets
        new_password = secrets.token_urlsafe(12)

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now()
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    log_audit("update", "user", user.user_id, f"{user.username} password reset")
    logger.info(f"重置用户密码: {user_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "new_password": new_password if not data.get("new_password") else None
        }
    })


@app.route("/api/v1/users/<user_id>/toggle-status", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def toggle_user_status(user_id: str):
    """启用/禁用用户"""
    db = get_db_session()

    user = db.query(User).filter(User.user_id == user_id, User.status != 'deleted').first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    old_status = user.status
    user.status = "inactive" if user.status == "active" else "active"
    db.commit()

    log_audit("update", "user", user.user_id, f"{user.username} status: {old_status} -> {user.status}")
    logger.info(f"切换用户状态: {user_id} -> {user.status}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"status": user.status}
    })


# ==================== 角色管理 API ====================

@app.route("/api/v1/roles", methods=["GET"])
@require_jwt(optional=True)
def list_roles():
    """列出所有角色"""
    db = get_db_session()

    include_system = request.args.get("include_system", "true").lower() == "true"
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))

    query = db.query(Role)
    if not include_system:
        query = query.filter(Role.is_system == False)

    total = query.count()
    roles = query.order_by(Role.priority.desc(), Role.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "roles": [r.to_dict(include_permissions=True) for r in roles],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/roles", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.MANAGE)
def create_role():
    """创建角色"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "角色名称不能为空"}), 400

    existing = db.query(Role).filter(Role.name == name).first()
    if existing:
        return jsonify({"code": 40003, "message": "角色名称已存在"}), 409

    role = Role(
        role_id=generate_id("role_"),
        name=name,
        display_name=data.get("display_name", name),
        description=data.get("description"),
        role_type="custom",
        is_system=False,
        priority=data.get("priority", 0),
        parent_role_id=data.get("parent_role_id"),
        created_by=getattr(g, 'username', 'system')
    )

    # 分配权限
    permission_ids = data.get("permission_ids", [])
    if permission_ids:
        permissions = db.query(Permission).filter(Permission.permission_id.in_(permission_ids)).all()
        role.permissions = permissions

    db.add(role)
    db.commit()
    db.refresh(role)

    log_audit("create", "role", role.role_id, role.name, changes={"after": role.to_dict()})
    logger.info(f"创建角色: {role.role_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": role.to_dict(include_permissions=True)
    }), 201


@app.route("/api/v1/roles/<role_id>", methods=["GET"])
@require_jwt(optional=True)
def get_role(role_id: str):
    """获取角色详情"""
    db = get_db_session()

    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        return jsonify({"code": 40401, "message": "角色不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": role.to_dict(include_permissions=True, include_users=True)
    })


@app.route("/api/v1/roles/<role_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.USER, Operation.MANAGE)
def update_role(role_id: str):
    """更新角色"""
    db = get_db_session()
    data = request.json

    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        return jsonify({"code": 40401, "message": "角色不存在"}), 404

    if role.is_system:
        return jsonify({"code": 40002, "message": "系统角色不可修改"}), 400

    old_data = role.to_dict()

    if data.get("display_name"):
        role.display_name = data["display_name"]
    if data.get("description") is not None:
        role.description = data["description"]
    if data.get("priority") is not None:
        role.priority = data["priority"]
    if data.get("is_active") is not None:
        role.is_active = data["is_active"]

    # 更新权限
    if "permission_ids" in data:
        permissions = db.query(Permission).filter(Permission.permission_id.in_(data["permission_ids"])).all()
        role.permissions = permissions

    db.commit()
    db.refresh(role)

    log_audit("update", "role", role.role_id, role.name, changes={"before": old_data, "after": role.to_dict()})
    logger.info(f"更新角色: {role_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": role.to_dict(include_permissions=True)
    })


@app.route("/api/v1/roles/<role_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.USER, Operation.MANAGE)
def delete_role(role_id: str):
    """删除角色"""
    db = get_db_session()

    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        return jsonify({"code": 40401, "message": "角色不存在"}), 404

    if role.is_system:
        return jsonify({"code": 40002, "message": "系统角色不可删除"}), 400

    if role.users:
        return jsonify({"code": 40002, "message": "角色已分配给用户，无法删除"}), 400

    db.delete(role)
    db.commit()

    log_audit("delete", "role", role.role_id, role.name)
    logger.info(f"删除角色: {role_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/permissions", methods=["GET"])
@require_jwt(optional=True)
def list_permissions():
    """列出所有权限"""
    db = get_db_session()

    category = request.args.get("category")

    query = db.query(Permission)
    if category:
        query = query.filter(Permission.category == category)

    permissions = query.order_by(Permission.category, Permission.resource, Permission.operation).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "permissions": [p.to_dict() for p in permissions]
        }
    })


# ==================== 用户组管理 API ====================

@app.route("/api/v1/groups", methods=["GET"])
@require_jwt(optional=True)
def list_groups():
    """列出所有用户组"""
    db = get_db_session()

    group_type = request.args.get("type")
    search = request.args.get("search")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(UserGroup).filter(UserGroup.is_active == True)

    if group_type:
        query = query.filter(UserGroup.group_type == group_type)
    if search:
        query = query.filter(
            (UserGroup.name.ilike(f"%{search}%")) |
            (UserGroup.display_name.ilike(f"%{search}%"))
        )

    total = query.count()
    groups = query.order_by(UserGroup.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "groups": [g.to_dict() for g in groups],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/groups", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.CREATE)
def create_group():
    """创建用户组"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "用户组名称不能为空"}), 400

    existing = db.query(UserGroup).filter(UserGroup.name == name).first()
    if existing:
        return jsonify({"code": 40003, "message": "用户组名称已存在"}), 409

    group = UserGroup(
        group_id=generate_id("group_"),
        name=name,
        display_name=data.get("display_name", name),
        description=data.get("description"),
        group_type=data.get("group_type", "custom"),
        parent_group_id=data.get("parent_group_id"),
        created_by=getattr(g, 'username', 'system')
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    log_audit("create", "group", group.group_id, group.name, changes={"after": group.to_dict()})
    logger.info(f"创建用户组: {group.group_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": group.to_dict()
    }), 201


@app.route("/api/v1/groups/<group_id>", methods=["GET"])
@require_jwt(optional=True)
def get_group(group_id: str):
    """获取用户组详情"""
    db = get_db_session()

    group = db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
    if not group:
        return jsonify({"code": 40401, "message": "用户组不存在"}), 404

    include_members = request.args.get("include_members", "false").lower() == "true"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": group.to_dict(include_members=include_members)
    })


@app.route("/api/v1/groups/<group_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def update_group(group_id: str):
    """更新用户组"""
    db = get_db_session()
    data = request.json

    group = db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
    if not group:
        return jsonify({"code": 40401, "message": "用户组不存在"}), 404

    old_data = group.to_dict()

    if data.get("display_name"):
        group.display_name = data["display_name"]
    if data.get("description") is not None:
        group.description = data["description"]
    if data.get("group_type"):
        group.group_type = data["group_type"]
    if data.get("parent_group_id") is not None:
        group.parent_group_id = data["parent_group_id"]

    db.commit()
    db.refresh(group)

    log_audit("update", "group", group.group_id, group.name, changes={"before": old_data, "after": group.to_dict()})
    logger.info(f"更新用户组: {group_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": group.to_dict()
    })


@app.route("/api/v1/groups/<group_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.USER, Operation.DELETE)
def delete_group(group_id: str):
    """删除用户组"""
    db = get_db_session()

    group = db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
    if not group:
        return jsonify({"code": 40401, "message": "用户组不存在"}), 404

    if group.members:
        return jsonify({"code": 40002, "message": "用户组还有成员，无法删除"}), 400

    db.delete(group)
    db.commit()

    log_audit("delete", "group", group.group_id, group.name)
    logger.info(f"删除用户组: {group_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/groups/<group_id>/members", methods=["POST"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def add_group_members(group_id: str):
    """添加用户组成员"""
    db = get_db_session()
    data = request.json

    group = db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
    if not group:
        return jsonify({"code": 40401, "message": "用户组不存在"}), 404

    user_ids = data.get("user_ids", [])
    if not user_ids:
        return jsonify({"code": 40001, "message": "用户ID列表不能为空"}), 400

    users = db.query(User).filter(User.user_id.in_(user_ids), User.status != 'deleted').all()
    for user in users:
        if user not in group.members:
            group.members.append(user)

    db.commit()

    log_audit("update", "group", group.group_id, f"{group.name} members added: {len(users)}")
    logger.info(f"添加用户组成员: {group_id}, 添加 {len(users)} 人")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"added_count": len(users)}
    })


@app.route("/api/v1/groups/<group_id>/members/<user_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.USER, Operation.UPDATE)
def remove_group_member(group_id: str, user_id: str):
    """移除用户组成员"""
    db = get_db_session()

    group = db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
    if not group:
        return jsonify({"code": 40401, "message": "用户组不存在"}), 404

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return jsonify({"code": 40401, "message": "用户不存在"}), 404

    if user in group.members:
        group.members.remove(user)
        db.commit()

    log_audit("update", "group", group.group_id, f"{group.name} member removed: {user.username}")
    logger.info(f"移除用户组成员: {group_id}, 用户 {user_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 审计日志 API ====================

@app.route("/api/v1/audit/logs", methods=["GET"])
@app.route("/api/v1/admin/audit-logs", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def list_audit_logs():
    """列出审计日志"""
    db = get_db_session()

    # 查询参数
    user_id = request.args.get("user_id")
    action = request.args.get("action")
    resource_type = request.args.get("resource_type")
    resource_id = request.args.get("resource_id")
    success = request.args.get("success")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if success is not None:
        query = query.filter(AuditLog.success == (success.lower() == 'true'))
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/audit/logs/<audit_id>", methods=["GET"])
@app.route("/api/v1/admin/audit-logs/<audit_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_audit_log(audit_id: str):
    """获取审计日志详情"""
    db = get_db_session()

    log = db.query(AuditLog).filter(AuditLog.audit_id == audit_id).first()
    if not log:
        return jsonify({"code": 40401, "message": "日志不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": log.to_dict()
    })


@app.route("/api/v1/audit/export", methods=["POST"])
@app.route("/api/v1/admin/audit-logs/export", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def export_audit_logs():
    """导出审计日志"""
    data = request.json
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    format_type = data.get("format", "csv")

    # 这里简化实现，实际应该生成文件并返回下载链接
    export_id = generate_id("export_")

    log_audit("export", "system", export_id, f"audit_logs_{format_type}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "export_id": export_id,
            "download_url": f"/api/v1/audit/exports/{export_id}/download"
        }
    })


@app.route("/api/v1/admin/audit-logs/statistics", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_audit_statistics():
    """获取审计日志统计"""
    db = get_db_session()

    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    query = db.query(AuditLog)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)

    total_actions = query.count()
    success_count = query.filter(AuditLog.success == True).count()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "total_actions": total_actions,
            "success_rate": round(success_count / total_actions * 100, 2) if total_actions > 0 else 0,
            "action_distribution": {},
            "resource_distribution": {},
            "top_users": [],
            "daily_stats": []
        }
    })


@app.route("/api/v1/admin/audit-logs/active-users", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_active_users():
    """获取活跃用户列表"""
    db = get_db_session()

    # 获取最近有操作的用户（按最近活动时间排序）
    from datetime import timedelta

    days = int(request.args.get("days", 7))
    since = datetime.now() - timedelta(days=days)

    # 从审计日志中获取活跃用户
    active_users = db.query(
        AuditLog.user_id,
        AuditLog.username,
        func.count(AuditLog.audit_id).label('action_count')
    ).filter(
        AuditLog.created_at >= since
    ).group_by(
        AuditLog.user_id,
        AuditLog.username
    ).order_by(
        func.count(AuditLog.audit_id).desc()
    ).limit(20).all()

    # 获取用户详细信息
    result = []
    for user_id, username, action_count in active_users:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            result.append({
                "user_id": user_id,
                "username": username or user.username,
                "display_name": user.display_name,
                "email": user.email,
                "department": user.department,
                "action_count": action_count,
                "last_activity": db.query(func.max(AuditLog.created_at)).filter(
                    AuditLog.user_id == user_id
                ).scalar()
            })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "active_users": result,
            "total_active_count": len(result),
            "period_days": days
        }
    })


# ==================== 系统设置 API ====================

@app.route("/api/v1/settings", methods=["GET"])
@app.route("/api/v1/admin/settings", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_system_settings():
    """获取系统设置"""
    db = get_db_session()

    settings = db.query(SystemSettings).all()

    # 构建设置对象
    result = {}
    for s in settings:
        result[s.setting_key] = s.get_value()

    # 添加默认值
    defaults = {
        "site_name": "ONE-DATA-STUDIO",
        "site_description": "企业级 DataOps + MLOps + LLMOps 融合平台",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "email_enabled": False,
        "storage_type": "local",
        "password_min_length": 8,
        "password_require_uppercase": True,
        "password_require_lowercase": True,
        "password_require_number": True,
        "password_require_special": False,
        "session_timeout_minutes": 60,
        "max_login_attempts": 5,
        "lockout_duration_minutes": 30,
        "features_enabled": {
            "alldata": True,
            "cube": True,
            "bisheng": True,
            "workflows": True
        }
    }

    for key, default in defaults.items():
        if key not in result:
            result[key] = default

    return jsonify({
        "code": 0,
        "message": "success",
        "data": result
    })


@app.route("/api/v1/settings", methods=["PUT"])
@app.route("/api/v1/admin/settings", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def update_system_settings():
    """更新系统设置"""
    db = get_db_session()
    data = request.json

    updated_keys = []
    for key, value in data.items():
        setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
        if setting:
            setting.set_value(value)
            setting.updated_by = getattr(g, 'username', 'system')
        else:
            setting = SystemSettings(
                setting_key=key,
                updated_by=getattr(g, 'username', 'system')
            )
            setting.set_value(value)
            db.add(setting)
        updated_keys.append(key)

    db.commit()

    log_audit("update", "settings", None, f"Updated: {', '.join(updated_keys)}")
    logger.info(f"更新系统设置: {updated_keys}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/settings/test-email", methods=["POST"])
@app.route("/api/v1/admin/settings/test-email", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def test_email():
    """测试邮件发送"""
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"code": 40001, "message": "邮箱地址不能为空"}), 400

    # 简化实现
    logger.info(f"测试邮件发送到: {email}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"sent": True}
    })


# ==================== 通知渠道 API ====================

@app.route("/api/v1/notification-channels", methods=["GET"])
@app.route("/api/v1/admin/settings/notification-channels", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def list_notification_channels():
    """列出通知渠道"""
    db = get_db_session()

    channels = db.query(NotificationChannel).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "channels": [c.to_dict() for c in channels]
        }
    })


@app.route("/api/v1/notification-channels", methods=["POST"])
@app.route("/api/v1/admin/settings/notification-channels", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_notification_channel():
    """创建通知渠道"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    channel_type = data.get("type")

    if not name or not channel_type:
        return jsonify({"code": 40001, "message": "渠道名称和类型不能为空"}), 400

    channel = NotificationChannel(
        channel_id=generate_id("channel_"),
        name=name,
        channel_type=channel_type,
        enabled=data.get("enabled", True),
        created_by=getattr(g, 'username', 'system')
    )

    if data.get("config"):
        channel.set_config(data["config"])

    db.add(channel)
    db.commit()
    db.refresh(channel)

    log_audit("create", "system", channel.channel_id, f"notification_channel: {name}")
    logger.info(f"创建通知渠道: {channel.channel_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"channel_id": channel.channel_id}
    }), 201


@app.route("/api/v1/notification-channels/<channel_id>", methods=["GET"])
@app.route("/api/v1/admin/settings/notification-channels/<channel_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_notification_channel(channel_id: str):
    """获取通知渠道详情"""
    db = get_db_session()

    channel = db.query(NotificationChannel).filter(NotificationChannel.channel_id == channel_id).first()
    if not channel:
        return jsonify({"code": 40401, "message": "通知渠道不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": channel.to_dict(hide_secrets=False)
    })


@app.route("/api/v1/notification-channels/<channel_id>", methods=["PUT"])
@app.route("/api/v1/admin/settings/notification-channels/<channel_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def update_notification_channel(channel_id: str):
    """更新通知渠道"""
    db = get_db_session()
    data = request.json

    channel = db.query(NotificationChannel).filter(NotificationChannel.channel_id == channel_id).first()
    if not channel:
        return jsonify({"code": 40401, "message": "通知渠道不存在"}), 404

    old_data = channel.to_dict()

    if data.get("name"):
        channel.name = data["name"]
    if data.get("type") is not None:
        channel.channel_type = data["type"]
    if data.get("enabled") is not None:
        channel.enabled = data["enabled"]
    if data.get("config") is not None:
        channel.set_config(data["config"])

    db.commit()
    db.refresh(channel)

    log_audit("update", "system", channel.channel_id, f"notification_channel: {channel.name}", changes={"before": old_data, "after": channel.to_dict()})
    logger.info(f"更新通知渠道: {channel_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": channel.to_dict(hide_secrets=False)
    })


@app.route("/api/v1/notification-channels/<channel_id>", methods=["DELETE"])
@app.route("/api/v1/admin/settings/notification-channels/<channel_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.DELETE)
def delete_notification_channel(channel_id: str):
    """删除通知渠道"""
    db = get_db_session()

    channel = db.query(NotificationChannel).filter(NotificationChannel.channel_id == channel_id).first()
    if not channel:
        return jsonify({"code": 40401, "message": "通知渠道不存在"}), 404

    channel_name = channel.name
    db.delete(channel)
    db.commit()

    log_audit("delete", "system", channel_id, f"notification_channel: {channel_name}")
    logger.info(f"删除通知渠道: {channel_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/notification-channels/<channel_id>/test", methods=["POST"])
@app.route("/api/v1/admin/settings/notification-channels/<channel_id>/test", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def test_notification_channel(channel_id: str):
    """测试通知渠道"""
    db = get_db_session()

    channel = db.query(NotificationChannel).filter(NotificationChannel.channel_id == channel_id).first()
    if not channel:
        return jsonify({"code": 40401, "message": "通知渠道不存在"}), 404

    # 简化实现 - 实际应该根据渠道类型发送测试通知
    logger.info(f"测试通知渠道: {channel_id} ({channel.channel_type})")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "sent": True,
            "message": "测试通知已发送"
        }
    })


# ==================== 通知规则 API ====================

@app.route("/api/v1/notification-rules", methods=["GET"])
@app.route("/api/v1/admin/settings/notification-rules", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def list_notification_rules():
    """列出通知规则"""
    db = get_db_session()

    enabled = request.args.get("enabled")
    event_type = request.args.get("event_type")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(NotificationRule)

    if enabled is not None:
        query = query.filter(NotificationRule.enabled == (enabled.lower() == 'true'))
    if event_type:
        query = query.filter(NotificationRule.events.like(f'%"{event_type}"%'))

    total = query.count()
    rules = query.order_by(NotificationRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "rules": [r.to_dict() for r in rules],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/notification-rules", methods=["POST"])
@app.route("/api/v1/admin/settings/notification-rules", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_notification_rule():
    """创建通知规则"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "规则名称不能为空"}), 400

    rule = NotificationRule(
        rule_id=generate_id("rule_"),
        name=name,
        enabled=data.get("enabled", True),
        created_by=getattr(g, 'username', 'system')
    )

    if data.get("events"):
        rule.set_events(data["events"])
    if data.get("channel_ids"):
        rule.set_channel_ids(data["channel_ids"])
    if data.get("conditions"):
        rule.conditions = data["conditions"]

    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_audit("create", "system", rule.rule_id, f"notification_rule: {name}")
    logger.info(f"创建通知规则: {rule.rule_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": rule.to_dict()
    }), 201


@app.route("/api/v1/notification-rules/<rule_id>", methods=["GET"])
@app.route("/api/v1/admin/settings/notification-rules/<rule_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_notification_rule(rule_id: str):
    """获取通知规则详情"""
    db = get_db_session()

    rule = db.query(NotificationRule).filter(NotificationRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "规则不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": rule.to_dict()
    })


@app.route("/api/v1/notification-rules/<rule_id>", methods=["PUT"])
@app.route("/api/v1/admin/settings/notification-rules/<rule_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def update_notification_rule(rule_id: str):
    """更新通知规则"""
    db = get_db_session()
    data = request.json

    rule = db.query(NotificationRule).filter(NotificationRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "规则不存在"}), 404

    old_data = rule.to_dict()

    if data.get("name"):
        rule.name = data["name"]
    if data.get("enabled") is not None:
        rule.enabled = data["enabled"]
    if data.get("events") is not None:
        rule.set_events(data["events"])
    if data.get("channel_ids") is not None:
        rule.set_channel_ids(data["channel_ids"])
    if data.get("conditions") is not None:
        rule.conditions = data["conditions"]

    db.commit()
    db.refresh(rule)

    log_audit("update", "system", rule.rule_id, rule.name, changes={"before": old_data, "after": rule.to_dict()})
    logger.info(f"更新通知规则: {rule_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": rule.to_dict()
    })


@app.route("/api/v1/notification-rules/<rule_id>", methods=["DELETE"])
@app.route("/api/v1/admin/settings/notification-rules/<rule_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.DELETE)
def delete_notification_rule(rule_id: str):
    """删除通知规则"""
    db = get_db_session()

    rule = db.query(NotificationRule).filter(NotificationRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "规则不存在"}), 404

    rule_name = rule.name
    db.delete(rule)
    db.commit()

    log_audit("delete", "system", rule_id, f"notification_rule: {rule_name}")
    logger.info(f"删除通知规则: {rule_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 通知模板 API ====================

@app.route("/api/v1/notification-templates", methods=["GET"])
@app.route("/api/v1/admin/notification-templates", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def list_notification_templates():
    """列出通知模板"""
    db = get_db_session()

    event_type = request.args.get("event_type")
    channel = request.args.get("channel")
    enabled = request.args.get("enabled")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(NotificationTemplate)

    if event_type:
        query = query.filter(NotificationTemplate.event_type == event_type)
    if channel:
        query = query.filter(NotificationTemplate.channel == channel)
    if enabled is not None:
        query = query.filter(NotificationTemplate.is_enabled == (enabled.lower() == 'true'))

    total = query.count()
    templates = query.order_by(NotificationTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": [t.to_dict() for t in templates],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/notification-templates", methods=["POST"])
@app.route("/api/v1/admin/notification-templates", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_notification_template():
    """创建通知模板"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    event_type = data.get("event_type")
    channel = data.get("channel")

    if not name or not event_type or not channel:
        return jsonify({"code": 40001, "message": "模板名称、事件类型和渠道不能为空"}), 400

    template = NotificationTemplate(
        template_id=NotificationTemplate.generate_id(),
        name=name,
        description=data.get("description"),
        event_type=event_type,
        channel=channel,
        subject_template=data.get("subject_template"),
        body_template=data.get("body_template"),
        is_enabled=data.get("is_enabled", True),
        is_default=data.get("is_default", False),
        created_by=getattr(g, 'username', 'system')
    )

    if data.get("variables"):
        template.set_variables(data["variables"])

    db.add(template)
    db.commit()
    db.refresh(template)

    log_audit("create", "system", template.template_id, f"notification_template: {name}")
    logger.info(f"创建通知模板: {template.template_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    }), 201


@app.route("/api/v1/notification-templates/<template_id>", methods=["GET"])
@app.route("/api/v1/admin/notification-templates/<template_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_notification_template(template_id: str):
    """获取通知模板详情"""
    db = get_db_session()

    template = db.query(NotificationTemplate).filter(NotificationTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    })


@app.route("/api/v1/notification-templates/<template_id>", methods=["PUT"])
@app.route("/api/v1/admin/notification-templates/<template_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def update_notification_template(template_id: str):
    """更新通知模板"""
    db = get_db_session()
    data = request.json

    template = db.query(NotificationTemplate).filter(NotificationTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    old_data = template.to_dict()

    if data.get("name"):
        template.name = data["name"]
    if data.get("description") is not None:
        template.description = data["description"]
    if data.get("event_type"):
        template.event_type = data["event_type"]
    if data.get("channel"):
        template.channel = data["channel"]
    if data.get("subject_template") is not None:
        template.subject_template = data["subject_template"]
    if data.get("body_template") is not None:
        template.body_template = data["body_template"]
    if data.get("variables") is not None:
        template.set_variables(data["variables"])
    if data.get("is_enabled") is not None:
        template.is_enabled = data["is_enabled"]
    if data.get("is_default") is not None:
        template.is_default = data["is_default"]

    template.updated_by = getattr(g, 'username', 'system')

    db.commit()
    db.refresh(template)

    log_audit("update", "system", template.template_id, template.name, changes={"before": old_data, "after": template.to_dict()})
    logger.info(f"更新通知模板: {template_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    })


@app.route("/api/v1/notification-templates/<template_id>", methods=["DELETE"])
@app.route("/api/v1/admin/notification-templates/<template_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.DELETE)
def delete_notification_template(template_id: str):
    """删除通知模板"""
    db = get_db_session()

    template = db.query(NotificationTemplate).filter(NotificationTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    template_name = template.name
    db.delete(template)
    db.commit()

    log_audit("delete", "system", template_id, f"notification_template: {template_name}")
    logger.info(f"删除通知模板: {template_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 通知发送 API ====================

@app.route("/api/v1/notifications/send", methods=["POST"])
@app.route("/api/v1/admin/notifications/send", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def send_notification():
    """发送通知"""
    import asyncio
    db = get_db_session()
    data = request.json

    channel = data.get("channel")
    recipients = data.get("recipients", [])
    subject = data.get("subject", "")
    content = data.get("content", "")
    template_id = data.get("template_id")
    variables = data.get("variables", {})

    if not channel:
        return jsonify({"code": 40001, "message": "渠道类型不能为空"}), 400
    if not recipients:
        return jsonify({"code": 40001, "message": "接收方不能为空"}), 400

    # 如果使用模板，先渲染模板
    if template_id:
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.template_id == template_id,
            NotificationTemplate.is_enabled == True
        ).first()
        if not template:
            return jsonify({"code": 40401, "message": "模板不存在或未启用"}), 404
        subject, content = template.render(variables)

    if not content:
        return jsonify({"code": 40001, "message": "通知内容不能为空"}), 400

    # 导入通知服务
    try:
        sys.path.insert(0, '/app/shared')
        from notification_service import get_notification_service
        service = get_notification_service()
    except ImportError:
        return jsonify({"code": 50001, "message": "通知服务不可用"}), 500

    # 发送通知并记录日志
    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for recipient in recipients:
            # 创建日志记录
            log_entry = NotificationLog(
                log_id=NotificationLog.generate_id(),
                channel=channel,
                template_id=template_id,
                subject=subject,
                content=content,
                recipient_type=data.get("recipient_type", "user"),
                recipient_id=recipient,
                recipient_address=data.get("addresses", {}).get(recipient, recipient),
                status="sending",
                source_type=data.get("source_type"),
                source_id=data.get("source_id"),
                event_type=data.get("event_type"),
                created_by=getattr(g, 'username', 'system')
            )
            db.add(log_entry)
            db.flush()

            # 异步发送
            extra = data.get("extra", {})
            result = loop.run_until_complete(
                service.send(channel, log_entry.recipient_address, subject, content, extra)
            )

            if result.success:
                log_entry.mark_sent()
                if result.response_data:
                    log_entry.set_response_data(result.response_data)
            else:
                log_entry.mark_failed(result.error or "Unknown error", result.error_code)

            results.append({
                "recipient": recipient,
                "success": result.success,
                "log_id": log_entry.log_id,
                "error": result.error
            })

        db.commit()
    finally:
        loop.close()

    success_count = sum(1 for r in results if r["success"])
    log_audit("create", "notification", None, f"Sent {success_count}/{len(results)} notifications via {channel}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "total": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": results
        }
    })


@app.route("/api/v1/notifications/send-by-event", methods=["POST"])
@app.route("/api/v1/admin/notifications/send-by-event", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def send_notification_by_event():
    """基于事件类型发送通知"""
    import asyncio
    db = get_db_session()
    data = request.json

    event_type = data.get("event_type")
    recipients = data.get("recipients", [])
    variables = data.get("variables", {})
    channels = data.get("channels")  # 可选，不指定则使用模板配置的渠道

    if not event_type:
        return jsonify({"code": 40001, "message": "事件类型不能为空"}), 400
    if not recipients:
        return jsonify({"code": 40001, "message": "接收方不能为空"}), 400

    # 查找该事件类型的所有启用模板
    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.event_type == event_type,
        NotificationTemplate.is_enabled == True
    )
    if channels:
        query = query.filter(NotificationTemplate.channel.in_(channels))

    templates = query.all()
    if not templates:
        return jsonify({"code": 40401, "message": f"未找到事件类型 {event_type} 的通知模板"}), 404

    # 导入通知服务
    try:
        sys.path.insert(0, '/app/shared')
        from notification_service import get_notification_service
        service = get_notification_service()
    except ImportError:
        return jsonify({"code": 50001, "message": "通知服务不可用"}), 500

    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for template in templates:
            subject, content = template.render(variables)

            for recipient in recipients:
                log_entry = NotificationLog(
                    log_id=NotificationLog.generate_id(),
                    channel=template.channel,
                    template_id=template.template_id,
                    subject=subject,
                    content=content,
                    recipient_type=data.get("recipient_type", "user"),
                    recipient_id=recipient,
                    recipient_address=data.get("addresses", {}).get(recipient, recipient),
                    status="sending",
                    source_type=data.get("source_type"),
                    source_id=data.get("source_id"),
                    event_type=event_type,
                    created_by=getattr(g, 'username', 'system')
                )
                db.add(log_entry)
                db.flush()

                extra = data.get("extra", {})
                result = loop.run_until_complete(
                    service.send(template.channel, log_entry.recipient_address, subject, content, extra)
                )

                if result.success:
                    log_entry.mark_sent()
                    if result.response_data:
                        log_entry.set_response_data(result.response_data)
                else:
                    log_entry.mark_failed(result.error or "Unknown error", result.error_code)

                results.append({
                    "recipient": recipient,
                    "channel": template.channel,
                    "template_id": template.template_id,
                    "success": result.success,
                    "log_id": log_entry.log_id,
                    "error": result.error
                })

        db.commit()
    finally:
        loop.close()

    success_count = sum(1 for r in results if r["success"])
    log_audit("create", "notification", None, f"Event {event_type}: sent {success_count}/{len(results)} notifications")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "event_type": event_type,
            "total": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": results
        }
    })


# ==================== 通知日志 API ====================

@app.route("/api/v1/notification-logs", methods=["GET"])
@app.route("/api/v1/admin/notification-logs", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def list_notification_logs():
    """列出通知发送日志"""
    db = get_db_session()

    channel = request.args.get("channel")
    status = request.args.get("status")
    recipient_id = request.args.get("recipient_id")
    event_type = request.args.get("event_type")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(NotificationLog)

    if channel:
        query = query.filter(NotificationLog.channel == channel)
    if status:
        query = query.filter(NotificationLog.status == status)
    if recipient_id:
        query = query.filter(NotificationLog.recipient_id == recipient_id)
    if event_type:
        query = query.filter(NotificationLog.event_type == event_type)
    if start_time:
        query = query.filter(NotificationLog.created_at >= start_time)
    if end_time:
        query = query.filter(NotificationLog.created_at <= end_time)

    total = query.count()
    logs = query.order_by(NotificationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/notification-logs/<log_id>", methods=["GET"])
@app.route("/api/v1/admin/notification-logs/<log_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_notification_log(log_id: str):
    """获取通知日志详情"""
    db = get_db_session()

    log = db.query(NotificationLog).filter(NotificationLog.log_id == log_id).first()
    if not log:
        return jsonify({"code": 40401, "message": "日志不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": log.to_dict()
    })


@app.route("/api/v1/notification-logs/<log_id>/retry", methods=["POST"])
@app.route("/api/v1/admin/notification-logs/<log_id>/retry", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def retry_notification(log_id: str):
    """重试发送通知"""
    import asyncio
    db = get_db_session()

    log = db.query(NotificationLog).filter(NotificationLog.log_id == log_id).first()
    if not log:
        return jsonify({"code": 40401, "message": "日志不存在"}), 404

    if not log.can_retry():
        return jsonify({"code": 40002, "message": "该通知不可重试（已达最大重试次数或状态非失败）"}), 400

    # 导入通知服务
    try:
        sys.path.insert(0, '/app/shared')
        from notification_service import get_notification_service
        service = get_notification_service()
    except ImportError:
        return jsonify({"code": 50001, "message": "通知服务不可用"}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        log.retry_count += 1
        log.status = "sending"

        result = loop.run_until_complete(
            service.send(log.channel, log.recipient_address, log.subject, log.content, {})
        )

        if result.success:
            log.mark_sent()
            if result.response_data:
                log.set_response_data(result.response_data)
        else:
            log.mark_failed(result.error or "Unknown error", result.error_code)

        db.commit()
    finally:
        loop.close()

    log_audit("update", "notification", log_id, f"Retry notification: {'success' if result.success else 'failed'}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "success": result.success,
            "retry_count": log.retry_count,
            "status": log.status,
            "error": result.error if not result.success else None
        }
    })


@app.route("/api/v1/notification-logs/statistics", methods=["GET"])
@app.route("/api/v1/admin/notification-logs/statistics", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_notification_statistics():
    """获取通知发送统计"""
    db = get_db_session()

    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    query = db.query(NotificationLog)
    if start_time:
        query = query.filter(NotificationLog.created_at >= start_time)
    if end_time:
        query = query.filter(NotificationLog.created_at <= end_time)

    total = query.count()
    sent_count = query.filter(NotificationLog.status.in_(['sent', 'delivered'])).count()
    failed_count = query.filter(NotificationLog.status == 'failed').count()
    pending_count = query.filter(NotificationLog.status.in_(['pending', 'sending'])).count()

    # 按渠道统计
    channel_stats = db.query(
        NotificationLog.channel,
        func.count(NotificationLog.id).label('count')
    ).group_by(NotificationLog.channel).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "pending_count": pending_count,
            "success_rate": round(sent_count / total * 100, 2) if total > 0 else 0,
            "channel_distribution": {ch: cnt for ch, cnt in channel_stats}
        }
    })


# ==================== 门户 - 用户通知 API (P7.3 消息中心) ====================

@app.route("/api/v1/portal/notifications", methods=["GET"])
@require_jwt()
def get_user_notifications():
    """获取当前用户的通知列表"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    # 查询参数
    category = request.args.get("category")
    is_read = request.args.get("is_read")
    notification_type = request.args.get("type")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_deleted == False
    )

    if category:
        query = query.filter(UserNotification.category == category)
    if is_read is not None:
        query = query.filter(UserNotification.is_read == (is_read.lower() == 'true'))
    if notification_type:
        query = query.filter(UserNotification.notification_type == notification_type)

    # 未归档的排前面
    query = query.order_by(UserNotification.is_archived, UserNotification.created_at.desc())

    total = query.count()
    notifications = query.offset((page - 1) * page_size).limit(page_size).all()

    # 未读数量
    unread_count = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_read == False,
        UserNotification.is_deleted == False
    ).count()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [n.to_dict() for n in notifications],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/portal/notifications/unread-count", methods=["GET"])
@require_jwt()
def get_unread_count():
    """获取未读通知数量"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    unread_count = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_read == False,
        UserNotification.is_deleted == False
    ).count()

    # 按类别统计
    category_counts = db.query(
        UserNotification.category,
        func.count(UserNotification.id).label('count')
    ).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_read == False,
        UserNotification.is_deleted == False
    ).group_by(UserNotification.category).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "unread_count": unread_count,
            "by_category": {cat: cnt for cat, cnt in category_counts if cat}
        }
    })


@app.route("/api/v1/portal/notifications/<notification_id>", methods=["GET"])
@require_jwt()
def get_user_notification(notification_id: str):
    """获取单条通知详情"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    notification = db.query(UserNotification).filter(
        UserNotification.notification_id == notification_id,
        UserNotification.user_id == user_id,
        UserNotification.is_deleted == False
    ).first()

    if not notification:
        return jsonify({"code": 40401, "message": "通知不存在"}), 404

    # 自动标记为已读
    if not notification.is_read:
        notification.mark_read()
        db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": notification.to_dict()
    })


@app.route("/api/v1/portal/notifications/<notification_id>/read", methods=["POST"])
@require_jwt()
def mark_notification_read(notification_id: str):
    """标记通知为已读"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    notification = db.query(UserNotification).filter(
        UserNotification.notification_id == notification_id,
        UserNotification.user_id == user_id
    ).first()

    if not notification:
        return jsonify({"code": 40401, "message": "通知不存在"}), 404

    notification.mark_read()
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/portal/notifications/read-all", methods=["POST"])
@require_jwt()
def mark_all_notifications_read():
    """标记所有通知为已读"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)
    data = request.json or {}

    category = data.get("category")

    query = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_read == False
    )

    if category:
        query = query.filter(UserNotification.category == category)

    count = query.update({
        UserNotification.is_read: True,
        UserNotification.read_at: datetime.utcnow()
    })
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"marked_count": count}
    })


@app.route("/api/v1/portal/notifications/<notification_id>/archive", methods=["POST"])
@require_jwt()
def archive_notification(notification_id: str):
    """归档通知"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    notification = db.query(UserNotification).filter(
        UserNotification.notification_id == notification_id,
        UserNotification.user_id == user_id
    ).first()

    if not notification:
        return jsonify({"code": 40401, "message": "通知不存在"}), 404

    notification.mark_archived()
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/portal/notifications/<notification_id>", methods=["DELETE"])
@require_jwt()
def delete_user_notification(notification_id: str):
    """删除通知（软删除）"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    notification = db.query(UserNotification).filter(
        UserNotification.notification_id == notification_id,
        UserNotification.user_id == user_id
    ).first()

    if not notification:
        return jsonify({"code": 40401, "message": "通知不存在"}), 404

    notification.is_deleted = True
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/portal/notifications", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_user_notification():
    """创建用户通知（管理员或系统调用）"""
    db = get_db_session()
    data = request.json

    user_ids = data.get("user_ids", [])
    if not user_ids:
        return jsonify({"code": 40001, "message": "接收用户不能为空"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"code": 40001, "message": "标题不能为空"}), 400

    created_notifications = []
    for user_id in user_ids:
        notification = UserNotification(
            notification_id=UserNotification.generate_id(),
            user_id=user_id,
            title=title,
            content=data.get("content"),
            summary=data.get("summary") or (title[:100] if title else ""),
            notification_type=data.get("notification_type", "info"),
            category=data.get("category", "message"),
            severity=data.get("severity", "info"),
            action_url=data.get("action_url"),
            action_label=data.get("action_label"),
            action_type=data.get("action_type"),
            source_type=data.get("source_type"),
            source_id=data.get("source_id"),
            source_name=data.get("source_name"),
            sender_id=getattr(g, 'user_id', 'system'),
            sender_name=getattr(g, 'username', 'system')
        )

        if data.get("extra_data"):
            notification.set_extra_data(data["extra_data"])

        db.add(notification)
        created_notifications.append(notification)

    db.commit()

    logger.info(f"创建用户通知: {len(created_notifications)} 条")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "created_count": len(created_notifications),
            "notification_ids": [n.notification_id for n in created_notifications]
        }
    }), 201


# ==================== 门户 - 待办事项 API (P7.3 工作台) ====================

@app.route("/api/v1/portal/todos", methods=["GET"])
@require_jwt()
def get_user_todos():
    """获取当前用户的待办事项"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    # 查询参数
    status = request.args.get("status")
    todo_type = request.args.get("type")
    priority = request.args.get("priority")
    include_completed = request.args.get("include_completed", "false").lower() == "true"
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(UserTodo).filter(UserTodo.user_id == user_id)

    if status:
        query = query.filter(UserTodo.status == status)
    elif not include_completed:
        query = query.filter(UserTodo.status.in_(['pending', 'in_progress']))
    if todo_type:
        query = query.filter(UserTodo.todo_type == todo_type)
    if priority:
        query = query.filter(UserTodo.priority == priority)

    # 按优先级和截止日期排序
    priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
    query = query.order_by(
        UserTodo.status.asc(),  # pending 和 in_progress 在前
        UserTodo.due_date.asc().nullslast(),
        UserTodo.created_at.desc()
    )

    total = query.count()
    todos = query.offset((page - 1) * page_size).limit(page_size).all()

    # 统计
    pending_count = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending'
    ).count()

    overdue_count = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending',
        UserTodo.due_date < datetime.utcnow()
    ).count()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "todos": [t.to_dict() for t in todos],
            "total": total,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/portal/todos/summary", methods=["GET"])
@require_jwt()
def get_todos_summary():
    """获取待办事项统计摘要"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    # 各状态数量
    status_counts = db.query(
        UserTodo.status,
        func.count(UserTodo.id).label('count')
    ).filter(UserTodo.user_id == user_id).group_by(UserTodo.status).all()

    # 各类型数量
    type_counts = db.query(
        UserTodo.todo_type,
        func.count(UserTodo.id).label('count')
    ).filter(
        UserTodo.user_id == user_id,
        UserTodo.status.in_(['pending', 'in_progress'])
    ).group_by(UserTodo.todo_type).all()

    # 过期数量
    overdue_count = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending',
        UserTodo.due_date < datetime.utcnow()
    ).count()

    # 今日到期
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59)
    due_today = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending',
        UserTodo.due_date <= today_end,
        UserTodo.due_date >= datetime.utcnow()
    ).count()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "by_status": {s: c for s, c in status_counts},
            "by_type": {t: c for t, c in type_counts if t},
            "overdue_count": overdue_count,
            "due_today": due_today
        }
    })


@app.route("/api/v1/portal/todos/<todo_id>", methods=["GET"])
@require_jwt()
def get_user_todo(todo_id: str):
    """获取单条待办详情"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    todo = db.query(UserTodo).filter(
        UserTodo.todo_id == todo_id,
        UserTodo.user_id == user_id
    ).first()

    if not todo:
        return jsonify({"code": 40401, "message": "待办不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": todo.to_dict()
    })


@app.route("/api/v1/portal/todos/<todo_id>/start", methods=["POST"])
@require_jwt()
def start_todo(todo_id: str):
    """开始处理待办"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    todo = db.query(UserTodo).filter(
        UserTodo.todo_id == todo_id,
        UserTodo.user_id == user_id
    ).first()

    if not todo:
        return jsonify({"code": 40401, "message": "待办不存在"}), 404

    todo.start()
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": todo.to_dict()
    })


@app.route("/api/v1/portal/todos/<todo_id>/complete", methods=["POST"])
@require_jwt()
def complete_todo(todo_id: str):
    """完成待办"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    todo = db.query(UserTodo).filter(
        UserTodo.todo_id == todo_id,
        UserTodo.user_id == user_id
    ).first()

    if not todo:
        return jsonify({"code": 40401, "message": "待办不存在"}), 404

    todo.complete()
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": todo.to_dict()
    })


@app.route("/api/v1/portal/todos/<todo_id>/cancel", methods=["POST"])
@require_jwt()
def cancel_todo(todo_id: str):
    """取消待办"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    todo = db.query(UserTodo).filter(
        UserTodo.todo_id == todo_id,
        UserTodo.user_id == user_id
    ).first()

    if not todo:
        return jsonify({"code": 40401, "message": "待办不存在"}), 404

    todo.cancel()
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/portal/todos", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_user_todo():
    """创建用户待办（管理员或系统调用）"""
    db = get_db_session()
    data = request.json

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"code": 40001, "message": "用户ID不能为空"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"code": 40001, "message": "标题不能为空"}), 400

    todo = UserTodo(
        todo_id=UserTodo.generate_id(),
        user_id=user_id,
        title=title,
        description=data.get("description"),
        todo_type=data.get("todo_type", "task"),
        priority=data.get("priority", "medium"),
        source_type=data.get("source_type"),
        source_id=data.get("source_id"),
        source_name=data.get("source_name"),
        source_url=data.get("source_url"),
        created_by=getattr(g, 'username', 'system')
    )

    if data.get("due_date"):
        todo.due_date = datetime.fromisoformat(data["due_date"].replace('Z', '+00:00'))
    if data.get("reminder_at"):
        todo.reminder_at = datetime.fromisoformat(data["reminder_at"].replace('Z', '+00:00'))

    db.add(todo)
    db.commit()
    db.refresh(todo)

    logger.info(f"创建用户待办: {todo.todo_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": todo.to_dict()
    }), 201


# ==================== 门户 - 公告管理 API ====================

@app.route("/api/v1/portal/announcements", methods=["GET"])
@require_jwt(optional=True)
def get_announcements():
    """获取公告列表"""
    db = get_db_session()

    # 查询参数
    status = request.args.get("status")
    announcement_type = request.args.get("type")
    active_only = request.args.get("active_only", "true").lower() == "true"
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(Announcement)

    if status:
        query = query.filter(Announcement.status == status)
    elif active_only:
        query = query.filter(Announcement.status == 'published')

    if announcement_type:
        query = query.filter(Announcement.announcement_type == announcement_type)

    # 按置顶和优先级排序
    query = query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.priority.desc(),
        Announcement.publish_at.desc()
    )

    total = query.count()
    announcements = query.offset((page - 1) * page_size).limit(page_size).all()

    # 过滤掉已过期的
    if active_only:
        now = datetime.utcnow()
        announcements = [a for a in announcements if a.is_active()]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "announcements": [a.to_dict() for a in announcements],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/portal/announcements/popup", methods=["GET"])
@require_jwt()
def get_popup_announcements():
    """获取需要弹窗显示的公告"""
    db = get_db_session()

    announcements = db.query(Announcement).filter(
        Announcement.status == 'published',
        Announcement.is_popup == True
    ).order_by(Announcement.priority.desc()).all()

    # 过滤已过期的
    active_announcements = [a for a in announcements if a.is_active()]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "announcements": [a.to_dict() for a in active_announcements]
        }
    })


@app.route("/api/v1/portal/announcements/<announcement_id>", methods=["GET"])
@require_jwt(optional=True)
def get_announcement(announcement_id: str):
    """获取公告详情"""
    db = get_db_session()

    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()

    if not announcement:
        return jsonify({"code": 40401, "message": "公告不存在"}), 404

    # 增加浏览次数
    announcement.view_count = (announcement.view_count or 0) + 1
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": announcement.to_dict()
    })


@app.route("/api/v1/portal/announcements", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.CREATE)
def create_announcement():
    """创建公告"""
    db = get_db_session()
    data = request.json

    title = data.get("title")
    if not title:
        return jsonify({"code": 40001, "message": "公告标题不能为空"}), 400

    announcement = Announcement(
        announcement_id=Announcement.generate_id(),
        title=title,
        content=data.get("content"),
        summary=data.get("summary"),
        announcement_type=data.get("announcement_type", "info"),
        priority=data.get("priority", 0),
        is_pinned=data.get("is_pinned", False),
        is_popup=data.get("is_popup", False),
        status=data.get("status", "draft"),
        created_by=getattr(g, 'username', 'system')
    )

    if data.get("target_roles"):
        announcement.target_roles = json.dumps(data["target_roles"])
    if data.get("start_time"):
        announcement.start_time = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
    if data.get("end_time"):
        announcement.end_time = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))
    if data.get("status") == "published":
        announcement.publish_at = datetime.utcnow()

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    log_audit("create", "announcement", announcement.announcement_id, announcement.title)
    logger.info(f"创建公告: {announcement.announcement_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": announcement.to_dict()
    }), 201


@app.route("/api/v1/portal/announcements/<announcement_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.UPDATE)
def update_announcement(announcement_id: str):
    """更新公告"""
    db = get_db_session()
    data = request.json

    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()

    if not announcement:
        return jsonify({"code": 40401, "message": "公告不存在"}), 404

    old_data = announcement.to_dict()

    if data.get("title"):
        announcement.title = data["title"]
    if data.get("content") is not None:
        announcement.content = data["content"]
    if data.get("summary") is not None:
        announcement.summary = data["summary"]
    if data.get("announcement_type"):
        announcement.announcement_type = data["announcement_type"]
    if data.get("priority") is not None:
        announcement.priority = data["priority"]
    if data.get("is_pinned") is not None:
        announcement.is_pinned = data["is_pinned"]
    if data.get("is_popup") is not None:
        announcement.is_popup = data["is_popup"]
    if data.get("status"):
        old_status = announcement.status
        announcement.status = data["status"]
        if data["status"] == "published" and old_status != "published":
            announcement.publish_at = datetime.utcnow()
    if data.get("target_roles") is not None:
        announcement.target_roles = json.dumps(data["target_roles"]) if data["target_roles"] else None
    if data.get("start_time"):
        announcement.start_time = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
    if data.get("end_time"):
        announcement.end_time = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))

    announcement.updated_by = getattr(g, 'username', 'system')

    db.commit()
    db.refresh(announcement)

    log_audit("update", "announcement", announcement.announcement_id, announcement.title,
              changes={"before": old_data, "after": announcement.to_dict()})
    logger.info(f"更新公告: {announcement_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": announcement.to_dict()
    })


@app.route("/api/v1/portal/announcements/<announcement_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.DELETE)
def delete_announcement(announcement_id: str):
    """删除公告"""
    db = get_db_session()

    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()

    if not announcement:
        return jsonify({"code": 40401, "message": "公告不存在"}), 404

    title = announcement.title
    db.delete(announcement)
    db.commit()

    log_audit("delete", "announcement", announcement_id, title)
    logger.info(f"删除公告: {announcement_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 门户 - 用户活动日志 API ====================

@app.route("/api/v1/portal/activities", methods=["GET"])
@require_jwt()
def get_user_activities():
    """获取当前用户的活动记录"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    # 查询参数
    action = request.args.get("action")
    resource_type = request.args.get("resource_type")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(UserActivityLog).filter(UserActivityLog.user_id == user_id)

    if action:
        query = query.filter(UserActivityLog.action == action)
    if resource_type:
        query = query.filter(UserActivityLog.resource_type == resource_type)
    if start_time:
        query = query.filter(UserActivityLog.created_at >= start_time)
    if end_time:
        query = query.filter(UserActivityLog.created_at <= end_time)

    query = query.order_by(UserActivityLog.created_at.desc())

    total = query.count()
    activities = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "activities": [a.to_dict() for a in activities],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/portal/activities", methods=["POST"])
@require_jwt()
def log_user_activity():
    """记录用户活动（前端调用）"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)
    username = getattr(g, 'username', None)
    data = request.json

    action = data.get("action")
    if not action:
        return jsonify({"code": 40001, "message": "操作类型不能为空"}), 400

    activity = UserActivityLog(
        log_id=UserActivityLog.generate_id(),
        user_id=user_id,
        username=username,
        action=action,
        action_label=data.get("action_label"),
        resource_type=data.get("resource_type"),
        resource_id=data.get("resource_id"),
        resource_name=data.get("resource_name"),
        resource_url=data.get("resource_url"),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:512],
        duration_ms=data.get("duration_ms")
    )

    db.add(activity)
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"log_id": activity.log_id}
    }), 201


# ==================== 门户统计 API ====================

@app.route("/api/v1/portal/dashboard", methods=["GET"])
@require_jwt()
def get_portal_dashboard():
    """获取门户仪表板数据"""
    db = get_db_session()
    user_id = getattr(g, 'user_id', None)

    if not user_id:
        return jsonify({"code": 40101, "message": "未登录"}), 401

    # 未读通知数
    unread_notifications = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_read == False,
        UserNotification.is_deleted == False
    ).count()

    # 待办统计
    pending_todos = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending'
    ).count()

    overdue_todos = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status == 'pending',
        UserTodo.due_date < datetime.utcnow()
    ).count()

    # 今日活动数
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_activities = db.query(UserActivityLog).filter(
        UserActivityLog.user_id == user_id,
        UserActivityLog.created_at >= today_start
    ).count()

    # 最近待办
    recent_todos = db.query(UserTodo).filter(
        UserTodo.user_id == user_id,
        UserTodo.status.in_(['pending', 'in_progress'])
    ).order_by(UserTodo.due_date.asc().nullslast()).limit(5).all()

    # 最近通知
    recent_notifications = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.is_deleted == False
    ).order_by(UserNotification.created_at.desc()).limit(5).all()

    # 活跃公告
    active_announcements = db.query(Announcement).filter(
        Announcement.status == 'published',
        Announcement.is_pinned == True
    ).order_by(Announcement.priority.desc()).limit(3).all()
    active_announcements = [a for a in active_announcements if a.is_active()]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "stats": {
                "unread_notifications": unread_notifications,
                "pending_todos": pending_todos,
                "overdue_todos": overdue_todos,
                "today_activities": today_activities
            },
            "recent_todos": [t.to_dict() for t in recent_todos],
            "recent_notifications": [n.to_dict() for n in recent_notifications],
            "active_announcements": [a.to_dict() for a in active_announcements]
        }
    })


# ==================== 成本报告 API ====================

@app.route("/api/v1/cost/summary", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_cost_summary():
    """获取成本概览"""
    # 模拟数据
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "total_cost": 12580.50,
            "compute_cost": 8500.00,
            "storage_cost": 2000.00,
            "network_cost": 1080.50,
            "api_cost": 1000.00,
            "period": "2024-01",
            "trend": "+5.2%"
        }
    })


@app.route("/api/v1/cost/usage", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_cost_usage():
    """获取用量明细"""
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {"resource": "GPU (A100)", "usage": "1200 GPU-hours", "cost": 6000.00},
                {"resource": "CPU", "usage": "5000 vCPU-hours", "cost": 2500.00},
                {"resource": "Storage", "usage": "10 TB", "cost": 2000.00},
                {"resource": "Network", "usage": "5 TB", "cost": 1080.50},
                {"resource": "API Calls", "usage": "1M requests", "cost": 1000.00}
            ]
        }
    })


@app.route("/api/v1/cost/trends", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.READ)
def get_cost_trends():
    """获取成本趋势"""
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "trends": [
                {"date": "2024-01-01", "cost": 400.00},
                {"date": "2024-01-02", "cost": 420.00},
                {"date": "2024-01-03", "cost": 380.00},
                {"date": "2024-01-04", "cost": 450.00},
                {"date": "2024-01-05", "cost": 410.00}
            ]
        }
    })


# ==================== 平台统计 API ====================

@app.route("/api/v1/stats/overview", methods=["GET"])
@require_jwt(optional=True)
def get_stats_overview():
    """获取平台统计概览（供 HomePage 使用）"""
    db = get_db_session()

    # 用户统计
    total_users = db.query(User).filter(User.status != 'deleted').count()
    active_users = db.query(User).filter(User.status == 'active').count()

    # 模拟其他统计数据
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "datasets": {
                "total": 156,
                "recent": 12
            },
            "models": {
                "total": 45,
                "deployed": 18
            },
            "workflows": {
                "total": 89,
                "running": 5
            },
            "experiments": {
                "total": 234,
                "completed": 198
            },
            "api_calls": {
                "today": 12580,
                "total": 1580000
            },
            "storage": {
                "used_gb": 256.5,
                "total_gb": 1024
            },
            "compute": {
                "gpu_hours_today": 48,
                "cpu_hours_today": 256
            }
        }
    })


# ==================== 初始化数据库 ====================

def init_default_data():
    """初始化默认数据"""
    db = SessionLocal()
    try:
        # 创建默认权限
        default_permissions = [
            ("perm_user_create", "创建用户", "user:create", "user", "create", "用户管理"),
            ("perm_user_read", "查看用户", "user:read", "user", "read", "用户管理"),
            ("perm_user_update", "更新用户", "user:update", "user", "update", "用户管理"),
            ("perm_user_delete", "删除用户", "user:delete", "user", "delete", "用户管理"),
            ("perm_user_manage", "管理用户", "user:manage", "user", "manage", "用户管理"),
            ("perm_dataset_create", "创建数据集", "dataset:create", "dataset", "create", "数据管理"),
            ("perm_dataset_read", "查看数据集", "dataset:read", "dataset", "read", "数据管理"),
            ("perm_dataset_update", "更新数据集", "dataset:update", "dataset", "update", "数据管理"),
            ("perm_dataset_delete", "删除数据集", "dataset:delete", "dataset", "delete", "数据管理"),
            ("perm_model_create", "创建模型", "model:create", "model", "create", "模型管理"),
            ("perm_model_read", "查看模型", "model:read", "model", "read", "模型管理"),
            ("perm_model_update", "更新模型", "model:update", "model", "update", "模型管理"),
            ("perm_model_delete", "删除模型", "model:delete", "model", "delete", "模型管理"),
            ("perm_model_execute", "执行模型", "model:execute", "model", "execute", "模型管理"),
            ("perm_workflow_create", "创建工作流", "workflow:create", "workflow", "create", "工作流管理"),
            ("perm_workflow_read", "查看工作流", "workflow:read", "workflow", "read", "工作流管理"),
            ("perm_workflow_update", "更新工作流", "workflow:update", "workflow", "update", "工作流管理"),
            ("perm_workflow_delete", "删除工作流", "workflow:delete", "workflow", "delete", "工作流管理"),
            ("perm_workflow_execute", "执行工作流", "workflow:execute", "workflow", "execute", "工作流管理"),
            ("perm_system_read", "查看系统设置", "system:read", "system", "read", "系统管理"),
            ("perm_system_update", "更新系统设置", "system:update", "system", "update", "系统管理"),
            ("perm_system_manage", "管理系统", "system:manage", "system", "manage", "系统管理"),
        ]

        for perm_id, name, code, resource, operation, category in default_permissions:
            existing = db.query(Permission).filter(Permission.permission_id == perm_id).first()
            if not existing:
                perm = Permission(
                    permission_id=perm_id,
                    name=name,
                    code=code,
                    resource=resource,
                    operation=operation,
                    category=category,
                    is_system=True
                )
                db.add(perm)

        # 创建默认角色
        default_roles = [
            ("role_admin", "admin", "系统管理员", "拥有所有权限", True, 100),
            ("role_data_engineer", "data_engineer", "数据工程师", "数据集和元数据管理权限", True, 50),
            ("role_ai_developer", "ai_developer", "AI 开发者", "模型和工作流管理权限", True, 50),
            ("role_user", "user", "普通用户", "基础读取权限", True, 10),
        ]

        for role_id, name, display_name, description, is_system, priority in default_roles:
            existing = db.query(Role).filter(Role.role_id == role_id).first()
            if not existing:
                role = Role(
                    role_id=role_id,
                    name=name,
                    display_name=display_name,
                    description=description,
                    role_type="system",
                    is_system=is_system,
                    priority=priority
                )
                db.add(role)

        # 创建默认管理员用户
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                user_id="user_admin",
                username="admin",
                email="admin@one-data.local",
                password_hash=hash_password("admin123"),
                display_name="系统管理员",
                status="active",
                created_by="system"
            )
            db.add(admin)
            db.flush()

            # 分配管理员角色
            admin_role = db.query(Role).filter(Role.role_id == "role_admin").first()
            if admin_role:
                admin.roles.append(admin_role)

        db.commit()
        logger.info("默认数据初始化完成")

    except Exception as e:
        logger.error(f"初始化默认数据失败: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== 启动应用 ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))

    # 初始化数据库
    try:
        init_db()
        init_default_data()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化跳过: {e}")

    debug = os.getenv("DEBUG", "false").lower() == "true"

    if debug:
        logger.warning("WARNING: Debug mode is ENABLED. This should NEVER be used in production!")

    logger.info(f"Starting Admin API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
