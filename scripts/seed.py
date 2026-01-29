#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 初始化数据导入脚本
Seed Data Import Script

用法:
    python scripts/seed.py                      # 导入所有数据
    python scripts/seed.py --service admin      # 仅导入 admin 数据
    python scripts/seed.py --service data agent model  # 导入指定服务
    python scripts/seed.py --force              # 强制覆盖已有数据
    python scripts/seed.py --dry-run            # 预览模式
"""

import argparse
import importlib.util
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 种子数据目录
SEED_DATA_DIR = PROJECT_ROOT / "data" / "seed"

# 支持的服务
SERVICES = ["admin", "data", "agent", "model"]

# 服务目录映射（使用连字符的目录名）
SERVICE_DIR_MAP = {
    "admin": "admin-api",
    "data": "data-api",
    "agent": "agent-api",
    "model": "model-api",
}

# 导入顺序（按依赖关系）
IMPORT_ORDER = {
    "admin": ["permissions", "roles", "users", "settings"],
    "data": ["datasources", "datasets", "metadata", "quality_rules", "asset_categories"],
    "agent": ["tools", "knowledge_bases", "prompt_templates", "agent_templates", "workflows"],
    "model": ["resource_pools", "aihub_categories", "pipeline_templates", "aihub_models"],
}


def load_module_from_path(module_name: str, file_path: Path):
    """从指定路径动态加载模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SeedDataImporter:
    """种子数据导入器"""

    def __init__(self, dry_run: bool = False, force: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.stats = {
            "created": 0,
            "skipped": 0,
            "updated": 0,
            "failed": 0,
        }

        # 数据库会话（延迟初始化）
        self._session = None
        self._models_cache = {}

    def _load_service_models(self, service: str):
        """动态加载服务的模型模块"""
        if service in self._models_cache:
            return self._models_cache[service]

        service_dir = SERVICE_DIR_MAP.get(service)
        if not service_dir:
            return None

        # 优先检查 src/models.py（容器使用的模型）
        src_models = PROJECT_ROOT / "services" / service_dir / "src" / "models.py"
        if src_models.exists():
            try:
                module = load_module_from_path(f"{service}_src_models", src_models)
                self._models_cache[service] = module
                return module
            except Exception as e:
                logger.debug(f"加载 src/models.py 失败: {e}")

        # 回退到 models/__init__.py
        models_init = PROJECT_ROOT / "services" / service_dir / "models" / "__init__.py"
        if not models_init.exists():
            logger.debug(f"模型文件不存在: {models_init}")
            return None

        try:
            # 先加载 base 模块
            base_path = PROJECT_ROOT / "services" / service_dir / "models" / "base.py"
            if base_path.exists():
                load_module_from_path(f"{service}_models_base", base_path)

            # 加载主模块
            module = load_module_from_path(f"{service}_models", models_init)
            self._models_cache[service] = module
            return module
        except Exception as e:
            logger.debug(f"加载模型模块失败: {e}")
            return None

    def _get_session(self):
        """获取数据库会话"""
        if self._session is None:
            self._session = self._create_session_from_env()
        return self._session

    def _create_session_from_env(self):
        """从环境变量创建数据库会话"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        database_url = os.environ.get(
            "DATABASE_URL",
            "mysql+pymysql://onedata:dev123@localhost:3306/onedata"
        )
        engine = create_engine(database_url, echo=self.verbose)
        Session = sessionmaker(bind=engine)
        return Session()

    def load_yaml(self, file_path: Path) -> dict:
        """加载 YAML 文件"""
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def generate_id(self, prefix: str = "") -> str:
        """生成唯一 ID"""
        short_uuid = str(uuid.uuid4())[:8]
        if prefix:
            return f"{prefix}-{short_uuid}"
        return short_uuid

    def import_all(self, services: list[str] | None = None):
        """导入所有数据"""
        if services is None:
            services = SERVICES

        logger.info("=" * 60)
        logger.info("ONE-DATA-STUDIO 种子数据导入")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("[预览模式] 不会实际写入数据库")

        if self.force:
            logger.info("[强制模式] 将覆盖已有数据")

        for service in services:
            if service not in SERVICES:
                logger.warning(f"未知服务: {service}，跳过")
                continue

            self.import_service(service)

        self._print_summary()

    def import_service(self, service: str):
        """导入指定服务的数据"""
        logger.info("")
        logger.info(f">>> 导入 {service.upper()} 服务数据")
        logger.info("-" * 40)

        service_dir = SEED_DATA_DIR / service
        if not service_dir.exists():
            logger.warning(f"服务目录不存在: {service_dir}")
            return

        import_files = IMPORT_ORDER.get(service, [])
        for file_name in import_files:
            file_path = service_dir / f"{file_name}.yaml"
            if file_path.exists():
                self._import_file(service, file_name, file_path)
            else:
                logger.debug(f"文件不存在，跳过: {file_path}")

    def _import_file(self, service: str, data_type: str, file_path: Path):
        """导入单个文件"""
        logger.info(f"  导入 {data_type}...")
        data = self.load_yaml(file_path)

        if not data:
            logger.info(f"    - 无数据")
            return

        # 根据服务和数据类型调用对应的导入方法
        import_method = getattr(self, f"_import_{service}_{data_type}", None)
        if import_method:
            try:
                import_method(data)
            except Exception as e:
                logger.error(f"    - 导入失败: {e}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                self.stats["failed"] += 1
                # 回滚会话以便后续导入继续
                try:
                    if self.session:
                        self.session.rollback()
                except:
                    pass
        else:
            logger.warning(f"    - 未实现导入方法: _import_{service}_{data_type}")

    # ==================== Admin 服务导入方法 ====================

    def _import_admin_permissions(self, data: dict):
        """导入权限数据"""
        permissions = data.get("permissions", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(permissions)} 条权限")
            return

        models = self._load_service_models("admin")
        if models is None:
            logger.warning("    - 无法加载 Admin 模型，跳过权限导入")
            return

        Permission = getattr(models, "Permission", None)
        if Permission is None:
            logger.warning("    - Permission 模型不存在，跳过")
            return

        session = self._get_session()

        for perm_data in permissions:
            # 优先检查 code 字段（唯一约束）
            existing = session.query(Permission).filter_by(
                code=perm_data["code"]
            ).first()

            if existing:
                if self.force:
                    for key, value in perm_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                    logger.debug(f"    - 更新: {perm_data['name']}")
                else:
                    self.stats["skipped"] += 1
                    logger.debug(f"    - 跳过: {perm_data['name']} (已存在)")
            else:
                permission = Permission(**perm_data)
                session.add(permission)
                self.stats["created"] += 1
                logger.debug(f"    - 创建: {perm_data['name']}")

        session.commit()
        logger.info(f"    - 完成: {len(permissions)} 条权限")

    def _import_admin_roles(self, data: dict):
        """导入角色数据"""
        roles = data.get("roles", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(roles)} 个角色")
            return

        models = self._load_service_models("admin")
        if models is None:
            logger.warning("    - 无法加载 Admin 模型，跳过角色导入")
            return

        Role = getattr(models, "Role", None)
        Permission = getattr(models, "Permission", None)
        if Role is None:
            logger.warning("    - Role 模型不存在，跳过")
            return

        session = self._get_session()

        for role_data in roles.copy():
            # 提取权限代码列表
            permission_codes = role_data.pop("permissions", [])

            # 优先检查 name 字段（通常唯一）
            existing = session.query(Role).filter_by(
                name=role_data["name"]
            ).first()

            if existing:
                if self.force:
                    for key, value in role_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    role = existing
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
                    logger.debug(f"    - 跳过: {role_data['name']} (已存在)")
                    continue
            else:
                role = Role(**role_data)
                session.add(role)
                self.stats["created"] += 1

            # 关联权限
            if permission_codes and Permission:
                permissions = session.query(Permission).filter(
                    Permission.code.in_(permission_codes)
                ).all()
                role.permissions = permissions

        session.commit()
        logger.info(f"    - 完成: {len(roles)} 个角色")

    def _import_admin_users(self, data: dict):
        """导入用户数据"""
        users = data.get("users", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(users)} 个用户")
            return

        models = self._load_service_models("admin")
        if models is None:
            logger.warning("    - 无法加载 Admin 模型，跳过用户导入")
            return

        User = getattr(models, "User", None)
        Role = getattr(models, "Role", None)
        if User is None:
            logger.warning("    - User 模型不存在，跳过")
            return

        session = self._get_session()

        for user_data in users.copy():
            # 提取角色名称列表
            role_names = user_data.pop("roles", [])

            # 优先检查 username 字段（唯一约束）
            existing = session.query(User).filter_by(
                username=user_data["username"]
            ).first()

            if existing:
                if self.force:
                    for key, value in user_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    user = existing
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
                    logger.debug(f"    - 跳过: {user_data['username']} (已存在)")
                    continue
            else:
                user = User(**user_data)
                session.add(user)
                self.stats["created"] += 1

            # 关联角色
            if role_names and Role:
                roles = session.query(Role).filter(
                    Role.name.in_(role_names)
                ).all()
                user.roles = roles

        session.commit()
        logger.info(f"    - 完成: {len(users)} 个用户")

    def _import_admin_settings(self, data: dict):
        """导入系统设置"""
        settings = data.get("settings", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(settings)} 条设置")
            return

        models = self._load_service_models("admin")
        if models is None:
            logger.warning("    - 无法加载 Admin 模型，跳过设置导入")
            return

        SystemSettings = getattr(models, "SystemSettings", None)
        if SystemSettings is None:
            logger.warning("    - SystemSettings 模型不存在，跳过")
            return

        session = self._get_session()

        for setting_data in settings:
            # 映射 YAML 字段到模型字段
            setting_key = setting_data.get("key") or setting_data.get("setting_key")
            setting_value = setting_data.get("value") or setting_data.get("setting_value")

            existing = session.query(SystemSettings).filter_by(
                setting_key=setting_key
            ).first()

            if existing:
                if self.force:
                    existing.setting_value = setting_value
                    existing.category = setting_data.get("category")
                    existing.description = setting_data.get("description")
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                setting = SystemSettings(
                    setting_key=setting_key,
                    setting_value=setting_value,
                    category=setting_data.get("category"),
                    description=setting_data.get("description")
                )
                session.add(setting)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(settings)} 条设置")

    def _print_summary(self):
        """打印导入汇总"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("导入汇总")
        logger.info("=" * 60)
        logger.info(f"  创建: {self.stats['created']}")
        logger.info(f"  跳过: {self.stats['skipped']}")
        logger.info(f"  更新: {self.stats['updated']}")
        logger.info(f"  失败: {self.stats['failed']}")
        logger.info("=" * 60)

    def close(self):
        """关闭数据库连接"""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ONE-DATA-STUDIO 种子数据导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/seed.py                      # 导入所有数据
  python scripts/seed.py --service admin      # 仅导入 admin 数据
  python scripts/seed.py --service data agent model  # 导入指定服务
  python scripts/seed.py --force              # 强制覆盖已有数据
  python scripts/seed.py --dry-run            # 预览模式
        """
    )

    parser.add_argument(
        "--service", "-s",
        nargs="+",
        choices=SERVICES,
        help="指定要导入的服务（可多选）"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制覆盖已有数据"
    )

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="预览模式，不实际写入数据库"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建导入器并执行
    importer = SeedDataImporter(
        dry_run=args.dry_run,
        force=args.force,
        verbose=args.verbose
    )

    try:
        importer.import_all(args.service)
    finally:
        importer.close()


if __name__ == "__main__":
    main()
