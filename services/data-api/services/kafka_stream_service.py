"""
Kafka 流式数据采集服务
支持实时数据流消费、处理和存储
"""

import logging
import json
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Generator
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class KafkaConsumerStatus(str, Enum):
    """Kafka 消费者状态"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CONSUMING = "consuming"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class OffsetReset(str, Enum):
    """偏移量重置策略"""
    EARLIEST = "earliest"
    LATEST = "latest"
    NONE = "none"


@dataclass
class KafkaTopicConfig:
    """Kafka Topic 配置"""
    topic: str
    partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 604800000  # 7 days

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "partitions": self.partitions,
            "replication_factor": self.replication_factor,
            "retention_ms": self.retention_ms,
        }


@dataclass
class KafkaConsumerConfig:
    """Kafka 消费者配置"""
    bootstrap_servers: str
    group_id: str
    topics: List[str]
    auto_offset_reset: OffsetReset = OffsetReset.LATEST
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500
    max_poll_interval_ms: int = 300000
    additional_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": self.group_id,
            "topics": self.topics,
            "auto_offset_reset": self.auto_offset_reset.value,
            "enable_auto_commit": self.enable_auto_commit,
            "auto_commit_interval_ms": self.auto_commit_interval_ms,
            "session_timeout_ms": self.session_timeout_ms,
            "heartbeat_interval_ms": self.heartbeat_interval_ms,
            "max_poll_records": self.max_poll_records,
            "max_poll_interval_ms": self.max_poll_interval_ms,
            "additional_config": self.additional_config,
        }


@dataclass
class StreamMessage:
    """流消息"""
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    value: Any
    timestamp: int
    headers: Dict[str, str] = field(default_factory=dict)
    processed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "headers": self.headers,
            "processed": self.processed,
            "error": self.error,
        }


@dataclass
class ConsumerMetrics:
    """消费者指标"""
    consumer_id: str
    status: KafkaConsumerStatus
    messages_consumed: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    bytes_consumed: int = 0
    last_offset: Dict[str, int] = field(default_factory=dict)
    current_lag: Dict[str, int] = field(default_factory=dict)
    last_message_time: Optional[datetime] = None
    connection_time: Optional[datetime] = None
    error_message: Optional[str] = None
    avg_processing_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "consumer_id": self.consumer_id,
            "status": self.status.value,
            "messages_consumed": self.messages_consumed,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "bytes_consumed": self.bytes_consumed,
            "last_offset": self.last_offset,
            "current_lag": self.current_lag,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
            "error_message": self.error_message,
            "avg_processing_time_ms": self.avg_processing_time_ms,
        }


class KafkaStreamConsumer:
    """Kafka 流消费者"""

    def __init__(
        self,
        consumer_id: str,
        config: KafkaConsumerConfig,
        message_handler: Optional[Callable[[StreamMessage], bool]] = None,
    ):
        self.consumer_id = consumer_id
        self.config = config
        self.message_handler = message_handler
        self.status = KafkaConsumerStatus.IDLE
        self.metrics = ConsumerMetrics(
            consumer_id=consumer_id,
            status=KafkaConsumerStatus.IDLE,
        )
        self._consumer = None
        self._thread = None
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """连接 Kafka 集群"""
        try:
            self.status = KafkaConsumerStatus.CONNECTING
            logger.info(f"连接 Kafka: {self.config.bootstrap_servers}")

            # 尝试导入 kafka-python
            try:
                from kafka import KafkaConsumer as PyKafkaConsumer
                import kafka.errors as KafkaErrors

                # 构建配置
                consumer_config = {
                    "bootstrap_servers": self.config.bootstrap_servers,
                    "group_id": self.config.group_id,
                    "auto_offset_reset": self.config.auto_offset_reset.value,
                    "enable_auto_commit": self.config.enable_auto_commit,
                    "auto_commit_interval_ms": self.config.auto_commit_interval_ms,
                    "session_timeout_ms": self.config.session_timeout_ms,
                    "heartbeat_interval_ms": self.config.heartbeat_interval_ms,
                    "max_poll_records": self.config.max_poll_records,
                    "max_poll_interval_ms": self.config.max_poll_interval_ms,
                    **self.config.additional_config,
                }

                self._consumer = PyKafkaConsumer(**consumer_config)
                self.status = KafkaConsumerStatus.CONNECTED
                self.metrics.connection_time = datetime.utcnow()
                logger.info(f"Kafka 连接成功: {self.consumer_id}")
                return True

            except ImportError:
                self.status = KafkaConsumerStatus.ERROR
                self.metrics.error_message = "kafka-python 库未安装"
                logger.error("kafka-python 库未安装，请运行: pip install kafka-python")
                return False

        except Exception as e:
            self.status = KafkaConsumerStatus.ERROR
            self.metrics.error_message = str(e)
            logger.error(f"Kafka 连接失败: {e}")
            return False

    def start(self) -> bool:
        """启动消费"""
        with self._lock:
            if self._running:
                logger.warning(f"消费者已在运行: {self.consumer_id}")
                return False

            if not self._consumer or self.status != KafkaConsumerStatus.CONNECTED:
                if not self.connect():
                    return False

            self._running = True
            self._paused = False
            self._thread = threading.Thread(
                target=self._consume_loop,
                daemon=True,
                name=f"kafka-consumer-{self.consumer_id}",
            )
            self._thread.start()

            self.status = KafkaConsumerStatus.CONSUMING
            logger.info(f"Kafka 消费者启动: {self.consumer_id}")
            return True

    def pause(self):
        """暂停消费"""
        with self._lock:
            self._paused = True
            self.status = KafkaConsumerStatus.PAUSED
            if self._consumer:
                # 暂停所有分区
                for tp in self._consumer.assignment():
                    self._consumer.pause(tp)
            logger.info(f"消费者已暂停: {self.consumer_id}")

    def resume(self):
        """恢复消费"""
        with self._lock:
            self._paused = False
            self.status = KafkaConsumerStatus.CONSUMING
            if self._consumer:
                # 恢复所有分区
                for tp in self._consumer.assignment():
                    self._consumer.resume(tp)
            logger.info(f"消费者已恢复: {self.consumer_id}")

    def stop(self):
        """停止消费"""
        with self._lock:
            self._running = False
            self.status = KafkaConsumerStatus.STOPPED

            if self._consumer:
                self._consumer.close(timeout=5)

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)

            logger.info(f"消费者已停止: {self.consumer_id}")

    def _consume_loop(self):
        """消费循环"""
        try:
            logger.info(f"开始消费 Topic: {self.config.topics}")

            # 订阅主题
            self._consumer.subscribe(self.config.topics)

            processing_times = []

            while self._running:
                if self._paused:
                    time.sleep(0.1)
                    continue

                try:
                    # 批量拉取消息
                    start_time = time.time()
                    records = self._consumer.poll(timeout_ms=1000, max_records=self.config.max_poll_records)

                    if not records:
                        continue

                    for topic_partition, messages in records.items():
                        topic = topic_partition.topic
                        partition = topic_partition.partition

                        for msg in messages:
                            try:
                                # 解析消息
                                stream_msg = StreamMessage(
                                    topic=topic,
                                    partition=partition,
                                    offset=msg.offset,
                                    key=msg.key.decode('utf-8') if msg.key else None,
                                    value=self._deserialize_value(msg.value),
                                    timestamp=msg.timestamp,
                                    headers=dict(msg.headers) if msg.headers else {},
                                )

                                # 更新指标
                                self.metrics.messages_consumed += 1
                                self.metrics.bytes_consumed += len(msg.value) if msg.value else 0
                                self.metrics.last_offset[f"{topic}:{partition}"] = msg.offset
                                self.metrics.last_message_time = datetime.utcnow()

                                # 调用消息处理器
                                msg_start = time.time()
                                success = True
                                if self.message_handler:
                                    success = self.message_handler(stream_msg)

                                msg_duration = (time.time() - msg_start) * 1000
                                processing_times.append(msg_duration)
                                if len(processing_times) > 100:
                                    processing_times.pop(0)

                                if success:
                                    self.metrics.messages_processed += 1
                                    stream_msg.processed = True
                                else:
                                    self.metrics.messages_failed += 1
                                    stream_msg.error = "处理失败"

                            except Exception as e:
                                self.metrics.messages_failed += 1
                                logger.error(f"消息处理失败: {e}")

                    poll_duration = (time.time() - start_time) * 1000

                except Exception as e:
                    logger.error(f"消费异常: {e}")
                    self.metrics.error_message = str(e)
                    self.status = KafkaConsumerStatus.ERROR
                    time.sleep(5)
                    # 尝试重连
                    if self._running:
                        self.connect()
                        self.status = KafkaConsumerStatus.CONSUMING

            # 更新平均处理时间
            if processing_times:
                self.metrics.avg_processing_time_ms = sum(processing_times) / len(processing_times)

        except Exception as e:
            logger.error(f"消费循环异常: {e}")
            self.status = KafkaConsumerStatus.ERROR
            self.metrics.error_message = str(e)
        finally:
            self._running = False

    def _deserialize_value(self, value: bytes) -> Any:
        """反序列化消息值"""
        if not value:
            return None

        try:
            # 尝试 JSON 解析
            return json.loads(value.decode('utf-8'))
        except:
            # 返回原始字符串
            return value.decode('utf-8', errors='ignore')

    def get_metrics(self) -> ConsumerMetrics:
        """获取消费者指标"""
        # 更新状态
        self.metrics.status = self.status
        return self.metrics

    def seek_to_offset(self, topic: str, partition: int, offset: int):
        """跳转到指定偏移量"""
        if not self._consumer:
            return False

        try:
            from kafka.structs import TopicPartition
            tp = TopicPartition(topic, partition)
            self._consumer.seek(tp, offset)
            logger.info(f"跳转偏移量: {topic}:{partition} -> {offset}")
            return True
        except Exception as e:
            logger.error(f"跳转偏移量失败: {e}")
            return False

    def get_current_offsets(self) -> Dict[str, int]:
        """获取当前偏移量"""
        if not self._consumer:
            return {}

        offsets = {}
        try:
            for tp in self._consumer.assignment():
                pos = self._consumer.position(tp)
                offsets[f"{tp.topic}:{tp.partition}"] = pos
        except Exception as e:
            logger.error(f"获取偏移量失败: {e}")

        return offsets


class KafkaStreamService:
    """Kafka 流服务"""

    def __init__(self):
        self._consumers: Dict[str, KafkaStreamConsumer] = {}
        self._message_buffers: Dict[str, List[StreamMessage]] = defaultdict(list)
        self._buffer_lock = threading.Lock()
        self._max_buffer_size = 10000

    def create_consumer(
        self,
        consumer_id: str,
        config: KafkaConsumerConfig,
        message_handler: Optional[Callable[[StreamMessage], bool]] = None,
    ) -> KafkaStreamConsumer:
        """创建消费者"""
        if consumer_id in self._consumers:
            logger.warning(f"消费者已存在: {consumer_id}")
            return self._consumers[consumer_id]

        # 如果没有提供处理器，使用默认的缓冲处理器
        if message_handler is None:
            message_handler = self._default_message_handler

        consumer = KafkaStreamConsumer(
            consumer_id=consumer_id,
            config=config,
            message_handler=message_handler,
        )

        self._consumers[consumer_id] = consumer
        return consumer

    def _default_message_handler(self, message: StreamMessage) -> bool:
        """默认消息处理器（将消息存入缓冲区）"""
        with self._buffer_lock:
            buffer = self._message_buffers[message.topic]
            buffer.append(message)

            # 限制缓冲区大小
            if len(buffer) > self._max_buffer_size:
                buffer.pop(0)

        return True

    def start_consumer(self, consumer_id: str) -> bool:
        """启动消费者"""
        consumer = self._consumers.get(consumer_id)
        if not consumer:
            logger.error(f"消费者不存在: {consumer_id}")
            return False

        return consumer.start()

    def stop_consumer(self, consumer_id: str):
        """停止消费者"""
        consumer = self._consumers.get(consumer_id)
        if consumer:
            consumer.stop()

    def remove_consumer(self, consumer_id: str):
        """移除消费者"""
        self.stop_consumer(consumer_id)
        self._consumers.pop(consumer_id, None)
        self._message_buffers.pop(consumer_id, None)

    def get_consumer_metrics(self, consumer_id: str) -> Optional[ConsumerMetrics]:
        """获取消费者指标"""
        consumer = self._consumers.get(consumer_id)
        if consumer:
            return consumer.get_metrics()
        return None

    def get_all_metrics(self) -> Dict[str, ConsumerMetrics]:
        """获取所有消费者指标"""
        return {
            consumer_id: consumer.get_metrics()
            for consumer_id, consumer in self._consumers.items()
        }

    def get_buffered_messages(
        self,
        topic: str,
        limit: int = 100,
        clear: bool = False,
    ) -> List[StreamMessage]:
        """获取缓冲的消息"""
        with self._buffer_lock:
            buffer = self._message_buffers.get(topic, [])

            if clear:
                messages = buffer[:limit]
                self._message_buffers[topic] = buffer[limit:]
            else:
                messages = buffer[-limit:]

            return [m.to_dict() for m in messages]

    def create_topic_config(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 1,
        retention_ms: int = 604800000,
    ) -> KafkaTopicConfig:
        """创建 Topic 配置"""
        return KafkaTopicConfig(
            topic=topic,
            partitions=partitions,
            replication_factor=replication_factor,
            retention_ms=retention_ms,
        )

    def validate_connection(self, bootstrap_servers: str) -> Dict[str, Any]:
        """验证 Kafka 连接"""
        result = {
            "success": False,
            "error": None,
            "version": None,
            "brokers": [],
        }

        try:
            from kafka import KafkaAdminClient
            from kafka.errors import KafkaError

            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=5000,
            )

            # 获取集群元数据
            cluster_metadata = admin_client._client.cluster
            result["success"] = True
            result["brokers"] = [
                {"id": b.nodeId, "host": b.host, "port": b.port}
                for b in cluster_metadata.brokers()
            ]

            admin_client.close()

        except ImportError:
            result["error"] = "kafka-python 库未安装"
        except Exception as e:
            result["error"] = str(e)

        return result

    def get_consumer_config_from_datasource(self, datasource_config: Dict) -> KafkaConsumerConfig:
        """从数据源配置创建消费者配置"""
        connection_config = json.loads(datasource_config.get("connection_config", "{}"))

        return KafkaConsumerConfig(
            bootstrap_servers=connection_config.get("bootstrap_servers", "localhost:9092"),
            group_id=connection_config.get("group_id", "data-consumer-group"),
            topics=connection_config.get("topics", []),
            auto_offset_reset=OffsetReset(connection_config.get("auto_offset_reset", "latest")),
            enable_auto_commit=connection_config.get("enable_auto_commit", True),
            auto_commit_interval_ms=connection_config.get("auto_commit_interval_ms", 5000),
            max_poll_records=connection_config.get("max_poll_records", 500),
            additional_config=connection_config.get("additional_config", {}),
        )


# 全局服务实例
_kafka_stream_service: Optional[KafkaStreamService] = None


def get_kafka_stream_service() -> KafkaStreamService:
    """获取 Kafka 流服务实例"""
    global _kafka_stream_service
    if _kafka_stream_service is None:
        _kafka_stream_service = KafkaStreamService()
    return _kafka_stream_service
