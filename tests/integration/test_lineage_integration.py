"""
数据血缘集成测试

测试场景:
1. 血缘事件发送与持久化
2. 血缘边自动推导
3. 上游/下游查询
4. 血缘路径查找
5. 影响分析
"""

import os
import sys
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from models.lineage_event import (
    LineageEvent,
    DatasetOperationEvent,
    DatasetIdentifier,
    EventType,
    EventSource,
    create_etl_lineage_event,
    create_scan_lineage_event,
    LineageEdgeModel,
)
from services.openlineage_event_service import (
    OpenLineageEventService,
    get_openlineage_event_service,
)

# 测试配置
TEST_NAMESPACE = "test_lineage"


@pytest.fixture
def mock_db():
    """模拟数据库"""
    with patch('services.openlineage_event_service.db_manager') as mock:
        session = Mock()
        mock.get_session.return_value = session
        yield session


@pytest.fixture
def lineage_service():
    """血缘服务实例"""
    service = OpenLineageEventService(batch_size=10, flush_interval=1)
    service.start()
    yield service
    service.stop()


class TestLineageEventCreation:
    """血缘事件创建测试"""

    def test_create_etl_lineage_event(self):
        """测试创建 ETL 血缘事件"""
        event = create_etl_lineage_event(
            job_name="test_etl_job",
            source_tables["source.db.table1", "source.db.table2"],
            target_tables=["target.db.result"],
            transformation="SELECT * FROM source",
        )

        assert event.job_name == "test_etl_job"
        assert len(event.input_datasets) == 2
        assert len(event.output_datasets) == 1
        assert event.transformation == "SELECT * FROM source"

    def test_create_scan_lineage_event(self):
        """测试创建扫描血缘事件"""
        event = create_scan_lineage_event(
            database="test_db",
            tables_scanned=["table1", "table2", "table3"],
            scan_id="scan_001",
        )

        assert event.event_type == EventType.DATASET_SCANNED
        assert event.job_name == "metadata_scan_test_db"
        assert len(event.output_datasets) == 3

    def test_dataset_operation_event(self):
        """测试数据集操作事件"""
        dataset = DatasetIdentifier(
            namespace="test_ns",
            name="test_table",
            type="table",
        )
        event = DatasetOperationEvent(
            event_type=EventType.DATASET_CREATED,
            source=EventSource.API_OPERATION,
            dataset=dataset,
            description="Test table created",
        )

        assert event.event_type == EventType.DATASET_CREATED
        assert event.dataset.namespace == "test_ns"
        assert event.dataset.name == "test_table"

    def test_event_to_openlineage_dict(self):
        """测试转换为 OpenLineage 格式"""
        event = LineageEvent(
            job_name="test_job",
            input_datasets=[
                DatasetIdentifier(namespace="source", name="table1"),
            ],
            output_datasets=[
                DatasetIdentifier(namespace="target", name="table2"),
            ],
        )

        lineage_dict = event.to_openlineage_dict()

        assert lineage_dict["eventType"] == "START"
        assert lineage_dict["job"]["name"] == "test_job"
        assert len(lineage_dict["inputs"]) == 1
        assert len(lineage_dict["outputs"]) == 1


class TestLineageEventService:
    """血缘事件服务测试"""

    def test_emit_event(self, lineage_service, mock_db):
        """测试发送事件"""
        event = LineageEvent(
            job_name="test_job",
            input_datasets=[
                DatasetIdentifier(namespace="source", name="table1"),
            ],
            output_datasets=[
                DatasetIdentifier(namespace="target", name="table2"),
            ],
        )

        result = lineage_service.emit_event(event)

        assert result is True
        assert lineage_service._stats["events_received"] == 1

    def test_emit_etl_event(self, lineage_service, mock_db):
        """测试发送 ETL 事件"""
        result = lineage_service.emit_etl_event(
            job_name="test_etl",
            source_tables=["source.db.table1"],
            target_tables=["target.db.table2"],
            transformation="INSERT INTO target SELECT * FROM source",
        )

        assert result is True

    def test_emit_batch_events(self, lineage_service, mock_db):
        """测试批量发送事件"""
        events = [
            LineageEvent(
                job_name=f"job_{i}",
                input_datasets=[DatasetIdentifier(namespace="source", name=f"table_{i}")],
                output_datasets=[DatasetIdentifier(namespace="target", name=f"result_{i}")],
            )
            for i in range(5)
        ]

        count = lineage_service.emit_batch(events)

        assert count == 5

    def test_health_check(self, lineage_service):
        """测试健康检查"""
        assert lineage_service.health_check() is True

        lineage_service.stop()
        assert lineage_service.health_check() is False

    def test_get_stats(self, lineage_service):
        """测试获取统计信息"""
        stats = lineage_service.get_stats()

        assert "events_received" in stats
        assert "events_persisted" in stats
        assert "queue_size" in stats


class TestLineagePersistence:
    """血缘持久化测试"""

    def test_persist_event(self, mock_db):
        """测试事件持久化"""
        service = OpenLineageEventService()

        event = LineageEvent(
            event_id="test-event-001",
            job_name="test_job",
            input_datasets=[
                DatasetIdentifier(namespace="source", name="table1"),
            ],
            output_datasets=[
                DatasetIdentifier(namespace="target", name="table2"),
            ],
        )

        # 模拟持久化
        model = service._event_to_model(event)

        assert model.event_id == "test-event-001"
        assert model.job_name == "test_job"
        assert model.input_datasets is not None
        assert model.output_datasets is not None

    def test_derive_edges(self, mock_db):
        """测试血缘边推导"""
        service = OpenLineageEventService()

        events = [
            LineageEvent(
                job_name="etl_1",
                input_datasets=[
                    DatasetIdentifier(namespace="source", name="table1"),
                ],
                output_datasets=[
                    DatasetIdentifier(namespace="target", name="table2"),
                ],
            ),
            LineageEvent(
                job_name="etl_2",
                input_datasets=[
                    DatasetIdentifier(namespace="target", name="table2"),
                ],
                output_datasets=[
                    DatasetIdentifier(namespace="target", name="table3"),
                ],
            ),
        ]

        edges = service._derive_edges(events)

        assert len(edges) == 2
        # 第一条边: source.table1 -> target.table2
        assert edges[0]["source_namespace"] == "source"
        assert edges[0]["source_name"] == "table1"
        assert edges[0]["target_namespace"] == "target"
        assert edges[0]["target_name"] == "table2"
        # 第二条边: target.table2 -> target.table3
        assert edges[1]["source_namespace"] == "target"
        assert edges[1]["source_name"] == "table2"
        assert edges[1]["target_namespace"] == "target"
        assert edges[1]["target_name"] == "table3"


class TestLineageQueries:
    """血缘查询测试"""

    @pytest.fixture
    def sample_edges(self, mock_db):
        """创建示例血缘边数据"""
        # 模拟查询返回的边数据
        edges = [
            Mock(
                source_namespace="source",
                source_name="table1",
                source_type="table",
                target_namespace="staging",
                target_name="stg_table1",
                target_type="table",
                source_fqn="source.table1",
                target_fqn="staging.stg_table1",
                transformation="SELECT * FROM source.table1",
            ),
            Mock(
                source_namespace="staging",
                source_name="stg_table1",
                source_type="table",
                target_namespace="prod",
                target_name="prod_table1",
                target_type="table",
                source_fqn="staging.stg_table1",
                target_fqn="prod.prod_table1",
                transformation="SELECT * FROM staging.stg_table1",
            ),
            Mock(
                source_namespace="prod",
                source_name="prod_table1",
                source_type="table",
                target_namespace="analytics",
                target_name="analytics_table1",
                target_type="table",
                source_fqn="prod.prod_table1",
                target_fqn="analytics.analytics_table1",
                transformation=None,
            ),
        ]
        return edges

    def test_get_upstream(self, sample_edges, mock_db):
        """测试获取上游依赖"""
        service = OpenLineageEventService()

        # 模拟查询
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = service.get_upstream(
            dataset_namespace="prod",
            dataset_name="prod_table1",
            max_depth=3,
        )

        # 结果应该包含上游数据集
        assert isinstance(result, list)

    def test_get_downstream(self, sample_edges, mock_db):
        """测试获取下游依赖"""
        service = OpenLineageEventService()

        # 模拟查询
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = service.get_downstream(
            dataset_namespace="staging",
            dataset_name="stg_table1",
            max_depth=3,
        )

        assert isinstance(result, list)

    def test_get_path(self, sample_edges, mock_db):
        """测试获取血缘路径"""
        service = OpenLineageEventService()

        # 模拟查询
        mock_db.query.return_value.filter.return_value.all.return_value = sample_edges

        path = service.get_path(
            source_namespace="source",
            source_name="table1",
            target_namespace="analytics",
            target_name="analytics_table1",
            max_depth=10,
        )

        # 路径应该是: source.table1 -> staging.stg_table1 -> prod.prod_table1 -> analytics.analytics_table1
        assert path is not None
        assert len(path) == 4
        assert path[0] == "source.table1"
        assert path[-1] == "analytics.analytics_table1"

    def test_impact_analysis(self, sample_edges, mock_db):
        """测试影响分析"""
        service = OpenLineageEventService()

        # 模拟查询返回所有下游
        mock_db.query.return_value.filter.return_value.all.return_value = sample_edges

        impact = service.get_impact_analysis(
            dataset_namespace="staging",
            dataset_name="stg_table1",
            max_depth=5,
        )

        assert impact["source"] == "staging.stg_table1"
        assert impact["total_downstream"] >= 0
        assert "by_depth" in impact
        assert "by_type" in impact


class TestOpenLineageProtocol:
    """OpenLineage 协议测试"""

    def test_event_serialization(self):
        """测试事件序列化"""
        event = LineageEvent(
            event_id="test-001",
            event_type=EventType.JOB_STARTED,
            event_time=datetime(2024, 1, 1, 12, 0, 0),
            job_namespace="test_ns",
            job_name="test_job",
            run_id="run-001",
            input_datasets=[
                DatasetIdentifier(
                    namespace="source",
                    name="table1",
                    type="table",
                    facets={"schema": {"columns": ["id", "name"]}},
                )
            ],
            output_datasets=[
                DatasetIdentifier(
                    namespace="target",
                    name="table2",
                    type="table",
                )
            ],
        )

        lineage_dict = event.to_openlineage_dict()

        # 验证 OpenLineage 格式
        assert "eventType" in lineage_dict
        assert "eventTime" in lineage_dict
        assert "run" in lineage_dict
        assert "job" in lineage_dict
        assert "inputs" in lineage_dict
        assert "outputs" in lineage_dict

        assert lineage_dict["eventType"] == "START"
        assert lineage_dict["job"]["namespace"] == "test_ns"
        assert lineage_dict["job"]["name"] == "test_job"

    def test_dataset_facets(self):
        """测试数据集 facets"""
        dataset = DatasetIdentifier(
            namespace="test",
            name="test_table",
            facets={
                "schema": {
                    "fields": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "VARCHAR"},
                    ]
                },
                "ownership": [{"name": "data-team", "type": "GROUP"}],
            }
        )

        assert dataset.facets["schema"]["fields"][0]["name"] == "id"
        assert dataset.facets["ownership"][0]["name"] == "data-team"

    def test_multiple_outputs(self):
        """测试多输出场景"""
        event = LineageEvent(
            job_name="split_job",
            input_datasets=[
                DatasetIdentifier(namespace="source", name="input_table"),
            ],
            output_datasets=[
                DatasetIdentifier(namespace="output", name="table_a"),
                DatasetIdentifier(namespace="output", name="table_b"),
                DatasetIdentifier(namespace="output", name="table_c"),
            ],
        )

        edges = OpenLineageEventService._derive_edges(None, [event])

        # 应该生成 3 条边: input -> table_a, input -> table_b, input -> table_c
        assert len(edges) == 3


class TestLineageEdgeModel:
    """血缘边模型测试"""

    def test_edge_model_properties(self):
        """测试边模型属性"""
        edge = LineageEdgeModel(
            source_namespace="source",
            source_name="table1",
            source_type="table",
            target_namespace="target",
            target_name="table2",
            target_type="table",
            edge_type="data_flow",
            transformation="SELECT * FROM source",
        )

        assert edge.source_fqn == "source.table1"
        assert edge.target_fqn == "target.table2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
