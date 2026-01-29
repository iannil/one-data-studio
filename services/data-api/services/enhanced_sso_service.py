"""
增强型统一 SSO 服务
支持多种登录方式：OAuth2/OIDC、短信验证码、扫码登录、第三方授权
"""

import logging
import secrets
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SSOProvider:
    """SSO 提供商配置"""

    def __init__(
        self,
        provider_id: str,
        provider_type: str,
        name: str,
        enabled: bool = True,
        config: Dict = None,
        icon: str = "",
        color: str = "",
    ):
        self.provider_id = provider_id
        self.provider_type = provider_type  # oidc, saml, cas, oauth2, sms, qrcode, wechat, dingtalk
        self.name = name
        self.enabled = enabled
        self.config = config or {}
        self.icon = icon
        self.color = color
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "name": self.name,
            "enabled": self.enabled,
            "config": self._sanitize_config(),
            "icon": self.icon,
            "color": self.color,
        }

    def _sanitize_config(self) -> Dict:
        """脱敏配置"""
        safe_config = self.config.copy()
        sensitive_keys = ["client_secret", "api_secret", "private_key", "signing_key"]
        for key in sensitive_keys:
            if key in safe_config:
                safe_config[key] = "******"
        return safe_config


class UserSession:
    """用户会话"""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        provider: str,
        login_method: str,
        created_at: datetime = None,
        expires_at: datetime = None,
        last_activity: datetime = None,
        ip_address: str = "",
        user_agent: str = "",
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.provider = provider
        self.login_method = login_method
        self.created_at = created_at or datetime.now()
        self.expires_at = expires_at or (datetime.now() + timedelta(hours=8))
        self.last_activity = last_activity or datetime.now()
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "login_method": self.login_method,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
        }

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def refresh(self, extend_hours: int = 8):
        """刷新会话过期时间"""
        self.expires_at = datetime.now() + timedelta(hours=extend_hours)
        self.last_activity = datetime.now()


class VerificationCode:
    """验证码"""

    def __init__(
        self,
        code: str,
        phone: str,
        purpose: str = "login",
        expires_in: int = 300,
    ):
        self.code = code
        self.phone = phone
        self.purpose = purpose
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(seconds=expires_in)
        self.used = False
        self.attempts = 0
        self.max_attempts = 3

    def is_valid(self) -> bool:
        """检查验证码是否有效"""
        return (
            not self.used
            and self.attempts < self.max_attempts
            and datetime.now() < self.expires_at
        )

    def verify(self, input_code: str) -> bool:
        """验证输入的验证码"""
        self.attempts += 1
        if self.is_valid() and self.code == input_code:
            self.used = True
            return True
        return False


class QRCodeSession:
    """扫码登录会话"""

    def __init__(
        self,
        session_id: str,
        provider: str = "qrcode",
        expires_in: int = 120,
    ):
        self.session_id = session_id
        self.provider = provider
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(seconds=expires_in)
        self.status = "pending"  # pending, scanned, confirmed, expired, cancelled
        self.user_id: Optional[str] = None
        self.qr_data: str = self._generate_qr_data()

    def _generate_qr_data(self) -> str:
        """生成二维码数据"""
        return json.dumps({
            "sid": self.session_id,
            "ts": int(self.created_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
        })

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "qr_data": self.qr_data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class EnhancedSSOService:
    """增强型统一 SSO 服务"""

    def __init__(self):
        # 存储配置（生产环境应使用数据库）
        self._providers: Dict[str, SSOProvider] = {}
        self._sessions: Dict[str, UserSession] = {}
        self._verification_codes: Dict[str, VerificationCode] = {}
        self._qrcode_sessions: Dict[str, QRCodeSession] = {}

        # 初始化默认提供商
        self._init_default_providers()

    def _init_default_providers(self):
        """初始化默认 SSO 提供商"""
        # Keycloak (OIDC)
        self._providers["keycloak"] = SSOProvider(
            provider_id="keycloak",
            provider_type="oidc",
            name="Keycloak",
            enabled=True,
            config={
                "issuer_url": "",
                "client_id": "",
                "client_secret": "",
                "scope": "openid profile email",
            },
            icon="🔐",
            color="#1890ff",
        )

        # CAS
        self._providers["cas"] = SSOProvider(
            provider_id="cas",
            provider_type="cas",
            name="CAS 单点登录",
            enabled=False,
            config={
                "cas_url": "",
                "cas_version": "3.0",
            },
            icon="🎫",
            color="#52c41a",
        )

        # MaxKey
        self._providers["maxkey"] = SSOProvider(
            provider_id="maxkey",
            provider_type="oauth2",
            name="MaxKey",
            enabled=False,
            config={
                "issuer_url": "",
                "client_id": "",
                "client_secret": "",
            },
            icon="🔑",
            color="#722ed1",
        )

        # 短信验证码登录
        self._providers["sms"] = SSOProvider(
            provider_id="sms",
            provider_type="sms",
            name="短信验证码",
            enabled=False,
            config={
                "provider": "aliyun",  # aliyun, tencent
                "access_key": "",
                "access_secret": "",
                "sign_name": "",
                "template_code": "",
            },
            icon="📱",
            color="#fa8c16",
        )

        # 扫码登录
        self._providers["qrcode"] = SSOProvider(
            provider_id="qrcode",
            provider_type="qrcode",
            name="扫码登录",
            enabled=True,
            config={},
            icon="📱",
            color="#13c2c2",
        )

        # 企业微信
        self._providers["wechat_work"] = SSOProvider(
            provider_id="wechat_work",
            provider_type="oauth2",
            name="企业微信",
            enabled=False,
            config={
                "corp_id": "",
                "agent_id": "",
                "secret": "",
            },
            icon="💼",
            color="#00D768",
        )

        # 钉钉
        self._providers["dingtalk"] = SSOProvider(
            provider_id="dingtalk",
            provider_type="oauth2",
            name="钉钉",
            enabled=False,
            config={
                "app_id": "",
                "app_secret": "",
            },
            icon="📌",
            color="#0089FF",
        )

    # ==================== 提供商管理 ====================

    def list_providers(self, include_disabled: bool = False) -> List[Dict]:
        """列出所有 SSO 提供商"""
        providers = list(self._providers.values())
        if not include_disabled:
            providers = [p for p in providers if p.enabled]
        return [p.to_dict() for p in providers]

    def get_provider(self, provider_id: str) -> Optional[Dict]:
        """获取指定提供商配置"""
        provider = self._providers.get(provider_id)
        return provider.to_dict() if provider else None

    def add_provider(self, provider_config: Dict) -> Dict:
        """添加新的 SSO 提供商"""
        provider_id = provider_config.get("provider_id") or f"custom_{secrets.token_hex(4)}"
        provider = SSOProvider(
            provider_id=provider_id,
            provider_type=provider_config.get("provider_type", "oauth2"),
            name=provider_config.get("name", "自定义提供商"),
            enabled=provider_config.get("enabled", True),
            config=provider_config.get("config", {}),
            icon=provider_config.get("icon", "🔗"),
            color=provider_config.get("color", "#666"),
        )
        self._providers[provider_id] = provider
        return provider.to_dict()

    def update_provider(self, provider_id: str, updates: Dict) -> Optional[Dict]:
        """更新提供商配置"""
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        if "enabled" in updates:
            provider.enabled = updates["enabled"]
        if "config" in updates:
            provider.config.update(updates["config"])
        if "name" in updates:
            provider.name = updates["name"]

        return provider.to_dict()

    def delete_provider(self, provider_id: str) -> bool:
        """删除提供商"""
        if provider_id in self._providers:
            del self._providers[provider_id]
            return True
        return False

    # ==================== 短信验证码登录 ====================

    def send_sms_code(self, phone: str, purpose: str = "login") -> Dict:
        """
        发送短信验证码

        Args:
            phone: 手机号
            purpose: 用途 (login, register, reset_password)

        Returns:
            发送结果
        """
        provider = self._providers.get("sms")
        if not provider or not provider.enabled:
            return {
                "success": False,
                "message": "短信登录未启用",
            }

        # 生成6位验证码
        code = f"{secrets.randbelow(1000000):06d}"

        # 存储验证码
        verification = VerificationCode(code, phone, purpose)
        # 清理该手机号的旧验证码
        self._verification_codes = {
            k: v for k, v in self._verification_codes.items()
            if v.phone != phone or v.is_valid()
        }
        self._verification_codes[f"{phone}:{purpose}"] = verification

        # 这里应该调用短信服务商 API
        # 模拟发送
        logger.info(f"发送短信验证码到 {phone}: {code}")

        return {
            "success": True,
            "message": "验证码已发送",
            "expires_in": 300,  # 5分钟
        }

    def verify_sms_code(self, phone: str, code: str, purpose: str = "login") -> Dict:
        """验证短信验证码"""
        key = f"{phone}:{purpose}"
        verification = self._verification_codes.get(key)

        if not verification:
            return {
                "success": False,
                "message": "验证码不存在或已过期",
            }

        if verification.verify(code):
            return {
                "success": True,
                "message": "验证成功",
            }

        remaining_attempts = verification.max_attempts - verification.attempts
        return {
            "success": False,
            "message": f"验证码错误，剩余尝试次数: {remaining_attempts}",
        }

    # ==================== 扫码登录 ====================

    def create_qrcode_session(self) -> Dict:
        """创建扫码登录会话"""
        session_id = secrets.token_urlsafe(32)
        qrcode_session = QRCodeSession(session_id)
        self._qrcode_sessions[session_id] = qrcode_session

        return {
            "session_id": session_id,
            "qr_data": qrcode_session.qr_data,
            "expires_at": qrcode_session.expires_at.isoformat(),
        }

    def get_qrcode_status(self, session_id: str) -> Dict:
        """获取二维码状态"""
        session = self._qrcode_sessions.get(session_id)

        if not session or session.is_expired():
            return {
                "status": "expired",
                "session_id": session_id,
            }

        return session.to_dict()

    def scan_qrcode(self, session_id: str, user_id: str) -> Dict:
        """
        用户扫描二维码

        Args:
            session_id: 二维码会话ID
            user_id: 扫码用户的ID

        Returns:
            扫码结果
        """
        session = self._qrcode_sessions.get(session_id)

        if not session or session.is_expired():
            return {
                "success": False,
                "message": "二维码已过期",
            }

        if session.status != "pending":
            return {
                "success": False,
                "message": "二维码已被使用",
            }

        session.status = "scanned"
        session.user_id = user_id

        return {
            "success": True,
            "message": "扫码成功，请在手机上确认",
            "status": "scanned",
        }

    def confirm_qrcode_login(self, session_id: str) -> Dict:
        """
        用户确认登录

        Args:
            session_id: 二维码会话ID

        Returns:
            确认结果
        """
        session = self._qrcode_sessions.get(session_id)

        if not session or session.is_expired():
            return {
                "success": False,
                "message": "二维码已过期",
            }

        if session.status != "scanned":
            return {
                "success": False,
                "message": "请先扫描二维码",
            }

        session.status = "confirmed"

        # 创建用户会话
        user_session = UserSession(
            session_id=secrets.token_urlsafe(32),
            user_id=session.user_id,
            provider="qrcode",
            login_method="qrcode",
        )
        self._sessions[user_session.session_id] = user_session

        return {
            "success": True,
            "message": "登录成功",
            "session_id": user_session.session_id,
            "user_id": session.user_id,
        }

    def cancel_qrcode_login(self, session_id: str) -> bool:
        """取消扫码登录"""
        session = self._qrcode_sessions.get(session_id)
        if session:
            session.status = "cancelled"
            return True
        return False

    # ==================== 会话管理 ====================

    def create_session(
        self,
        user_id: str,
        provider: str,
        login_method: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Dict:
        """创建用户会话"""
        session_id = secrets.token_urlsafe(32)
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            provider=provider,
            login_method=login_method,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._sessions[session_id] = session
        return session.to_dict()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            return session.to_dict()
        return None

    def refresh_session(self, session_id: str) -> Optional[Dict]:
        """刷新会话"""
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            session.refresh()
            return session.to_dict()
        return None

    def destroy_session(self, session_id: str) -> bool:
        """销毁会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def destroy_user_sessions(self, user_id: str) -> int:
        """销毁用户的所有会话（单点登出）"""
        to_remove = [
            sid for sid, session in self._sessions.items()
            if session.user_id == user_id
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def list_user_sessions(self, user_id: str) -> List[Dict]:
        """列出用户的所有活跃会话"""
        return [
            session.to_dict()
            for session in self._sessions.values()
            if session.user_id == user_id and not session.is_expired()
        ]

    # ==================== 单点登出 ====================

    def logout(self, session_id: str, global_logout: bool = False) -> Dict:
        """
        用户登出

        Args:
            session_id: 会话ID
            global_logout: 是否全局登出（销毁所有设备的会话）

        Returns:
            登出结果
        """
        session = self._sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "message": "会话不存在",
            }

        user_id = session.user_id

        if global_logout:
            # 单点登出：销毁所有会话
            count = self.destroy_user_sessions(user_id)
            return {
                "success": True,
                "message": f"已从 {count} 个设备登出",
                "global": True,
            }
        else:
            # 单设备登出
            self.destroy_session(session_id)
            return {
                "success": True,
                "message": "登出成功",
                "global": False,
            }

    # ==================== 第三方授权登录 ====================

    def get_oauth_url(
        self,
        provider_id: str,
        redirect_uri: str,
        state: str = "",
    ) -> Dict:
        """
        获取 OAuth 授权 URL

        Args:
            provider_id: 提供商ID
            redirect_uri: 回调地址
            state: 状态参数

        Returns:
            授权 URL
        """
        provider = self._providers.get(provider_id)
        if not provider or not provider.enabled:
            return {
                "success": False,
                "message": "提供商未启用",
            }

        # 根据不同提供商生成授权 URL
        if provider_id == "wechat_work":
            # 企业微信 OAuth2
            config = provider.config
            auth_url = (
                f"https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
                f"?appid={config.get('corp_id')}"
                f"&agentid={config.get('agent_id')}"
                f"&redirect_uri={redirect_uri}"
                f"&state={state}"
            )
            return {
                "success": True,
                "auth_url": auth_url,
                "provider": provider_id,
            }

        elif provider_id == "dingtalk":
            # 钉钉 OAuth2
            config = provider.config
            auth_url = (
                f"https://login.dingtalk.com/oauth2/auth"
                f"?redirect_uri={redirect_uri}"
                f"&response_type=code"
                f"&client_id={config.get('app_id')}"
                f"&state={state}"
                f"&scope=openid corpid"
                f"&prompt=consent"
            )
            return {
                "success": True,
                "auth_url": auth_url,
                "provider": provider_id,
            }

        return {
            "success": False,
            "message": "不支持的提供商",
        }

    def handle_oauth_callback(
        self,
        provider_id: str,
        code: str,
        state: str,
    ) -> Dict:
        """
        处理 OAuth 回调

        Args:
            provider_id: 提供商ID
            code: 授权码
            state: 状态参数

        Returns:
            用户信息和会话
        """
        # 这里应该调用提供商的 API 获取用户信息
        # 简化处理

        # 创建会话
        session = self.create_session(
            user_id=f"{provider_id}_user_{secrets.token_hex(4)}",
            provider=provider_id,
            login_method="oauth2",
        )

        return {
            "success": True,
            "user_id": session["user_id"],
            "session_id": session["session_id"],
            "provider": provider_id,
        }

    # ==================== 清理 ====================

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired()
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def cleanup_expired_codes(self) -> int:
        """清理过期验证码"""
        expired = [
            key for key, code in self._verification_codes.items()
            if not code.is_valid()
        ]
        for key in expired:
            del self._verification_codes[key]
        return len(expired)

    def cleanup_expired_qrcodes(self) -> int:
        """清理过期二维码"""
        expired = [
            sid for sid, session in self._qrcode_sessions.items()
            if session.is_expired() or session.status in ["confirmed", "cancelled", "expired"]
        ]
        for sid in expired:
            del self._qrcode_sessions[sid]
        return len(expired)


# 创建全局服务实例
_enhanced_sso_service = None


def get_enhanced_sso_service() -> EnhancedSSOService:
    """获取增强型 SSO 服务实例"""
    global _enhanced_sso_service
    if _enhanced_sso_service is None:
        _enhanced_sso_service = EnhancedSSOService()
    return _enhanced_sso_service
