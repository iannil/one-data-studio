#!/usr/bin/env python3
"""
OCR服务命令行工具
支持从命令行直接调用OCR服务
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# 添加SDK到路径
sdk_path = Path(__file__).parent.parent / "sdk" / "python"
sys.path.insert(0, str(sdk_path))

from ocr_client import (
    OCRClient,
    DocumentType,
    OCRClientError,
    ServiceUnavailableError,
    TaskFailedError
)


def cmd_health(args):
    """健康检查命令"""
    client = OCRClient(args.url)
    health = client.health_check()
    print(json.dumps(health, indent=2, ensure_ascii=False))
    client.close()


def cmd_extract(args):
    """文档提取命令"""
    client = OCRClient(args.url, timeout=args.timeout)

    # 解析文档类型
    doc_type = DocumentType.AUTO if args.type == "auto" else args.type

    try:
        # 提取文档
        result = client.extract(args.file, doc_type)

        # 输出结果
        if args.output:
            # 保存到文件
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    'task_id': result.task_id,
                    'document_type': result.document_type,
                    'status': result.status.value,
                    'structured_data': result.structured_data,
                    'tables': result.tables,
                    'confidence_score': result.confidence_score,
                    'cross_field_validation': result.cross_field_validation,
                    'layout_info': result.layout_info,
                    'completeness': result.completeness,
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ 结果已保存到: {args.output}")
        else:
            # 打印到标准输出
            print(json.dumps({
                'task_id': result.task_id,
                'document_type': result.document_type,
                'status': result.status.value,
                'confidence': f"{result.confidence_score:.1%}",
                'structured_data': result.structured_data
            }, indent=2, ensure_ascii=False))

        # 显示验证状态
        if not args.quiet:
            if result.is_valid():
                print("✅ 验证通过", file=sys.stderr)
            else:
                print("⚠️  需要人工审核", file=sys.stderr)

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)

    client.close()


def cmd_batch(args):
    """批量处理命令"""
    client = OCRClient(args.url, timeout=args.timeout)

    # 收集文件
    files = []
    for path in args.files:
        p = Path(path)
        if p.is_dir():
            files.extend(p.glob("*.pdf"))
            files.extend(p.glob("*.jpg"))
            files.extend(p.glob("*.png"))
        else:
            files.append(p)

    print(f"📁 找到 {len(files)} 个文件")

    # 批量处理
    doc_type = DocumentType.AUTO if args.type == "auto" else args.type
    results = client.extract_batch(files, doc_type)

    # 统计结果
    passed = sum(1 for r in results if r.is_valid())
    failed = sum(1 for r in results if r.status.value == "failed")

    print(f"\n📊 处理完成: {len(results)} 个文件")
    print(f"   ✅ 通过: {passed}")
    print(f"   ❌ 失败: {failed}")

    # 保存结果
    if args.output:
        output_data = [
            {
                'file': str(f),
                'task_id': r.task_id,
                'status': r.status.value,
                'confidence': r.confidence_score,
                'structured_data': r.structured_data
            }
            for f, r in zip(files, results)
        ]
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"📄 结果已保存到: {args.output}")

    client.close()


def cmd_detect(args):
    """文档类型检测命令"""
    client = OCRClient(args.url)

    try:
        detection = client.detect_type(args.file)
        print(f"📄 文档类型: {detection['type']}")
        print(f"📊 置信度: {detection['confidence']:.1%}")

        if detection.get('alternatives'):
            print("\n其他可能:")
            for alt in detection['alternatives']:
                print(f"  - {alt['type']}: {alt['confidence']:.1%}")

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)

    client.close()


def cmd_templates(args):
    """模板管理命令"""
    client = OCRClient(args.url)

    if args.action == "list":
        templates = client.list_templates(
            template_type=args.type,
            is_active=None if args.all else True
        )

        print(f"📋 找到 {len(templates)} 个模板\n")

        for t in templates:
            status = "✅" if t.is_active else "❌"
            print(f"{status} {t.name} ({t.template_type})")
            if t.category:
                print(f"   分类: {t.category}")
            print(f"   ID: {t.id}")
            print()

    elif args.action == "load-defaults":
        if client.load_default_templates():
            print("✅ 默认模板加载成功")
        else:
            print("❌ 模板加载失败")
            sys.exit(1)

    elif args.action == "types":
        types = client.get_supported_types()
        print("📋 支持的文档类型:\n")
        for key, name in types.items():
            print(f"  {key}: {name}")

    client.close()


def cmd_server(args):
    """服务信息命令"""
    client = OCRClient(args.url)

    if args.info:
        # 服务信息
        health = client.health_check()
        print("🔧 OCR服务信息")
        print(f"   状态: {health.get('status')}")
        print(f"   OCR引擎: {'就绪' if health.get('ocr_engine') else '未就绪'}")
        print(f"   数据库: {'连接' if health.get('database') else '断开'}")
        print(f"   Redis: {'连接' if health.get('redis') else '断开'}")

    client.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="OCR服务命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 健康检查
  ocr-cli health

  # 提取文档
  ocr-cli extract invoice.pdf --type invoice

  # 自动检测类型
  ocr-cli detect document.pdf

  # 批量处理
  ocr-cli batch ./documents --output results.json

  # 列出模板
  ocr-cli templates list

  # 加载默认模板
  ocr-cli templates load-defaults
        """
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8007",
        help="OCR服务地址 (默认: http://localhost:8007)"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # health 命令
    subparsers.add_parser("health", help="健康检查")

    # extract 命令
    extract_parser = subparsers.add_parser("extract", help="提取文档")
    extract_parser.add_argument("file", help="文档文件路径")
    extract_parser.add_argument("--type", "-t", default="auto",
                               choices=["auto", "invoice", "contract", "purchase_order",
                                      "delivery_note", "quotation", "receipt", "report", "general"],
                               help="文档类型 (默认: auto)")
    extract_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    extract_parser.add_argument("--timeout", type=int, default=300, help="超时时间（秒）")
    extract_parser.add_argument("--quiet", "-q", action="store_true", help="安静模式")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理")
    batch_parser.add_argument("files", nargs="+", help="文件或目录路径")
    batch_parser.add_argument("--type", "-t", default="auto",
                            choices=["auto", "invoice", "contract", "purchase_order",
                                   "delivery_note", "quotation", "receipt", "report", "general"],
                            help="文档类型 (默认: auto)")
    batch_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    batch_parser.add_argument("--timeout", type=int, default=300, help="超时时间（秒）")

    # detect 命令
    detect_parser = subparsers.add_parser("detect", help="检测文档类型")
    detect_parser.add_argument("file", help="文档文件路径")

    # templates 命令
    templates_parser = subparsers.add_parser("templates", help="模板管理")
    templates_parser.add_argument("action",
                                  choices=["list", "load-defaults", "types"],
                                  help="操作类型")
    templates_parser.add_argument("--type", "-t", help="筛选模板类型")
    templates_parser.add_argument("--all", "-a", action="store_true",
                                 help="显示所有模板（包括禁用的）")

    # server 命令
    server_parser = subparsers.add_parser("server", help="服务信息")
    server_parser.add_argument("--info", "-i", action="store_true", help="显示服务信息")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 执行命令
    commands = {
        "health": cmd_health,
        "extract": cmd_extract,
        "batch": cmd_batch,
        "detect": cmd_detect,
        "templates": cmd_templates,
        "server": cmd_server,
    }

    try:
        commands[args.command](args)
    except ServiceUnavailableError:
        print("❌ 服务不可用，请检查服务地址和状态", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  操作已取消")
        sys.exit(130)


if __name__ == "__main__":
    main()
