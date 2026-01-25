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
