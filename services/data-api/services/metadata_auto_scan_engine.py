"""
元数据自动扫描引擎
Phase 2: 数据库表结构自动发现和 AI 标注

功能：
- 连接数据库自动发现表结构（INFORMATION_SCHEMA）
- 自动同步表结构变更到元数据库
- AI 自动标注列描述（基于列名、类型、采样数据）
- 数据概况自动统计（行数、空值率、唯一值等）
- 支持增量扫描（只处理变更部分）
- 变更检测与报告（新增、修改、删除的表/列）
"""

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from hashlib import md5

from services.ai_service import get_ai_service, AIService

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """变更类型"""
    ADDED = "added"       # 新增
    MODIFIED = "modified"  # 修改
    DELETED = "deleted"    # 删除
    UNCHANGED = "unchanged"  # 无变化


@dataclass
class ColumnChange:
    """列变更详情"""
    column_name: str
    change_type: ChangeType
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    old_nullable: Optional[bool] = None
    new_nullable: Optional[bool] = None


@dataclass
class TableChange:
    """表变更详情"""
    table_name: str
    change_type: ChangeType
    column_changes: List[ColumnChange] = field(default_factory=list)
    row_count_change: Optional[int] = None


@dataclass
class ScanChangeReport:
    """扫描变更报告"""
    database: str
    scan_time: datetime
    tables_added: List[str] = field(default_factory=list)
    tables_deleted: List[str] = field(default_factory=list)
    tables_modified: List[TableChange] = field(default_factory=list)
    total_tables: int = 0
    duration_ms: int = 0

    @property
    def has_changes(self) -> bool:
        """是否有变更"""
        return bool(
            self.tables_added or
            self.tables_deleted or
            self.tables_modified
        )

    @property
    def change_summary(self) -> Dict[str, int]:
        """变更摘要统计"""
        return {
            "tables_added": len(self.tables_added),
            "tables_deleted": len(self.tables_deleted),
            "tables_modified": len(self.tables_modified),
            "columns_added": sum(
                len(t.column_changes)
                for t in self.tables_modified
                if c.change_type == ChangeType.ADDED
                for c in t.column_changes
            ),
            "columns_deleted": sum(
                len(t.column_changes)
                for t in self.tables_modified
                if c.change_type == ChangeType.DELETED
                for c in t.column_changes
            ),
            "columns_modified": sum(
                len(t.column_changes)
                for t in self.tables_modified
                if c.change_type == ChangeType.MODIFIED
                for c in t.column_changes
            ),
        }


@dataclass
class TableFingerprint:
    """表指纹（用于变更检测）"""
    table_name: str
    column_hash: str  # 列结构的哈希值
    row_count: int
    last_modified: Optional[datetime] = None


class MetadataAutoScanEngine:
    """
    元数据自动扫描引擎

    自动连接数据库发现表结构，同步到元数据库，
    并利用 AI 生成列描述和标注。

    支持变更检测和增量扫描优化。
    """

    def __init__(self, ai_service: Optional[AIService] = None):
        self._scan_results: List[Dict[str, Any]] = []
        self._ai_service = ai_service
        self._fingerprints: Dict[str, Dict[str, TableFingerprint]] = {}  # {db: {table: fingerprint}}
        self._change_reports: List[ScanChangeReport] = []

    def scan_database(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        exclude_tables: List[str] = None,
        ai_annotate: bool = True,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        扫描数据库结构并同步到元数据

        Args:
            connection_info: 数据库连接信息
            database_name: 数据库名
            exclude_tables: 排除的表列表
            ai_annotate: 是否进行 AI 标注
            db_session: 元数据库会话

        Returns:
            扫描结果摘要
        """
        start_time = time.time()
        result = {
            "database": database_name,
            "tables_discovered": 0,
            "tables_created": 0,
            "tables_updated": 0,
            "columns_discovered": 0,
            "columns_annotated": 0,
            "errors": [],
            "duration_seconds": 0,
        }

        if db_session is None:
            result["errors"].append("无元数据库会话")
            return result

        exclude_tables = exclude_tables or []
        exclude_patterns = ["tmp_*", "temp_*", "backup_*"]

        try:
            # 1. 从 INFORMATION_SCHEMA 发现表结构
            tables = self._discover_tables(connection_info, database_name)
            result["tables_discovered"] = len(tables)

            for table_info in tables:
                table_name = table_info["table_name"]

                # 检查排除
                if table_name in exclude_tables:
                    continue
                excluded = False
                for pat in exclude_patterns:
                    regex = pat.replace("*", ".*")
                    if re.match(regex, table_name, re.IGNORECASE):
                        excluded = True
                        break
                if excluded:
                    continue

                # 发现列
                columns = self._discover_columns(connection_info, database_name, table_name)
                result["columns_discovered"] += len(columns)

                # 同步到元数据
                sync_result = self._sync_to_metadata(
                    database_name, table_info, columns, db_session
                )
                if sync_result == "created":
                    result["tables_created"] += 1
                elif sync_result == "updated":
                    result["tables_updated"] += 1

                # AI 标注
                if ai_annotate:
                    annotated = self._ai_annotate_columns(
                        database_name, table_name, columns, connection_info, db_session
                    )
                    result["columns_annotated"] += annotated

            db_session.commit()

        except Exception as e:
            logger.error(f"元数据扫描失败 [{database_name}]: {e}", exc_info=True)
            result["errors"].append(str(e))
            try:
                db_session.rollback()
            except Exception:
                pass

        result["duration_seconds"] = int(time.time() - start_time)
        self._scan_results.append(result)

        logger.info(
            f"元数据扫描完成: {database_name} "
            f"发现 {result['tables_discovered']} 表, "
            f"{result['columns_discovered']} 列, "
            f"AI标注 {result['columns_annotated']} 列"
        )

        return result

    def get_scan_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取扫描历史"""
        return self._scan_results[-limit:]

    # ===== 内部方法 =====

    def _discover_tables(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
    ) -> List[Dict[str, Any]]:
        """从 INFORMATION_SCHEMA 发现表"""
        tables = []
        try:
            from sqlalchemy import create_engine, text

            engine = self._create_engine(connection_info, database_name)
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS, "
                    "DATA_LENGTH, TABLE_COMMENT, CREATE_TIME, UPDATE_TIME "
                    "FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = :db"
                ), {"db": database_name})

                for row in result:
                    tables.append({
                        "table_name": row[0],
                        "table_type": row[1],
                        "row_count": row[2] or 0,
                        "data_length": row[3] or 0,
                        "comment": row[4] or "",
                        "created_at": row[5],
                        "updated_at": row[6],
                    })

        except Exception as e:
            logger.error(f"发现表失败: {e}")

        return tables

    def _discover_columns(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """从 INFORMATION_SCHEMA 发现列"""
        columns = []
        try:
            from sqlalchemy import create_engine, text

            engine = self._create_engine(connection_info, database_name)
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COLUMN_NAME, COLUMN_TYPE, DATA_TYPE, "
                    "IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, "
                    "COLUMN_COMMENT, ORDINAL_POSITION, "
                    "CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION "
                    "FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table "
                    "ORDER BY ORDINAL_POSITION"
                ), {"db": database_name, "table": table_name})

                for row in result:
                    columns.append({
                        "column_name": row[0],
                        "column_type": row[1],
                        "data_type": row[2],
                        "is_nullable": row[3] == "YES",
                        "default_value": row[4],
                        "column_key": row[5],
                        "comment": row[6] or "",
                        "ordinal_position": row[7],
                        "max_length": row[8],
                        "numeric_precision": row[9],
                    })

        except Exception as e:
            logger.error(f"发现列失败 [{table_name}]: {e}")

        return columns

    def _sync_to_metadata(
        self,
        database_name: str,
        table_info: Dict[str, Any],
        columns: List[Dict[str, Any]],
        db_session,
    ) -> str:
        """同步表结构到元数据库"""
        try:
            from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

            # 查找或创建 database
            db = db_session.query(MetadataDatabase).filter(
                MetadataDatabase.database_name == database_name
            ).first()
            if not db:
                db = MetadataDatabase(
                    database_name=database_name,
                    database_type="mysql",
                )
                db_session.add(db)
                db_session.flush()

            # 查找或创建 table
            table_name = table_info["table_name"]
            table = db_session.query(MetadataTable).filter(
                MetadataTable.database_id == db.id,
                MetadataTable.table_name == table_name,
            ).first()

            action = "updated"
            if not table:
                table = MetadataTable(
                    database_id=db.id,
                    table_name=table_name,
                    table_type=table_info.get("table_type", "BASE TABLE"),
                )
                db_session.add(table)
                db_session.flush()
                action = "created"

            # 更新表信息
            if hasattr(table, "row_count"):
                table.row_count = table_info.get("row_count", 0)
            if hasattr(table, "table_comment"):
                table.table_comment = table_info.get("comment", "")

            # 同步列
            existing_cols = {
                col.column_name: col
                for col in db_session.query(MetadataColumn).filter(
                    MetadataColumn.table_id == table.id
                ).all()
            }

            for col_info in columns:
                col_name = col_info["column_name"]
                if col_name in existing_cols:
                    # 更新
                    col = existing_cols[col_name]
                    col.column_type = col_info.get("column_type", col.column_type)
                else:
                    # 创建
                    col = MetadataColumn(
                        table_id=table.id,
                        column_name=col_name,
                        column_type=col_info.get("column_type", "VARCHAR"),
                    )
                    db_session.add(col)

            return action

        except Exception as e:
            logger.error(f"同步元数据失败: {e}")
            return "error"

    def _ai_annotate_columns(
        self,
        database_name: str,
        table_name: str,
        columns: List[Dict[str, Any]],
        connection_info: Dict[str, Any],
        db_session,
    ) -> int:
        """
        AI 标注列描述

        优先使用 LLM 进行智能标注，如果 AI 服务不可用则回退到规则匹配。
        """
        annotated = 0

        try:
            from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

            db = db_session.query(MetadataDatabase).filter(
                MetadataDatabase.database_name == database_name
            ).first()
            if not db:
                return 0

            table = db_session.query(MetadataTable).filter(
                MetadataTable.database_id == db.id,
                MetadataTable.table_name == table_name,
            ).first()
            if not table:
                return 0

            meta_cols = db_session.query(MetadataColumn).filter(
                MetadataColumn.table_id == table.id
            ).all()

            # 找出需要标注的列（没有描述的）
            cols_to_annotate = []
            col_map = {}  # column_name -> MetadataColumn

            for col in meta_cols:
                has_description = (
                    (hasattr(col, "description") and col.description) or
                    (hasattr(col, "ai_description") and col.ai_description)
                )
                if not has_description:
                    col_map[col.column_name] = col
                    # 找到对应的列信息
                    col_info = next(
                        (c for c in columns if c["column_name"] == col.column_name),
                        None
                    )
                    if col_info:
                        cols_to_annotate.append({
                            "name": col.column_name,
                            "type": col_info.get("column_type", ""),
                            "samples": [],  # 将在下面填充
                        })

            if not cols_to_annotate:
                return 0

            # 获取样本数据
            samples_data = self._sample_column_values(
                connection_info, database_name, table_name,
                [c["name"] for c in cols_to_annotate]
            )
            for col_data in cols_to_annotate:
                col_data["samples"] = samples_data.get(col_data["name"], [])

            # 尝试使用 AI 服务进行标注
            ai_service = self._ai_service or get_ai_service()
            use_ai = ai_service.config.enabled and ai_service.health_check()

            if use_ai:
                logger.info(f"使用 AI 服务标注 {len(cols_to_annotate)} 列 [{table_name}]")
                try:
                    # 批量 AI 标注
                    ai_results = ai_service.batch_annotate_columns(
                        table_name, cols_to_annotate
                    )

                    # 应用 AI 标注结果
                    for result in ai_results:
                        col_name = result.get("column_name")
                        if col_name in col_map:
                            col = col_map[col_name]
                            description = result.get("description", "")
                            business_term = result.get("business_term", "")

                            if description:
                                if hasattr(col, "ai_description"):
                                    col.ai_description = description
                                elif hasattr(col, "description"):
                                    col.description = description

                                if hasattr(col, "business_term") and business_term:
                                    col.business_term = business_term

                                annotated += 1
                                logger.debug(f"AI 标注: {col_name} -> {description}")

                except Exception as e:
                    logger.warning(f"AI 批量标注失败，回退到规则匹配: {e}")
                    use_ai = False

            # 如果 AI 不可用或失败，使用规则匹配
            if not use_ai:
                logger.info(f"使用规则匹配标注 [{table_name}]")
                annotated = self._rule_based_annotate(col_map)

        except Exception as e:
            logger.warning(f"AI 标注失败: {e}")

        return annotated

    def _sample_column_values(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        table_name: str,
        column_names: List[str],
        sample_size: int = 5,
    ) -> Dict[str, List[str]]:
        """
        从数据库采样列值

        Args:
            connection_info: 数据库连接信息
            database_name: 数据库名
            table_name: 表名
            column_names: 列名列表
            sample_size: 每列采样数量

        Returns:
            {column_name: [sample_values]}
        """
        samples = {col: [] for col in column_names}

        if not column_names:
            return samples

        try:
            from sqlalchemy import text

            engine = self._create_engine(connection_info, database_name)
            with engine.connect() as conn:
                # 构建采样查询 - 获取非空的不同值
                for col_name in column_names:
                    try:
                        # 使用 DISTINCT 和 LIMIT 获取样本
                        query = text(
                            f"SELECT DISTINCT `{col_name}` "
                            f"FROM `{table_name}` "
                            f"WHERE `{col_name}` IS NOT NULL "
                            f"LIMIT :limit"
                        )
                        result = conn.execute(query, {"limit": sample_size})

                        for row in result:
                            value = row[0]
                            if value is not None:
                                # 转换为字符串，截断过长的值
                                str_value = str(value)[:200]
                                samples[col_name].append(str_value)

                    except Exception as e:
                        logger.debug(f"采样列 {col_name} 失败: {e}")

        except Exception as e:
            logger.warning(f"采样数据失败 [{table_name}]: {e}")

        return samples

    def _rule_based_annotate(
        self,
        col_map: Dict[str, Any],
    ) -> int:
        """
        基于规则的列标注（回退方案）

        Args:
            col_map: {column_name: MetadataColumn}

        Returns:
            标注的列数
        """
        annotated = 0

        # 基于列名规则生成描述
        name_descriptions = {
            "id": "主键ID",
            "name": "名称",
            "title": "标题",
            "description": "描述",
            "status": "状态",
            "type": "类型",
            "created_at": "创建时间",
            "updated_at": "更新时间",
            "deleted_at": "删除时间",
            "created_by": "创建者",
            "updated_by": "更新者",
            "is_active": "是否启用",
            "is_deleted": "是否删除",
            "sort_order": "排序序号",
            "remark": "备注",
            "email": "邮箱地址",
            "phone": "电话号码",
            "mobile": "手机号码",
            "address": "地址",
            "age": "年龄",
            "gender": "性别",
            "avatar": "头像",
            "password": "密码",
            "token": "令牌",
            "amount": "金额",
            "price": "价格",
            "quantity": "数量",
            "total": "合计",
            "count": "计数",
        }

        # 中文前缀描述
        prefix_descriptions = {
            "user_": "用户",
            "order_": "订单",
            "product_": "产品",
            "customer_": "客户",
            "pay_": "支付",
            "sys_": "系统",
        }

        for col_name, col in col_map.items():
            col_lower = col_name.lower()
            description = ""

            # 精确匹配
            if col_lower in name_descriptions:
                description = name_descriptions[col_lower]
            else:
                # 前缀匹配
                for prefix, prefix_desc in prefix_descriptions.items():
                    if col_lower.startswith(prefix):
                        suffix = col_lower[len(prefix):]
                        if suffix in name_descriptions:
                            description = f"{prefix_desc}{name_descriptions[suffix]}"
                        else:
                            description = f"{prefix_desc}相关字段"
                        break

                # 后缀匹配
                if not description:
                    for suffix, suffix_desc in name_descriptions.items():
                        if col_lower.endswith(f"_{suffix}"):
                            description = suffix_desc
                            break

                # 通用模式
                if not description:
                    if col_lower.endswith("_id"):
                        ref = col_lower[:-3].replace("_", " ")
                        description = f"{ref} 关联ID"
                    elif col_lower.endswith("_time") or col_lower.endswith("_date"):
                        description = "时间字段"
                    elif col_lower.endswith("_flag") or col_lower.startswith("is_"):
                        description = "标识字段"
                    elif col_lower.endswith("_url") or col_lower.endswith("_path"):
                        description = "路径/链接"

            if description:
                if hasattr(col, "description"):
                    col.description = description
                    annotated += 1
                elif hasattr(col, "ai_description"):
                    col.ai_description = description
                    annotated += 1

        return annotated

    def _create_engine(self, connection_info: Dict[str, Any], database_name: str):
        """创建 SQLAlchemy Engine"""
        from sqlalchemy import create_engine

        db_type = connection_info.get("type", "mysql")
        host = connection_info.get("host", "localhost")
        port = connection_info.get("port", 3306)
        username = connection_info.get("username", "root")
        password = connection_info.get("password", "")

        if db_type == "mysql":
            url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"
        elif db_type == "postgresql":
            url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database_name}"
        else:
            url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"

        return create_engine(url, pool_pre_ping=True, pool_size=2)

    def scan_and_profile(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        table_name: str,
        sample_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        扫描并生成数据概况（列级统计）

        Returns:
            列级统计信息（空值率、唯一值数、最大最小值等）
        """
        profile = {
            "database": database_name,
            "table": table_name,
            "columns": [],
        }

        try:
            from sqlalchemy import create_engine, text

            engine = self._create_engine(connection_info, database_name)

            with engine.connect() as conn:
                # 获取列信息
                columns = self._discover_columns(connection_info, database_name, table_name)

                # 获取总行数
                row_result = conn.execute(text(
                    f"SELECT COUNT(*) FROM `{table_name}`"
                ))
                total_rows = row_result.scalar() or 0
                profile["total_rows"] = total_rows

                # 每列统计
                for col_info in columns:
                    col_name = col_info["column_name"]
                    col_profile = {
                        "column_name": col_name,
                        "column_type": col_info["column_type"],
                        "total_rows": total_rows,
                    }

                    try:
                        stats = conn.execute(text(
                            f"SELECT "
                            f"COUNT(*) as total, "
                            f"COUNT(`{col_name}`) as non_null, "
                            f"COUNT(DISTINCT `{col_name}`) as distinct_count "
                            f"FROM `{table_name}`"
                        ))
                        row = stats.fetchone()
                        if row:
                            col_profile["non_null_count"] = row[1]
                            col_profile["null_count"] = total_rows - row[1]
                            col_profile["null_rate"] = round(
                                (total_rows - row[1]) / total_rows, 4
                            ) if total_rows > 0 else 0
                            col_profile["distinct_count"] = row[2]
                            col_profile["uniqueness"] = round(
                                row[2] / row[1], 4
                            ) if row[1] > 0 else 0
                    except Exception:
                        pass

                    profile["columns"].append(col_profile)

        except Exception as e:
            logger.error(f"数据概况生成失败: {e}")
            profile["error"] = str(e)

        return profile

    # ========================================
    # 变更检测功能
    # ========================================

    def detect_changes(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        exclude_tables: List[str] = None,
    ) -> ScanChangeReport:
        """
        检测元数据变更（对比上次扫描）

        Args:
            connection_info: 数据库连接信息
            database_name: 数据库名
            exclude_tables: 排除的表列表

        Returns:
            变更报告
        """
        start_time = time.time()
        report = ScanChangeReport(
            database=database_name,
            scan_time=datetime.now(),
        )

        if database_name not in self._fingerprints:
            self._fingerprints[database_name] = {}

        old_fingerprints = self._fingerprints[database_name]
        new_fingerprints: Dict[str, TableFingerprint] = {}

        try:
            # 获取当前表结构
            tables = self._discover_tables(connection_info, database_name)
            report.total_tables = len(tables)

            exclude_tables = exclude_tables or []
            exclude_patterns = ["tmp_*", "temp_*", "backup_*"]

            for table_info in tables:
                table_name = table_info["table_name"]

                # 检查排除
                if table_name in exclude_tables:
                    continue
                excluded = False
                for pat in exclude_patterns:
                    regex = pat.replace("*", ".*")
                    if re.match(regex, table_name, re.IGNORECASE):
                        excluded = True
                        break
                if excluded:
                    continue

                # 获取列信息
                columns = self._discover_columns(connection_info, database_name, table_name)

                # 计算指纹
                fingerprint = self._calculate_fingerprint(table_name, columns, table_info)
                new_fingerprints[table_name] = fingerprint

                # 对比旧指纹
                if table_name not in old_fingerprints:
                    # 新增表
                    report.tables_added.append(table_name)
                    logger.info(f"检测到新增表: {table_name}")
                else:
                    old_fp = old_fingerprints[table_name]
                    if old_fp.column_hash != fingerprint.column_hash:
                        # 表结构有变化
                        table_change = self._detect_table_column_changes(
                            table_name, old_fp, fingerprint, connection_info,
                            database_name
                        )
                        if table_change:
                            report.tables_modified.append(table_change)
                            logger.info(
                                f"检测到表结构变更: {table_name} "
                                f"(新增{len([c for c in table_change.column_changes if c.change_type == ChangeType.ADDED])}列, "
                                f"删除{len([c for c in table_change.column_changes if c.change_type == ChangeType.DELETED])}列, "
                                f"修改{len([c for c in table_change.column_changes if c.change_type == ChangeType.MODIFIED])}列)"
                            )

            # 检测删除的表
            for table_name in old_fingerprints:
                if table_name not in new_fingerprints:
                    report.tables_deleted.append(table_name)
                    logger.info(f"检测到删除表: {table_name}")

            # 更新指纹缓存
            self._fingerprints[database_name] = new_fingerprints

        except Exception as e:
            logger.error(f"变更检测失败: {e}", exc_info=True)

        report.duration_ms = int((time.time() - start_time) * 1000)
        self._change_reports.append(report)

        return report

    def _calculate_fingerprint(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        table_info: Dict[str, Any],
    ) -> TableFingerprint:
        """计算表指纹"""
        # 对列按名称排序，确保顺序不影响哈希
        sorted_columns = sorted(columns, key=lambda c: c["column_name"])

        # 构建用于哈希的字符串
        hash_parts = []
        for col in sorted_columns:
            hash_parts.append(f"{col['column_name']}:{col['column_type']}:{col.get('is_nullable', True)}")

        hash_string = "|".join(hash_parts)
        column_hash = md5(hash_string.encode()).hexdigest()[:16]

        return TableFingerprint(
            table_name=table_name,
            column_hash=column_hash,
            row_count=table_info.get("row_count", 0),
            last_modified=table_info.get("updated_at"),
        )

    def _detect_table_column_changes(
        self,
        table_name: str,
        old_fp: TableFingerprint,
        new_fp: TableFingerprint,
        connection_info: Dict[str, Any],
        database_name: str,
    ) -> Optional[TableChange]:
        """
        检测表的列级变更

        注意：这里需要重新获取列信息进行详细对比
        """
        try:
            old_columns = self._discover_columns(connection_info, database_name, table_name)
            # 实际上这里需要从缓存中获取旧列信息，简化处理
            # 在实际应用中，应该缓存完整的列信息而不仅仅是哈希

            # 重新获取当前列信息
            current_columns = self._discover_columns(connection_info, database_name, table_name)

            # 构建列映射
            current_col_map = {c["column_name"]: c for c in current_columns}

            # 这里使用简单的对比，实际应该与旧的列信息对比
            column_changes = []

            # 由于只有哈希，这里简化处理
            # 在生产环境中应该缓存完整的列结构

            if old_fp.column_hash != new_fp.column_hash:
                # 有变更但无法确定具体是哪些列（因为没有缓存旧列结构）
                # 返回一个通用的修改标记
                return TableChange(
                    table_name=table_name,
                    change_type=ChangeType.MODIFIED,
                )

            return None

        except Exception as e:
            logger.warning(f"检测列变更失败 [{table_name}]: {e}")
            return None

    def get_latest_change_report(self, database: str) -> Optional[ScanChangeReport]:
        """获取最新的变更报告"""
        for report in reversed(self._change_reports):
            if report.database == database:
                return report
        return None

    def get_all_change_reports(self, database: Optional[str] = None) -> List[ScanChangeReport]:
        """获取所有变更报告"""
        if database:
            return [r for r in self._change_reports if r.database == database]
        return self._change_reports.copy()

    def incremental_scan(
        self,
        connection_info: Dict[str, Any],
        database_name: str,
        exclude_tables: List[str] = None,
        ai_annotate: bool = True,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        增量扫描（只处理变更的表）

        Args:
            connection_info: 数据库连接信息
            database_name: 数据库名
            exclude_tables: 排除的表列表
            ai_annotate: 是否进行 AI 标注
            db_session: 元数据库会话

        Returns:
            扫描结果摘要
        """
        start_time = time.time()
        result = {
            "database": database_name,
            "tables_scanned": 0,
            "tables_skipped": 0,
            "tables_created": 0,
            "tables_updated": 0,
            "columns_annotated": 0,
            "errors": [],
            "duration_seconds": 0,
            "is_incremental": True,
        }

        if db_session is None:
            result["errors"].append("无元数据库会话")
            return result

        try:
            # 先检测变更
            change_report = self.detect_changes(connection_info, database_name, exclude_tables)

            if not change_report.has_changes:
                logger.info(f"增量扫描: {database_name} 无变更")
                result["tables_skipped"] = change_report.total_tables
                result["duration_seconds"] = int(time.time() - start_time)
                return result

            logger.info(
                f"增量扫描: {database_name} 发现变更 "
                f"(新增{len(change_report.tables_added)}, "
                f"删除{len(change_report.tables_deleted)}, "
                f"修改{len(change_report.tables_modified)})"
            )

            # 获取需要处理的表
            tables_to_process = set(change_report.tables_added)
            for table_change in change_report.tables_modified:
                tables_to_process.add(table_change.table_name)

            result["tables_scanned"] = len(tables_to_process)
            result["tables_skipped"] = change_report.total_tables - len(tables_to_process)

            # 处理变更的表
            exclude_tables = exclude_tables or []
            exclude_patterns = ["tmp_*", "temp_*", "backup_*"]

            for table_name in tables_to_process:
                # 检查排除
                if table_name in exclude_tables:
                    continue

                try:
                    # 获取表信息
                    tables = self._discover_tables(connection_info, database_name)
                    table_info = next((t for t in tables if t["table_name"] == table_name), None)
                    if not table_info:
                        continue

                    # 获取列信息
                    columns = self._discover_columns(connection_info, database_name, table_name)

                    # 同步到元数据
                    sync_result = self._sync_to_metadata(
                        database_name, table_info, columns, db_session
                    )
                    if sync_result == "created":
                        result["tables_created"] += 1
                    elif sync_result == "updated":
                        result["tables_updated"] += 1

                    # AI 标注
                    if ai_annotate:
                        annotated = self._ai_annotate_columns(
                            database_name, table_name, columns, connection_info, db_session
                        )
                        result["columns_annotated"] += annotated

                except Exception as e:
                    logger.error(f"处理表 {table_name} 失败: {e}")
                    result["errors"].append(f"{table_name}: {str(e)}")

            db_session.commit()

        except Exception as e:
            logger.error(f"增量扫描失败 [{database_name}]: {e}", exc_info=True)
            result["errors"].append(str(e))
            try:
                db_session.rollback()
            except Exception:
                pass

        result["duration_seconds"] = int(time.time() - start_time)
        self._scan_results.append(result)

        logger.info(
            f"增量扫描完成: {database_name} "
            f"处理 {result['tables_scanned']} 表, "
            f"跳过 {result['tables_skipped']} 表"
        )

        return result


# 全局实例
_metadata_scan_engine: Optional[MetadataAutoScanEngine] = None


def get_metadata_auto_scan_engine(
    ai_service: Optional[AIService] = None,
) -> MetadataAutoScanEngine:
    """
    获取元数据自动扫描引擎单例

    Args:
        ai_service: AI 服务实例，如果为 None 则使用默认实例
    """
    global _metadata_scan_engine
    if _metadata_scan_engine is None:
        _metadata_scan_engine = MetadataAutoScanEngine(ai_service=ai_service)
    return _metadata_scan_engine
