"""
数据加密服务模块
Sprint 29: 企业安全强化

提供:
- AES-256-GCM 字段级加密
- 密钥管理和轮换支持
- 加密数据标识和版本化
"""

import os
import base64
import hashlib
import secrets
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    AESGCM = None
    PBKDF2HMAC = None

logger = logging.getLogger(__name__)

# 加密数据前缀标识
ENCRYPTED_PREFIX = "ENC$v1$"
KEY_VERSION_SEPARATOR = "$"


@dataclass
class EncryptionConfig:
    """加密配置"""
    # 主加密密钥（32字节用于AES-256）
    master_key: str = ""

    # 密钥派生盐
    key_salt: str = ""

    # 当前密钥版本
    key_version: int = 1

    # 历史密钥（用于解密旧数据）
    previous_keys: Dict[int, str] = None

    # 是否启用加密
    enabled: bool = True

    def __post_init__(self):
        if self.previous_keys is None:
            self.previous_keys = {}

        # 从环境变量加载
        if not self.master_key:
            self.master_key = os.getenv('ENCRYPTION_MASTER_KEY', '')
        if not self.key_salt:
            self.key_salt = os.getenv('ENCRYPTION_KEY_SALT', 'one-data-studio-salt')

        env_version = os.getenv('ENCRYPTION_KEY_VERSION')
        if env_version:
            self.key_version = int(env_version)

        # 加载历史密钥
        prev_keys_env = os.getenv('ENCRYPTION_PREVIOUS_KEYS', '')
        if prev_keys_env:
            for item in prev_keys_env.split(','):
                if ':' in item:
                    version, key = item.split(':', 1)
                    try:
                        self.previous_keys[int(version)] = key.strip()
                    except ValueError:
                        logger.warning(f"Invalid previous key version: {version}")


class EncryptionService:
    """
    AES-256-GCM 加密服务

    使用 256 位 AES-GCM 进行认证加密，提供:
    - 机密性：数据加密
    - 完整性：GCM 认证标签
    - 防重放：每次加密使用随机 IV

    加密数据格式:
    ENC$v1${key_version}${iv_base64}${ciphertext_base64}
    """

    # IV/Nonce 长度（12字节是GCM推荐值）
    IV_LENGTH = 12

    # 密钥长度（32字节 = 256位）
    KEY_LENGTH = 32

    def __init__(self, config: Optional[EncryptionConfig] = None):
        self.config = config or EncryptionConfig()
        self._keys: Dict[int, bytes] = {}

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography library not available, encryption disabled")
            self.config.enabled = False
            return

        if self.config.enabled and not self.config.master_key:
            logger.warning("ENCRYPTION_MASTER_KEY not set, encryption disabled")
            self.config.enabled = False
            return

        # 派生当前密钥
        if self.config.enabled:
            self._keys[self.config.key_version] = self._derive_key(
                self.config.master_key,
                self.config.key_version
            )

            # 派生历史密钥
            for version, key in self.config.previous_keys.items():
                self._keys[version] = self._derive_key(key, version)

    def _derive_key(self, master_key: str, version: int) -> bytes:
        """
        使用 PBKDF2 从主密钥派生加密密钥

        Args:
            master_key: 主密钥字符串
            version: 密钥版本号

        Returns:
            32字节派生密钥
        """
        salt = f"{self.config.key_salt}-v{version}".encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=100000,
        )

        return kdf.derive(master_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 要加密的明文

        Returns:
            加密后的密文字符串（Base64编码，带版本前缀）
        """
        if not self.config.enabled or not plaintext:
            return plaintext

        if self._is_encrypted(plaintext):
            # 已经加密过了
            return plaintext

        try:
            key = self._keys.get(self.config.key_version)
            if not key:
                raise ValueError(f"Key version {self.config.key_version} not found")

            # 生成随机 IV
            iv = secrets.token_bytes(self.IV_LENGTH)

            # 加密
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)

            # 编码为 Base64
            iv_b64 = base64.b64encode(iv).decode('ascii')
            ciphertext_b64 = base64.b64encode(ciphertext).decode('ascii')

            # 返回格式化的加密字符串
            return f"{ENCRYPTED_PREFIX}{self.config.key_version}{KEY_VERSION_SEPARATOR}{iv_b64}{KEY_VERSION_SEPARATOR}{ciphertext_b64}"

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串

        Args:
            ciphertext: 加密的密文字符串

        Returns:
            解密后的明文
        """
        if not self.config.enabled or not ciphertext:
            return ciphertext

        if not self._is_encrypted(ciphertext):
            # 未加密的数据，直接返回
            return ciphertext

        try:
            # 解析加密数据
            version, iv, encrypted_data = self._parse_encrypted_string(ciphertext)

            key = self._keys.get(version)
            if not key:
                raise ValueError(f"Key version {version} not found")

            # 解密
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, encrypted_data, None)

            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")

    def _is_encrypted(self, data: str) -> bool:
        """检查数据是否已加密"""
        return data.startswith(ENCRYPTED_PREFIX)

    def _parse_encrypted_string(self, encrypted: str) -> Tuple[int, bytes, bytes]:
        """
        解析加密字符串

        Args:
            encrypted: 加密的字符串

        Returns:
            (版本号, IV字节, 密文字节)
        """
        if not encrypted.startswith(ENCRYPTED_PREFIX):
            raise ValueError("Invalid encrypted string format")

        # 移除前缀
        data = encrypted[len(ENCRYPTED_PREFIX):]

        # 分割各部分
        parts = data.split(KEY_VERSION_SEPARATOR)
        if len(parts) != 3:
            raise ValueError("Invalid encrypted string format")

        version = int(parts[0])
        iv = base64.b64decode(parts[1])
        ciphertext = base64.b64decode(parts[2])

        return version, iv, ciphertext

    def rotate_key(self, new_master_key: str) -> int:
        """
        轮换加密密钥

        Args:
            new_master_key: 新的主密钥

        Returns:
            新的密钥版本号
        """
        # 保存当前密钥到历史
        old_version = self.config.key_version
        old_key = self.config.master_key
        self.config.previous_keys[old_version] = old_key

        # 设置新密钥
        new_version = old_version + 1
        self.config.key_version = new_version
        self.config.master_key = new_master_key

        # 派生新密钥
        self._keys[new_version] = self._derive_key(new_master_key, new_version)

        logger.info(f"Encryption key rotated from version {old_version} to {new_version}")

        return new_version

    def re_encrypt(self, ciphertext: str) -> str:
        """
        使用当前密钥重新加密数据

        用于密钥轮换后迁移旧数据

        Args:
            ciphertext: 使用旧密钥加密的数据

        Returns:
            使用新密钥加密的数据
        """
        plaintext = self.decrypt(ciphertext)
        return self.encrypt(plaintext)

    def get_key_version(self, ciphertext: str) -> Optional[int]:
        """
        获取加密数据使用的密钥版本

        Args:
            ciphertext: 加密的字符串

        Returns:
            密钥版本号，如果未加密则返回 None
        """
        if not self._is_encrypted(ciphertext):
            return None

        try:
            version, _, _ = self._parse_encrypted_string(ciphertext)
            return version
        except Exception as e:
            logger.debug(f"Failed to detect encryption version: {e}")
            return None

    @property
    def is_enabled(self) -> bool:
        """检查加密是否启用"""
        return self.config.enabled


class EncryptionError(Exception):
    """加密相关异常"""
    pass


# 全局加密服务实例
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """获取全局加密服务实例"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt(plaintext: str) -> str:
    """加密字符串（便捷函数）"""
    return get_encryption_service().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """解密字符串（便捷函数）"""
    return get_encryption_service().decrypt(ciphertext)


def is_encrypted(data: str) -> bool:
    """检查数据是否已加密（便捷函数）"""
    return get_encryption_service()._is_encrypted(data)


# 字段加密装饰器（用于 SQLAlchemy 模型）
class EncryptedField:
    """
    加密字段描述符

    用于 SQLAlchemy 模型自动加密/解密字段

    Usage:
        class User(Base):
            __tablename__ = 'users'

            _api_key = Column('api_key', String(500))
            api_key = EncryptedField('_api_key')
    """

    def __init__(self, storage_attr: str):
        self.storage_attr = storage_attr

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        encrypted_value = getattr(obj, self.storage_attr, None)
        if encrypted_value is None:
            return None

        return decrypt(encrypted_value)

    def __set__(self, obj, value):
        if value is None:
            setattr(obj, self.storage_attr, None)
        else:
            setattr(obj, self.storage_attr, encrypt(value))


def generate_encryption_key() -> str:
    """
    生成新的加密主密钥

    Returns:
        Base64编码的随机密钥
    """
    return base64.b64encode(secrets.token_bytes(32)).decode('ascii')
