"""
OCR服务Python客户端SDK使用示例
"""

from ocr_client import OCRClient, DocumentType, extract_document
from pathlib import Path


def example_basic_usage():
    """基础使用示例"""
    print("=== 基础使用示例 ===\n")

    # 创建客户端
    client = OCRClient("http://localhost:8007")

    # 健康检查
    health = client.health_check()
    print(f"服务状态: {health}")

    # 提取文档
    result = client.extract("sample_invoice.pdf", DocumentType.INVOICE)

    print(f"任务ID: {result.task_id}")
    print(f"文档类型: {result.document_type}")
    print(f"置信度: {result.confidence_score:.1%}")

    # 获取字段
    print(f"发票号码: {result.get_field('invoice_number')}")
    print(f"发票金额: {result.get_field('total_amount')}")

    # 检查是否有效
    if result.is_valid():
        print("✅ 提取结果有效")
    else:
        print("⚠️ 提取结果需要人工审核")

    client.close()


def example_auto_detect():
    """自动检测文档类型"""
    print("\n=== 自动检测文档类型 ===\n")

    client = OCRClient("http://localhost:8007")

    # 自动检测类型
    detection = client.detect_type("unknown_document.pdf")
    print(f"检测到的类型: {detection['type']}")
    print(f"置信度: {detection['confidence']:.1%}")

    # 使用检测到的类型提取
    result = client.extract("unknown_document.pdf", detection['type'])

    client.close()


def example_batch_processing():
    """批量处理示例"""
    print("\n=== 批量处理示例 ===\n")

    client = OCRClient("http://localhost:8007")

    # 批量处理多个文件
    files = [
        "documents/invoice1.pdf",
        "documents/invoice2.pdf",
        "documents/contract1.pdf"
    ]

    results = client.extract_batch(files, DocumentType.AUTO)

    for i, result in enumerate(results):
        print(f"\n文件 {i+1}:")
        print(f"  状态: {result.status}")
        print(f"  置信度: {result.confidence_score:.1%}")
        if result.error_message:
            print(f"  错误: {result.error_message}")

    client.close()


def example_custom_template():
    """使用自定义模板"""
    print("\n=== 自定义模板示例 ===\n")

    client = OCRClient("http://localhost:8007")

    # 列出可用模板
    templates = client.list_templates(template_type="invoice")
    print(f"找到 {len(templates)} 个发票模板")

    # 使用特定模板
    if templates:
        template_id = templates[0].id
        result = client.extract(
            "invoice.pdf",
            template_id=template_id
        )
        print(f"使用模板: {templates[0].name}")

    client.close()


def example_async_processing():
    """异步处理示例（不等待结果）"""
    print("\n=== 异步处理示例 ===\n")

    client = OCRClient("http://localhost:8007")

    # 提交任务，不等待结果
    task_id = client.extract("large_document.pdf", wait_for_result=False)
    print(f"任务已提交: {task_id}")

    # 稍后获取结果
    # result = client.get_result(task_id)

    client.close()


def example_validation():
    """结果验证示例"""
    print("\n=== 结果验证示例 ===\n")

    client = OCRClient("http://localhost:8007")

    result = client.extract("contract.pdf", DocumentType.CONTRACT)

    # 跨字段校验
    validation = result.cross_field_validation
    print(f"跨字段校验: {'通过' if validation.get('valid') else '失败'}")

    if not validation.get('valid'):
        for error in validation.get('errors', []):
            print(f"  错误: {error['description']}")

    # 完整性检查
    completeness = result.completeness
    print(f"完整率: {completeness.get('completeness_rate', 0):.0f}%")

    if completeness.get('missing_required'):
        print(f"缺少必填字段: {completeness['missing_required']}")

    client.close()


def example_table_extraction():
    """表格提取示例"""
    print("\n=== 表格提取示例 ===\n")

    client = OCRClient("http://localhost:8007")

    result = client.extract("invoice_with_table.pdf", DocumentType.INVOICE)

    print(f"识别到 {len(result.tables)} 个表格")

    for i, table in enumerate(result.tables):
        print(f"\n表格 {i+1} (第{table['page_number']}页):")
        print(f"  表头: {', '.join(table['headers'])}")
        print(f"  行数: {len(table['rows'])}")
        print(f"  置信度: {table['confidence']:.1%}")

    client.close()


def example_layout_info():
    """布局分析示例"""
    print("\n=== 布局分析示例 ===\n")

    client = OCRClient("http://localhost:8007")

    result = client.extract("contract.pdf", DocumentType.CONTRACT)

    layout = result.layout_info

    # 签名区域
    if layout.get('has_signatures'):
        print(f"检测到 {len(layout['signature_regions'])} 个签名区域")
        for sig in layout['signature_regions']:
            print(f"  - {sig['label']} (第{sig['page']}页)")

    # 印章区域
    if layout.get('has_seals'):
        print(f"检测到 {len(layout['seal_regions'])} 个印章区域")
        for seal in layout['seal_regions']:
            print(f"  - {seal['label']} (第{seal['page']}页)")

    client.close()


def example_convenience_function():
    """便捷函数示例"""
    print("\n=== 便捷函数示例 ===\n")

    # 一行代码完成提取
    result = extract_document("invoice.pdf")

    print(f"提取完成，置信度: {result.confidence_score:.1%}")


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===\n")

    from ocr_client import (
        OCRClientError,
        ServiceUnavailableError,
        TaskFailedError
    )

    try:
        client = OCRClient("http://localhost:8007")
        result = client.extract("corrupted.pdf")
        client.close()

    except ServiceUnavailableError as e:
        print(f"服务不可用: {e}")

    except TaskFailedError as e:
        print(f"任务失败: {e}")

    except OCRClientError as e:
        print(f"客户端错误: {e}")


def main():
    """运行所有示例"""
    examples = [
        ("基础使用", example_basic_usage),
        ("自动检测", example_auto_detect),
        ("批量处理", example_batch_processing),
        ("自定义模板", example_custom_template),
        ("异步处理", example_async_processing),
        ("结果验证", example_validation),
        ("表格提取", example_table_extraction),
        ("布局分析", example_layout_info),
        ("便捷函数", example_convenience_function),
        ("错误处理", example_error_handling),
    ]

    print("OCR服务Python客户端SDK - 使用示例")
    print("=" * 50)

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n示例执行出错: {e}")

    print("\n" + "=" * 50)
    print("示例执行完毕")


if __name__ == "__main__":
    main()
