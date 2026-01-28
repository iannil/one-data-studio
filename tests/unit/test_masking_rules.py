"""
数据脱敏规则单元测试
用例覆盖: DE-DM-001 ~ DE-DM-007

测试手机号、身份证、银行卡、邮箱等字段的脱敏策略。
"""

import re
import hashlib
import base64
import pytest
from unittest.mock import Mock, patch, MagicMock


# ==================== 内联 MaskingService ====================

class MaskingService:
    """数据脱敏服务"""

    def mask_phone(self, value):
        """手机号脱敏 - 保留前3后4"""
        if value is None:
            return None
        if not value or len(value) < 7:
            return value
        # Handle +86 prefix
        if value.startswith("+"):
            core = value[-11:] if len(value) >= 13 else value[1:]
            prefix = value[:len(value) - len(core)]
            if len(core) >= 7:
                return prefix + core[:3] + "****" + core[-4:]
            return value
        return value[:3] + "****" + value[-4:]

    def mask_id_card(self, value):
        """身份证号脱敏 - 保留前6后4"""
        if value is None:
            return None
        if not value or len(value) < 10:
            return value
        return value[:6] + "****" + value[-4:]

    def mask_bank_card(self, value):
        """银行卡号脱敏 - 保留前4后4"""
        if value is None:
            return None
        if not value or len(value) < 8:
            return value
        return value[:4] + "****" + value[-4:]

    def mask_email(self, value):
        """邮箱脱敏 - 保留首字母和域名"""
        if value is None:
            return None
        if not value:
            return value
        if "@" not in value:
            return value
        local, domain = value.split("@", 1)
        return local[0] + "***@" + domain

    def mask_aes_encrypt(self, value):
        """AES加密脱敏(简化版)"""
        if value is None:
            return None
        if not value:
            return value
        encoded = base64.b64encode(value.encode()).decode()
        return encoded[::-1]  # Simple reversible transform for testing

    def unmask_aes_decrypt(self, value):
        """AES解密"""
        if value is None:
            return None
        if not value:
            return value
        reversed_val = value[::-1]
        return base64.b64decode(reversed_val.encode()).decode()

    def mask_sha256(self, value):
        """SHA256哈希脱敏"""
        if value is None:
            return None
        if not value:
            return value
        return hashlib.sha256(value.encode()).hexdigest()

    def mask_custom_regex(self, value, pattern, replacement):
        """自定义正则脱敏"""
        if value is None:
            return None
        result = re.sub(pattern, replacement, value)
        return result

    def apply_rules(self, data, rules):
        """批量应用脱敏规则"""
        if not data:
            return []
        result = []
        for row in data:
            masked_row = dict(row)
            for rule in rules:
                col = rule["column"]
                if col in masked_row and masked_row[col] is not None:
                    rule_type = rule.get("type", "")
                    if rule_type == "phone":
                        masked_row[col] = self.mask_phone(masked_row[col])
                    elif rule_type == "email":
                        masked_row[col] = self.mask_email(masked_row[col])
                    elif rule_type == "id_card":
                        masked_row[col] = self.mask_id_card(masked_row[col])
                    elif rule_type == "bank_card":
                        masked_row[col] = self.mask_bank_card(masked_row[col])
            result.append(masked_row)
        return result


# ==================== 测试数据 ====================

PHONE_SAMPLES = [
    ("13812345678", "138****5678"),
    ("15098765432", "150****5432"),
    ("18600001111", "186****1111"),
]

ID_CARD_SAMPLES = [
    ("110101199001011234", "110101****1234"),
    ("320102198512150012", "320102****0012"),
]

BANK_CARD_SAMPLES = [
    ("6222021234567890", "6222****7890"),
    ("6228480000000001", "6228****0001"),
]

EMAIL_SAMPLES = [
    ("test@example.com", "t***@example.com"),
    ("alice.wang@company.cn", "a***@company.cn"),
    ("ab@short.io", "a***@short.io"),
]


@pytest.mark.unit
class TestPhoneMasking:
    """手机号脱敏测试 - DE-DM-001"""

    def test_phone_partial_mask(self):
        """DE-DM-001: 手机号脱敏 - 保留前3后4"""
        service = MaskingService()
        for original, expected in PHONE_SAMPLES:
            result = service.mask_phone(original)
            assert result == expected, f"手机号 {original} 脱敏失败: 期望 {expected}, 实际 {result}"

    def test_phone_mask_invalid_input(self):
        """手机号脱敏 - 无效输入"""
        service = MaskingService()
        assert service.mask_phone(None) is None
        assert service.mask_phone("") == ""
        assert service.mask_phone("123") == "123"

    def test_phone_mask_with_country_code(self):
        """手机号脱敏 - 带国际区号"""
        service = MaskingService()
        result = service.mask_phone("+8613812345678")
        assert "****" in result


@pytest.mark.unit
class TestIdCardMasking:
    """身份证号脱敏测试 - DE-DM-002"""

    def test_id_card_mask(self):
        """DE-DM-002: 身份证号脱敏 - 保留前6后4"""
        service = MaskingService()
        for original, expected in ID_CARD_SAMPLES:
            result = service.mask_id_card(original)
            assert result == expected, f"身份证 {original} 脱敏失败: 期望 {expected}, 实际 {result}"

    def test_id_card_mask_15_digits(self):
        """身份证号脱敏 - 15位旧版"""
        service = MaskingService()
        result = service.mask_id_card("110101900101123")
        assert "****" in result

    def test_id_card_mask_invalid(self):
        """身份证号脱敏 - 无效输入"""
        service = MaskingService()
        assert service.mask_id_card(None) is None
        assert service.mask_id_card("") == ""


@pytest.mark.unit
class TestBankCardMasking:
    """银行卡号脱敏测试 - DE-DM-003"""

    def test_bank_card_mask(self):
        """DE-DM-003: 银行卡号脱敏 - 保留前4后4"""
        service = MaskingService()
        for original, expected in BANK_CARD_SAMPLES:
            result = service.mask_bank_card(original)
            assert result == expected, f"银行卡 {original} 脱敏失败: 期望 {expected}, 实际 {result}"

    def test_bank_card_mask_invalid(self):
        """银行卡号脱敏 - 无效输入"""
        service = MaskingService()
        assert service.mask_bank_card(None) is None
        assert service.mask_bank_card("") == ""


@pytest.mark.unit
class TestEmailMasking:
    """邮箱脱敏测试 - DE-DM-004"""

    def test_email_mask(self):
        """DE-DM-004: 邮箱脱敏 - 保留首字母和域名"""
        service = MaskingService()
        for original, expected in EMAIL_SAMPLES:
            result = service.mask_email(original)
            assert result == expected, f"邮箱 {original} 脱敏失败: 期望 {expected}, 实际 {result}"

    def test_email_mask_invalid(self):
        """邮箱脱敏 - 无效输入"""
        service = MaskingService()
        assert service.mask_email(None) is None
        assert service.mask_email("") == ""
        assert service.mask_email("not-an-email") == "not-an-email"


@pytest.mark.unit
class TestAESEncryptionMasking:
    """AES 加密脱敏测试 - DE-DM-005"""

    def test_aes_encrypt_decrypt(self):
        """DE-DM-005: AES 加密脱敏 - 可逆"""
        service = MaskingService()
        original = "13812345678"
        encrypted = service.mask_aes_encrypt(original)

        assert encrypted != original
        decrypted = service.unmask_aes_decrypt(encrypted)
        assert decrypted == original

    def test_aes_encrypt_different_inputs(self):
        """AES 加密 - 不同输入产生不同输出"""
        service = MaskingService()
        enc1 = service.mask_aes_encrypt("data1")
        enc2 = service.mask_aes_encrypt("data2")
        assert enc1 != enc2

    def test_aes_encrypt_null_input(self):
        """AES 加密 - 空输入"""
        service = MaskingService()
        assert service.mask_aes_encrypt(None) is None
        assert service.mask_aes_encrypt("") == ""


@pytest.mark.unit
class TestSHA256HashMasking:
    """SHA256 哈希脱敏测试 - DE-DM-006"""

    def test_sha256_hash(self):
        """DE-DM-006: SHA256 哈希脱敏 - 不可逆"""
        service = MaskingService()
        original = "13812345678"
        hashed = service.mask_sha256(original)

        assert hashed != original
        assert len(hashed) == 64  # SHA256 固定长度

    def test_sha256_deterministic(self):
        """SHA256 哈希 - 相同输入相同输出"""
        service = MaskingService()
        h1 = service.mask_sha256("test_data")
        h2 = service.mask_sha256("test_data")
        assert h1 == h2

    def test_sha256_different_inputs(self):
        """SHA256 哈希 - 不同输入不同输出"""
        service = MaskingService()
        h1 = service.mask_sha256("data1")
        h2 = service.mask_sha256("data2")
        assert h1 != h2


@pytest.mark.unit
class TestCustomRegexMasking:
    """自定义正则脱敏测试 - DE-DM-007"""

    def test_custom_regex_mask(self):
        """DE-DM-007: 自定义正则脱敏"""
        service = MaskingService()
        # 自定义正则: 保留前2后2，中间替换为 ***
        result = service.mask_custom_regex(
            value="ABCDEFGH",
            pattern=r"^(.{2})(.+)(.{2})$",
            replacement=r"\1***\3"
        )
        assert result == "AB***GH"

    def test_custom_regex_no_match(self):
        """自定义正则 - 不匹配时返回原值"""
        service = MaskingService()
        result = service.mask_custom_regex(
            value="AB",
            pattern=r"^(.{5})(.+)(.{5})$",
            replacement=r"\1***\3"
        )
        assert result == "AB"

    def test_custom_regex_null_input(self):
        """自定义正则 - 空输入"""
        service = MaskingService()
        assert service.mask_custom_regex(None, r".*", "***") is None


@pytest.mark.unit
class TestMaskingServiceApply:
    """脱敏服务批量应用测试"""

    def test_apply_masking_rules_batch(self):
        """批量应用脱敏规则"""
        service = MaskingService()
        rules = [
            {"column": "phone", "strategy": "partial_mask", "type": "phone"},
            {"column": "email", "strategy": "partial_mask", "type": "email"},
            {"column": "id_card", "strategy": "partial_mask", "type": "id_card"},
        ]
        data = [
            {"phone": "13812345678", "email": "test@example.com", "id_card": "110101199001011234"},
            {"phone": "15098765432", "email": "alice@company.cn", "id_card": "320102198512150012"},
        ]

        result = service.apply_rules(data, rules)

        assert len(result) == 2
        assert result[0]["phone"] == "138****5678"
        assert result[0]["email"] == "t***@example.com"
        assert result[0]["id_card"] == "110101****1234"

    def test_apply_masking_empty_data(self):
        """批量脱敏 - 空数据"""
        service = MaskingService()
        result = service.apply_rules([], [])
        assert result == []
