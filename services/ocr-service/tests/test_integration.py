"""
OCR服务集成测试
测试完整的文档处理流程
"""

import pytest
import os
import tempfile
from datetime import datetime


class TestOCREndToEnd:
    """OCR服务端到端测试"""

    @pytest.fixture(scope="module")
    def client(self):
        """创建测试客户端"""
        from app import app
        from fastapi.testclient import TestClient

        return TestClient(app)

    @pytest.fixture
    def sample_invoice_file(self):
        """创建测试用发票文件"""
        # 这里应该准备实际的测试文件
        # 实际部署时需要放在 tests/fixtures/ 目录
        return None

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "OCR文档识别服务"

    def test_get_document_types(self, client):
        """测试获取文档类型列表"""
        response = client.get("/api/v1/ocr/templates/types")
        assert response.status_code == 200
        data = response.json()
        assert "document_types" in data

        doc_types = {dt["type"] for dt in data["document_types"]}
        assert "invoice" in doc_types
        assert "contract" in doc_types
        assert "purchase_order" in doc_types
        assert "delivery_note" in doc_types
        assert "quotation" in doc_types
        assert "receipt" in doc_types

    def test_create_task_missing_file(self, client):
        """测试缺少文件的错误处理"""
        response = client.post("/api/v1/ocr/tasks")
        assert response.status_code == 422  # Unprocessable Entity

    def test_get_nonexistent_task(self, client):
        """测试获取不存在的任务"""
        response = client.get("/api/v1/ocr/tasks/nonexistent-id")
        assert response.status_code == 404

    def test_list_tasks_empty(self, client):
        """测试空任务列表"""
        response = client.get("/api/v1/ocr/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "tasks" in data
        assert data["total"] == 0

    def test_get_templates_default(self, client):
        """测试获取默认模板列表"""
        response = client.get("/api/v1/ocr/templates")
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)

    def test_load_default_templates(self, client):
        """测试加载默认模板"""
        response = client.post("/api/v1/ocr/templates/load-defaults")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "count" in data


class TestCrossFieldValidatorIntegration:
    """跨字段校验集成测试"""

    def test_invoice_validation_complete(self):
        """测试发票完整校验流程"""
        from services.cross_field_validator import CrossFieldValidator

        validator = CrossFieldValidator()

        # 模拟完整的发票数据
        invoice_data = {
            "invoice_number": "12345678",
            "invoice_date": "2024-01-15",
            "buyer_name": "测试公司A",
            "seller_name": "测试公司B",
            "amount": 10000.0,
            "tax_rate": 0.13,
            "tax_amount": 1300.0,
            "total_amount": 11300.0,
            "items": [
                {"name": "商品A", "quantity": 10, "unit_price": 1000, "amount": 10000}
            ]
        }

        invoice_template = {
            "type": "invoice",
            "fields": [
                {"key": "invoice_number", "name": "发票号码", "required": True},
                {"key": "total_amount", "name": "价税合计", "required": True},
            ],
            "tables": [
                {
                    "key": "items",
                    "fields": [
                        {"key": "amount", "name": "金额"}
                    ]
                }
            ],
            "cross_field_validation": [
                {
                    "rule": "total_amount_check",
                    "fields": ["total_amount", "items"],
                    "severity": "error"
                },
                {
                    "rule": "tax_calculation_check",
                    "fields": ["amount", "tax_rate", "tax_amount"]
                }
            ]
        }

        result = validator.validate(invoice_data, invoice_template)

        # 验证通过
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_contract_validation_enhanced(self):
        """测试增强合同校验流程"""
        from services.cross_field_validator import CrossFieldValidator

        validator = CrossFieldValidator()

        contract_data = {
            "contract_number": "CT2024001",
            "contract_name": "采购合同",
            "party_a": "甲方公司",
            "party_b": "乙方公司",
            "contract_amount": 100000.0,
            "signing_date": "2024-01-01",
            "effective_date": "2024-01-05",
            "expiry_date": "2024-12-31",
            "price_details": [
                {"amount": 60000.0},
                {"amount": 40000.0}
            ],
            "payment_schedule": [
                {"percentage": 30},
                {"percentage": 40},
                {"percentage": 30}
            ]
        }

        contract_template = {
            "type": "contract",
            "cross_field_validation": [
                {
                    "rule": "amount_sum_check",
                    "fields": ["contract_amount", "price_details"]
                },
                {
                    "rule": "date_logic_check",
                    "fields": ["effective_date", "expiry_date"]
                },
                {
                    "rule": "signing_before_effective_check",
                    "fields": ["signing_date", "effective_date"]
                },
                {
                    "rule": "payment_sum_check",
                    "fields": ["payment_schedule"]
                }
            ]
        }

        result = validator.validate(contract_data, contract_template)

        # 所有校验应该通过
        assert result["valid"] is True


class TestLayoutAnalyzerIntegration:
    """布局分析集成测试"""

    def test_signature_detection_keywords(self):
        """测试基于关键词的签名检测"""
        from services.layout_analyzer import LayoutAnalyzer

        analyzer = LayoutAnalyzer()

        # 模拟包含签名关键词的文本
        text_with_signatures = """
        合同编号：CT2024001
        甲方：某某公司
        乙方：某某公司

        甲方签字：_____________
        日期：2024年1月1日

        乙方签字：_____________
        日期：2024年1月1日

        公章：
        """

        signature_areas = analyzer.detect_signature_areas(text_with_signatures)

        assert len(signature_areas) >= 2
        labels = [area["label"] for area in signature_areas]
        assert "party_a_signature" in labels or "signature" in labels

    def test_page_type_detection(self):
        """测试页面类型检测"""
        from services.layout_analyzer import LayoutAnalyzer

        analyzer = LayoutAnalyzer()

        # 封面页
        cover_text = "采购合同\n合同编号：CT2024001\n签订日期：2024年1月1日"
        page_type = analyzer._detect_page_type(cover_text)
        assert page_type in ["cover", "content"]

        # 签署页
        signature_text = "甲方签字：_____________\n乙方签字：_____________"
        page_type = analyzer._detect_page_type(signature_text)
        assert page_type in ["signature", "content"]


class TestTemplateProcessing:
    """模板处理测试"""

    @pytest.fixture
    def templates_dir(self):
        """获取模板目录"""
        import os
        return os.path.join(os.path.dirname(__file__), "..", "templates")

    def test_invoice_template_valid(self, templates_dir):
        """测试发票模板格式正确"""
        import json
        import os

        template_path = os.path.join(templates_dir, "invoice.json")
        assert os.path.exists(template_path)

        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        assert "fields" in template
        assert "tables" in template
        assert template["type"] == "invoice"

        # 检查必需字段
        required_fields = [f for f in template["fields"] if f.get("required")]
        assert len(required_fields) > 0

    def test_contract_enhanced_template_valid(self, templates_dir):
        """测试增强合同模板格式正确"""
        import json
        import os

        template_path = os.path.join(templates_dir, "contract_enhanced.json")
        assert os.path.exists(template_path)

        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        assert "fields" in template
        assert "tables" in template
        assert "layout_detection" in template
        assert "cross_field_validation" in template
        assert template["type"] == "contract"

        # 检查表格配置
        assert len(template["tables"]) == 4

        # 检查校验规则
        assert len(template["cross_field_validation"]) == 6

    def test_new_templates_exist(self, templates_dir):
        """测试新模板文件是否存在"""
        import os

        new_templates = [
            "purchase_order.json",
            "delivery_note.json",
            "quotation.json",
            "receipt.json",
            "report_enhanced.json"
        ]

        for template_name in new_templates:
            template_path = os.path.join(templates_dir, template_name)
            assert os.path.exists(template_path), f"模板文件 {template_name} 不存在"


class TestExtractionTypeSupport:
    """提取类型支持测试"""

    def test_extraction_type_enum_has_new_types(self):
        """测试提取类型枚举包含新类型"""
        from models.ocr_task import ExtractionType

        # 检查新类型存在
        assert hasattr(ExtractionType, "PURCHASE_ORDER")
        assert hasattr(ExtractionType, "DELIVERY_NOTE")
        assert hasattr(ExtractionType, "QUOTATION")
        assert hasattr(ExtractionType, "RECEIPT")

        # 检查值正确
        assert ExtractionType.PURCHASE_ORDER.value == "purchase_order"
        assert ExtractionType.DELIVERY_NOTE.value == "delivery_note"
        assert ExtractionType.QUOTATION.value == "quotation"
        assert ExtractionType.RECEIPT.value == "receipt"

    def test_ai_extractor_has_new_methods(self):
        """测试AI提取器有新方法"""
        from services.ai_extractor import AIExtractor

        extractor = AIExtractor()

        # 检查方法存在
        assert hasattr(extractor, "extract_purchase_order")
        assert hasattr(extractor, "extract_delivery_note")
        assert hasattr(extractor, "extract_quotation")
        assert hasattr(extractor, "extract_receipt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
