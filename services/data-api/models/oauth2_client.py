"""
OAuth2 客户端和 API Key 模型
Phase 2: 统一认证框架增强

支持：
- OAuth2 客户端应用注册
- API Key 管理
- 授权码管理
- Token 吊销记录
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Text, TIMESTAMP, JSON, Index
from .base import Base


class OAuth2Client(Base):
    """OAuth2 客户端应用表"""
    __tablename__ = "oauth2_clients"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(String(128), unique=True, nullable=False, index=True, comment="客户端ID")
    client_secret_hash = Column(String(256), nullable=False, comment="客户端密钥哈希")
    client_name = Column(String(128), nullable=False, comment="客户端名称")
    description = Column(Text, comment="描述")

    # 授权配置
    grant_types = Column(JSON, comment="支持的授权类型 ['authorization_code','client_credentials','refresh_token']")
    redirect_uris = Column(JSON, comment="回调地址列表")
    scopes = Column(JSON, comment="允许的权限范围 ['read','write','admin']")

    # 安全配置
    token_lifetime = Column(Integer, default=3600, comment="Access Token 有效期(秒)")
    refresh_token_lifetime = Column(Integer, default=604800, comment="Refresh Token 有效期(秒)")
    require_pkce = Column(Integer, default=0, comment="是否要求PKCE (0=否 1=是)")

    # 状态
    status = Column(String(16), default="active", comment="状态: active, suspended, revoked")
    owner = Column(String(128), comment="所有者")

    # 审计
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(128))
    last_used_at = Column(TIMESTAMP, comment="最后使用时间")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "description": self.description,
            "grant_types": self.grant_types or [],
            "redirect_uris": self.redirect_uris or [],
            "scopes": self.scopes or [],
            "token_lifetime": self.token_lifetime,
            "refresh_token_lifetime": self.refresh_token_lifetime,
            "require_pkce": bool(self.require_pkce),
            "status": self.status,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class APIKey(Base):
    """API Key 表"""
    __tablename__ = "api_keys"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True, comment="Key标识")
    key_hash = Column(String(256), nullable=False, comment="Key哈希")
    key_prefix = Column(String(16), comment="Key前缀(用于识别)")
    name = Column(String(128), nullable=False, comment="Key名称")
    description = Column(Text, comment="描述")

    # 关联
    user_id = Column(String(128), nullable=False, index=True, comment="所属用户")
    client_id = Column(String(128), comment="关联的OAuth2客户端")

    # 权限
    scopes = Column(JSON, comment="权限范围")
    allowed_ips = Column(JSON, comment="IP白名单")
    rate_limit = Column(Integer, default=1000, comment="每小时请求限制")

    # 有效期
    expires_at = Column(TIMESTAMP, comment="过期时间(null=永不过期)")
    status = Column(String(16), default="active", comment="状态: active, suspended, revoked")

    # 审计
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_used_at = Column(TIMESTAMP)
    usage_count = Column(BigInteger, default=0, comment="使用次数")

    def to_dict(self):
        return {
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "scopes": self.scopes or [],
            "allowed_ips": self.allowed_ips or [],
            "rate_limit": self.rate_limit,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
        }


class TokenRevocation(Base):
    """Token 吊销记录"""
    __tablename__ = "token_revocations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_jti = Column(String(256), unique=True, nullable=False, index=True, comment="Token JTI(唯一标识)")
    token_type = Column(String(16), comment="Token类型: access, refresh")
    client_id = Column(String(128), comment="关联客户端")
    user_id = Column(String(128), comment="关联用户")
    revoked_at = Column(TIMESTAMP, default=datetime.utcnow)
    revoked_by = Column(String(128))
    reason = Column(String(255), comment="吊销原因")
    expires_at = Column(TIMESTAMP, comment="Token原过期时间(用于清理)")

    __table_args__ = (
        Index("idx_revocation_expires", "expires_at"),
    )


class AuthAuditLog(Base):
    """认证审计日志"""
    __tablename__ = "auth_audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True, comment="事件ID")
    event_type = Column(String(32), nullable=False, comment="事件类型: login, logout, token_refresh, token_revoke, api_key_create, etc.")
    event_status = Column(String(16), default="success", comment="success, failed")

    # 用户
    user_id = Column(String(128), index=True)
    user_name = Column(String(128))
    ip_address = Column(String(64))
    user_agent = Column(String(512))

    # 认证方式
    auth_method = Column(String(32), comment="认证方式: password, sso, api_key, oauth2, qr_code, sms")
    provider = Column(String(64), comment="SSO提供商")
    client_id = Column(String(128), comment="OAuth2客户端ID")

    # 详情
    details = Column(JSON)
    error_message = Column(Text)

    # 时间
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_auth_audit_user", "user_id", "created_at"),
        Index("idx_auth_audit_type", "event_type", "created_at"),
    )

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_status": self.event_status,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "ip_address": self.ip_address,
            "auth_method": self.auth_method,
            "provider": self.provider,
            "client_id": self.client_id,
            "details": self.details,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
