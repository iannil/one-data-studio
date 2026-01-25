#!/usr/bin/env python3
"""
ONE-DATA-STUDIO 初始化数据导入脚本
Seed Data Import Script

用法:
    python scripts/seed.py                      # 导入所有数据
    python scripts/seed.py --service admin      # 仅导入 admin 数据
    python scripts/seed.py --service alldata bisheng  # 导入指定服务
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
SERVICES = ["admin", "alldata", "bisheng", "cube"]

# 服务目录映射（使用连字符的目录名）
SERVICE_DIR_MAP = {
    "admin": "admin-api",
    "alldata": "alldata-api",
    "bisheng": "bisheng-api",
    "cube": "cube-api",
}

# 导入顺序（按依赖关系）
IMPORT_ORDER = {
    "admin": ["permissions", "roles", "users", "settings"],
    "alldata": ["datasources", "datasets", "metadata", "quality_rules", "asset_categories"],
    "bisheng": ["tools", "knowledge_bases", "prompt_templates", "agent_templates", "workflows"],
    "cube": ["resource_pools", "aihub_categories", "pipeline_templates", "aihub_models"],
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

    # ==================== Alldata 服务导入方法 ====================

    def _import_alldata_datasources(self, data: dict):
        """导入数据源"""
        datasources = data.get("datasources", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(datasources)} 个数据源")
            return

        models = self._load_service_models("alldata")
        if models is None:
            logger.warning("    - 无法加载 Alldata 模型，跳过数据源导入")
            return

        DataSource = getattr(models, "DataSource", None)
        if DataSource is None:
            logger.warning("    - DataSource 模型不存在，跳过")
            return

        session = self._get_session()

        for ds_data in datasources:
            existing = session.query(DataSource).filter_by(
                source_id=ds_data["source_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in ds_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                datasource = DataSource(**ds_data)
                session.add(datasource)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(datasources)} 个数据源")

    def _import_alldata_datasets(self, data: dict):
        """导入数据集"""
        datasets = data.get("datasets", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(datasets)} 个数据集")
            return

        models = self._load_service_models("alldata")
        if models is None:
            logger.warning("    - 无法加载 Alldata 模型，跳过数据集导入")
            return

        Dataset = getattr(models, "Dataset", None)
        if Dataset is None:
            logger.warning("    - Dataset 模型不存在，跳过")
            return

        session = self._get_session()

        for ds_data in datasets:
            existing = session.query(Dataset).filter_by(
                dataset_id=ds_data["dataset_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in ds_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                dataset = Dataset(**ds_data)
                session.add(dataset)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(datasets)} 个数据集")

    def _import_alldata_metadata(self, data: dict):
        """导入元数据"""
        databases = data.get("databases", [])
        tables = data.get("tables", [])
        columns = data.get("columns", [])

        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(databases)} 个数据库, {len(tables)} 个表, {len(columns)} 个列")
            return

        models = self._load_service_models("alldata")
        if models is None:
            logger.warning("    - 无法加载 Alldata 模型，跳过元数据导入")
            return

        MetadataDatabase = getattr(models, "MetadataDatabase", None)
        MetadataTable = getattr(models, "MetadataTable", None)
        MetadataColumn = getattr(models, "MetadataColumn", None)

        session = self._get_session()

        # 导入数据库
        if MetadataDatabase:
            for db_data in databases:
                existing = session.query(MetadataDatabase).filter_by(
                    database_name=db_data["database_name"]
                ).first()
                if not existing or self.force:
                    if existing and self.force:
                        for key, value in db_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        self.stats["updated"] += 1
                    else:
                        db = MetadataDatabase(**db_data)
                        session.add(db)
                        self.stats["created"] += 1
                else:
                    self.stats["skipped"] += 1

        session.flush()  # 确保数据库记录已写入

        # 导入表
        if MetadataTable:
            for tbl_data in tables:
                existing = session.query(MetadataTable).filter_by(
                    table_name=tbl_data["table_name"],
                    database_name=tbl_data["database_name"]
                ).first()
                if not existing or self.force:
                    if existing and self.force:
                        for key, value in tbl_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        self.stats["updated"] += 1
                    else:
                        tbl = MetadataTable(**tbl_data)
                        session.add(tbl)
                        self.stats["created"] += 1
                else:
                    self.stats["skipped"] += 1

        session.flush()  # 确保表记录已写入

        # 导入列
        if MetadataColumn and MetadataTable:
            for col_data in columns:
                # 查找对应的 table_id
                table = session.query(MetadataTable).filter_by(
                    table_name=col_data["table_name"],
                    database_name=col_data["database_name"]
                ).first()
                if not table:
                    logger.warning(f"    - 找不到表 {col_data['database_name']}.{col_data['table_name']}，跳过列 {col_data['column_name']}")
                    self.stats["skipped"] += 1
                    continue

                existing = session.query(MetadataColumn).filter_by(
                    column_name=col_data["column_name"],
                    table_name=col_data["table_name"],
                    database_name=col_data["database_name"]
                ).first()
                if not existing or self.force:
                    # 添加 table_id
                    col_data_with_table_id = {**col_data, "table_id": table.id}
                    if existing and self.force:
                        for key, value in col_data_with_table_id.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        self.stats["updated"] += 1
                    else:
                        col = MetadataColumn(**col_data_with_table_id)
                        session.add(col)
                        self.stats["created"] += 1
                else:
                    self.stats["skipped"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(databases)} 个数据库, {len(tables)} 个表, {len(columns)} 个列")

    def _import_alldata_quality_rules(self, data: dict):
        """导入质量规则"""
        rules = data.get("quality_rules", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(rules)} 条质量规则")
            return

        models = self._load_service_models("alldata")
        if models is None:
            logger.warning("    - 无法加载 Alldata 模型，跳过质量规则导入")
            return

        QualityRule = getattr(models, "QualityRule", None)
        if QualityRule is None:
            logger.warning("    - QualityRule 模型不存在，跳过")
            return

        session = self._get_session()

        for rule_data in rules:
            existing = session.query(QualityRule).filter_by(
                rule_id=rule_data["rule_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in rule_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                rule = QualityRule(**rule_data)
                session.add(rule)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(rules)} 条质量规则")

    def _import_alldata_asset_categories(self, data: dict):
        """导入资产分类"""
        categories = data.get("asset_categories", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(categories)} 个资产分类")
            return

        models = self._load_service_models("alldata")
        if models is None:
            logger.warning("    - 无法加载 Alldata 模型，跳过资产分类导入")
            return

        AssetCategory = getattr(models, "AssetCategory", None)
        if AssetCategory is None:
            logger.warning("    - AssetCategory 模型不存在，跳过")
            return

        session = self._get_session()

        for cat_data in categories:
            existing = session.query(AssetCategory).filter_by(
                category_id=cat_data["category_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in cat_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                category = AssetCategory(**cat_data)
                session.add(category)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(categories)} 个资产分类")

    # ==================== Bisheng 服务导入方法 ====================

    def _import_bisheng_workflows(self, data: dict):
        """导入工作流"""
        workflows = data.get("workflows", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(workflows)} 个工作流")
            return

        models = self._load_service_models("bisheng")
        if models is None:
            logger.warning("    - 无法加载 Bisheng 模型，跳过工作流导入")
            return

        Workflow = getattr(models, "Workflow", None)
        if Workflow is None:
            logger.warning("    - Workflow 模型不存在，跳过")
            return

        session = self._get_session()

        for wf_data in workflows:
            # 处理 definition 字段（转为 JSON 字符串）
            if "definition" in wf_data and isinstance(wf_data["definition"], dict):
                wf_data["definition"] = json.dumps(wf_data["definition"], ensure_ascii=False)

            existing = session.query(Workflow).filter_by(
                workflow_id=wf_data["workflow_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in wf_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                workflow = Workflow(**wf_data)
                session.add(workflow)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(workflows)} 个工作流")

    def _import_bisheng_agent_templates(self, data: dict):
        """导入 Agent 模板"""
        templates = data.get("agent_templates", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(templates)} 个 Agent 模板")
            return

        models = self._load_service_models("bisheng")
        if models is None:
            logger.warning("    - 无法加载 Bisheng 模型，跳过 Agent 模板导入")
            return

        AgentTemplate = getattr(models, "AgentTemplate", None)
        if AgentTemplate is None:
            logger.warning("    - AgentTemplate 模型不存在，跳过")
            return

        session = self._get_session()

        for tpl_data in templates:
            existing = session.query(AgentTemplate).filter_by(
                template_id=tpl_data["template_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in tpl_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                template = AgentTemplate(**tpl_data)
                session.add(template)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(templates)} 个 Agent 模板")

    def _import_bisheng_prompt_templates(self, data: dict):
        """导入 Prompt 模板"""
        templates = data.get("prompt_templates", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(templates)} 个 Prompt 模板")
            return

        models = self._load_service_models("bisheng")
        if models is None:
            logger.warning("    - 无法加载 Bisheng 模型，跳过 Prompt 模板导入")
            return

        PromptTemplate = getattr(models, "PromptTemplate", None)
        if PromptTemplate is None:
            logger.warning("    - PromptTemplate 模型不存在，跳过")
            return

        session = self._get_session()

        for tpl_data in templates:
            existing = session.query(PromptTemplate).filter_by(
                template_id=tpl_data["template_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in tpl_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                template = PromptTemplate(**tpl_data)
                session.add(template)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(templates)} 个 Prompt 模板")

    def _import_bisheng_tools(self, data: dict):
        """导入工具"""
        tools = data.get("tools", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(tools)} 个工具")
            return

        models = self._load_service_models("bisheng")
        if models is None:
            logger.warning("    - 无法加载 Bisheng 模型，跳过工具导入")
            return

        Tool = getattr(models, "Tool", None)
        if Tool is None:
            logger.warning("    - Tool 模型不存在，跳过")
            return

        session = self._get_session()

        for tool_data in tools:
            existing = session.query(Tool).filter_by(
                tool_id=tool_data["tool_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in tool_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                tool = Tool(**tool_data)
                session.add(tool)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(tools)} 个工具")

    def _import_bisheng_knowledge_bases(self, data: dict):
        """导入知识库"""
        kbs = data.get("knowledge_bases", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(kbs)} 个知识库")
            return

        models = self._load_service_models("bisheng")
        if models is None:
            logger.warning("    - 无法加载 Bisheng 模型，跳过知识库导入")
            return

        KnowledgeBase = getattr(models, "KnowledgeBase", None)
        if KnowledgeBase is None:
            logger.warning("    - KnowledgeBase 模型不存在，跳过")
            return

        session = self._get_session()

        for kb_data in kbs:
            existing = session.query(KnowledgeBase).filter_by(
                kb_id=kb_data["kb_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in kb_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                kb = KnowledgeBase(**kb_data)
                session.add(kb)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(kbs)} 个知识库")

    # ==================== Cube 服务导入方法 ====================

    def _import_cube_resource_pools(self, data: dict):
        """导入资源池"""
        pools = data.get("resource_pools", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(pools)} 个资源池")
            return

        models = self._load_service_models("cube")
        if models is None:
            logger.warning("    - 无法加载 Cube 模型，跳过资源池导入")
            return

        ResourcePool = getattr(models, "ResourcePool", None)
        if ResourcePool is None:
            logger.warning("    - ResourcePool 模型不存在，跳过")
            return

        session = self._get_session()

        for pool_data in pools:
            existing = session.query(ResourcePool).filter_by(
                pool_id=pool_data["pool_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in pool_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                pool = ResourcePool(**pool_data)
                session.add(pool)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(pools)} 个资源池")

    def _import_cube_pipeline_templates(self, data: dict):
        """导入流水线模板"""
        templates = data.get("pipeline_templates", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(templates)} 个流水线模板")
            return

        models = self._load_service_models("cube")
        if models is None:
            logger.warning("    - 无法加载 Cube 模型，跳过流水线模板导入")
            return

        PipelineTemplate = getattr(models, "PipelineTemplate", None)
        if PipelineTemplate is None:
            logger.warning("    - PipelineTemplate 模型不存在，跳过")
            return

        session = self._get_session()

        for tpl_data in templates:
            existing = session.query(PipelineTemplate).filter_by(
                template_id=tpl_data["template_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in tpl_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                template = PipelineTemplate(**tpl_data)
                session.add(template)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(templates)} 个流水线模板")

    def _import_cube_aihub_categories(self, data: dict):
        """导入 AI Hub 分类"""
        categories = data.get("aihub_categories", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(categories)} 个 AI Hub 分类")
            return

        models = self._load_service_models("cube")
        if models is None:
            logger.warning("    - 无法加载 Cube 模型，跳过 AI Hub 分类导入")
            return

        AIHubCategory = getattr(models, "AIHubCategory", None)
        if AIHubCategory is None:
            logger.warning("    - AIHubCategory 模型不存在，跳过")
            return

        session = self._get_session()

        for cat_data in categories:
            existing = session.query(AIHubCategory).filter_by(
                category_id=cat_data["category_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in cat_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                category = AIHubCategory(**cat_data)
                session.add(category)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(categories)} 个 AI Hub 分类")

    def _import_cube_aihub_models(self, data: dict):
        """导入 AI Hub 模型"""
        models_data = data.get("aihub_models", [])
        if self.dry_run:
            logger.info(f"    - [预览] 将导入 {len(models_data)} 个 AI Hub 模型")
            return

        models = self._load_service_models("cube")
        if models is None:
            logger.warning("    - 无法加载 Cube 模型，跳过 AI Hub 模型导入")
            return

        AIHubModel = getattr(models, "AIHubModel", None)
        if AIHubModel is None:
            logger.warning("    - AIHubModel 模型不存在，跳过")
            return

        session = self._get_session()

        for model_data in models_data:
            existing = session.query(AIHubModel).filter_by(
                model_id=model_data["model_id"]
            ).first()

            if existing:
                if self.force:
                    for key, value in model_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    self.stats["updated"] += 1
                else:
                    self.stats["skipped"] += 1
            else:
                model = AIHubModel(**model_data)
                session.add(model)
                self.stats["created"] += 1

        session.commit()
        logger.info(f"    - 完成: {len(models_data)} 个 AI Hub 模型")

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
  python scripts/seed.py --service alldata bisheng  # 导入指定服务
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
