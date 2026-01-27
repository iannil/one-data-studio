#!/usr/bin/env python3
"""
批量测试OCR服务
用于验证不同类型文档的识别效果
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# 配置
OCR_API_URL = os.getenv("OCR_API_URL", "http://localhost:8007/api/v1/ocr")
TEST_DOCS_DIR = Path(__file__).parent.parent / "tests" / "documents"

# 测试文档配置
TEST_CONFIGS = [
    {
        "name": "发票测试",
        "type": "invoice",
        "file": "sample_invoice.pdf",
        "expected_fields": ["invoice_number", "invoice_date", "total_amount"]
    },
    {
        "name": "合同测试",
        "type": "contract",
        "file": "sample_contract.pdf",
        "expected_fields": ["contract_number", "party_a", "party_b", "contract_amount"]
    },
    {
        "name": "采购订单测试",
        "type": "purchase_order",
        "file": "sample_purchase_order.pdf",
        "expected_fields": ["order_number", "supplier_name", "total_amount"]
    },
    {
        "name": "送货单测试",
        "type": "delivery_note",
        "file": "sample_delivery_note.pdf",
        "expected_fields": ["delivery_number", "supplier_name", "receiver_name"]
    },
    {
        "name": "报价单测试",
        "type": "quotation",
        "file": "sample_quotation.pdf",
        "expected_fields": ["quotation_number", "provider_name", "total_amount"]
    },
    {
        "name": "收据测试",
        "type": "receipt",
        "file": "sample_receipt.pdf",
        "expected_fields": ["receipt_number", "amount", "payee_name"]
    },
]


class BatchTester:
    """批量测试器"""

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.results = []

    def check_service_health(self) -> bool:
        """检查服务健康状态"""
        try:
            response = requests.get(f"{self.api_url.replace('/api/v1/ocr', '')}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 服务健康检查失败: {e}")
            return False

    def upload_document(self, file_path: str, doc_type: str) -> Dict:
        """上传文档进行OCR识别"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'extraction_type': doc_type}
                response = requests.post(
                    f"{self.api_url}/tasks",
                    files=files,
                    data=data,
                    timeout=30
                )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as e:
            return {"error": str(e)}

    def get_result(self, task_id: str, max_wait: int = 60) -> Dict:
        """获取识别结果，等待处理完成"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_url}/tasks/{task_id}/result/enhanced",
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'completed':
                        return data
                    elif data.get('status') == 'failed':
                        return {"error": data.get('error_message', 'Processing failed')}
                time.sleep(2)
            except Exception as e:
                return {"error": str(e)}

        return {"error": "Timeout waiting for result"}

    def validate_result(self, result: Dict, expected_fields: List[str]) -> Dict:
        """验证识别结果"""
        validation = {
            "passed": True,
            "missing_fields": [],
            "confidence": 0.0
        }

        structured_data = result.get('structured_data', {})

        for field in expected_fields:
            if field not in structured_data or not structured_data[field]:
                validation["passed"] = False
                validation["missing_fields"].append(field)

        validation["confidence"] = result.get('confidence_score', 0.0)
        return validation

    def run_test(self, config: Dict) -> Dict:
        """运行单个测试"""
        print(f"\n🧪 测试: {config['name']}")
        print("-" * 50)

        file_path = TEST_DOCS_DIR / config['file']

        if not file_path.exists():
            print(f"⚠️  测试文件不存在: {file_path}")
            return {
                "name": config['name'],
                "status": "skipped",
                "reason": "文件不存在"
            }

        # 上传文档
        print(f"📤 上传文档: {config['file']}")
        upload_result = self.upload_document(str(file_path), config['type'])

        if 'error' in upload_result:
            print(f"❌ 上传失败: {upload_result['error']}")
            return {
                "name": config['name'],
                "status": "failed",
                "error": upload_result['error']
            }

        task_id = upload_result.get('task_id')
        print(f"✅ 任务创建成功: {task_id}")

        # 获取结果
        print(f"⏳ 等待处理完成...")
        result = self.get_result(task_id)

        if 'error' in result:
            print(f"❌ 处理失败: {result['error']}")
            return {
                "name": config['name'],
                "status": "failed",
                "error": result['error']
            }

        # 验证结果
        validation = self.validate_result(result, config['expected_fields'])

        print(f"📊 识别置信度: {validation['confidence']:.1%}")
        print(f"📋 提取字段数: {len(result.get('structured_data', {}))}")
        print(f"📈 识别表格数: {len(result.get('tables', []))}")

        if validation['passed']:
            print(f"✅ 字段验证通过")
        else:
            print(f"⚠️  缺少字段: {', '.join(validation['missing_fields'])}")

        return {
            "name": config['name'],
            "status": "passed" if validation['passed'] else "partial",
            "confidence": validation['confidence'],
            "fields_count": len(result.get('structured_data', {})),
            "tables_count": len(result.get('tables', [])),
            "missing_fields": validation['missing_fields']
        }

    def run_all_tests(self) -> List[Dict]:
        """运行所有测试"""
        print("=" * 60)
        print("OCR服务批量测试")
        print("=" * 60)
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_url}")

        # 健康检查
        if not self.check_service_health():
            print("\n❌ 服务不可用，请先启动OCR服务")
            return []

        # 运行测试
        results = []
        for config in TEST_CONFIGS:
            result = self.run_test(config)
            results.append(result)

        # 输出总结
        self.print_summary(results)
        return results

    def print_summary(self, results: List[Dict]):
        """输出测试总结"""
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)

        passed = sum(1 for r in results if r['status'] == 'passed')
        partial = sum(1 for r in results if r['status'] == 'partial')
        failed = sum(1 for r in results if r['status'] == 'failed')
        skipped = sum(1 for r in results if r['status'] == 'skipped')
        total = len(results)

        print(f"📊 总计: {total} | ✅ 通过: {passed} | ⚠️  部分通过: {partial} | ❌ 失败: {failed} | ⏭️  跳过: {skipped}")

        if passed == total:
            print("\n🎉 所有测试通过！")
        else:
            print("\n⚠️  部分测试未通过，请检查详细日志")

        # 保存结果
        report_path = Path(__file__).parent / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 测试报告已保存: {report_path}")


def main():
    """主函数"""
    tester = BatchTester(OCR_API_URL)
    results = tester.run_all_tests()

    # 返回退出码
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    sys.exit(min(failed_count, 1))


if __name__ == "__main__":
    main()
