"""
OCR服务实施验证脚本
检查所有新增和修改的文件是否存在且格式正确
"""

import os
import json
import sys
from pathlib import Path


def check_file_exists(filepath, description=""):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - 文件不存在")
        return False


def check_json_format(filepath, description=""):
    """检查JSON文件格式是否正确"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ {description}: {filepath}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ {description}: {filepath} - JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ {description}: {filepath} - 错误: {e}")
        return False


def check_python_syntax(filepath, description=""):
    """检查Python文件语法是否正确"""
    try:
        import ast
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print(f"✅ {description}: {filepath}")
        return True
    except SyntaxError as e:
        print(f"❌ {description}: {filepath} - 语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ {description}: {filepath} - 错误: {e}")
        return False


def check_import_statement(filepath, module_name):
    """检查Python文件是否包含特定导入"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if f"from {module_name}" in content or f"import {module_name}" in content:
            print(f"✅ 导入检查: {module_name} 在 {filepath.name}")
            return True
        else:
            print(f"❌ 导入检查: {module_name} 未在 {filepath.name} 中找到")
            return False
    except Exception as e:
        print(f"❌ 导入检查错误: {e}")
        return False


def main():
    """主验证流程"""
    # 脚本位于 services/ocr-service/scripts/
    # 需要向上一级找到ocr-service目录，向上三级找到项目根目录
    script_dir = Path(__file__).parent.resolve()
    ocr_service_dir = script_dir.parent  # services/ocr-service/
    base_dir = script_dir.parent.parent.parent  # 项目根目录/

    print("=" * 60)
    print("OCR服务实施验证")
    print("=" * 60)

    all_passed = True

    # Phase 1: Docker配置
    print("\n📦 Phase 1: Docker部署配置")
    print("-" * 40)
    all_passed &= check_file_exists(
        ocr_service_dir / "Dockerfile", "Dockerfile"
    )
    all_passed &= check_file_exists(
        base_dir / "deploy" / "local" / "docker-compose.yml",
        "docker-compose.yml"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "migrations" / "init.sql",
        "数据库初始化脚本"
    )

    # Phase 2: 增强合同模板
    print("\n📄 Phase 2: 增强合同模板")
    print("-" * 40)
    all_passed &= check_json_format(
        ocr_service_dir / "templates" / "contract_enhanced.json",
        "增强合同模板"
    )

    # Phase 3: 新文档类型模板
    print("\n📋 Phase 3: 新文档类型模板")
    print("-" * 40)
    new_templates = [
        ("purchase_order.json", "采购订单模板"),
        ("delivery_note.json", "送货单模板"),
        ("quotation.json", "报价单模板"),
        ("receipt.json", "收据模板"),
        ("report_enhanced.json", "增强报告模板")
    ]
    for filename, desc in new_templates:
        all_passed &= check_json_format(
            ocr_service_dir / "templates" / filename,
            desc
        )

    # Phase 4: 布局分析服务
    print("\n🔍 Phase 4: 布局分析服务")
    print("-" * 40)
    all_passed &= check_file_exists(
        ocr_service_dir / "services" / "layout_analyzer.py",
        "布局分析器"
    )
    all_passed &= check_python_syntax(
        ocr_service_dir / "services" / "layout_analyzer.py",
        "布局分析器语法"
    )

    # Phase 5: 跨字段校验服务
    print("\n✓ Phase 5: 跨字段校验服务")
    print("-" * 40)
    all_passed &= check_file_exists(
        ocr_service_dir / "services" / "cross_field_validator.py",
        "跨字段校验器"
    )
    all_passed &= check_python_syntax(
        ocr_service_dir / "services" / "cross_field_validator.py",
        "跨字段校验器语法"
    )

    # Phase 6: 多页文档处理器
    print("\n📑 Phase 6: 多页文档处理器")
    print("-" * 40)
    all_passed &= check_file_exists(
        ocr_service_dir / "services" / "multi_page_processor.py",
        "多页处理器"
    )
    all_passed &= check_python_syntax(
        ocr_service_dir / "services" / "multi_page_processor.py",
        "多页处理器语法"
    )

    # Phase 7: API更新
    print("\n🔌 Phase 7: API端点更新")
    print("-" * 40)
    all_passed &= check_python_syntax(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "OCR任务API"
    )
    all_passed &= check_python_syntax(
        ocr_service_dir / "api" / "templates.py",
        "模板管理API"
    )

    # Phase 8: 前端组件
    print("\n🎨 Phase 8: 前端组件增强")
    print("-" * 40)
    web_dir = base_dir / "web"

    all_passed &= check_file_exists(
        web_dir / "src" / "services" / "ocr.ts",
        "OCR服务客户端"
    )
    all_passed &= check_file_exists(
        web_dir / "src" / "components" / "data" / "DocumentViewer.tsx",
        "文档查看器组件"
    )
    all_passed &= check_file_exists(
        web_dir / "src" / "components" / "data" / "DocumentViewer.css",
        "文档查看器样式"
    )

    # 测试和文档
    print("\n🧪 测试和文档")
    print("-" * 40)
    all_passed &= check_file_exists(
        ocr_service_dir / "tests" / "__init__.py",
        "测试包初始化"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "tests" / "test_cross_field_validator.py",
        "跨字段校验测试"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "tests" / "test_integration.py",
        "集成测试"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "pytest.ini",
        "测试配置"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "README.md",
        "服务README"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "API.md",
        "API文档"
    )
    all_passed &= check_file_exists(
        ocr_service_dir / "IMPLEMENTATION_SUMMARY.md",
        "实施总结"
    )

    # 检查模型更新
    print("\n🗃️ 模型更新")
    print("-" * 40)
    all_passed &= check_python_syntax(
        ocr_service_dir / "models" / "ocr_task.py",
        "OCR任务模型"
    )

    # 检查导入是否正确
    print("\n🔗 导入检查")
    print("-" * 40)
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "services.layout_analyzer"
    )
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "services.cross_field_validator"
    )
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "services.multi_page_processor"
    )

    # 检查服务初始化
    print("\n⚙️ 服务初始化检查")
    print("-" * 40)
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "LayoutAnalyzer"
    )
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "CrossFieldValidator"
    )
    all_passed &= check_import_statement(
        ocr_service_dir / "api" / "ocr_tasks.py",
        "MultiPageProcessor"
    )

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！OCR服务增强实施已完成。")
        print("\n下一步：")
        print("1. 启动服务: docker-compose -f deploy/local/docker-compose.yml up -d ocr-service")
        print("2. 加载模板: curl -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults")
        print("3. 测试上传: curl -X POST http://localhost:8007/api/v1/ocr/tasks -F \"file=@test.pdf\"")
    else:
        print("❌ 存在问题，请检查上述错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()
