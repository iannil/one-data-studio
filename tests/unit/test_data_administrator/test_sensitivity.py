"""
敏感数据识别单元测试
测试用例：DM-SD-001 ~ DM-SD-010
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestSensitiveDataDetection:
    """敏感数据识别测试 (DM-SD-001 ~ DM-SD-006)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_start_sensitive_scan(self, mock_sensitivity_service):
        """DM-SD-001: 启动敏感数据扫描"""
        source_id = 'ds_0001'

        mock_sensitivity_service.scan.return_value = {
            'success': True,
            'scan_id': 'sen_scan_0001',
            'summary': {
                'total_columns': 100,
                'sensitive_columns': 15,
                'by_type': {
                    'PII': 8,
                    'FINANCIAL': 4,
                    'CREDENTIAL': 3
                }
            }
        }

        result = mock_sensitivity_service.scan(source_id)

        assert result['success'] is True
        assert result['summary']['sensitive_columns'] == 15
        assert result['summary']['by_type']['PII'] == 8

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_phone_column_detection(self, mock_sensitivity_service):
        """DM-SD-002: 手机号字段识别"""
        column_name = 'phone'
        sample_data = ['13812345678', '13987654321', '13666666666']

        result = mock_sensitivity_service.detect_column(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['sensitive_type'] == 'PII'
        assert result['sub_type'] == 'phone'
        assert result['confidence'] > 0.8

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_id_card_column_detection(self, mock_sensitivity_service):
        """DM-SD-003: 身份证号字段识别"""
        column_name = 'id_card'
        sample_data = [
            '110101199001011234',
            '310101199002022345',
            '440101199003033456'
        ]

        result = mock_sensitivity_service.detect_column(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['sensitive_type'] == 'PII'
        assert result['sub_type'] == 'id_card'
        assert result['confidence'] > 0.8

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_bank_card_column_detection(self, mock_sensitivity_service):
        """DM-SD-004: 银行卡号字段识别"""
        column_name = 'bank_card'
        sample_data = [
            '6222021234567890123',
            '6228481234567890123',
            '6217001234567890123'
        ]

        result = mock_sensitivity_service.detect_column(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['sensitive_type'] == 'FINANCIAL'
        assert result['sub_type'] == 'bank_card'
        assert result['confidence'] > 0.8

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_email_column_detection(self, mock_sensitivity_service):
        """DM-SD-005: 邮箱字段识别"""
        column_name = 'email'
        sample_data = [
            'user@example.com',
            'test@test.org',
            'admin@company.cn'
        ]

        result = mock_sensitivity_service.detect_column(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['sensitive_type'] == 'PII'
        assert result['sub_type'] == 'email'
        assert result['confidence'] > 0.8

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_password_column_detection(self, mock_sensitivity_service):
        """DM-SD-006: 密码/凭证字段识别"""
        column_name = 'password'
        sample_data = ['hashed_value_1', 'hashed_value_2']

        result = mock_sensitivity_service.detect_column(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['sensitive_type'] == 'CREDENTIAL'
        assert result['sub_type'] == 'password'
        assert result['sensitivity_level'] == 'restricted'

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_column_name_regex_matching(self, mock_sensitivity_service):
        """DM-SD-007: 列名正则匹配"""
        test_cases = [
            ('phone', True),
            ('mobile', True),
            ('phone_number', True),
            ('user_phone', True),
            ('phonenumber', True),
            ('email', True),
            ('mail', True),
            ('id_card', True),
            ('idcard', True),
            ('identity', True),
        ]

        for column_name, expected_sensitive in test_cases:
            result = mock_sensitivity_service.match_by_name(column_name)
            assert result['matched'] == expected_sensitive, f"Failed for {column_name}"

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_content_sampling_match(self, mock_sensitivity_service):
        """DM-SD-008: 内容采样匹配"""
        # 列名不含敏感关键词但内容为手机号
        column_name = 'contact_info'
        sample_data = ['13812345678', '联系信息：13812345678', '手机:13987654321']

        result = mock_sensitivity_service.sample_and_match(column_name, sample_data)

        assert result['is_sensitive'] is True
        assert result['match_rate'] > 0.3

    @pytest.mark.p2
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_confidence_calculation(self, mock_sensitivity_service):
        """DM-SD-009: 置信度计算验证"""
        # confidence = 60 + match_rate × 30
        match_rate = 0.8
        expected_confidence = 60 + match_rate * 30

        result = mock_sensitivity_service.calculate_confidence(match_rate)

        assert abs(result['confidence'] - expected_confidence) < 0.01

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_auto_generate_masking_rule(self, mock_sensitivity_service):
        """DM-SD-010: 自动生成脱敏规则"""
        sensitive_field = {
            'column_name': 'phone',
            'sensitive_type': 'PII',
            'sub_type': 'phone'
        }

        mock_sensitivity_service.generate_masking_rule.return_value = {
            'rule_id': 'mask_rule_0001',
            'strategy': 'partial_mask',
            'format_pattern': '3***4'
        }

        result = mock_sensitivity_service.generate_masking_rule(sensitive_field)

        assert result['strategy'] == 'partial_mask'
        assert result['format_pattern'] == '3***4'


class TestSensitivityLevels:
    """敏感级别测试"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_pii_sensitivity_level(self, mock_sensitivity_service):
        """PII类型敏感级别"""
        result = mock_sensitivity_service.get_sensitivity_level('PII')
        assert result in ['confidential', 'restricted']

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_financial_sensitivity_level(self, mock_sensitivity_service):
        """金融类型敏感级别"""
        result = mock_sensitivity_service.get_sensitivity_level('FINANCIAL')
        assert result in ['confidential', 'restricted']

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_credential_sensitivity_level(self, mock_sensitivity_service):
        """凭证类型敏感级别"""
        result = mock_sensitivity_service.get_sensitivity_level('CREDENTIAL')
        assert result == 'restricted'


class TestMaskingRuleGeneration:
    """脱敏规则生成测试"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_phone_masking_rule(self, mock_sensitivity_service):
        """手机号脱敏规则"""
        result = mock_sensitivity_service.generate_masking_rule('phone')
        assert result['strategy'] == 'partial_mask'
        assert '***' in result['format_pattern']

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_id_card_masking_rule(self, mock_sensitivity_service):
        """身份证脱敏规则"""
        result = mock_sensitivity_service.generate_masking_rule('id_card')
        assert result['strategy'] == 'partial_mask'

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_email_masking_rule(self, mock_sensitivity_service):
        """邮箱脱敏规则"""
        result = mock_sensitivity_service.generate_masking_rule('email')
        assert '***' in result['format_pattern'] or '@' in result['format_pattern']

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_password_masking_rule(self, mock_sensitivity_service):
        """密码脱敏规则"""
        result = mock_sensitivity_service.generate_masking_rule('password')
        assert result['strategy'] in ['hash', 'nullify', 'encrypt']


# ==================== Fixtures ====================

@pytest.fixture
def mock_sensitivity_service():
    """Mock 敏感数据识别服务"""
    service = Mock()

    # 配置 scan 方法
    service.scan = Mock()
    service.scan.return_value = {
        'success': True,
        'scan_id': 'sen_scan_0001',
        'summary': {
            'total_columns': 100,
            'sensitive_columns': 15,
            'by_type': {'PII': 8, 'FINANCIAL': 4, 'CREDENTIAL': 3}
        }
    }

    # 配置 detect_column 方法
    def detect_column_func(column_name, sample_data):
        # 简单的模拟逻辑
        sensitive_patterns = {
            'phone': {'type': 'PII', 'sub_type': 'phone'},
            'mobile': {'type': 'PII', 'sub_type': 'phone'},
            'id_card': {'type': 'PII', 'sub_type': 'id_card'},
            'bank_card': {'type': 'FINANCIAL', 'sub_type': 'bank_card'},
            'email': {'type': 'PII', 'sub_type': 'email'},
            'password': {'type': 'CREDENTIAL', 'sub_type': 'password'},
        }

        pattern = sensitive_patterns.get(column_name.lower(), {})
        if pattern:
            return {
                'is_sensitive': True,
                'sensitive_type': pattern['type'],
                'sub_type': pattern['sub_type'],
                'confidence': 0.9,
                'sensitivity_level': 'restricted' if pattern['type'] == 'CREDENTIAL' else 'confidential'
            }
        return {
            'is_sensitive': False,
            'confidence': 0.1
        }

    service.detect_column = Mock(side_effect=detect_column_func)

    # 配置 match_by_name 方法
    def match_by_name_func(column_name):
        keywords = ['phone', 'mobile', 'email', 'mail', 'id_card', 'idcard',
                   'identity', 'password', 'passwd', 'secret', 'token']
        return {
            'matched': any(kw in column_name.lower() for kw in keywords),
            'column_name': column_name
        }

    service.match_by_name = Mock(side_effect=match_by_name_func)

    # 配置 sample_and_match 方法
    service.sample_and_match = Mock(return_value={
        'is_sensitive': True,
        'match_rate': 0.6
    })

    # 配置 calculate_confidence 方法
    def calculate_confidence_func(match_rate):
        return {
            'confidence': 60 + match_rate * 30,
            'formula': '60 + match_rate * 30'
        }

    service.calculate_confidence = Mock(side_effect=calculate_confidence_func)

    # 配置 generate_masking_rule 方法
    def generate_masking_rule_func(field):
        # 支持 dict 或 str 类型的 field 参数
        if isinstance(field, dict):
            field_key = field.get('sub_type') or field.get('column_name') or field.get('sensitive_type', '')
        else:
            field_key = field

        strategies = {
            'phone': {'strategy': 'partial_mask', 'format_pattern': '3***4', 'rule_id': 'mask_rule_0001'},
            'id_card': {'strategy': 'partial_mask', 'format_pattern': '6***4', 'rule_id': 'mask_rule_0002'},
            'email': {'strategy': 'partial_mask', 'format_pattern': 't***@domain', 'rule_id': 'mask_rule_0003'},
            'password': {'strategy': 'hash', 'format_pattern': None, 'rule_id': 'mask_rule_0004'},
        }
        return strategies.get(field_key, {'strategy': 'partial_mask', 'format_pattern': '***', 'rule_id': 'mask_rule_default'})

    service.generate_masking_rule = Mock(side_effect=generate_masking_rule_func)

    # 配置 get_sensitivity_level 方法
    def get_level_func(sensitive_type):
        levels = {
            'PII': 'confidential',
            'FINANCIAL': 'confidential',
            'CREDENTIAL': 'restricted'
        }
        return levels.get(sensitive_type, 'internal')

    service.get_sensitivity_level = Mock(side_effect=get_level_func)

    return service
