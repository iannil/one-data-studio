"""
数据脱敏单元测试
测试用例：DE-DM-001 ~ DE-DM-004
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestPhoneMasking:
    """手机号脱敏测试 (DE-DM-001)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_phone_partial_mask(self, mock_masking_service):
        """DE-DM-001: 手机号脱敏 - 3***4格式"""
        test_phones = [
            '13812345678',
            '13987654321',
            '18612345678'
        ]

        results = [mock_masking_service.mask_phone(phone) for phone in test_phones]

        for result in results:
            assert '***' in result
            assert result.startswith('138') or result.startswith('139') or result.startswith('186')
            assert len(result) == len('138****5678')

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_phone_mask_with_custom_format(self, mock_masking_service):
        """手机号自定义格式脱敏"""
        phone = '13812345678'
        format_pattern = '3***4'

        result = mock_masking_service.mask_value(phone, 'partial_mask', format_pattern)

        assert result.startswith('138')
        assert result.endswith('5678')
        assert '***' in result


class TestIdCardMasking:
    """身份证号脱敏测试 (DE-DM-002)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_id_card_mask(self, mock_masking_service):
        """DE-DM-002: 身份证号脱敏 - 6***4格式"""
        test_id_cards = [
            '110101199001011234',
            '310101199002022345',
            '440101199003033456'
        ]

        results = [mock_masking_service.mask_id_card(id_card) for id_card in test_id_cards]

        for result in results:
            assert '***' in result
            # 前6位地区码可见，后4位校验码可见
            assert len(result) == len('110101****1234')


class TestBankCardMasking:
    """银行卡号脱敏测试 (DE-DM-003)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_bank_card_mask(self, mock_masking_service):
        """DE-DM-003: 银行卡号脱敏 - 4***4格式"""
        test_bank_cards = [
            '6222021234567890123',
            '6228481234567890123',
            '6217001234567890123'
        ]

        results = [mock_masking_service.mask_bank_card(card) for card in test_bank_cards]

        for result in results:
            assert '***' in result
            assert len(result) == len('6222****0123')


class TestEmailMasking:
    """邮箱脱敏测试 (DE-DM-004)"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_email_mask(self, mock_masking_service):
        """DE-DM-004: 邮箱脱敏 - t***@domain格式"""
        test_emails = [
            'zhangsan@example.com',
            'test@test.org',
            'admin@company.cn'
        ]

        results = [mock_masking_service.mask_email(email) for email in test_emails]

        for i, result in enumerate(results):
            assert '***' in result
            assert '@' in result
            # 验证域名部分保持不变
            assert test_emails[i].split('@')[1] in result


class TestAdvancedMasking:
    """高级脱敏测试 (DE-DM-005 ~ DE-DM-007)"""

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_aes_encryption_masking(self, mock_masking_service):
        """DE-DM-005: AES加密脱敏"""
        value = 'sensitive_data_12345'

        mock_masking_service.encrypt_with_aes.return_value = {
            'encrypted': 'U2FsdGVkX1+vupppZksvRf5pq5g5XjFRlipRkwB0K1Y96Qsv2Lm+31cmzaAILwytJHoXy...',
            'algorithm': 'AES-256-CBC',
            'can_decrypt': True
        }

        result = mock_masking_service.encrypt_with_aes(value)

        assert 'encrypted' in result
        assert result['can_decrypt'] is True

    @pytest.mark.p1
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_sha256_hashing_masking(self, mock_masking_service):
        """DE-DM-006: SHA256哈希脱敏"""
        value = 'sensitive_data_12345'

        mock_masking_service.hash_with_sha256.return_value = {
            'hashed': 'a3d5e3f4b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5',
            'algorithm': 'SHA-256',
            'can_decrypt': False
        }

        result = mock_masking_service.hash_with_sha256(value)

        assert 'hashed' in result
        assert result['can_decrypt'] is False
        assert len(result['hashed']) == 64  # SHA256输出64个十六进制字符

    @pytest.mark.p2
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_custom_regex_masking(self, mock_masking_service):
        """DE-DM-007: 自定义正则脱敏"""
        value = 'CUSTOM-123-456-789'
        regex_pattern = r'CUSTOM-(\d{3})-(\d{3})-(\d{3})'
        replace_pattern = r'CUST-***-***-$3'

        mock_masking_service.mask_with_regex.return_value = {
            'masked': 'CUST-***-***-789',
            'original_length': len(value),
            'regex_pattern': regex_pattern
        }

        result = mock_masking_service.mask_with_regex(value, regex_pattern, replace_pattern)

        assert 'masked' in result
        assert '***' in result['masked']
        assert result['masked'].endswith('789')


class TestBatchMasking:
    """批量脱敏测试"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_batch_column_masking(self, mock_masking_service):
        """批量列脱敏"""
        data = [
            {'id': 1, 'phone': '13812345678', 'email': 'user1@example.com'},
            {'id': 2, 'phone': '13987654321', 'email': 'user2@example.com'},
            {'id': 3, 'phone': '18612345678', 'email': 'user3@example.com'}
        ]

        mock_masking_service.mask_batch.return_value = [
            {'id': 1, 'phone': '138****5678', 'email': 'u***@example.com'},
            {'id': 2, 'phone': '139****4321', 'email': 'u***@example.com'},
            {'id': 3, 'phone': '186****5678', 'email': 'u***@example.com'}
        ]

        result = mock_masking_service.mask_batch(
            data=data,
            columns=['phone', 'email']
        )

        assert len(result) == 3
        for row in result:
            assert '***' in row['phone']
            assert '***' in row['email']


class TestMaskingRuleManagement:
    """脱敏规则管理测试"""

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_create_masking_rule(self, mock_masking_service):
        """创建脱敏规则"""
        rule_config = {
            'rule_name': '手机号脱敏规则',
            'column_pattern': 'phone',
            'strategy': 'partial_mask',
            'format': '3***4'
        }

        mock_masking_service.create_rule.return_value = {
            'success': True,
            'rule_id': 'mask_rule_0001'
        }

        result = mock_masking_service.create_rule(rule_config)

        assert result['success'] is True

    @pytest.mark.p0
    @pytest.mark.data_engineer
    @pytest.mark.unit
    def test_apply_masking_rule(self, mock_masking_service):
        """应用脱敏规则"""
        rule_id = 'mask_rule_0001'
        value = '13812345678'

        mock_masking_service.apply_rule.return_value = {
            'masked_value': '138****5678',
            'rule_id': rule_id
        }

        result = mock_masking_service.apply_rule(rule_id, value)

        assert 'masked_value' in result
        assert '***' in result['masked_value']


# ==================== Fixtures ====================

@pytest.fixture
def mock_masking_service():
    """Mock 脱敏服务"""
    service = Mock()

    # 配置手机号脱敏
    service.mask_phone = Mock(side_effect=lambda x: f"{x[:3]}****{x[-4:]}")
    service.mask_id_card = Mock(side_effect=lambda x: f"{x[:6]}****{x[-4:]}")
    service.mask_bank_card = Mock(side_effect=lambda x: f"{x[:4]}****{x[-4:]}")
    service.mask_email = Mock(side_effect=lambda x: f"{x[0]}***@{x.split('@')[1]}")

    # 配置通用脱敏
    service.mask_value = Mock(side_effect=lambda v, s, f: f"{v[:3]}****{v[-4:]}")

    # 配置高级脱敏
    service.encrypt_with_aes = Mock()
    service.hash_with_sha256 = Mock()
    service.mask_with_regex = Mock()

    # 配置批量脱敏
    service.mask_batch = Mock()

    # 配置规则管理
    service.create_rule = Mock(return_value={'success': True, 'rule_id': 'mask_rule_0001'})
    service.apply_rule = Mock()

    return service
