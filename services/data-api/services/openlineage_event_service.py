"""
OpenLineage 事件服务

完整实现 OpenLineage 标准协议，支持:
1. 事件捕获与持久化
2. OpenLineage 事件推送
3. 血缘边自动维护
4. 血缘路径查询
5. 影响分析

与现有 OpenLineageService 的区别:
- OpenLineageService: 专注于与 OpenMetadata 的血缘同步
- OpenLineageEventService: 专注于事件处理、存储和查询
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from queue import Queue, Empty
from dataclasses import asdict

from models.lineage_event import (
    LineageEvent,
    DatasetOperationEvent,
    DatasetIdentifier,
    JobIdentifier,
    EventType,
    EventSource,
    LineageEventModel,
    LineageEdgeModel,
    LineageNodeCache,
    create_etl_lineage_event,
    create_scan_lineage_event,
    create_column_masked_event,
)
from database import db_manager

logger = logging.getLogger(__name__)


class OpenLineageEventService:
    """
    OpenLineage 事件服务

    功能:
    1. 事件接收与验证
    2. 异步持久化队列
    3. 血缘边自动推导与维护
    4. OpenLineage 协议推送
    5. 血缘查询 API
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: int = 5,
        max_queue_size: int = 10000,
    ):
        """
        初始化事件服务

        Args:
            batch_size: 批量写入大小
            flush_interval: 刷新间隔 (秒)
            max_queue_size: 队列最大长度
        """
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._event_queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 统计
        self._stats = {
            "events_received": 0,
            "events_persisted": 0,
            "events_failed": 0,
            "edges_created": 0,
        }

    # ==================== 生命周期管理 ====================

    def start(self) -> None:
        """启动事件处理"""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_events,
                daemon=True,
                name="OpenLineageEventWorker",
            )
            self._worker_thread.start()
            logger.info("OpenLineage event service started")

    def stop(self) -> None:
        """停止事件处理"""
        with self._lock:
            if not self._running:
                return

            self._running = False

        # 等待队列处理完成
        if self._worker_thread:
            self._worker_thread.join(timeout=30)
            self._worker_thread = None

        # 最后刷新一次
        self._flush_queue()

        logger.info("OpenLineage event service stopped")

    def health_check(self) -> bool:
        """健康检查"""
        return self._running

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
        }

    # ==================== 事件接收 ====================

    def emit_event(self, event: LineageEvent) -> bool:
        """
        发送血缘事件

        Args:
            event: LineageEvent 对象

        Returns:
            是否成功入队
        """
        try:
            self._event_queue.put(event, block=False)
            self._stats["events_received"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to queue event: {e}")
            self._stats["events_failed"] += 1
            return False

    def emit_etl_event(
        self,
        job_name: str,
        source_tables: List[str],
        target_tables: List[str],
        transformation: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> bool:
        """
        发送 ETL 任务事件

        Args:
            job_name: 任务名称
            source_tables: 源表 FQN 列表
            target_tables: 目标表 FQN 列表
            transformation: 转换 SQL
            run_id: 运行 ID

        Returns:
            是否成功
        """
        event = create_etl_lineage_event(
            job_name=job_name,
            source_tables=source_tables,
            target_tables=target_tables,
            transformation=transformation,
            run_id=run_id,
        )
        return self.emit_event(event)

    def emit_scan_event(
        self,
        database: str,
        tables_scanned: List[str],
        scan_id: Optional[str] = None,
    ) -> bool:
        """发送元数据扫描事件"""
        event = create_scan_lineage_event(
            database=database,
            tables_scanned=tables_scanned,
            scan_id=scan_id,
        )
        return self.emit_event(event)

    def emit_dataset_operation(
        self,
        operation: EventType,
        dataset_fqn: str,
        column_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        发送数据集操作事件

        Args:
            operation: 操作类型
            dataset_fqn: 数据集 FQN
            column_name: 列名 (可选)
            description: 描述

        Returns:
            是否成功
        """
        event = DatasetOperationEvent(
            event_type=operation,
            source=EventSource.API_OPERATION,
            dataset=DatasetIdentifier.from_fqn(dataset_fqn),
            column_name=column_name,
            description=description,
        )
        return self.emit_event(event)

    def emit_batch(self, events: List[LineageEvent]) -> int:
        """批量发送事件"""
        count = 0
        for event in events:
            if self.emit_event(event):
                count += 1
        return count

    # ==================== 事件处理 ====================

    def _process_events(self) -> None:
        """后台事件处理线程"""
        batch = []
        last_flush = time.time()

        while self._running:
            try:
                # 尝试获取事件
                event = self._event_queue.get(timeout=1.0)
                batch.append(event)

                # 检查是否需要刷新
                should_flush = (
                    len(batch) >= self._batch_size or
                    time.time() - last_flush >= self._flush_interval
                )

                if should_flush:
                    self._persist_batch(batch)
                    batch = []
                    last_flush = time.time()

            except Empty:
                # 超时，刷新当前批次
                if batch:
                    self._persist_batch(batch)
                    batch = []
                    last_flush = time.time()
            except Exception as e:
                logger.error(f"Error processing events: {e}", exc_info=True)

        # 处理剩余事件
        if batch:
            self._persist_batch(batch)

    def _persist_batch(self, batch: List[LineageEvent]) -> None:
        """持久化事件批次"""
        if not batch:
            return

        session = None
        try:
            session = db_manager.get_session()

            # 持久化事件
            for event in batch:
                model = self._event_to_model(event)
                session.add(model)

            # 推导并创建血缘边
            edges = self._derive_edges(batch)
            for edge_data in edges:
                edge = LineageEdgeModel(**edge_data)
                session.merge(edge)  # 使用 merge 避免重复

            session.commit()

            self._stats["events_persisted"] += len(batch)
            self._stats["edges_created"] += len(edges)

            logger.debug(
                "Persisted %d events, %d edges",
                len(batch),
                len(edges)
            )

        except Exception as e:
            logger.error(f"Failed to persist batch: {e}", exc_info=True)
            if session:
                session.rollback()
            self._stats["events_failed"] += len(batch)
        finally:
            if session:
                session.close()

    def _flush_queue(self) -> None:
        """刷新队列中所有剩余事件"""
        batch = []
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                batch.append(event)
            except Empty:
                break

        if batch:
            self._persist_batch(batch)

    def _event_to_model(self, event: LineageEvent) -> LineageEventModel:
        """转换事件为数据库模型"""
        return LineageEventModel(
            event_id=event.event_id,
            event_type=event.event_type.value,
            event_time=event.event_time,
            source=event.source.value,
            job_namespace=event.job_namespace,
            job_name=event.job_name,
            run_id=event.run_id,
            input_datasets=[
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "type": ds.type.value,
                    "facets": ds.facets,
                }
                for ds in event.input_datasets
            ]
            if event.input_datasets
            else None,
            output_datasets=[
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "type": ds.type.value,
                    "facets": ds.facets,
                }
                for ds in event.output_datasets
            ]
            if event.output_datasets
            else None,
            transformation=event.transformation,
            description=event.description,
            metadata=event.metadata,
        )

    def _derive_edges(self, events: List[LineageEvent]) -> List[Dict[str, Any]]:
        """
        从事件中推导血缘边

        对于每个事件的 input -> output 创建边
        """
        edges = []
        seen = set()  # 避免重复边

        for event in events:
            if not event.input_datasets or not event.output_datasets:
                continue

            for input_ds in event.input_datasets:
                for output_ds in event.output_datasets:
                    edge_key = (
                        input_ds.namespace,
                        input_ds.name,
                        output_ds.namespace,
                        output_ds.name,
                    )

                    if edge_key in seen:
                        continue

                    seen.add(edge_key)
                    edges.append({
                        "source_namespace": input_ds.namespace,
                        "source_name": input_ds.name,
                        "source_type": input_ds.type.value,
                        "target_namespace": output_ds.namespace,
                        "target_name": output_ds.name,
                        "target_type": output_ds.type.value,
                        "edge_type": "data_flow",
                        "transformation": event.transformation,
                        "description": event.description or f"From {event.job_name}",
                        "metadata": {
                            "job_name": event.job_name,
                            "run_id": event.run_id,
                            "event_id": event.event_id,
                        },
                    })

        return edges

    # ==================== 血缘查询 ====================

    def get_upstream(
        self,
        dataset_namespace: str,
        dataset_name: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        获取上游依赖数据集

        Args:
            dataset_namespace: 数据集命名空间
            dataset_name: 数据集名称
            max_depth: 最大追溯深度

        Returns:
            上游数据集列表
        """
        session = None
        try:
            session = db_manager.get_session()

            visited = set()
            result = []
            current_level = [(dataset_namespace, dataset_name)]

            for depth in range(max_depth):
                if not current_level:
                    break

                next_level = []

                for namespace, name in current_level:
                    fqn = f"{namespace}.{name}"
                    if fqn in visited:
                        continue
                    visited.add(fqn)

                    # 查找上游边
                    edges = session.query(LineageEdgeModel).filter(
                        LineageEdgeModel.target_namespace == namespace,
                        LineageEdgeModel.target_name == name,
                    ).all()

                    for edge in edges:
                        source_fqn = edge.source_fqn
                        if source_fqn not in visited:
                            result.append({
                                "fqn": source_fqn,
                                "namespace": edge.source_namespace,
                                "name": edge.source_name,
                                "type": edge.source_type,
                                "depth": depth + 1,
                                "transformation": edge.transformation,
                            })
                            next_level.append(
                                (edge.source_namespace, edge.source_name)
                            )

                current_level = next_level

            return result

        except Exception as e:
            logger.error(f"Failed to get upstream: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()

    def get_downstream(
        self,
        dataset_namespace: str,
        dataset_name: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        获取下游依赖数据集

        Args:
            dataset_namespace: 数据集命名空间
            dataset_name: 数据集名称
            max_depth: 最大追溯深度

        Returns:
            下游数据集列表
        """
        session = None
        try:
            session = db_manager.get_session()

            visited = set()
            result = []
            current_level = [(dataset_namespace, dataset_name)]

            for depth in range(max_depth):
                if not current_level:
                    break

                next_level = []

                for namespace, name in current_level:
                    fqn = f"{namespace}.{name}"
                    if fqn in visited:
                        continue
                    visited.add(fqn)

                    # 查找下游边
                    edges = session.query(LineageEdgeModel).filter(
                        LineageEdgeModel.source_namespace == namespace,
                        LineageEdgeModel.source_name == name,
                    ).all()

                    for edge in edges:
                        target_fqn = edge.target_fqn
                        if target_fqn not in visited:
                            result.append({
                                "fqn": target_fqn,
                                "namespace": edge.target_namespace,
                                "name": edge.target_name,
                                "type": edge.target_type,
                                "depth": depth + 1,
                                "transformation": edge.transformation,
                            })
                            next_level.append(
                                (edge.target_namespace, edge.target_name)
                            )

                current_level = next_level

            return result

        except Exception as e:
            logger.error(f"Failed to get downstream: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()

    def get_path(
        self,
        source_namespace: str,
        source_name: str,
        target_namespace: str,
        target_name: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """
        获取两个数据集之间的血缘路径

        Args:
            source_namespace: 源数据集命名空间
            source_name: 源数据集名称
            target_namespace: 目标数据集命名空间
            target_name: 目标数据集名称
            max_depth: 最大搜索深度

        Returns:
            路径 FQN 列表，如果不存在则返回 None
        """
        # 使用 BFS 搜索路径
        from collections import deque

        session = None
        try:
            session = db_manager.get_session()

            start_fqn = f"{source_namespace}.{source_name}"
            end_fqn = f"{target_namespace}.{target_name}"

            # (fqn, path)
            queue = deque([(start_fqn, [start_fqn])])
            visited = {start_fqn}

            while queue:
                current_fqn, path = queue.popleft()

                if len(path) > max_depth:
                    continue

                if current_fqn == end_fqn:
                    return path

                # 获取下游节点
                namespace, name = current_fqn.split(".", 1)
                edges = session.query(LineageEdgeModel).filter(
                    LineageEdgeModel.source_namespace == namespace,
                    LineageEdgeModel.source_name == name,
                ).all()

                for edge in edges:
                    next_fqn = edge.target_fqn
                    if next_fqn not in visited:
                        visited.add(next_fqn)
                        queue.append((next_fqn, path + [next_fqn]))

            return None

        except Exception as e:
            logger.error(f"Failed to get path: {e}", exc_info=True)
            return None
        finally:
            if session:
                session.close()

    def get_impact_analysis(
        self,
        dataset_namespace: str,
        dataset_name: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """
        影响分析 - 评估数据集变更的影响范围

        Args:
            dataset_namespace: 数据集命名空间
            dataset_name: 数据集名称
            max_depth: 分析深度

        Returns:
            影响分析报告
        """
        downstream = self.get_downstream(dataset_namespace, dataset_name, max_depth)

        # 按深度和类型分组
        by_depth = defaultdict(list)
        by_type = defaultdict(list)

        for item in downstream:
            by_depth[item["depth"]].append(item)
            by_type[item["type"]].append(item)

        return {
            "source": f"{dataset_namespace}.{dataset_name}",
            "total_downstream": len(downstream),
            "by_depth": {str(k): len(v) for k, v in by_depth.items()},
            "by_type": {k: len(v) for k, v in by_type.items()},
            "direct_downstream": by_depth.get("1", []),
            "all_downstream": downstream,
        }

    # ==================== 事件查询 ====================

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[EventType] = None,
        job_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取最近的事件

        Args:
            limit: 返回数量
            event_type: 事件类型过滤
            job_name: 任务名称过滤

        Returns:
            事件列表
        """
        session = None
        try:
            session = db_manager.get_session()

            query = session.query(LineageEventModel)

            if event_type:
                query = query.filter(LineageEventModel.event_type == event_type.value)
            if job_name:
                query = query.filter(LineageEventModel.job_name == job_name)

            events = (
                query.order_by(LineageEventModel.event_time.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "event_time": e.event_time.isoformat(),
                    "source": e.source,
                    "job_name": e.job_name,
                    "run_id": e.run_id,
                    "input_count": len(e.input_datasets) if e.input_datasets else 0,
                    "output_count": len(e.output_datasets) if e.output_datasets else 0,
                }
                for e in events
            ]

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()

    def get_job_history(
        self,
        job_name: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取任务执行历史

        Args:
            job_name: 任务名称
            limit: 返回数量

        Returns:
            执行历史列表
        """
        session = None
        try:
            session = db_manager.get_session()

            events = (
                session.query(LineageEventModel)
                .filter(LineageEdgeModel.job_name == job_name)
                .order_by(LineageEventModel.event_time.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "event_time": e.event_time.isoformat(),
                    "run_id": e.run_id,
                    "status": e.status,
                    "input_datasets": e.input_datasets,
                    "output_datasets": e.output_datasets,
                }
                for e in events
            ]

        except Exception as e:
            logger.error(f"Failed to get job history: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()

    # ==================== OpenLineage 协议 ====================

    def to_openlineage_events(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        导出为 OpenLineage 标准格式

        Args:
            limit: 导出数量

        Returns:
            OpenLineage 事件列表
        """
        session = None
        try:
            session = db_manager.get_session()

            events = (
                session.query(LineageEventModel)
                .order_by(LineageEventModel.event_time.desc())
                .limit(limit)
                .all()
            )

            return [e.to_lineage_event().to_openlineage_dict() for e in events]

        except Exception as e:
            logger.error(f"Failed to export events: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()


# ==================== 全局实例 ====================

_event_service: Optional[OpenLineageEventService] = None
_service_lock = threading.Lock()


def get_openlineage_event_service() -> OpenLineageEventService:
    """获取全局事件服务实例（单例）"""
    global _event_service

    if _event_service is None:
        with _service_lock:
            if _event_service is None:
                _event_service = OpenLineageEventService()
                _event_service.start()

    return _event_service


def init_openlineage_event_service() -> OpenLineageEventService:
    """初始化并启动事件服务"""
    service = get_openlineage_event_service()
    logger.info("OpenLineage event service initialized")
    return service


# ==================== 便捷函数 ====================

def emit_etl_lineage(
    job_name: str,
    source_tables: List[str],
    target_tables: List[str],
    transformation: Optional[str] = None,
) -> bool:
    """便捷函数: 发送 ETL 血缘事件"""
    service = get_openlineage_event_service()
    return service.emit_etl_event(
        job_name=job_name,
        source_tables=source_tables,
        target_tables=target_tables,
        transformation=transformation,
    )


def emit_dataset_created(dataset_fqn: str, description: Optional[str] = None) -> bool:
    """便捷函数: 发送数据集创建事件"""
    service = get_openlineage_event_service()
    return service.emit_dataset_operation(
        operation=EventType.DATASET_CREATED,
        dataset_fqn=dataset_fqn,
        description=description,
    )


def emit_dataset_updated(dataset_fqn: str, description: Optional[str] = None) -> bool:
    """便捷函数: 发送数据集更新事件"""
    service = get_openlineage_event_service()
    return service.emit_dataset_operation(
        operation=EventType.DATASET_UPDATED,
        dataset_fqn=dataset_fqn,
        description=description,
    )
