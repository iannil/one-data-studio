"""
统一认证服务
Phase 2: OAuth2 授权服务器 + API Key 管理 + 认证审计

功能：
- OAuth2 客户端注册与管理
- Client Credentials Flow（服务间认证）
- Authorization Code Flow（第三方应用授权）
- API Key 生成、验证与管理
- Token 吊销与黑名单
- 认证事件审计日志
- 会话管理增强（强制下线、会话查询）
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 配置
TOKEN_SECRET_KEY = os.getenv("TOKEN_SECRET_KEY", "default-secret-key-change-in-production")
AUTH_CODE_EXPIRY_SECONDS = 300  # 授权码 5 分钟有效
API_KEY_PREFIX = "odsk_"  # one-data-studio key


class UnifiedAuthService:
    """
    统一认证服务

    整合 OAuth2 授权、API Key 管理和认证审计，
    为平台提供完整的认证授权基础设施。
    """

    def __init__(self):
        # 内存缓存（授权码、token 黑名单）
        self._auth_codes: Dict[str, Dict[str, Any]] = {}
        self._revoked_tokens: Dict[str, float] = {}  # jti -> expiry timestamp

    # ==================== OAuth2 客户端管理 ====================

    def register_client(
        self,
        client_name: str,
        grant_types: List[str],
        redirect_uris: List[str] = None,
        scopes: List[str] = None,
        owner: str = "",
        created_by: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        注册 OAuth2 客户端

        Args:
            client_name: 客户端名称
            grant_types: 授权类型列表
            redirect_uris: 回调地址列表
            scopes: 权限范围
            owner: 所有者
            created_by: 创建者
            db_session: 数据库会话

        Returns:
            包含 client_id 和 client_secret 的注册结果
        """
        result = {"success": False, "client_id": None, "client_secret": None, "message": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        # 验证授权类型
        valid_grant_types = {"authorization_code", "client_credentials", "refresh_token"}
        for gt in grant_types:
            if gt not in valid_grant_types:
                result["message"] = f"不支持的授权类型: {gt}"
                return result

        # authorization_code 需要 redirect_uris
        if "authorization_code" in grant_types and not redirect_uris:
            result["message"] = "authorization_code 需要指定 redirect_uris"
            return result

        try:
            from models.oauth2_client import OAuth2Client

            client_id = f"cli_{uuid.uuid4().hex[:16]}"
            client_secret = secrets.token_urlsafe(48)
            secret_hash = self._hash_secret(client_secret)

            client = OAuth2Client(
                client_id=client_id,
                client_secret_hash=secret_hash,
                client_name=client_name,
                grant_types=grant_types,
                redirect_uris=redirect_uris or [],
                scopes=scopes or ["read"],
                owner=owner,
                created_by=created_by,
            )

            db_session.add(client)
            db_session.commit()

            # 记录审计
            self._log_auth_event(
                event_type="client_register",
                user_id=created_by,
                details={"client_id": client_id, "client_name": client_name},
                db_session=db_session,
            )

            result["success"] = True
            result["client_id"] = client_id
            result["client_secret"] = client_secret  # 仅在注册时返回一次
            result["message"] = f"客户端 {client_name} 注册成功"

            logger.info(f"OAuth2 客户端注册: {client_id} ({client_name})")

        except Exception as e:
            logger.error(f"客户端注册失败: {e}", exc_info=True)
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def list_clients(
        self,
        owner: str = None,
        status: str = None,
        page: int = 1,
        page_size: int = 20,
        db_session=None,
    ) -> Dict[str, Any]:
        """列出 OAuth2 客户端"""
        if db_session is None:
            return {"total": 0, "items": []}

        try:
            from models.oauth2_client import OAuth2Client

            query = db_session.query(OAuth2Client)
            if owner:
                query = query.filter(OAuth2Client.owner == owner)
            if status:
                query = query.filter(OAuth2Client.status == status)

            total = query.count()
            clients = query.order_by(OAuth2Client.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return {
                "total": total,
                "items": [c.to_dict() for c in clients],
            }

        except Exception as e:
            logger.error(f"查询客户端列表失败: {e}")
            return {"total": 0, "items": []}

    def update_client_status(
        self,
        client_id: str,
        status: str,
        operator: str = "",
        db_session=None,
    ) -> bool:
        """更新客户端状态 (active/suspended/revoked)"""
        if db_session is None:
            return False

        try:
            from models.oauth2_client import OAuth2Client

            client = db_session.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id
            ).first()

            if not client:
                return False

            client.status = status
            client.updated_at = datetime.utcnow()
            db_session.commit()

            self._log_auth_event(
                event_type="client_status_change",
                user_id=operator,
                details={"client_id": client_id, "new_status": status},
                db_session=db_session,
            )

            return True

        except Exception as e:
            logger.error(f"更新客户端状态失败: {e}")
            return False

    # ==================== Client Credentials Flow ====================

    def client_credentials_authenticate(
        self,
        client_id: str,
        client_secret: str,
        requested_scopes: List[str] = None,
        ip_address: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        Client Credentials 认证（服务间认证）

        Returns:
            包含 access_token 信息的认证结果
        """
        result = {
            "success": False,
            "access_token": None,
            "token_type": "Bearer",
            "expires_in": 0,
            "scope": "",
            "error": "",
        }

        if db_session is None:
            result["error"] = "server_error"
            return result

        try:
            from models.oauth2_client import OAuth2Client

            client = db_session.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.status == "active",
            ).first()

            if not client:
                result["error"] = "invalid_client"
                self._log_auth_event(
                    event_type="client_auth",
                    event_status="failed",
                    details={"client_id": client_id, "reason": "client_not_found"},
                    ip_address=ip_address,
                    db_session=db_session,
                )
                return result

            # 验证密钥
            if not self._verify_secret(client_secret, client.client_secret_hash):
                result["error"] = "invalid_client"
                self._log_auth_event(
                    event_type="client_auth",
                    event_status="failed",
                    details={"client_id": client_id, "reason": "invalid_secret"},
                    ip_address=ip_address,
                    db_session=db_session,
                )
                return result

            # 验证授权类型
            if "client_credentials" not in (client.grant_types or []):
                result["error"] = "unauthorized_client"
                return result

            # 验证范围
            allowed_scopes = set(client.scopes or ["read"])
            req_scopes = set(requested_scopes or ["read"])
            granted_scopes = req_scopes & allowed_scopes

            if not granted_scopes:
                result["error"] = "invalid_scope"
                return result

            # 生成 Token
            token_data = self._generate_service_token(
                client_id=client_id,
                scopes=list(granted_scopes),
                lifetime=client.token_lifetime or 3600,
            )

            # 更新最后使用时间
            client.last_used_at = datetime.utcnow()
            db_session.commit()

            self._log_auth_event(
                event_type="client_auth",
                event_status="success",
                auth_method="client_credentials",
                client_id=client_id,
                details={"scopes": list(granted_scopes)},
                ip_address=ip_address,
                db_session=db_session,
            )

            result["success"] = True
            result["access_token"] = token_data["token"]
            result["expires_in"] = token_data["expires_in"]
            result["scope"] = " ".join(granted_scopes)

        except Exception as e:
            logger.error(f"Client Credentials 认证失败: {e}")
            result["error"] = "server_error"

        return result

    # ==================== Authorization Code Flow ====================

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        user_id: str,
        code_challenge: str = None,
        code_challenge_method: str = None,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        生成授权码（用户授权后调用）

        Returns:
            包含 code 和 redirect_uri 的结果
        """
        result = {"success": False, "code": None, "redirect_uri": "", "error": ""}

        if db_session is None:
            result["error"] = "server_error"
            return result

        try:
            from models.oauth2_client import OAuth2Client

            client = db_session.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.status == "active",
            ).first()

            if not client:
                result["error"] = "invalid_client"
                return result

            if "authorization_code" not in (client.grant_types or []):
                result["error"] = "unauthorized_client"
                return result

            # 验证 redirect_uri
            if redirect_uri not in (client.redirect_uris or []):
                result["error"] = "invalid_redirect_uri"
                return result

            # 生成授权码
            code = secrets.token_urlsafe(32)
            self._auth_codes[code] = {
                "client_id": client_id,
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "created_at": time.time(),
            }

            result["success"] = True
            result["code"] = code
            result["redirect_uri"] = f"{redirect_uri}?code={code}&state={state}"

            logger.info(f"授权码已生成: client={client_id}, user={user_id}")

        except Exception as e:
            logger.error(f"生成授权码失败: {e}")
            result["error"] = "server_error"

        return result

    def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: str = None,
        ip_address: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        用授权码换取 Token

        Returns:
            Token 信息
        """
        result = {
            "success": False,
            "access_token": None,
            "refresh_token": None,
            "token_type": "Bearer",
            "expires_in": 0,
            "scope": "",
            "error": "",
        }

        if db_session is None:
            result["error"] = "server_error"
            return result

        # 验证授权码
        code_data = self._auth_codes.pop(code, None)
        if not code_data:
            result["error"] = "invalid_grant"
            return result

        # 检查过期
        if time.time() - code_data["created_at"] > AUTH_CODE_EXPIRY_SECONDS:
            result["error"] = "invalid_grant"
            return result

        # 验证参数
        if code_data["client_id"] != client_id:
            result["error"] = "invalid_client"
            return result

        if code_data["redirect_uri"] != redirect_uri:
            result["error"] = "invalid_redirect_uri"
            return result

        # PKCE 验证
        if code_data.get("code_challenge"):
            if not code_verifier:
                result["error"] = "invalid_grant"
                return result
            if not self._verify_pkce(code_verifier, code_data["code_challenge"],
                                      code_data.get("code_challenge_method", "S256")):
                result["error"] = "invalid_grant"
                return result

        try:
            from models.oauth2_client import OAuth2Client

            client = db_session.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.status == "active",
            ).first()

            if not client or not self._verify_secret(client_secret, client.client_secret_hash):
                result["error"] = "invalid_client"
                return result

            scopes = code_data.get("scope", "read").split()

            # 生成 Token
            token_data = self._generate_user_token(
                user_id=code_data["user_id"],
                client_id=client_id,
                scopes=scopes,
                lifetime=client.token_lifetime or 3600,
            )

            refresh_token = secrets.token_urlsafe(48)

            client.last_used_at = datetime.utcnow()
            db_session.commit()

            self._log_auth_event(
                event_type="authorization_code_exchange",
                event_status="success",
                user_id=code_data["user_id"],
                auth_method="authorization_code",
                client_id=client_id,
                ip_address=ip_address,
                db_session=db_session,
            )

            result["success"] = True
            result["access_token"] = token_data["token"]
            result["refresh_token"] = refresh_token
            result["expires_in"] = token_data["expires_in"]
            result["scope"] = " ".join(scopes)

        except Exception as e:
            logger.error(f"授权码换取 Token 失败: {e}")
            result["error"] = "server_error"

        return result

    # ==================== API Key 管理 ====================

    def create_api_key(
        self,
        name: str,
        user_id: str,
        scopes: List[str] = None,
        allowed_ips: List[str] = None,
        expires_days: int = None,
        rate_limit: int = 1000,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        创建 API Key

        Returns:
            包含 api_key 的创建结果（仅创建时返回完整 Key）
        """
        result = {"success": False, "key_id": None, "api_key": None, "message": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        try:
            from models.oauth2_client import APIKey

            key_id = f"key_{uuid.uuid4().hex[:12]}"
            raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(42)}"
            key_hash = self._hash_secret(raw_key)
            key_prefix = raw_key[:12]

            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)

            api_key = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=name,
                user_id=user_id,
                scopes=scopes or ["read"],
                allowed_ips=allowed_ips or [],
                rate_limit=rate_limit,
                expires_at=expires_at,
            )

            db_session.add(api_key)
            db_session.commit()

            self._log_auth_event(
                event_type="api_key_create",
                user_id=user_id,
                details={"key_id": key_id, "name": name},
                db_session=db_session,
            )

            result["success"] = True
            result["key_id"] = key_id
            result["api_key"] = raw_key  # 仅此时返回
            result["key_prefix"] = key_prefix
            result["message"] = f"API Key '{name}' 创建成功"

            logger.info(f"API Key 创建: {key_id} for user={user_id}")

        except Exception as e:
            logger.error(f"API Key 创建失败: {e}")
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def validate_api_key(
        self,
        api_key: str,
        required_scopes: List[str] = None,
        ip_address: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        验证 API Key

        Returns:
            验证结果（包含用户信息和权限）
        """
        result = {
            "valid": False,
            "user_id": None,
            "scopes": [],
            "error": "",
        }

        if db_session is None:
            result["error"] = "server_error"
            return result

        try:
            from models.oauth2_client import APIKey

            # 用前缀快速过滤
            prefix = api_key[:12] if len(api_key) >= 12 else api_key
            candidates = db_session.query(APIKey).filter(
                APIKey.key_prefix == prefix,
                APIKey.status == "active",
            ).all()

            matched_key = None
            for candidate in candidates:
                if self._verify_secret(api_key, candidate.key_hash):
                    matched_key = candidate
                    break

            if not matched_key:
                result["error"] = "invalid_key"
                return result

            # 检查过期
            if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
                result["error"] = "key_expired"
                return result

            # IP 白名单
            if matched_key.allowed_ips and ip_address:
                if ip_address not in matched_key.allowed_ips:
                    result["error"] = "ip_not_allowed"
                    self._log_auth_event(
                        event_type="api_key_validate",
                        event_status="failed",
                        user_id=matched_key.user_id,
                        auth_method="api_key",
                        details={"key_id": matched_key.key_id, "reason": "ip_blocked", "ip": ip_address},
                        ip_address=ip_address,
                        db_session=db_session,
                    )
                    return result

            # 权限检查
            key_scopes = set(matched_key.scopes or [])
            if required_scopes:
                if not set(required_scopes).issubset(key_scopes):
                    result["error"] = "insufficient_scope"
                    return result

            # 更新使用计数
            matched_key.last_used_at = datetime.utcnow()
            matched_key.usage_count = (matched_key.usage_count or 0) + 1
            db_session.commit()

            result["valid"] = True
            result["user_id"] = matched_key.user_id
            result["scopes"] = matched_key.scopes or []
            result["key_id"] = matched_key.key_id

        except Exception as e:
            logger.error(f"API Key 验证失败: {e}")
            result["error"] = "server_error"

        return result

    def list_api_keys(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        db_session=None,
    ) -> Dict[str, Any]:
        """列出用户的 API Key"""
        if db_session is None:
            return {"total": 0, "items": []}

        try:
            from models.oauth2_client import APIKey

            query = db_session.query(APIKey).filter(APIKey.user_id == user_id)
            total = query.count()
            keys = query.order_by(APIKey.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return {
                "total": total,
                "items": [k.to_dict() for k in keys],
            }

        except Exception as e:
            logger.error(f"查询 API Key 列表失败: {e}")
            return {"total": 0, "items": []}

    def revoke_api_key(
        self,
        key_id: str,
        user_id: str,
        db_session=None,
    ) -> bool:
        """吊销 API Key"""
        if db_session is None:
            return False

        try:
            from models.oauth2_client import APIKey

            key = db_session.query(APIKey).filter(
                APIKey.key_id == key_id,
                APIKey.user_id == user_id,
            ).first()

            if not key:
                return False

            key.status = "revoked"
            db_session.commit()

            self._log_auth_event(
                event_type="api_key_revoke",
                user_id=user_id,
                details={"key_id": key_id},
                db_session=db_session,
            )

            return True

        except Exception as e:
            logger.error(f"API Key 吊销失败: {e}")
            return False

    # ==================== Token 吊销 ====================

    def revoke_token(
        self,
        token_jti: str,
        token_type: str = "access",
        user_id: str = "",
        client_id: str = "",
        reason: str = "",
        expires_at: datetime = None,
        revoked_by: str = "",
        db_session=None,
    ) -> bool:
        """吊销 Token"""
        if db_session is None:
            return False

        try:
            from models.oauth2_client import TokenRevocation

            revocation = TokenRevocation(
                token_jti=token_jti,
                token_type=token_type,
                client_id=client_id,
                user_id=user_id,
                revoked_by=revoked_by,
                reason=reason,
                expires_at=expires_at,
            )

            db_session.add(revocation)
            db_session.commit()

            # 缓存到内存
            exp_ts = expires_at.timestamp() if expires_at else time.time() + 86400
            self._revoked_tokens[token_jti] = exp_ts

            self._log_auth_event(
                event_type="token_revoke",
                user_id=user_id,
                client_id=client_id,
                details={"token_jti": token_jti, "token_type": token_type, "reason": reason},
                db_session=db_session,
            )

            return True

        except Exception as e:
            logger.error(f"Token 吊销失败: {e}")
            return False

    def is_token_revoked(self, token_jti: str, db_session=None) -> bool:
        """检查 Token 是否已吊销"""
        # 先查缓存
        if token_jti in self._revoked_tokens:
            if self._revoked_tokens[token_jti] > time.time():
                return True
            else:
                del self._revoked_tokens[token_jti]
                return False

        # 查数据库
        if db_session:
            try:
                from models.oauth2_client import TokenRevocation

                exists = db_session.query(TokenRevocation).filter(
                    TokenRevocation.token_jti == token_jti
                ).first()

                if exists:
                    exp_ts = exists.expires_at.timestamp() if exists.expires_at else time.time() + 86400
                    self._revoked_tokens[token_jti] = exp_ts
                    return True
            except Exception:
                pass

        return False

    # ==================== 认证审计 ====================

    def get_auth_audit_logs(
        self,
        user_id: str = None,
        event_type: str = None,
        event_status: str = None,
        start_time: str = None,
        end_time: str = None,
        page: int = 1,
        page_size: int = 50,
        db_session=None,
    ) -> Dict[str, Any]:
        """查询认证审计日志"""
        if db_session is None:
            return {"total": 0, "items": []}

        try:
            from models.oauth2_client import AuthAuditLog

            query = db_session.query(AuthAuditLog)

            if user_id:
                query = query.filter(AuthAuditLog.user_id == user_id)
            if event_type:
                query = query.filter(AuthAuditLog.event_type == event_type)
            if event_status:
                query = query.filter(AuthAuditLog.event_status == event_status)
            if start_time:
                query = query.filter(AuthAuditLog.created_at >= start_time)
            if end_time:
                query = query.filter(AuthAuditLog.created_at <= end_time)

            total = query.count()
            logs = query.order_by(AuthAuditLog.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return {
                "total": total,
                "items": [log.to_dict() for log in logs],
            }

        except Exception as e:
            logger.error(f"查询审计日志失败: {e}")
            return {"total": 0, "items": []}

    def get_auth_statistics(
        self,
        days: int = 7,
        db_session=None,
    ) -> Dict[str, Any]:
        """获取认证统计信息"""
        stats = {
            "total_logins": 0,
            "failed_logins": 0,
            "active_clients": 0,
            "active_api_keys": 0,
            "revoked_tokens": 0,
        }

        if db_session is None:
            return stats

        try:
            from models.oauth2_client import AuthAuditLog, OAuth2Client, APIKey, TokenRevocation
            from sqlalchemy import func

            since = datetime.utcnow() - timedelta(days=days)

            stats["total_logins"] = db_session.query(func.count(AuthAuditLog.id)).filter(
                AuthAuditLog.event_type.in_(["login", "client_auth", "authorization_code_exchange"]),
                AuthAuditLog.created_at >= since,
            ).scalar() or 0

            stats["failed_logins"] = db_session.query(func.count(AuthAuditLog.id)).filter(
                AuthAuditLog.event_type.in_(["login", "client_auth"]),
                AuthAuditLog.event_status == "failed",
                AuthAuditLog.created_at >= since,
            ).scalar() or 0

            stats["active_clients"] = db_session.query(func.count(OAuth2Client.id)).filter(
                OAuth2Client.status == "active",
            ).scalar() or 0

            stats["active_api_keys"] = db_session.query(func.count(APIKey.id)).filter(
                APIKey.status == "active",
            ).scalar() or 0

            stats["revoked_tokens"] = db_session.query(func.count(TokenRevocation.id)).filter(
                TokenRevocation.revoked_at >= since,
            ).scalar() or 0

        except Exception as e:
            logger.error(f"获取认证统计失败: {e}")

        return stats

    # ==================== 会话管理增强 ====================

    def force_logout_user(
        self,
        target_user_id: str,
        operator: str = "",
        reason: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """强制用户下线"""
        result = {"success": False, "sessions_terminated": 0, "message": ""}

        try:
            from services.enhanced_sso_service import get_enhanced_sso_service

            sso = get_enhanced_sso_service()
            count = sso.single_sign_out(target_user_id)

            self._log_auth_event(
                event_type="force_logout",
                user_id=target_user_id,
                details={"operator": operator, "reason": reason, "sessions": count},
                db_session=db_session,
            )

            result["success"] = True
            result["sessions_terminated"] = count
            result["message"] = f"已终止用户 {target_user_id} 的 {count} 个会话"

            logger.info(f"强制下线: user={target_user_id}, sessions={count}, by={operator}")

        except Exception as e:
            logger.error(f"强制下线失败: {e}")
            result["message"] = str(e)

        return result

    def get_active_sessions(
        self,
        user_id: str = None,
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """查询活跃会话"""
        try:
            from services.enhanced_sso_service import get_enhanced_sso_service

            sso = get_enhanced_sso_service()

            if user_id:
                sessions = [
                    s for s in sso._sessions.values()
                    if s.user_id == user_id and s.expires_at > datetime.utcnow()
                ]
            else:
                sessions = [
                    s for s in sso._sessions.values()
                    if s.expires_at > datetime.utcnow()
                ]

            return [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "provider": s.provider,
                    "login_method": s.login_method,
                    "ip_address": s.ip_address,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                    "last_activity": s.last_activity.isoformat() if s.last_activity else None,
                }
                for s in sessions
            ]

        except Exception as e:
            logger.error(f"查询会话失败: {e}")
            return []

    # ==================== 内部方法 ====================

    def _hash_secret(self, secret: str) -> str:
        """哈希密钥"""
        return hashlib.sha256(
            (secret + TOKEN_SECRET_KEY).encode()
        ).hexdigest()

    def _verify_secret(self, secret: str, secret_hash: str) -> bool:
        """验证密钥"""
        return hmac.compare_digest(
            self._hash_secret(secret),
            secret_hash,
        )

    def _verify_pkce(self, verifier: str, challenge: str, method: str) -> bool:
        """验证 PKCE"""
        if method == "S256":
            computed = hashlib.sha256(verifier.encode()).hexdigest()
            return hmac.compare_digest(computed, challenge)
        elif method == "plain":
            return verifier == challenge
        return False

    def _generate_service_token(
        self,
        client_id: str,
        scopes: List[str],
        lifetime: int,
    ) -> Dict[str, Any]:
        """生成服务 Token（JWT 形式的简化实现）"""
        jti = uuid.uuid4().hex
        payload = {
            "jti": jti,
            "sub": client_id,
            "type": "service",
            "scopes": scopes,
            "iat": int(time.time()),
            "exp": int(time.time()) + lifetime,
        }

        # 简化签名（生产环境应使用 PyJWT + RS256）
        import json
        import base64
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_input = f"{header}.{body}"
        signature = hmac.new(
            TOKEN_SECRET_KEY.encode(), sig_input.encode(), hashlib.sha256
        ).hexdigest()[:32]

        token = f"{header}.{body}.{signature}"
        return {"token": token, "expires_in": lifetime, "jti": jti}

    def _generate_user_token(
        self,
        user_id: str,
        client_id: str,
        scopes: List[str],
        lifetime: int,
    ) -> Dict[str, Any]:
        """生成用户 Token"""
        jti = uuid.uuid4().hex
        payload = {
            "jti": jti,
            "sub": user_id,
            "client_id": client_id,
            "type": "user",
            "scopes": scopes,
            "iat": int(time.time()),
            "exp": int(time.time()) + lifetime,
        }

        import json
        import base64
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_input = f"{header}.{body}"
        signature = hmac.new(
            TOKEN_SECRET_KEY.encode(), sig_input.encode(), hashlib.sha256
        ).hexdigest()[:32]

        token = f"{header}.{body}.{signature}"
        return {"token": token, "expires_in": lifetime, "jti": jti}

    def _log_auth_event(
        self,
        event_type: str,
        event_status: str = "success",
        user_id: str = "",
        user_name: str = "",
        auth_method: str = "",
        provider: str = "",
        client_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        details: Dict[str, Any] = None,
        error_message: str = "",
        db_session=None,
    ):
        """记录认证审计事件"""
        if db_session is None:
            return

        try:
            from models.oauth2_client import AuthAuditLog

            log = AuthAuditLog(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                event_type=event_type,
                event_status=event_status,
                user_id=user_id,
                user_name=user_name,
                ip_address=ip_address,
                user_agent=user_agent,
                auth_method=auth_method,
                provider=provider,
                client_id=client_id,
                details=details,
                error_message=error_message,
            )

            db_session.add(log)
            db_session.commit()

        except Exception as e:
            logger.debug(f"审计日志记录失败: {e}")

    def cleanup_expired(self, db_session=None):
        """清理过期数据"""
        now = time.time()

        # 清理过期授权码
        expired_codes = [
            code for code, data in self._auth_codes.items()
            if now - data["created_at"] > AUTH_CODE_EXPIRY_SECONDS
        ]
        for code in expired_codes:
            del self._auth_codes[code]

        # 清理过期 Token 黑名单缓存
        expired_tokens = [
            jti for jti, exp in self._revoked_tokens.items()
            if exp < now
        ]
        for jti in expired_tokens:
            del self._revoked_tokens[jti]

        logger.debug(f"清理: {len(expired_codes)} 授权码, {len(expired_tokens)} Token缓存")


# 全局实例
_unified_auth_service: Optional[UnifiedAuthService] = None


def get_unified_auth_service() -> UnifiedAuthService:
    """获取统一认证服务单例"""
    global _unified_auth_service
    if _unified_auth_service is None:
        _unified_auth_service = UnifiedAuthService()
    return _unified_auth_service
