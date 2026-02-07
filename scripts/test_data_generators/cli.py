"""
测试数据生成器 CLI

命令行接口，用于生成和清理测试数据
"""

import argparse
import sys
import os
from typing import List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from .base import GeneratorConfig
from .config import GeneratorQuantities, DatabaseConfig, MinIOConfig, MilvusConfig, RedisConfig
from .storage import get_mysql_manager, get_minio_manager, get_milvus_manager, get_redis_manager

from .generators import (
    UserGenerator,
    DatasourceGenerator,
    ETLGenerator,
    SensitiveGenerator,
    AssetGenerator,
    LineageGenerator,
    MLGenerator,
    KnowledgeGenerator,
    BIGenerator,
    AlertGenerator,
)

from .validators import DataValidator, LinkageValidator


# 生成器映射
GENERATORS = {
    "user": UserGenerator,
    "datasource": DatasourceGenerator,
    "etl": ETLGenerator,
    "sensitive": SensitiveGenerator,
    "asset": AssetGenerator,
    "lineage": LineageGenerator,
    "ml": MLGenerator,
    "knowledge": KnowledgeGenerator,
    "bi": BIGenerator,
    "alert": AlertGenerator,
}

# 生成器依赖关系
GENERATOR_DEPENDENCIES = {
    "datasource": [],
    "user": [],
    "etl": ["datasource"],
    "sensitive": ["datasource"],
    "asset": ["datasource"],
    "lineage": ["datasource", "etl"],
    "ml": [],
    "knowledge": [],
    "bi": ["datasource"],
    "alert": ["datasource"],
}


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="测试数据生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成全部测试数据
  python -m scripts.test_data_generators generate --all

  # 生成指定模块的数据
  python -m scripts.test_data_generators generate --module user,datasource,etl

  # 清理全部测试数据
  python -m scripts.test_data_generators cleanup --all

  # 验证数据
  python -m scripts.test_data_generators validate

  # 使用Mock模式（不连接真实数据库）
  python -m scripts.test_data_generators generate --all --mock
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # generate 命令
    generate_parser = subparsers.add_parser("generate", help="生成测试数据")
    generate_parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="生成全部数据"
    )
    generate_parser.add_argument(
        "--module", "-m",
        type=str,
        help="指定要生成的模块，逗号分隔，如: user,datasource,etl"
    )
    generate_parser.add_argument(
        "--mock",
        action="store_true",
        help="使用Mock模式（不连接真实数据库）"
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只生成不保存"
    )

    # cleanup 命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理测试数据")
    cleanup_parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="清理全部数据"
    )
    cleanup_parser.add_argument(
        "--module", "-m",
        type=str,
        help="指定要清理的模块，逗号分隔"
    )

    # validate 命令
    validate_parser = subparsers.add_parser("validate", help="验证数据")
    validate_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看数据统计")

    return parser.parse_args()


def get_storage_managers(mock: bool = False):
    """获取存储管理器"""
    mysql = get_mysql_manager(DatabaseConfig.from_env(), mock=mock)
    minio = get_minio_manager(MinIOConfig.from_env(), mock=mock)
    milvus = get_milvus_manager(MilvusConfig.from_env(), mock=mock)
    redis = get_redis_manager(RedisConfig.from_env(), mock=mock)

    # 连接
    if not mock:
        mysql.connect()
        minio.connect()
        milvus.connect()
        redis.connect()

    return {
        "mysql": mysql,
        "minio": minio,
        "milvus": milvus,
        "redis": redis,
    }


def resolve_dependencies(modules: List[str]) -> List[str]:
    """解析模块依赖关系，返回正确的执行顺序"""
    resolved = []
    visited = set()

    def visit(module: str):
        if module in visited:
            return
        visited.add(module)

        # 先访问依赖
        for dep in GENERATOR_DEPENDENCIES.get(module, []):
            if dep in GENERATORS:
                visit(dep)

        resolved.append(module)

    for module in modules:
        visit(module)

    return resolved


def generate_data(args):
    """生成数据"""
    config = GeneratorQuantities()
    storage = get_storage_managers(mock=args.mock)

    if args.all:
        modules = list(GENERATORS.keys())
    elif args.module:
        modules = [m.strip() for m in args.module.split(",")]
    else:
        print("错误: 请指定 --all 或 --module")
        return 1

    # 解析依赖关系
    modules = resolve_dependencies(modules)

    print(f"\n将生成以下模块的数据: {', '.join(modules)}\n")

    all_data = {}
    generated = {}

    # 按顺序生成数据
    for module in modules:
        generator_class = GENERATORS.get(module)
        if not generator_class:
            print(f"警告: 未知的模块 '{module}'")
            continue

        print(f"\n{'='*60}")
        print(f"生成 {module} 模块数据...")
        print(f"{'='*60}")

        try:
            # 创建生成器实例
            if module == "knowledge":
                generator = generator_class(
                    config,
                    storage_manager=storage["mysql"],
                    minio_manager=storage["minio"],
                    milvus_manager=storage["milvus"]
                )
            else:
                generator = generator_class(
                    config,
                    storage_manager=storage["mysql"]
                )

            # 设置依赖数据
            for dep_module in GENERATOR_DEPENDENCIES.get(module, []):
                dep_data = generated.get(dep_module)
                if dep_data:
                    generator.set_dependency(dep_module, dep_data.get(dep_module, {}))

            # 生成数据
            data = generator.generate()
            generated[module] = data
            all_data.update(data)

            # 保存数据
            if not args.dry_run and not args.mock:
                generator.save()

        except Exception as e:
            print(f"错误: 生成 {module} 数据失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*60}")
    print("数据生成完成!")
    print(f"{'='*60}\n")

    # 打印摘要
    if not args.dry_run and not args.mock:
        print_data_summary(storage["mysql"])

    return 0


def cleanup_data(args):
    """清理数据"""
    storage = get_storage_managers(mock=False)

    if args.all:
        modules = list(GENERATORS.keys())
    elif args.module:
        modules = [m.strip() for m in args.module.split(",")]
    else:
        print("错误: 请指定 --all 或 --module")
        return 1

    print(f"\n将清理以下模块的数据: {', '.join(modules)}\n")

    for module in modules:
        generator_class = GENERATORS.get(module)
        if not generator_class:
            print(f"警告: 未知的模块 '{module}'")
            continue

        try:
            generator = generator_class(storage_manager=storage["mysql"])
            generator.cleanup()
            print(f"✓ 已清理 {module} 模块数据")
        except Exception as e:
            print(f"✗ 清理 {module} 模块数据失败: {e}")

    print("\n数据清理完成!\n")
    return 0


def validate_data_cmd(args):
    """验证数据"""
    storage = get_storage_managers(mock=False)

    print("\n开始验证数据...\n")

    validator = DataValidator()

    # 从数据库读取数据
    for table_name, display_name in [
        ("users", "用户"),
        ("datasources", "数据源"),
        ("metadata_tables", "元数据表"),
        ("metadata_columns", "元数据列"),
        ("etl_tasks", "ETL任务"),
        ("etl_task_logs", "ETL日志"),
    ]:
        if storage["mysql"].table_exists(table_name):
            count = storage["mysql"].count_rows(table_name)
            data = storage["mysql"].fetch_all(f"SELECT * FROM {table_name} LIMIT 1000")
            validator.load_data(table_name, data)
            print(f"  {display_name}: {count} 条")

    # 执行验证
    result = validator.validate_all()

    print(f"\n{'='*60}")
    print("验证结果")
    print(f"{'='*60}")
    print(f"  总检查项: {result['total']}")
    print(f"  通过: {result['passed']}")
    print(f"  失败: {result['failed']}")

    if result['errors']:
        print(f"\n错误:")
        for error in result['errors']:
            print(f"  ✗ {error}")

    if result['warnings']:
        print(f"\n警告:")
        for warning in result['warnings']:
            print(f"  ! {warning}")

    print(f"{'='*60}\n")

    return 0 if result['failed'] == 0 else 1


def show_status(args):
    """显示数据统计"""
    storage = get_storage_managers(mock=False)

    print(f"\n{'='*60}")
    print("数据库统计")
    print(f"{'='*60}\n")

    stats = storage["mysql"].get_table_stats()

    for table, count in stats.items():
        if count > 0:
            print(f"  {table}: {count}")

    print(f"\n{'='*60}\n")

    return 0


def print_data_summary(mysql_manager):
    """打印数据摘要"""
    print(f"\n{'='*60}")
    print("数据生成摘要")
    print(f"{'='*60}\n")

    stats = mysql_manager.get_table_stats()

    total = 0
    for table, count in stats.items():
        if count > 0:
            print(f"  {table}: {count}")
            total += count

    print(f"\n  总计: {total} 条记录")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    args = parse_arguments()

    if args.command == "generate":
        return generate_data(args)
    elif args.command == "cleanup":
        return cleanup_data(args)
    elif args.command == "validate":
        return validate_data_cmd(args)
    elif args.command == "status":
        return show_status(args)
    else:
        print("请指定命令: generate, cleanup, validate, status")
        print("使用 -h/--help 查看帮助")
        return 1


if __name__ == "__main__":
    sys.exit(main())
