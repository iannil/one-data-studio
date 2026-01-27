"""
跨字段校验服务单元测试
"""

import pytest
from services.cross_field_validator import CrossFieldValidator


class TestCrossFieldValidator:
    """跨字段校验器测试"""

    @pytest.fixture
    def validator(self):
        """创建校验器实例"""
        return CrossFieldValidator()

    def test_validate_amount_sum(self, validator):
        """测试金额合计校验"""
        data = {
            "contract_amount": 10000.00,
            "price_details": [
                {"amount": 5000.00},
                {"amount": 3000.00},
                {"amount": 2000.00}
            ]
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "amount_sum_check",
                    "description": "合同金额应等于价格明细表合计金额",
                    "fields": ["contract_amount", "price_details"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is True

    def test_validate_amount_sum_mismatch(self, validator):
        """测试金额合计校验 - 不匹配"""
        data = {
            "contract_amount": 12000.00,
            "price_details": [
                {"amount": 5000.00},
                {"amount": 3000.00},
                {"amount": 2000.00}
            ]
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "amount_sum_check",
                    "description": "合同金额应等于价格明细表合计金额",
                    "fields": ["contract_amount", "price_details"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_date_logic_valid(self, validator):
        """测试日期逻辑校验 - 有效"""
        data = {
            "effective_date": "2024-01-01",
            "expiry_date": "2024-12-31"
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "date_logic_check",
                    "description": "生效日期应早于或等于截止日期",
                    "fields": ["effective_date", "expiry_date"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is True

    def test_validate_date_logic_invalid(self, validator):
        """测试日期逻辑校验 - 无效"""
        data = {
            "effective_date": "2024-12-31",
            "expiry_date": "2024-01-01"
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "date_logic_check",
                    "description": "生效日期应早于或等于截止日期",
                    "fields": ["effective_date", "expiry_date"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is False

    def test_validate_payment_sum_valid(self, validator):
        """测试付款计划合计校验 - 有效"""
        data = {
            "payment_schedule": [
                {"percentage": 30},
                {"percentage": 40},
                {"percentage": 30}
            ]
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "payment_sum_check",
                    "description": "付款计划合计比例应为100%",
                    "fields": ["payment_schedule"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is True

    def test_validate_payment_sum_invalid(self, validator):
        """测试付款计划合计校验 - 无效"""
        data = {
            "payment_schedule": [
                {"percentage": 30},
                {"percentage": 40},
                {"percentage": 20}
            ]
        }

        template = {
            "cross_field_validation": [
                {
                    "rule": "payment_sum_check",
                    "description": "付款计划合计比例应为100%",
                    "fields": ["payment_schedule"]
                }
            ]
        }

        result = validator.validate(data, template)
        assert result["valid"] is False

    def test_validate_template_completeness(self, validator):
        """测试模板完整性校验"""
        data = {
            "contract_number": "CT2024001",
            "party_a": "甲方公司",
            "contract_amount": 100000
        }

        template = {
            "fields": [
                {"key": "contract_number", "name": "合同编号", "required": True},
                {"key": "party_a", "name": "甲方", "required": True},
                {"key": "party_b", "name": "乙方", "required": True},
                {"key": "contract_amount", "name": "合同金额", "required": False}
            ]
        }

        result = validator.validate_template_completeness(data, template)
        assert result["valid"] is False
        assert len(result["missing_required"]) == 1
        assert result["missing_required"][0]["key"] == "party_b"

    def test_parse_number(self, validator):
        """测试数字解析"""
        assert validator._parse_number("1,234.56") == 1234.56
        assert validator._parse_number("¥1,234.56") == 1234.56
        assert validator._parse_number("50%") == 0.5
        assert validator._parse_number(1234) == 1234.0
        assert validator._parse_number("invalid") is None

    def test_parse_date(self, validator):
        """测试日期解析"""
        assert validator._parse_date("2024-01-01") is not None
        assert validator._parse_date("2024/01/01") is not None
        assert validator._parse_date("2024年01月01日") is not None
        assert validator._parse_date("invalid") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
