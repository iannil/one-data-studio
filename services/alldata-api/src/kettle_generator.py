"""
元数据驱动的 Kettle 配置自动生成服务
Phase 1 P2: 数据感知汇聚 - ETL 自动化

基于元数据自动生成 Kettle 转换配置 (.ktr) 和作业配置 (.kjb)

功能：
- 从源到目标的数据同步转换生成
- 支持多种数据源类型（数据库、文件、API）
- 字段映射与类型转换
- 数据清洗步骤生成
- 增量同步支持
"""

import json
import logging
import os
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.dom import minidom

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """数据源类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    HIVE = "hive"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    API = "api"


class TransformationType(Enum):
    """转换类型"""
    DIRECT_COPY = "direct_copy"  # 直接复制
    TYPE_CONVERSION = "type_conversion"  # 类型转换
    VALUE_MAPPING = "value_mapping"  # 值映射
    FORMULA = "formula"  # 公式计算
    STRING_OPERATION = "string_operation"  # 字符串操作
    DATE_OPERATION = "date_operation"  # 日期操作
    FILTER = "filter"  # 过滤
    AGGREGATION = "aggregation"  # 聚合


@dataclass
class ColumnMapping:
    """字段映射"""
    source_column: str
    target_column: str
    source_type: str = "String"
    target_type: str = "String"
    transformation: Optional[TransformationType] = None
    transformation_config: Optional[Dict[str, Any]] = None
    default_value: Optional[str] = None
    nullable: bool = True


@dataclass
class SourceConfig:
    """数据源配置"""
    source_type: SourceType
    connection_name: str = ""
    # 数据库配置
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""  # 实际使用时应该使用密钥管理
    schema: str = ""
    table: str = ""
    query: str = ""  # 自定义查询
    # 文件配置
    file_path: str = ""
    file_format: str = ""
    delimiter: str = ","
    encoding: str = "UTF-8"
    header: bool = True
    # API 配置
    api_url: str = ""
    api_method: str = "GET"
    api_headers: Dict[str, str] = field(default_factory=dict)
    # 增量配置
    incremental_field: str = ""  # 增量字段
    incremental_value: str = ""  # 上次同步值


@dataclass
class TargetConfig:
    """目标配置"""
    target_type: SourceType
    connection_name: str = ""
    # 数据库配置
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    schema: str = ""
    table: str = ""
    # 写入模式
    write_mode: str = "insert"  # insert, update, upsert, truncate_insert
    batch_size: int = 1000
    commit_size: int = 10000
    # 主键（用于 update/upsert）
    primary_keys: List[str] = field(default_factory=list)


@dataclass
class TransformationConfig:
    """转换配置"""
    name: str
    description: str = ""
    source: SourceConfig = None
    target: TargetConfig = None
    column_mappings: List[ColumnMapping] = field(default_factory=list)
    # 额外步骤
    add_filter: bool = False
    filter_condition: str = ""
    add_sort: bool = False
    sort_fields: List[Tuple[str, bool]] = field(default_factory=list)  # (field, ascending)
    add_distinct: bool = False
    # 错误处理
    error_handling: str = "abort"  # abort, skip, redirect
    error_redirect_step: str = ""


class KettleConfigGenerator:
    """
    Kettle 配置生成器

    基于元数据自动生成 Kettle 转换和作业配置
    """

    # 数据库连接类型映射
    DB_TYPE_MAPPING = {
        SourceType.MYSQL: ("MYSQL", "com.mysql.cj.jdbc.Driver", 3306),
        SourceType.POSTGRESQL: ("POSTGRESQL", "org.postgresql.Driver", 5432),
        SourceType.ORACLE: ("ORACLE", "oracle.jdbc.driver.OracleDriver", 1521),
        SourceType.SQLSERVER: ("MSSQLNATIVE", "com.microsoft.sqlserver.jdbc.SQLServerDriver", 1433),
        SourceType.HIVE: ("HIVE2", "org.apache.hive.jdbc.HiveDriver", 10000),
    }

    # Kettle 数据类型映射
    KETTLE_TYPE_MAPPING = {
        # 通用类型
        "string": "String",
        "varchar": "String",
        "char": "String",
        "text": "String",
        "nvarchar": "String",
        "nchar": "String",
        # 数值类型
        "int": "Integer",
        "integer": "Integer",
        "bigint": "Integer",
        "smallint": "Integer",
        "tinyint": "Integer",
        "float": "Number",
        "double": "Number",
        "decimal": "BigNumber",
        "numeric": "BigNumber",
        "real": "Number",
        # 日期类型
        "date": "Date",
        "datetime": "Date",
        "timestamp": "Date",
        "time": "Date",
        # 布尔类型
        "boolean": "Boolean",
        "bool": "Boolean",
        "bit": "Boolean",
        # 二进制类型
        "binary": "Binary",
        "varbinary": "Binary",
        "blob": "Binary",
        "bytea": "Binary",
    }

    def __init__(self):
        pass

    def normalize_type(self, db_type: str) -> str:
        """将数据库类型映射为 Kettle 类型"""
        if not db_type:
            return "String"
        db_type_lower = db_type.lower().split("(")[0].strip()
        return self.KETTLE_TYPE_MAPPING.get(db_type_lower, "String")

    def generate_transformation(self, config: TransformationConfig) -> str:
        """
        生成 Kettle 转换配置 (.ktr)

        Args:
            config: 转换配置

        Returns:
            XML 字符串
        """
        # 创建根元素
        root = ET.Element("transformation")

        # 添加基本信息
        info = ET.SubElement(root, "info")
        ET.SubElement(info, "name").text = config.name
        ET.SubElement(info, "description").text = config.description or f"Auto-generated transformation: {config.name}"
        ET.SubElement(info, "extended_description")
        ET.SubElement(info, "trans_version")
        ET.SubElement(info, "trans_type").text = "Normal"
        ET.SubElement(info, "trans_status").text = "0"
        ET.SubElement(info, "directory").text = "/"

        # 参数
        parameters = ET.SubElement(info, "parameters")

        # 添加日志配置
        self._add_log_config(info)

        # 添加连接
        if config.source and config.source.source_type in self.DB_TYPE_MAPPING:
            self._add_database_connection(root, config.source, "source_connection")
        if config.target and config.target.target_type in self.DB_TYPE_MAPPING:
            self._add_database_connection(root, config.target, "target_connection")

        # 添加步骤顺序
        order = ET.SubElement(root, "order")

        # 构建步骤列表
        steps = []
        step_names = []

        # 1. 输入步骤
        if config.source:
            input_step = self._create_input_step(config.source, config.column_mappings)
            if input_step is not None:
                steps.append(input_step)
                step_names.append(input_step.find("name").text)

        # 2. 过滤步骤
        if config.add_filter and config.filter_condition:
            filter_step = self._create_filter_step(config.filter_condition)
            steps.append(filter_step)
            step_names.append(filter_step.find("name").text)

        # 3. 排序步骤
        if config.add_sort and config.sort_fields:
            sort_step = self._create_sort_step(config.sort_fields)
            steps.append(sort_step)
            step_names.append(sort_step.find("name").text)

        # 4. 去重步骤
        if config.add_distinct:
            distinct_step = self._create_distinct_step([m.target_column for m in config.column_mappings])
            steps.append(distinct_step)
            step_names.append(distinct_step.find("name").text)

        # 5. 字段映射/选择步骤
        if config.column_mappings:
            select_step = self._create_select_values_step(config.column_mappings)
            steps.append(select_step)
            step_names.append(select_step.find("name").text)

        # 6. 输出步骤
        if config.target:
            output_step = self._create_output_step(config.target, config.column_mappings)
            if output_step is not None:
                steps.append(output_step)
                step_names.append(output_step.find("name").text)

        # 添加步骤连接顺序
        for i in range(len(step_names) - 1):
            hop = ET.SubElement(order, "hop")
            ET.SubElement(hop, "from").text = step_names[i]
            ET.SubElement(hop, "to").text = step_names[i + 1]
            ET.SubElement(hop, "enabled").text = "Y"

        # 添加步骤到根元素
        for step in steps:
            root.append(step)

        # 添加步骤错误处理
        step_error_handling = ET.SubElement(root, "step_error_handling")

        # 生成格式化的 XML
        return self._prettify_xml(root)

    def generate_job(
        self,
        job_name: str,
        transformations: List[str],
        description: str = "",
        sequential: bool = True,
    ) -> str:
        """
        生成 Kettle 作业配置 (.kjb)

        Args:
            job_name: 作业名称
            transformations: 转换文件路径列表
            description: 作业描述
            sequential: 是否顺序执行

        Returns:
            XML 字符串
        """
        root = ET.Element("job")

        # 基本信息
        ET.SubElement(root, "name").text = job_name
        ET.SubElement(root, "description").text = description or f"Auto-generated job: {job_name}"
        ET.SubElement(root, "extended_description")
        ET.SubElement(root, "job_version")
        ET.SubElement(root, "job_status").text = "0"
        ET.SubElement(root, "directory").text = "/"
        ET.SubElement(root, "created_user").text = "admin"
        ET.SubElement(root, "created_date").text = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        ET.SubElement(root, "modified_user").text = "admin"
        ET.SubElement(root, "modified_date").text = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        # 参数
        parameters = ET.SubElement(root, "parameters")

        # 添加步骤
        entries = []

        # 1. START 步骤
        start_entry = ET.Element("entry")
        ET.SubElement(start_entry, "name").text = "START"
        ET.SubElement(start_entry, "description")
        ET.SubElement(start_entry, "type").text = "SPECIAL"
        ET.SubElement(start_entry, "start").text = "Y"
        ET.SubElement(start_entry, "dummy").text = "N"
        ET.SubElement(start_entry, "repeat").text = "N"
        ET.SubElement(start_entry, "schedulerType").text = "0"
        ET.SubElement(start_entry, "parallel").text = "N"
        ET.SubElement(start_entry, "xloc").text = "50"
        ET.SubElement(start_entry, "yloc").text = "50"
        entries.append(start_entry)

        # 2. 转换步骤
        x_loc = 200
        for i, trans_path in enumerate(transformations):
            trans_entry = ET.Element("entry")
            trans_name = os.path.splitext(os.path.basename(trans_path))[0]
            ET.SubElement(trans_entry, "name").text = trans_name
            ET.SubElement(trans_entry, "description")
            ET.SubElement(trans_entry, "type").text = "TRANS"
            ET.SubElement(trans_entry, "specification_method").text = "filename"
            ET.SubElement(trans_entry, "trans_object_id")
            ET.SubElement(trans_entry, "filename").text = trans_path
            ET.SubElement(trans_entry, "transname")
            ET.SubElement(trans_entry, "directory")
            ET.SubElement(trans_entry, "arg_from_previous").text = "N"
            ET.SubElement(trans_entry, "params_from_previous").text = "N"
            ET.SubElement(trans_entry, "exec_per_row").text = "N"
            ET.SubElement(trans_entry, "clear_rows").text = "N"
            ET.SubElement(trans_entry, "clear_files").text = "N"
            ET.SubElement(trans_entry, "set_logfile").text = "N"
            ET.SubElement(trans_entry, "logfile")
            ET.SubElement(trans_entry, "logext")
            ET.SubElement(trans_entry, "add_date").text = "N"
            ET.SubElement(trans_entry, "add_time").text = "N"
            ET.SubElement(trans_entry, "loglevel").text = "Basic"
            ET.SubElement(trans_entry, "cluster").text = "N"
            ET.SubElement(trans_entry, "slave_server_name")
            ET.SubElement(trans_entry, "set_append_logfile").text = "N"
            ET.SubElement(trans_entry, "wait_until_finished").text = "Y"
            ET.SubElement(trans_entry, "follow_abort_remote").text = "N"
            ET.SubElement(trans_entry, "create_parent_folder").text = "N"
            ET.SubElement(trans_entry, "logging_remote_work").text = "N"
            ET.SubElement(trans_entry, "parallel").text = "N" if sequential else "Y"
            ET.SubElement(trans_entry, "xloc").text = str(x_loc)
            ET.SubElement(trans_entry, "yloc").text = "50"
            entries.append(trans_entry)
            x_loc += 150

        # 3. SUCCESS 步骤
        success_entry = ET.Element("entry")
        ET.SubElement(success_entry, "name").text = "Success"
        ET.SubElement(success_entry, "description")
        ET.SubElement(success_entry, "type").text = "SUCCESS"
        ET.SubElement(success_entry, "parallel").text = "N"
        ET.SubElement(success_entry, "xloc").text = str(x_loc)
        ET.SubElement(success_entry, "yloc").text = "50"
        entries.append(success_entry)

        # 添加所有步骤
        for entry in entries:
            root.append(entry)

        # 添加连接
        hops = ET.SubElement(root, "hops")

        # START -> 第一个转换
        if len(transformations) > 0:
            hop = ET.SubElement(hops, "hop")
            ET.SubElement(hop, "from").text = "START"
            trans_name = os.path.splitext(os.path.basename(transformations[0]))[0]
            ET.SubElement(hop, "to").text = trans_name
            ET.SubElement(hop, "from_nr").text = "0"
            ET.SubElement(hop, "to_nr").text = "0"
            ET.SubElement(hop, "enabled").text = "Y"
            ET.SubElement(hop, "evaluation").text = "Y"
            ET.SubElement(hop, "unconditional").text = "Y"

        # 转换之间的连接
        for i in range(len(transformations) - 1):
            hop = ET.SubElement(hops, "hop")
            from_name = os.path.splitext(os.path.basename(transformations[i]))[0]
            to_name = os.path.splitext(os.path.basename(transformations[i + 1]))[0]
            ET.SubElement(hop, "from").text = from_name
            ET.SubElement(hop, "to").text = to_name
            ET.SubElement(hop, "from_nr").text = "0"
            ET.SubElement(hop, "to_nr").text = "0"
            ET.SubElement(hop, "enabled").text = "Y"
            ET.SubElement(hop, "evaluation").text = "Y"
            ET.SubElement(hop, "unconditional").text = "N"

        # 最后一个转换 -> Success
        if len(transformations) > 0:
            hop = ET.SubElement(hops, "hop")
            last_trans_name = os.path.splitext(os.path.basename(transformations[-1]))[0]
            ET.SubElement(hop, "from").text = last_trans_name
            ET.SubElement(hop, "to").text = "Success"
            ET.SubElement(hop, "from_nr").text = "0"
            ET.SubElement(hop, "to_nr").text = "0"
            ET.SubElement(hop, "enabled").text = "Y"
            ET.SubElement(hop, "evaluation").text = "Y"
            ET.SubElement(hop, "unconditional").text = "N"

        # 注释
        notepads = ET.SubElement(root, "notepads")

        return self._prettify_xml(root)

    def generate_from_metadata(
        self,
        source_table_meta: Dict[str, Any],
        target_table_meta: Dict[str, Any],
        source_connection: Dict[str, Any],
        target_connection: Dict[str, Any],
        transformation_name: str = None,
        options: Dict[str, Any] = None,
    ) -> str:
        """
        从元数据生成转换配置

        Args:
            source_table_meta: 源表元数据
            target_table_meta: 目标表元数据
            source_connection: 源连接配置
            target_connection: 目标连接配置
            transformation_name: 转换名称
            options: 额外选项

        Returns:
            XML 字符串
        """
        options = options or {}

        # 构建源配置
        source_type = self._detect_source_type(source_connection.get("type", "mysql"))
        source = SourceConfig(
            source_type=source_type,
            connection_name=source_connection.get("name", "source_db"),
            host=source_connection.get("host", "localhost"),
            port=source_connection.get("port", self.DB_TYPE_MAPPING.get(source_type, ("", "", 3306))[2]),
            database=source_connection.get("database", ""),
            username=source_connection.get("username", ""),
            password=source_connection.get("password", ""),
            schema=source_table_meta.get("schema", ""),
            table=source_table_meta.get("table_name", ""),
            query=options.get("source_query", ""),
            incremental_field=options.get("incremental_field", ""),
            incremental_value=options.get("incremental_value", ""),
        )

        # 构建目标配置
        target_type = self._detect_source_type(target_connection.get("type", "mysql"))
        target = TargetConfig(
            target_type=target_type,
            connection_name=target_connection.get("name", "target_db"),
            host=target_connection.get("host", "localhost"),
            port=target_connection.get("port", self.DB_TYPE_MAPPING.get(target_type, ("", "", 3306))[2]),
            database=target_connection.get("database", ""),
            username=target_connection.get("username", ""),
            password=target_connection.get("password", ""),
            schema=target_table_meta.get("schema", ""),
            table=target_table_meta.get("table_name", ""),
            write_mode=options.get("write_mode", "insert"),
            batch_size=options.get("batch_size", 1000),
            commit_size=options.get("commit_size", 10000),
            primary_keys=options.get("primary_keys", []),
        )

        # 构建字段映射
        column_mappings = self._build_column_mappings(
            source_table_meta.get("columns", []),
            target_table_meta.get("columns", []),
            options.get("column_mappings", {}),
        )

        # 构建转换配置
        trans_name = transformation_name or f"sync_{source.table}_to_{target.table}"
        config = TransformationConfig(
            name=trans_name,
            description=f"Auto-generated: Sync {source.schema}.{source.table} to {target.schema}.{target.table}",
            source=source,
            target=target,
            column_mappings=column_mappings,
            add_filter=bool(options.get("filter_condition")),
            filter_condition=options.get("filter_condition", ""),
            add_sort=bool(options.get("sort_fields")),
            sort_fields=options.get("sort_fields", []),
            add_distinct=options.get("distinct", False),
        )

        return self.generate_transformation(config)

    def _detect_source_type(self, type_str: str) -> SourceType:
        """检测数据源类型"""
        type_lower = type_str.lower()
        if "mysql" in type_lower:
            return SourceType.MYSQL
        elif "postgres" in type_lower or "pg" in type_lower:
            return SourceType.POSTGRESQL
        elif "oracle" in type_lower:
            return SourceType.ORACLE
        elif "sqlserver" in type_lower or "mssql" in type_lower:
            return SourceType.SQLSERVER
        elif "hive" in type_lower:
            return SourceType.HIVE
        elif "csv" in type_lower:
            return SourceType.CSV
        elif "excel" in type_lower or "xlsx" in type_lower:
            return SourceType.EXCEL
        elif "json" in type_lower:
            return SourceType.JSON
        else:
            return SourceType.MYSQL

    def _build_column_mappings(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        custom_mappings: Dict[str, str] = None,
    ) -> List[ColumnMapping]:
        """构建字段映射"""
        mappings = []
        custom_mappings = custom_mappings or {}

        # 构建目标列字典
        target_col_dict = {col.get("column_name", col.get("name", "")).lower(): col for col in target_columns}

        for src_col in source_columns:
            src_name = src_col.get("column_name", src_col.get("name", ""))
            src_type = src_col.get("data_type", src_col.get("type", "string"))

            # 检查自定义映射
            if src_name in custom_mappings:
                tgt_name = custom_mappings[src_name]
            else:
                # 尝试同名映射
                tgt_name = src_name

            # 查找目标列
            tgt_col = target_col_dict.get(tgt_name.lower())
            if tgt_col:
                tgt_type = tgt_col.get("data_type", tgt_col.get("type", "string"))
                mappings.append(ColumnMapping(
                    source_column=src_name,
                    target_column=tgt_name,
                    source_type=self.normalize_type(src_type),
                    target_type=self.normalize_type(tgt_type),
                    nullable=tgt_col.get("nullable", True),
                ))

        return mappings

    def _add_log_config(self, info: ET.Element):
        """添加日志配置"""
        log = ET.SubElement(info, "log")

        # 转换日志表
        trans_log = ET.SubElement(log, "trans-log-table")
        ET.SubElement(trans_log, "connection")
        ET.SubElement(trans_log, "schema")
        ET.SubElement(trans_log, "table")
        ET.SubElement(trans_log, "size_limit_lines")
        ET.SubElement(trans_log, "interval")
        ET.SubElement(trans_log, "timeout_days")

        # 性能日志表
        perf_log = ET.SubElement(log, "perf-log-table")
        ET.SubElement(perf_log, "connection")
        ET.SubElement(perf_log, "schema")
        ET.SubElement(perf_log, "table")
        ET.SubElement(perf_log, "interval")
        ET.SubElement(perf_log, "timeout_days")

        # 步骤日志表
        step_log = ET.SubElement(log, "step-log-table")
        ET.SubElement(step_log, "connection")
        ET.SubElement(step_log, "schema")
        ET.SubElement(step_log, "table")
        ET.SubElement(step_log, "timeout_days")

        # 指标日志表
        metrics_log = ET.SubElement(log, "metrics-log-table")
        ET.SubElement(metrics_log, "connection")
        ET.SubElement(metrics_log, "schema")
        ET.SubElement(metrics_log, "table")
        ET.SubElement(metrics_log, "timeout_days")

    def _add_database_connection(
        self,
        root: ET.Element,
        config: Union[SourceConfig, TargetConfig],
        connection_name: str,
    ):
        """添加数据库连接"""
        if config.source_type if hasattr(config, 'source_type') else config.target_type not in self.DB_TYPE_MAPPING:
            return

        db_type = config.source_type if hasattr(config, 'source_type') else config.target_type
        kettle_type, driver, default_port = self.DB_TYPE_MAPPING[db_type]

        connection = ET.SubElement(root, "connection")
        ET.SubElement(connection, "name").text = config.connection_name or connection_name
        ET.SubElement(connection, "server").text = config.host
        ET.SubElement(connection, "type").text = kettle_type
        ET.SubElement(connection, "access").text = "Native"
        ET.SubElement(connection, "database").text = config.database
        ET.SubElement(connection, "port").text = str(config.port or default_port)
        ET.SubElement(connection, "username").text = config.username
        ET.SubElement(connection, "password").text = config.password
        ET.SubElement(connection, "servername")
        ET.SubElement(connection, "data_tablespace")
        ET.SubElement(connection, "index_tablespace")

        # 连接属性
        attributes = ET.SubElement(connection, "attributes")

        # MySQL 特定属性
        if db_type == SourceType.MYSQL:
            attr = ET.SubElement(attributes, "attribute")
            ET.SubElement(attr, "code").text = "USE_POOLING"
            ET.SubElement(attr, "attribute").text = "N"

            attr = ET.SubElement(attributes, "attribute")
            ET.SubElement(attr, "code").text = "FORCE_IDENTIFIERS_TO_LOWERCASE"
            ET.SubElement(attr, "attribute").text = "N"

            attr = ET.SubElement(attributes, "attribute")
            ET.SubElement(attr, "code").text = "FORCE_IDENTIFIERS_TO_UPPERCASE"
            ET.SubElement(attr, "attribute").text = "N"

    def _create_input_step(self, source: SourceConfig, mappings: List[ColumnMapping]) -> Optional[ET.Element]:
        """创建输入步骤"""
        if source.source_type in self.DB_TYPE_MAPPING:
            return self._create_table_input_step(source, mappings)
        elif source.source_type == SourceType.CSV:
            return self._create_csv_input_step(source, mappings)
        elif source.source_type == SourceType.JSON:
            return self._create_json_input_step(source)
        return None

    def _create_table_input_step(self, source: SourceConfig, mappings: List[ColumnMapping]) -> ET.Element:
        """创建表输入步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Table Input"
        ET.SubElement(step, "type").text = "TableInput"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "connection").text = source.connection_name or "source_connection"

        # 构建 SQL
        if source.query:
            sql = source.query
        else:
            columns = ", ".join([m.source_column for m in mappings]) if mappings else "*"
            table_ref = f"{source.schema}.{source.table}" if source.schema else source.table
            sql = f"SELECT {columns} FROM {table_ref}"

            # 增量条件
            if source.incremental_field and source.incremental_value:
                sql += f" WHERE {source.incremental_field} > '{source.incremental_value}'"

        ET.SubElement(step, "sql").text = sql
        ET.SubElement(step, "limit").text = "0"
        ET.SubElement(step, "lookup")
        ET.SubElement(step, "execute_each_row").text = "N"
        ET.SubElement(step, "variables_active").text = "Y"
        ET.SubElement(step, "lazy_conversion_active").text = "N"
        ET.SubElement(step, "cluster_schema")

        # GUI 位置
        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "100"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_csv_input_step(self, source: SourceConfig, mappings: List[ColumnMapping]) -> ET.Element:
        """创建 CSV 输入步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "CSV Input"
        ET.SubElement(step, "type").text = "CsvInput"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "filename").text = source.file_path
        ET.SubElement(step, "filename_field")
        ET.SubElement(step, "rownum_field")
        ET.SubElement(step, "include_filename").text = "N"
        ET.SubElement(step, "separator").text = source.delimiter
        ET.SubElement(step, "enclosure").text = '"'
        ET.SubElement(step, "escape_enclosure").text = '"'
        ET.SubElement(step, "header").text = "Y" if source.header else "N"
        ET.SubElement(step, "buffer_size").text = "50000"
        ET.SubElement(step, "lazy_conversion").text = "Y"
        ET.SubElement(step, "add_filename_result").text = "N"
        ET.SubElement(step, "parallel").text = "N"
        ET.SubElement(step, "newline_possible").text = "N"
        ET.SubElement(step, "encoding").text = source.encoding

        # 字段定义
        fields = ET.SubElement(step, "fields")
        for mapping in mappings:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "name").text = mapping.source_column
            ET.SubElement(field, "type").text = mapping.source_type
            ET.SubElement(field, "format")
            ET.SubElement(field, "currency")
            ET.SubElement(field, "decimal")
            ET.SubElement(field, "group")
            ET.SubElement(field, "length").text = "-1"
            ET.SubElement(field, "precision").text = "-1"
            ET.SubElement(field, "trim_type").text = "none"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "100"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_json_input_step(self, source: SourceConfig) -> ET.Element:
        """创建 JSON 输入步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "JSON Input"
        ET.SubElement(step, "type").text = "JsonInput"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "include").text = "N"
        ET.SubElement(step, "include_field")
        ET.SubElement(step, "rownum").text = "N"
        ET.SubElement(step, "addresultfile").text = "N"
        ET.SubElement(step, "readurl").text = "N"
        ET.SubElement(step, "removeSourceField").text = "N"
        ET.SubElement(step, "IsIgnoreEmptyFile").text = "N"
        ET.SubElement(step, "doNotFailIfNoFile").text = "Y"
        ET.SubElement(step, "ignoreMissingPath").text = "Y"
        ET.SubElement(step, "defaultPathLeafToNull").text = "Y"
        ET.SubElement(step, "rownum_field")
        ET.SubElement(step, "file").text = source.file_path
        ET.SubElement(step, "IsAFile").text = "Y"
        ET.SubElement(step, "limit").text = "0"
        ET.SubElement(step, "loopxpath").text = "$"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "100"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_output_step(self, target: TargetConfig, mappings: List[ColumnMapping]) -> Optional[ET.Element]:
        """创建输出步骤"""
        if target.target_type in self.DB_TYPE_MAPPING:
            return self._create_table_output_step(target, mappings)
        return None

    def _create_table_output_step(self, target: TargetConfig, mappings: List[ColumnMapping]) -> ET.Element:
        """创建表输出步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Table Output"
        ET.SubElement(step, "type").text = "TableOutput"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "connection").text = target.connection_name or "target_connection"
        ET.SubElement(step, "schema").text = target.schema or ""
        ET.SubElement(step, "table").text = target.table
        ET.SubElement(step, "commit").text = str(target.commit_size)
        ET.SubElement(step, "truncate").text = "Y" if target.write_mode == "truncate_insert" else "N"
        ET.SubElement(step, "ignore_errors").text = "N"
        ET.SubElement(step, "use_batch").text = "Y"
        ET.SubElement(step, "specify_fields").text = "Y"
        ET.SubElement(step, "partitioning_enabled").text = "N"
        ET.SubElement(step, "partitioning_field")
        ET.SubElement(step, "partitioning_daily").text = "N"
        ET.SubElement(step, "partitioning_monthly").text = "Y"
        ET.SubElement(step, "tablename_in_field").text = "N"
        ET.SubElement(step, "tablename_field")
        ET.SubElement(step, "tablename_in_table").text = "Y"
        ET.SubElement(step, "return_keys").text = "N"
        ET.SubElement(step, "return_field")
        ET.SubElement(step, "cluster_schema")

        # 字段映射
        fields = ET.SubElement(step, "fields")
        for mapping in mappings:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "column_name").text = mapping.target_column
            ET.SubElement(field, "stream_name").text = mapping.target_column

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "500"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_select_values_step(self, mappings: List[ColumnMapping]) -> ET.Element:
        """创建字段选择/映射步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Select Values"
        ET.SubElement(step, "type").text = "SelectValues"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        # 字段选择
        fields = ET.SubElement(step, "fields")
        for mapping in mappings:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "name").text = mapping.source_column
            ET.SubElement(field, "rename").text = mapping.target_column if mapping.source_column != mapping.target_column else ""
            ET.SubElement(field, "length").text = "-2"
            ET.SubElement(field, "precision").text = "-2"

        # 删除字段
        ET.SubElement(fields, "select_unspecified").text = "N"

        # 元数据变更
        metas = ET.SubElement(step, "meta")
        for mapping in mappings:
            if mapping.source_type != mapping.target_type:
                meta = ET.SubElement(metas, "field")
                ET.SubElement(meta, "name").text = mapping.target_column
                ET.SubElement(meta, "type").text = mapping.target_type
                ET.SubElement(meta, "length").text = "-2"
                ET.SubElement(meta, "precision").text = "-2"
                ET.SubElement(meta, "conversion_mask")
                ET.SubElement(meta, "date_format_lenient").text = "false"
                ET.SubElement(meta, "date_format_locale")
                ET.SubElement(meta, "date_format_timezone")
                ET.SubElement(meta, "lenient_string_to_number").text = "false"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "300"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_filter_step(self, condition: str) -> ET.Element:
        """创建过滤步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Filter Rows"
        ET.SubElement(step, "type").text = "FilterRows"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "send_true_to")
        ET.SubElement(step, "send_false_to")

        # 简化的条件表示
        compare = ET.SubElement(step, "compare")
        cond = ET.SubElement(compare, "condition")
        ET.SubElement(cond, "negated").text = "N"
        ET.SubElement(cond, "conditions")

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "200"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_sort_step(self, sort_fields: List[Tuple[str, bool]]) -> ET.Element:
        """创建排序步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Sort Rows"
        ET.SubElement(step, "type").text = "SortRows"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "directory").text = "%%java.io.tmpdir%%"
        ET.SubElement(step, "prefix").text = "out"
        ET.SubElement(step, "sort_size").text = "1000000"
        ET.SubElement(step, "free_memory")
        ET.SubElement(step, "compress").text = "N"
        ET.SubElement(step, "compress_variable")
        ET.SubElement(step, "unique_rows").text = "N"

        fields = ET.SubElement(step, "fields")
        for field_name, ascending in sort_fields:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "name").text = field_name
            ET.SubElement(field, "ascending").text = "Y" if ascending else "N"
            ET.SubElement(field, "case_sensitive").text = "N"
            ET.SubElement(field, "presorted").text = "N"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "200"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_distinct_step(self, fields: List[str]) -> ET.Element:
        """创建去重步骤"""
        step = ET.Element("step")
        ET.SubElement(step, "name").text = "Unique Rows"
        ET.SubElement(step, "type").text = "Unique"
        ET.SubElement(step, "description")
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "count_rows").text = "N"
        ET.SubElement(step, "count_field")
        ET.SubElement(step, "reject_duplicate_row").text = "N"
        ET.SubElement(step, "error_description")

        fields_elem = ET.SubElement(step, "fields")
        for field_name in fields:
            field = ET.SubElement(fields_elem, "field")
            ET.SubElement(field, "name").text = field_name

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = "200"
        ET.SubElement(gui, "yloc").text = "100"
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _prettify_xml(self, elem: ET.Element) -> str:
        """格式化 XML 输出"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)

    # =========================================
    # AI 集成：脱敏步骤
    # =========================================

    def _create_masking_step(
        self,
        column_name: str,
        masking_strategy: str,
        masking_params: Dict[str, Any] = None,
        x_loc: int = 400,
        y_loc: int = 100,
    ) -> ET.Element:
        """
        创建数据脱敏步骤（使用 Modified JavaScript Value）

        Args:
            column_name: 列名
            masking_strategy: 脱敏策略
            masking_params: 脱敏参数
            x_loc: X 位置
            y_loc: Y 位置

        Returns:
            步骤 XML 元素
        """
        masking_params = masking_params or {}

        step = ET.Element("step")
        ET.SubElement(step, "name").text = f"脱敏_{column_name}"
        ET.SubElement(step, "type").text = "ScriptValueMod"
        ET.SubElement(step, "description").text = f"对 {column_name} 进行 {masking_strategy} 脱敏"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "compatible").text = "N"
        ET.SubElement(step, "optimizationLevel").text = "9"

        # 生成脱敏脚本
        script = self._generate_masking_script(column_name, masking_strategy, masking_params)

        jsScripts = ET.SubElement(step, "jsScripts")
        jsScript = ET.SubElement(jsScripts, "jsScript")
        ET.SubElement(jsScript, "jsScript_type").text = "0"
        ET.SubElement(jsScript, "jsScript_name").text = "Script 1"
        ET.SubElement(jsScript, "jsScript_script").text = script

        # 输出字段
        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "name").text = column_name
        ET.SubElement(field, "rename").text = column_name
        ET.SubElement(field, "type").text = "String"
        ET.SubElement(field, "length").text = "-1"
        ET.SubElement(field, "precision").text = "-1"
        ET.SubElement(field, "replace").text = "Y"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(x_loc)
        ET.SubElement(gui, "yloc").text = str(y_loc)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _generate_masking_script(
        self,
        column_name: str,
        strategy: str,
        params: Dict[str, Any],
    ) -> str:
        """生成脱敏 JavaScript 代码"""
        scripts = {
            "partial_mask": f"""
// 部分遮盖脱敏
var value = {column_name};
if (value != null && value.length > 0) {{
    var start = {params.get('start', 0)};
    var end = {params.get('end', -4)};
    var mask_char = '{params.get('mask_char', '*')}';

    if (end < 0) end = value.length + end;
    if (end < start) end = start;

    var prefix = value.substring(0, start);
    var suffix = value.substring(end);
    var mask = '';
    for (var i = start; i < end; i++) mask += mask_char;

    {column_name} = prefix + mask + suffix;
}}
""",
            "hash": f"""
// 哈希脱敏
var value = {column_name};
if (value != null) {{
    var hash = 0;
    for (var i = 0; i < value.length; i++) {{
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash = hash & hash;
    }}
    {column_name} = Math.abs(hash).toString(16).toUpperCase();
}}
""",
            "replace": f"""
// 替换为固定值
{column_name} = '{params.get('replacement', '***')}';
""",
            "truncate": f"""
// 截断
var value = {column_name};
if (value != null && value.length > {params.get('length', 4)}) {{
    {column_name} = value.substring(0, {params.get('length', 4)}) + '...';
}}
""",
            "null_out": f"""
// 置空
{column_name} = null;
""",
            "email_mask": f"""
// 邮箱脱敏
var value = {column_name};
if (value != null && value.indexOf('@') > 0) {{
    var parts = value.split('@');
    var local = parts[0];
    var domain = parts[1];
    if (local.length > 2) {{
        local = local.substring(0, 2) + '***';
    }}
    {column_name} = local + '@' + domain;
}}
""",
            "phone_mask": f"""
// 手机号脱敏
var value = {column_name};
if (value != null && value.length >= 7) {{
    {column_name} = value.substring(0, 3) + '****' + value.substring(value.length - 4);
}}
""",
            "id_card_mask": f"""
// 身份证脱敏
var value = {column_name};
if (value != null && value.length >= 15) {{
    {column_name} = value.substring(0, 6) + '********' + value.substring(value.length - 4);
}}
""",
            "bank_card_mask": f"""
// 银行卡脱敏
var value = {column_name};
if (value != null && value.length >= 12) {{
    {column_name} = value.substring(0, 4) + ' **** **** ' + value.substring(value.length - 4);
}}
""",
            "name_mask": f"""
// 姓名脱敏
var value = {column_name};
if (value != null && value.length > 1) {{
    {column_name} = value.substring(0, 1) + '**';
}}
""",
            "address_mask": f"""
// 地址脱敏
var value = {column_name};
if (value != null && value.length > 6) {{
    {column_name} = value.substring(0, 6) + '******';
}}
""",
        }

        return scripts.get(strategy, f"// 未知脱敏策略: {strategy}")

    # =========================================
    # AI 集成：清洗步骤
    # =========================================

    def _create_null_handling_step(
        self,
        column_name: str,
        replace_value: str = "",
        x_loc: int = 400,
        y_loc: int = 100,
    ) -> ET.Element:
        """
        创建空值处理步骤（IfFieldValueIsNull）

        Args:
            column_name: 列名
            replace_value: 替换值
            x_loc: X 位置
            y_loc: Y 位置

        Returns:
            步骤 XML 元素
        """
        step = ET.Element("step")
        ET.SubElement(step, "name").text = f"空值处理_{column_name}"
        ET.SubElement(step, "type").text = "IfFieldValueIsNull"
        ET.SubElement(step, "description").text = f"将 {column_name} 的空值替换为 {replace_value}"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "name").text = column_name
        ET.SubElement(field, "value").text = str(replace_value)
        ET.SubElement(field, "mask")
        ET.SubElement(field, "set_empty_string").text = "N"

        ET.SubElement(step, "selectFields").text = "N"
        ET.SubElement(step, "selectValuesType")
        ET.SubElement(step, "replaceAllByValue")
        ET.SubElement(step, "replaceAllMask")
        ET.SubElement(step, "setEmptyStringAll").text = "N"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(x_loc)
        ET.SubElement(gui, "yloc").text = str(y_loc)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_value_mapper_step(
        self,
        column_name: str,
        mappings: List[Dict[str, str]],
        x_loc: int = 400,
        y_loc: int = 100,
    ) -> ET.Element:
        """
        创建值映射步骤（ValueMapper）

        Args:
            column_name: 列名
            mappings: 映射列表 [{"source": "old", "target": "new"}, ...]
            x_loc: X 位置
            y_loc: Y 位置

        Returns:
            步骤 XML 元素
        """
        step = ET.Element("step")
        ET.SubElement(step, "name").text = f"值映射_{column_name}"
        ET.SubElement(step, "type").text = "ValueMapper"
        ET.SubElement(step, "description").text = f"对 {column_name} 进行值映射转换"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "field_to_use").text = column_name
        ET.SubElement(step, "target_field")
        ET.SubElement(step, "non_match_default")

        fields = ET.SubElement(step, "fields")
        for mapping in mappings:
            field = ET.SubElement(fields, "field")
            ET.SubElement(field, "source_value").text = str(mapping.get("source", ""))
            ET.SubElement(field, "target_value").text = str(mapping.get("target", ""))

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(x_loc)
        ET.SubElement(gui, "yloc").text = str(y_loc)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_string_operations_step(
        self,
        column_name: str,
        operations: List[str],
        x_loc: int = 400,
        y_loc: int = 100,
    ) -> ET.Element:
        """
        创建字符串操作步骤（StringOperations）

        Args:
            column_name: 列名
            operations: 操作列表 ["trim", "upper", "lower", ...]
            x_loc: X 位置
            y_loc: Y 位置

        Returns:
            步骤 XML 元素
        """
        step = ET.Element("step")
        ET.SubElement(step, "name").text = f"字符串处理_{column_name}"
        ET.SubElement(step, "type").text = "StringOperations"
        ET.SubElement(step, "description").text = f"对 {column_name} 进行字符串操作"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "in_stream_name").text = column_name
        ET.SubElement(field, "out_stream_name")

        # 操作映射
        trim_type = "none"
        case_type = "none"

        for op in operations:
            op_lower = op.lower()
            if op_lower in ("trim", "trim_both"):
                trim_type = "both"
            elif op_lower in ("trim_left", "ltrim"):
                trim_type = "left"
            elif op_lower in ("trim_right", "rtrim"):
                trim_type = "right"
            elif op_lower in ("upper", "uppercase"):
                case_type = "upper"
            elif op_lower in ("lower", "lowercase"):
                case_type = "lower"
            elif op_lower in ("capitalize", "cap_first"):
                case_type = "cap_first"

        ET.SubElement(field, "trim_type").text = trim_type
        ET.SubElement(field, "lower_upper").text = case_type
        ET.SubElement(field, "padding_type").text = "none"
        ET.SubElement(field, "pad_char")
        ET.SubElement(field, "pad_len")
        ET.SubElement(field, "init_cap").text = "N"
        ET.SubElement(field, "mask_xml").text = "none"
        ET.SubElement(field, "digits").text = "none"
        ET.SubElement(field, "remove_special_characters").text = "none"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(x_loc)
        ET.SubElement(gui, "yloc").text = str(y_loc)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    def _create_regex_replace_step(
        self,
        column_name: str,
        pattern: str,
        replacement: str,
        x_loc: int = 400,
        y_loc: int = 100,
    ) -> ET.Element:
        """
        创建正则替换步骤（使用 Modified JavaScript Value）

        Args:
            column_name: 列名
            pattern: 正则表达式
            replacement: 替换值
            x_loc: X 位置
            y_loc: Y 位置

        Returns:
            步骤 XML 元素
        """
        step = ET.Element("step")
        ET.SubElement(step, "name").text = f"正则替换_{column_name}"
        ET.SubElement(step, "type").text = "ScriptValueMod"
        ET.SubElement(step, "description").text = f"对 {column_name} 进行正则替换"
        ET.SubElement(step, "distribute").text = "Y"
        ET.SubElement(step, "custom_distribution")
        ET.SubElement(step, "copies").text = "1"

        partition = ET.SubElement(step, "partitioning")
        ET.SubElement(partition, "method").text = "none"
        ET.SubElement(partition, "schema_name")

        ET.SubElement(step, "compatible").text = "N"
        ET.SubElement(step, "optimizationLevel").text = "9"

        # 正则替换脚本
        # 转义 JavaScript 字符串中的特殊字符
        escaped_pattern = pattern.replace("\\", "\\\\").replace("'", "\\'")
        escaped_replacement = replacement.replace("\\", "\\\\").replace("'", "\\'")

        script = f"""
// 正则替换
var value = {column_name};
if (value != null) {{
    var regex = new RegExp('{escaped_pattern}', 'g');
    {column_name} = value.replace(regex, '{escaped_replacement}');
}}
"""

        jsScripts = ET.SubElement(step, "jsScripts")
        jsScript = ET.SubElement(jsScripts, "jsScript")
        ET.SubElement(jsScript, "jsScript_type").text = "0"
        ET.SubElement(jsScript, "jsScript_name").text = "Script 1"
        ET.SubElement(jsScript, "jsScript_script").text = script

        fields = ET.SubElement(step, "fields")
        field = ET.SubElement(fields, "field")
        ET.SubElement(field, "name").text = column_name
        ET.SubElement(field, "rename").text = column_name
        ET.SubElement(field, "type").text = "String"
        ET.SubElement(field, "length").text = "-1"
        ET.SubElement(field, "precision").text = "-1"
        ET.SubElement(field, "replace").text = "Y"

        gui = ET.SubElement(step, "GUI")
        ET.SubElement(gui, "xloc").text = str(x_loc)
        ET.SubElement(gui, "yloc").text = str(y_loc)
        ET.SubElement(gui, "draw").text = "Y"

        return step

    # =========================================
    # AI 集成：增强的转换生成
    # =========================================

    def generate_transformation_with_ai_rules(
        self,
        config: TransformationConfig,
        cleaning_rules: List[Dict[str, Any]] = None,
        masking_rules: Dict[str, Dict[str, Any]] = None,
    ) -> str:
        """
        生成带有 AI 规则（清洗/脱敏）的 Kettle 转换配置

        Args:
            config: 基础转换配置
            cleaning_rules: AI 清洗规则列表
            masking_rules: AI 脱敏规则字典 {column_name: masking_config}

        Returns:
            XML 字符串
        """
        # 创建根元素
        root = ET.Element("transformation")

        # 添加基本信息
        info = ET.SubElement(root, "info")
        ET.SubElement(info, "name").text = config.name
        ET.SubElement(info, "description").text = config.description or f"AI-enhanced transformation: {config.name}"
        ET.SubElement(info, "extended_description")
        ET.SubElement(info, "trans_version")
        ET.SubElement(info, "trans_type").text = "Normal"
        ET.SubElement(info, "trans_status").text = "0"
        ET.SubElement(info, "directory").text = "/"

        parameters = ET.SubElement(info, "parameters")
        self._add_log_config(info)

        # 添加连接
        if config.source and config.source.source_type in self.DB_TYPE_MAPPING:
            self._add_database_connection(root, config.source, "source_connection")
        if config.target and config.target.target_type in self.DB_TYPE_MAPPING:
            self._add_database_connection(root, config.target, "target_connection")

        order = ET.SubElement(root, "order")
        steps = []
        step_names = []

        x_loc = 100
        y_loc = 100
        x_step = 200

        # 1. 输入步骤
        if config.source:
            input_step = self._create_input_step(config.source, config.column_mappings)
            if input_step is not None:
                gui = input_step.find("GUI")
                if gui is not None:
                    gui.find("xloc").text = str(x_loc)
                    gui.find("yloc").text = str(y_loc)
                steps.append(input_step)
                step_names.append(input_step.find("name").text)
                x_loc += x_step

        # 2. 清洗步骤（AI 规则）
        if cleaning_rules:
            for rule in cleaning_rules:
                cleaning_type = rule.get("cleaning_type", "")
                column_name = rule.get("column_name", "")
                kettle_config = rule.get("kettle_config", {})

                cleaning_step = None

                if cleaning_type == "NULL_HANDLING":
                    cleaning_step = self._create_null_handling_step(
                        column_name,
                        kettle_config.get("replace_value", ""),
                        x_loc, y_loc
                    )
                elif cleaning_type == "FORMAT_STANDARDIZATION":
                    operations = kettle_config.get("operations", ["trim"])
                    cleaning_step = self._create_string_operations_step(
                        column_name, operations, x_loc, y_loc
                    )
                elif cleaning_type == "VALUE_MAPPING":
                    mappings = kettle_config.get("mappings", [])
                    cleaning_step = self._create_value_mapper_step(
                        column_name, mappings, x_loc, y_loc
                    )
                elif cleaning_type in ("TRIM_WHITESPACE", "CASE_NORMALIZATION"):
                    operations = kettle_config.get("operations", ["trim"])
                    cleaning_step = self._create_string_operations_step(
                        column_name, operations, x_loc, y_loc
                    )
                elif cleaning_type == "PATTERN_EXTRACTION":
                    pattern = kettle_config.get("pattern", "")
                    replacement = kettle_config.get("replacement", "")
                    if pattern:
                        cleaning_step = self._create_regex_replace_step(
                            column_name, pattern, replacement, x_loc, y_loc
                        )

                if cleaning_step is not None:
                    steps.append(cleaning_step)
                    step_names.append(cleaning_step.find("name").text)
                    x_loc += x_step

        # 3. 过滤步骤
        if config.add_filter and config.filter_condition:
            filter_step = self._create_filter_step(config.filter_condition)
            gui = filter_step.find("GUI")
            if gui is not None:
                gui.find("xloc").text = str(x_loc)
                gui.find("yloc").text = str(y_loc)
            steps.append(filter_step)
            step_names.append(filter_step.find("name").text)
            x_loc += x_step

        # 4. 排序步骤
        if config.add_sort and config.sort_fields:
            sort_step = self._create_sort_step(config.sort_fields)
            gui = sort_step.find("GUI")
            if gui is not None:
                gui.find("xloc").text = str(x_loc)
                gui.find("yloc").text = str(y_loc)
            steps.append(sort_step)
            step_names.append(sort_step.find("name").text)
            x_loc += x_step

        # 5. 去重步骤
        if config.add_distinct:
            distinct_step = self._create_distinct_step([m.target_column for m in config.column_mappings])
            gui = distinct_step.find("GUI")
            if gui is not None:
                gui.find("xloc").text = str(x_loc)
                gui.find("yloc").text = str(y_loc)
            steps.append(distinct_step)
            step_names.append(distinct_step.find("name").text)
            x_loc += x_step

        # 6. 字段映射步骤
        if config.column_mappings:
            select_step = self._create_select_values_step(config.column_mappings)
            gui = select_step.find("GUI")
            if gui is not None:
                gui.find("xloc").text = str(x_loc)
                gui.find("yloc").text = str(y_loc)
            steps.append(select_step)
            step_names.append(select_step.find("name").text)
            x_loc += x_step

        # 7. 脱敏步骤（在输出前）
        if masking_rules:
            for column_name, masking_config in masking_rules.items():
                strategy = masking_config.get("strategy", "partial_mask")
                params = masking_config.get("params", {})
                masking_step = self._create_masking_step(
                    column_name, strategy, params, x_loc, y_loc
                )
                steps.append(masking_step)
                step_names.append(masking_step.find("name").text)
                x_loc += x_step

        # 8. 输出步骤
        if config.target:
            output_step = self._create_output_step(config.target, config.column_mappings)
            if output_step is not None:
                gui = output_step.find("GUI")
                if gui is not None:
                    gui.find("xloc").text = str(x_loc)
                    gui.find("yloc").text = str(y_loc)
                steps.append(output_step)
                step_names.append(output_step.find("name").text)

        # 添加步骤连接
        for i in range(len(step_names) - 1):
            hop = ET.SubElement(order, "hop")
            ET.SubElement(hop, "from").text = step_names[i]
            ET.SubElement(hop, "to").text = step_names[i + 1]
            ET.SubElement(hop, "enabled").text = "Y"

        # 添加步骤到根元素
        for step in steps:
            root.append(step)

        # 错误处理
        step_error_handling = ET.SubElement(root, "step_error_handling")

        return self._prettify_xml(root)


# 便捷函数
def generate_sync_transformation(
    source_table: str,
    target_table: str,
    source_connection: Dict[str, Any],
    target_connection: Dict[str, Any],
    source_columns: List[Dict[str, Any]],
    target_columns: List[Dict[str, Any]] = None,
    options: Dict[str, Any] = None,
) -> str:
    """
    生成数据同步转换配置

    Args:
        source_table: 源表名
        target_table: 目标表名
        source_connection: 源连接配置
        target_connection: 目标连接配置
        source_columns: 源列元数据列表
        target_columns: 目标列元数据列表（可选，不提供则使用源列）
        options: 额外选项

    Returns:
        Kettle 转换 XML 字符串
    """
    generator = KettleConfigGenerator()

    source_meta = {
        "table_name": source_table,
        "schema": source_connection.get("schema", ""),
        "columns": source_columns,
    }

    target_columns = target_columns or source_columns
    target_meta = {
        "table_name": target_table,
        "schema": target_connection.get("schema", ""),
        "columns": target_columns,
    }

    return generator.generate_from_metadata(
        source_table_meta=source_meta,
        target_table_meta=target_meta,
        source_connection=source_connection,
        target_connection=target_connection,
        options=options,
    )


def generate_etl_job(
    job_name: str,
    transformation_files: List[str],
    description: str = "",
) -> str:
    """
    生成 ETL 作业配置

    Args:
        job_name: 作业名称
        transformation_files: 转换文件路径列表
        description: 作业描述

    Returns:
        Kettle 作业 XML 字符串
    """
    generator = KettleConfigGenerator()
    return generator.generate_job(job_name, transformation_files, description)
