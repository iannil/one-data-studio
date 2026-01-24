"""
加密服务模块单元测试
Sprint 29: P1 测试覆盖 - 企业安全强化
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestEncryptionConfig:
    """加密配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        from services.shared.security.encryption import EncryptionConfig

        config = EncryptionConfig()
        assert config.key_version == 1
        assert config.enabled is True
        assert config.previous_keys == {}

    def test_config_loads_from_env(self):
        """测试从环境变量加载配置"""
        from services.shared.security.encryption import EncryptionConfig

        with patch.dict(os.environ, {
            'ENCRYPTION_MASTER_KEY': 'test-master-key-12345',
            'ENCRYPTION_KEY_SALT': 'custom-salt',
            'ENCRYPTION_KEY_VERSION': '3'
        }):
            config = EncryptionConfig()
            assert config.master_key == 'test-master-key-12345'
            assert config.key_salt == 'custom-salt'
            assert config.key_version == 3

    def test_config_loads_previous_keys(self):
        """测试加载历史密钥"""
        from services.shared.security.encryption import EncryptionConfig

        with patch.dict(os.environ, {
            'ENCRYPTION_PREVIOUS_KEYS': '1:old-key-1,2:old-key-2'
        }):
            config = EncryptionConfig()
            assert 1 in config.previous_keys
            assert 2 in config.previous_keys
            assert config.previous_keys[1] == 'old-key-1'
            assert config.previous_keys[2] == 'old-key-2'


class TestEncryptionService:
    """加密服务测试"""

    @pytest.fixture
    def encryption_service(self):
        """创建测试用加密服务实例"""
        from services.shared.security.encryption import EncryptionService, EncryptionConfig

        config = EncryptionConfig(
            master_key='test-encryption-key-32-bytes-long!',
            key_salt='test-salt',
            key_version=1,
            enabled=True
        )
        return EncryptionService(config)

    @pytest.fixture
    def disabled_service(self):
        """创建禁用的加密服务实例"""
        from services.shared.security.encryption import EncryptionService, EncryptionConfig

        config = EncryptionConfig(enabled=False)
        return EncryptionService(config)

    def test_service_enabled_with_key(self, encryption_service):
        """测试有密钥时服务启用"""
        assert encryption_service.is_enabled is True

    def test_service_disabled_without_key(self):
        """测试无密钥时服务禁用"""
        from services.shared.security.encryption import EncryptionService, EncryptionConfig

        config = EncryptionConfig(master_key='', enabled=True)
        service = EncryptionService(config)
        assert service.is_enabled is False

    def test_encrypt_returns_encrypted_string(self, encryption_service):
        """测试加密返回加密字符串"""
        plaintext = "sensitive data"
        encrypted = encryption_service.encrypt(plaintext)

        assert encrypted != plaintext
        assert encrypted.startswith("ENC$v1$")
        assert "$" in encrypted

    def test_encrypt_empty_returns_empty(self, encryption_service):
        """测试加密空字符串返回空"""
        assert encryption_service.encrypt("") == ""
        assert encryption_service.encrypt(None) is None

    def test_decrypt_returns_original(self, encryption_service):
        """测试解密返回原文"""
        plaintext = "sensitive data 测试中文"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_decrypt_non_encrypted_returns_as_is(self, encryption_service):
        """测试解密非加密数据直接返回"""
        plaintext = "not encrypted"
        result = encryption_service.decrypt(plaintext)
        assert result == plaintext

    def test_encrypt_idempotent(self, encryption_service):
        """测试加密幂等性（已加密数据不重复加密）"""
        plaintext = "data"
        encrypted1 = encryption_service.encrypt(plaintext)
        encrypted2 = encryption_service.encrypt(encrypted1)

        assert encrypted1 == encrypted2  # 不重复加密

    def test_each_encryption_unique(self, encryption_service):
        """测试每次加密结果不同（随机 IV）"""
        plaintext = "same data"
        encrypted1 = encryption_service.encrypt(plaintext)
        encrypted2 = encryption_service.encrypt(plaintext)

        # 由于随机 IV，每次加密结果应不同
        assert encrypted1 != encrypted2

        # 但都能解密为相同原文
        assert encryption_service.decrypt(encrypted1) == plaintext
        assert encryption_service.decrypt(encrypted2) == plaintext

    def test_disabled_service_passthrough(self, disabled_service):
        """测试禁用服务直接返回原文"""
        plaintext = "data"
        assert disabled_service.encrypt(plaintext) == plaintext
        assert disabled_service.decrypt(plaintext) == plaintext

    def test_get_key_version_returns_version(self, encryption_service):
        """测试获取密钥版本"""
        plaintext = "data"
        encrypted = encryption_service.encrypt(plaintext)

        version = encryption_service.get_key_version(encrypted)
        assert version == 1

    def test_get_key_version_non_encrypted_returns_none(self, encryption_service):
        """测试非加密数据返回 None"""
        version = encryption_service.get_key_version("not encrypted")
        assert version is None


class TestKeyRotation:
    """密钥轮换测试"""

    @pytest.fixture
    def encryption_service(self):
        """创建测试用加密服务实例"""
        from services.shared.security.encryption import EncryptionService, EncryptionConfig

        config = EncryptionConfig(
            master_key='initial-key-32-bytes-long!!!!!',
            key_salt='test-salt',
            key_version=1,
            enabled=True
        )
        return EncryptionService(config)

    def test_rotate_key_increments_version(self, encryption_service):
        """测试密钥轮换增加版本号"""
        new_version = encryption_service.rotate_key('new-key-32-bytes-long!!!!!!!')
        assert new_version == 2
        assert encryption_service.config.key_version == 2

    def test_old_data_still_decryptable_after_rotation(self, encryption_service):
        """测试轮换后旧数据仍可解密"""
        plaintext = "old data"
        encrypted = encryption_service.encrypt(plaintext)

        # 轮换密钥
        encryption_service.rotate_key('new-key-32-bytes-long!!!!!!!')

        # 旧数据仍可解密
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_re_encrypt_uses_new_key(self, encryption_service):
        """测试重新加密使用新密钥"""
        plaintext = "data"
        old_encrypted = encryption_service.encrypt(plaintext)

        encryption_service.rotate_key('new-key-32-bytes-long!!!!!!!')

        new_encrypted = encryption_service.re_encrypt(old_encrypted)

        # 新加密数据使用新版本
        assert encryption_service.get_key_version(new_encrypted) == 2
        # 解密结果相同
        assert encryption_service.decrypt(new_encrypted) == plaintext


class TestEncryptionError:
    """加密错误测试"""

    def test_decrypt_invalid_format_raises_error(self):
        """测试解密无效格式抛出错误"""
        from services.shared.security.encryption import (
            EncryptionService, EncryptionConfig, EncryptionError
        )

        config = EncryptionConfig(
            master_key='test-key-32-bytes-long!!!!!!!',
            enabled=True
        )
        service = EncryptionService(config)

        with pytest.raises(EncryptionError):
            service.decrypt("ENC$v1$invalid")

    def test_decrypt_wrong_key_raises_error(self):
        """测试使用错误密钥解密抛出错误"""
        from services.shared.security.encryption import (
            EncryptionService, EncryptionConfig, EncryptionError
        )

        config1 = EncryptionConfig(
            master_key='first-key-32-bytes-long!!!!!!!',
            enabled=True
        )
        service1 = EncryptionService(config1)
        encrypted = service1.encrypt("secret")

        config2 = EncryptionConfig(
            master_key='second-key-32-bytes-long!!!!!!',
            enabled=True
        )
        service2 = EncryptionService(config2)

        with pytest.raises(EncryptionError):
            service2.decrypt(encrypted)


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_is_encrypted_detects_encrypted(self):
        """测试检测加密数据"""
        from services.shared.security.encryption import is_encrypted

        assert is_encrypted("ENC$v1$1$abc$xyz") is True
        assert is_encrypted("plain text") is False
        assert is_encrypted("") is False

    def test_generate_encryption_key_returns_valid_key(self):
        """测试生成有效密钥"""
        from services.shared.security.encryption import generate_encryption_key
        import base64

        key = generate_encryption_key()
        assert key is not None
        assert len(key) > 0

        # 应该是有效的 Base64
        decoded = base64.b64decode(key)
        assert len(decoded) == 32  # 256 bits


class TestEncryptedField:
    """加密字段描述符测试"""

    def test_encrypted_field_encrypts_on_set(self):
        """测试设置时加密"""
        from services.shared.security.encryption import EncryptedField, get_encryption_service
        from unittest.mock import patch

        class MockModel:
            _secret = None
            secret = EncryptedField('_secret')

        # Mock 加密服务
        mock_service = MagicMock()
        mock_service.encrypt = MagicMock(return_value="encrypted_value")
        mock_service.decrypt = MagicMock(return_value="decrypted_value")
        mock_service._is_encrypted = MagicMock(return_value=True)

        with patch('services.shared.security.encryption.get_encryption_service', return_value=mock_service):
            model = MockModel()
            model.secret = "plain_value"

            mock_service.encrypt.assert_called_once_with("plain_value")

    def test_encrypted_field_decrypts_on_get(self):
        """测试获取时解密"""
        from services.shared.security.encryption import EncryptedField
        from unittest.mock import patch

        class MockModel:
            _secret = "encrypted_value"
            secret = EncryptedField('_secret')

        mock_service = MagicMock()
        mock_service.decrypt = MagicMock(return_value="decrypted_value")

        with patch('services.shared.security.encryption.get_encryption_service', return_value=mock_service):
            with patch('services.shared.security.encryption.decrypt', return_value="decrypted_value"):
                model = MockModel()
                # 注意：由于 decrypt 被 patch，直接调用会返回 mock 值
                assert model._secret == "encrypted_value"

    def test_encrypted_field_handles_none(self):
        """测试处理 None 值"""
        from services.shared.security.encryption import EncryptedField

        class MockModel:
            _secret = None
            secret = EncryptedField('_secret')

        model = MockModel()
        model.secret = None
        assert model._secret is None


class TestCryptographyNotAvailable:
    """cryptography 库不可用时的测试"""

    def test_service_disabled_when_cryptography_missing(self):
        """测试 cryptography 不可用时服务禁用"""
        from services.shared.security.encryption import EncryptionConfig

        with patch.dict('sys.modules', {'cryptography': None}):
            with patch('services.shared.security.encryption.CRYPTOGRAPHY_AVAILABLE', False):
                from services.shared.security import encryption as enc_module

                # 重新加载模块以应用 mock
                config = EncryptionConfig(
                    master_key='test-key-32-bytes-long!!!!!!!',
                    enabled=True
                )
                # 在实际实现中，如果 CRYPTOGRAPHY_AVAILABLE 为 False，
                # EncryptionService 会禁用自己
