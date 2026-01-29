"""
CDC (Change Data Capture) 增量数据采集服务
支持 MySQL binlog 和 PostgreSQL WAL 的增量数据捕获
"""

import logging
import json
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Generator
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CDCEventType(str, Enum):
    """CDC 事件类型"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"


class CDCSourceType(str, Enum):
    """CDC 源类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MONGODB = "mongodb"


@dataclass
class CDCEvent:
    """CDC 变更事件"""
    event_id: str
    event_type: CDCEventType
    source_type: CDCSourceType
    table: str
    database: str
    schema: str = ""
    timestamp: float = 0
    position: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    old_data: Dict[str, Any] = field(default_factory=dict)
    new_data: Dict[str, Any] = field(default_factory=dict)
    transaction_id: Optional[str] = None
    gtid: Optional[str] = None  # Global Transaction ID (MySQL)
    lsn: Optional[str] = None  # Log Sequence Number (PostgreSQL)
    processed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_type": self.source_type.value,
            "table": self.table,
            "database": self.database,
            "schema": self.schema,
            "timestamp": self.timestamp,
            "position": self.position,
            "data": self.data,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "transaction_id": self.transaction_id,
            "gtid": self.gtid,
            "lsn": self.lsn,
            "processed": self.processed,
            "error": self.error,
        }


@dataclass
class CDCConfig:
    """CDC 配置"""
    source_type: CDCSourceType
    host: str
    port: int
    username: str
    password: str
    database: str
    schema: str = ""
    tables: List[str] = field(default_factory=list)
    server_id: int = 1  # MySQL server ID
    include_ddl: bool = False
    include_query: bool = False
    snapshot_mode: str = "initial"  # initial, schema_only, never
    batch_size: int = 1000
    poll_interval_ms: int = 1000

    def to_connection_config(self) -> Dict:
        """转换为连接配置"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "database": self.database,
        }


@dataclass
class CDCMetrics:
    """CDC 指标"""
    cdc_id: str
    status: str
    events_captured: int = 0
    events_processed: int = 0
    events_failed: int = 0
    insert_events: int = 0
    update_events: int = 0
    delete_events: int = 0
    ddl_events: int = 0
    last_capture_time: Optional[datetime] = None
    last_position: Optional[str] = None
    current_lag_ms: int = 0
    error_message: Optional[str] = None
    throughput_per_second: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "cdc_id": self.cdc_id,
            "status": self.status,
            "events_captured": self.events_captured,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "insert_events": self.insert_events,
            "update_events": self.update_events,
            "delete_events": self.delete_events,
            "ddl_events": self.ddl_events,
            "last_capture_time": self.last_capture_time.isoformat() if self.last_capture_time else None,
            "last_position": self.last_position,
            "current_lag_ms": self.current_lag_ms,
            "error_message": self.error_message,
            "throughput_per_second": self.throughput_per_second,
        }


class MySQLBinlogCapture:
    """MySQL Binlog 捕获器"""

    def __init__(self, config: CDCConfig):
        self.config = config
        self._client = None

    def connect(self) -> bool:
        """连接到 MySQL"""
        try:
            import pymysql
            from pymysql.cursors import DictCursor

            self._client = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                cursorclass=DictCursor,
            )

            # 检查 binlog 是否启用
            with self._client.cursor() as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
                result = cursor.fetchone()
                if not result or result['Value'] != 'ON':
                    logger.warning("MySQL binlog 未启用")

            return True

        except ImportError:
            logger.error("pymysql 库未安装")
            return False
        except Exception as e:
            logger.error(f"MySQL 连接失败: {e}")
            return False

    def get_binlog_position(self) -> Optional[Dict[str, Any]]:
        """获取当前 binlog 位置"""
        if not self._client:
            return None

        try:
            with self._client.cursor() as cursor:
                cursor.execute("SHOW MASTER STATUS")
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"获取 binlog 位置失败: {e}")
            return None

    def get_current_gtid_set(self) -> Optional[str]:
        """获取当前 GTID 集合"""
        if not self._client:
            return None

        try:
            with self._client.cursor() as cursor:
                cursor.execute("SHOW MASTER STATUS")
                result = cursor.fetchone()
                return result.get('Executed_Gtid_Set') if result else None
        except Exception as e:
            logger.error(f"获取 GTID 失败: {e}")
            return None

    def get_table_changes_since(
        self,
        table: str,
        since_position: Optional[str] = None,
        limit: int = 1000,
    ) -> List[CDCEvent]:
        """
        获取表变更（基于时间戳增量查询）

        注意：这是一个简化的实现，生产环境应使用 Debezium 或 Maxwell
        """
        events = []

        try:
            if not self._client:
                if not self.connect():
                    return events

            with self._client.cursor() as cursor:
                # 获取表的更新时间字段
                cursor.execute(f"""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    AND COLUMN_NAME IN ('updated_at', 'update_time', 'modified_at')
                    ORDER BY ORDINAL_POSITION
                    LIMIT 1
                """, (self.config.database, table))

                time_column = cursor.fetchone()

                if not time_column:
                    logger.warning(f"表 {table} 没有时间戳字段，无法进行增量查询")
                    return events

                time_col = time_column['COLUMN_NAME']
                since_time = since_position or '1970-01-01 00:00:00'

                # 查询变更数据
                cursor.execute(f"""
                    SELECT * FROM `{self.config.database}`.`{table}`
                    WHERE `{time_col}` > %s
                    ORDER BY `{time_col}` ASC
                    LIMIT %s
                """, (since_time, limit))

                rows = cursor.fetchall()

                for row in rows:
                    # 根据主键判断是 INSERT 还是 UPDATE
                    events.append(CDCEvent(
                        event_id=f"mysql_{table}_{row.get('id', time.time())}",
                        event_type=CDCEventType.INSERT,  # 简化处理
                        source_type=CDCSourceType.MYSQL,
                        table=table,
                        database=self.config.database,
                        timestamp=time.time(),
                        position=str(row.get(time_col)),
                        new_data=row,
                    ))

        except Exception as e:
            logger.error(f"获取表变更失败: {e}")

        return events


class PostgreSQLWalCapture:
    """PostgreSQL WAL 捕获器"""

    def __init__(self, config: CDCConfig):
        self.config = config
        self._client = None

    def connect(self) -> bool:
        """连接到 PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            self._client = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                cursor_factory=DictCursor,
            )

            # 检查 wal_level 是否设置为 logical
            with self._client.cursor() as cursor:
                cursor.execute("SHOW wal_level;")
                result = cursor.fetchone()
                if result and result['wal_level'] != 'logical':
                    logger.warning("PostgreSQL wal_level 不是 logical，CDC 可能无法工作")

            return True

        except ImportError:
            logger.error("psycopg2 库未安装")
            return False
        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            return False

    def get_logical_replication_slots(self) -> List[Dict[str, Any]]:
        """获取逻辑复制槽"""
        if not self._client:
            return []

        try:
            with self._client.cursor() as cursor:
                cursor.execute("SELECT * FROM pg_replication_slots WHERE slot_type = 'logical'")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取复制槽失败: {e}")
            return []

    def create_replication_slot(self, slot_name: str, plugin: str = "pgoutput") -> bool:
        """创建逻辑复制槽"""
        if not self._client:
            return False

        try:
            with self._client.cursor() as cursor:
                cursor.execute(f"SELECT * FROM pg_create_logical_replication_slot('{slot_name}', '{plugin}')")
                self._client.commit()
                return True
        except Exception as e:
            logger.error(f"创建复制槽失败: {e}")
            return False

    def get_table_changes_since(
        self,
        table: str,
        since_lsn: Optional[str] = None,
        limit: int = 1000,
    ) -> List[CDCEvent]:
        """
        获取表变更（基于时间戳增量查询）

        注意：这是一个简化的实现，生产环境应使用 pglogical 或 Debezium
        """
        events = []

        try:
            if not self._client:
                if not self.connect():
                    return events

            with self._client.cursor() as cursor:
                # 获取表的更新时间字段
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    AND column_name IN ('updated_at', 'update_time', 'modified_at')
                    ORDER BY ordinal_position
                    LIMIT 1
                """, (self.config.schema or 'public', table))

                result = cursor.fetchone()

                if not result:
                    logger.warning(f"表 {table} 没有时间戳字段")
                    return events

                time_col = result['column_name']
                since_time = since_lsn or '1970-01-01 00:00:00'

                # 查询变更数据
                schema_name = self.config.schema or 'public'
                cursor.execute(f"""
                    SELECT * FROM "{schema_name}"."{table}"
                    WHERE "{time_col}" > %s
                    ORDER BY "{time_col}" ASC
                    LIMIT %s
                """, (since_time, limit))

                rows = cursor.fetchall()

                for row in rows:
                    events.append(CDCEvent(
                        event_id=f"pg_{table}_{row.get('id', time.time())}",
                        event_type=CDCEventType.UPDATE,  # 简化处理
                        source_type=CDCSourceType.POSTGRESQL,
                        table=table,
                        database=self.config.database,
                        schema=self.config.schema or 'public',
                        timestamp=time.time(),
                        position=str(row.get(time_col)),
                        new_data=dict(row),
                    ))

        except Exception as e:
            logger.error(f"获取表变更失败: {e}")

        return events


class CDCService:
    """CDC 服务"""

    def __init__(self):
        self._capturers: Dict[str, Any] = {}  # cdc_id -> capturer
        self._configs: Dict[str, CDCConfig] = {}
        self._metrics: Dict[str, CDCMetrics] = {}
        self._event_buffers: Dict[str, List[CDCEvent]] = defaultdict(list)
        self._running = False
        self._thread = None
        self._handlers: Dict[str, List[Callable[[CDCEvent], bool]]] = defaultdict(list)

    def create_cdc_task(
        self,
        cdc_id: str,
        config: CDCConfig,
    ) -> bool:
        """创建 CDC 任务"""
        try:
            self._configs[cdc_id] = config
            self._metrics[cdc_id] = CDCMetrics(
                cdc_id=cdc_id,
                status="idle",
            )

            # 创建对应的捕获器
            if config.source_type == CDCSourceType.MYSQL:
                capturer = MySQLBinlogCapture(config)
            elif config.source_type == CDCSourceType.POSTGRESQL:
                capturer = PostgreSQLWalCapture(config)
            else:
                logger.error(f"不支持的源类型: {config.source_type}")
                return False

            # 尝试连接
            if not capturer.connect():
                return False

            self._capturers[cdc_id] = capturer
            self._metrics[cdc_id].status = "connected"

            logger.info(f"CDC 任务创建成功: {cdc_id}")
            return True

        except Exception as e:
            logger.error(f"创建 CDC 任务失败: {e}")
            return False

    def start_cdc_task(self, cdc_id: str) -> bool:
        """启动 CDC 任务"""
        if cdc_id not in self._capturers:
            logger.error(f"CDC 任务不存在: {cdc_id}")
            return False

        try:
            self._metrics[cdc_id].status = "running"

            # 启动捕获线程
            if not self._running:
                self._running = True
                self._thread = threading.Thread(
                    target=self._capture_loop,
                    daemon=True,
                    name="cdc-capture-loop",
                )
                self._thread.start()

            logger.info(f"CDC 任务启动成功: {cdc_id}")
            return True

        except Exception as e:
            logger.error(f"启动 CDC 任务失败: {e}")
            return False

    def stop_cdc_task(self, cdc_id: str):
        """停止 CDC 任务"""
        if cdc_id in self._metrics:
            self._metrics[cdc_id].status = "stopped"

    def remove_cdc_task(self, cdc_id: str):
        """移除 CDC 任务"""
        self.stop_cdc_task(cdc_id)
        self._capturers.pop(cdc_id, None)
        self._configs.pop(cdc_id, None)
        self._metrics.pop(cdc_id, None)
        self._event_buffers.pop(cdc_id, None)

    def register_event_handler(self, cdc_id: str, handler: Callable[[CDCEvent], bool]):
        """注册事件处理器"""
        self._handlers[cdc_id].append(handler)

    def get_metrics(self, cdc_id: str) -> Optional[CDCMetrics]:
        """获取 CDC 指标"""
        return self._metrics.get(cdc_id)

    def get_all_metrics(self) -> Dict[str, CDCMetrics]:
        """获取所有 CDC 指标"""
        return self._metrics.copy()

    def get_buffered_events(
        self,
        cdc_id: str,
        limit: int = 100,
        clear: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取缓冲的事件"""
        buffer = self._event_buffers.get(cdc_id, [])

        if clear:
            events = buffer[:limit]
            self._event_buffers[cdc_id] = buffer[limit:]
        else:
            events = buffer[-limit:]

        return [e.to_dict() for e in events]

    def _capture_loop(self):
        """捕获循环"""
        while self._running:
            for cdc_id, capturer in self._capturers.items():
                if self._metrics.get(cdc_id)?.status != "running":
                    continue

                config = self._configs.get(cdc_id)
                if not config:
                    continue

                try:
                    # 对每个表进行增量捕获
                    tables = config.tables or self._get_all_tables(config)

                    for table in tables:
                        if isinstance(capturer, MySQLBinlogCapture):
                            events = capturer.get_table_changes_since(
                                table,
                                self._metrics[cdc_id].last_position,
                                config.batch_size,
                            )
                        elif isinstance(capturer, PostgreSQLWalCapture):
                            events = capturer.get_table_changes_since(
                                table,
                                self._metrics[cdc_id].last_position,
                                config.batch_size,
                            )
                        else:
                            continue

                        # 处理事件
                        for event in events:
                            self._process_event(cdc_id, event)

                    # 更新最后捕获时间
                    self._metrics[cdc_id].last_capture_time = datetime.utcnow()

                except Exception as e:
                    logger.error(f"CDC 捕获异常 ({cdc_id}): {e}")
                    self._metrics[cdc_id].error_message = str(e)
                    self._metrics[cdc_id].status = "error"

            time.sleep(self._config.poll_interval_ms / 1000 if hasattr(self, '_config') else 1)

    def _process_event(self, cdc_id: str, event: CDCEvent):
        """处理事件"""
        metrics = self._metrics.get(cdc_id)
        if not metrics:
            return

        # 更新指标
        metrics.events_captured += 1

        if event.event_type == CDCEventType.INSERT:
            metrics.insert_events += 1
        elif event.event_type == CDCEventType.UPDATE:
            metrics.update_events += 1
        elif event.event_type == CDCEventType.DELETE:
            metrics.delete_events += 1
        elif event.event_type == CDCEventType.DDL:
            metrics.ddl_events += 1

        # 调用处理器
        success = True
        for handler in self._handlers.get(cdc_id, []):
            try:
                if not handler(event):
                    success = False
            except Exception as e:
                logger.error(f"事件处理器异常: {e}")
                success = False

        if success:
            metrics.events_processed += 1
            event.processed = True
        else:
            metrics.events_failed += 1
            event.error = "处理失败"

        # 存入缓冲区
        self._event_buffers[cdc_id].append(event)

        # 限制缓冲区大小
        if len(self._event_buffers[cdc_id]) > 10000:
            self._event_buffers[cdc_id].pop(0)

    def _get_all_tables(self, config: CDCConfig) -> List[str]:
        """获取所有表"""
        # 简化实现
        return config.tables


# 全局服务实例
_cdc_service: Optional[CDCService] = None


def get_cdc_service() -> CDCService:
    """获取 CDC 服务实例"""
    global _cdc_service
    if _cdc_service is None:
        _cdc_service = CDCService()
    return _cdc_service
