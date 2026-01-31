"""
集成组件 Prometheus 指标单元测试
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加 shared 路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_shared_path = os.path.join(_project_root, "services", "shared")
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)


class TestIntegrationMetricsWithoutPrometheus:
    """测试无 prometheus_client 时的降级行为"""

    def test_import_without_prometheus(self):
        """无 prometheus_client 时应该正常导入"""
        # 模拟 prometheus_client 不可用
        with patch.dict(sys.modules, {"prometheus_client": None}):
            # 需要重新导入模块
            import importlib
            import integration_metrics as im
            importlib.reload(im)

            # 应该可以正常创建实例
            metrics = im.IntegrationMetrics()
            assert metrics is not None

            # 方法调用不应该报错
            metrics.record_etl_execution(im.ETLMetrics(
                engine="hop",
                pipeline_name="test",
                duration_seconds=1.0,
                rows_processed=100,
                success=True
            ))


class TestETLMetricsDataclass:
    """ETLMetrics 数据类测试"""

    def test_etl_metrics_creation(self):
        """创建 ETL 指标数据"""
        from integration_metrics import ETLMetrics

        metrics = ETLMetrics(
            engine="hop",
            pipeline_name="test_pipeline",
            duration_seconds=10.5,
            rows_processed=1000,
            success=True
        )

        assert metrics.engine == "hop"
        assert metrics.pipeline_name == "test_pipeline"
        assert metrics.duration_seconds == 10.5
        assert metrics.rows_processed == 1000
        assert metrics.success is True
        assert metrics.error_message is None

    def test_etl_metrics_with_error(self):
        """创建带错误的 ETL 指标"""
        from integration_metrics import ETLMetrics

        metrics = ETLMetrics(
            engine="kettle",
            pipeline_name="failed_pipeline",
            duration_seconds=5.0,
            rows_processed=0,
            success=False,
            error_message="Connection timeout"
        )

        assert metrics.success is False
        assert metrics.error_message == "Connection timeout"


class TestQualityMetricsDataclass:
    """QualityMetrics 数据类测试"""

    def test_quality_metrics_creation(self):
        """创建质量指标数据"""
        from integration_metrics import QualityMetrics

        metrics = QualityMetrics(
            engine="ge",
            rule_type="not_null",
            table_name="users",
            duration_seconds=2.5,
            rows_validated=500,
            pass_count=480,
            fail_count=20
        )

        assert metrics.engine == "ge"
        assert metrics.rule_type == "not_null"
        assert metrics.table_name == "users"
        assert metrics.pass_count == 480
        assert metrics.fail_count == 20


class TestLLMMetricsDataclass:
    """LLMMetrics 数据类测试"""

    def test_llm_metrics_creation(self):
        """创建 LLM 指标数据"""
        from integration_metrics import LLMMetrics

        metrics = LLMMetrics(
            backend="ollama",
            model="qwen2.5:7b",
            duration_seconds=3.2,
            input_tokens=150,
            output_tokens=200,
            success=True
        )

        assert metrics.backend == "ollama"
        assert metrics.model == "qwen2.5:7b"
        assert metrics.input_tokens == 150
        assert metrics.output_tokens == 200


class TestIntegrationMetricsETL:
    """ETL 指标记录测试"""

    @pytest.fixture
    def metrics(self):
        """创建指标实例"""
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_record_etl_execution_success(self, metrics):
        """记录成功的 ETL 执行"""
        from integration_metrics import ETLMetrics

        etl_data = ETLMetrics(
            engine="hop",
            pipeline_name="sync_users",
            duration_seconds=30.0,
            rows_processed=5000,
            success=True
        )

        # 不应该抛出异常
        metrics.record_etl_execution(etl_data)

    def test_record_etl_execution_failure(self, metrics):
        """记录失败的 ETL 执行"""
        from integration_metrics import ETLMetrics

        etl_data = ETLMetrics(
            engine="kettle",
            pipeline_name="sync_orders",
            duration_seconds=5.0,
            rows_processed=0,
            success=False,
            error_message="Source database unavailable"
        )

        metrics.record_etl_execution(etl_data)

    def test_set_etl_pipelines_active(self, metrics):
        """设置活跃 Pipeline 数量"""
        metrics.set_etl_pipelines_active("hop", 3)
        metrics.set_etl_pipelines_active("kettle", 2)

    def test_set_etl_engine_health(self, metrics):
        """设置 ETL 引擎健康状态"""
        metrics.set_etl_engine_health("hop", True)
        metrics.set_etl_engine_health("kettle", False)


class TestIntegrationMetricsQuality:
    """数据质量指标记录测试"""

    @pytest.fixture
    def metrics(self):
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_record_quality_validation_pass(self, metrics):
        """记录通过的质量校验"""
        from integration_metrics import QualityMetrics

        quality_data = QualityMetrics(
            engine="ge",
            rule_type="expect_column_values_to_not_be_null",
            table_name="users",
            duration_seconds=1.5,
            rows_validated=1000,
            pass_count=1000,
            fail_count=0
        )

        metrics.record_quality_validation(quality_data)

    def test_record_quality_validation_fail(self, metrics):
        """记录失败的质量校验"""
        from integration_metrics import QualityMetrics

        quality_data = QualityMetrics(
            engine="builtin",
            rule_type="range_check",
            table_name="orders",
            duration_seconds=2.0,
            rows_validated=500,
            pass_count=450,
            fail_count=50
        )

        metrics.record_quality_validation(quality_data)

    def test_set_quality_expectation_count(self, metrics):
        """设置质量规则数量"""
        metrics.set_quality_expectation_count("ge", 25)
        metrics.set_quality_expectation_count("builtin", 10)


class TestIntegrationMetricsLabeling:
    """数据标注指标记录测试"""

    @pytest.fixture
    def metrics(self):
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_record_labeling_task_created(self, metrics):
        """记录标注任务创建"""
        metrics.record_labeling_task_created("project_1", 10)
        metrics.record_labeling_task_created("project_2", 5)

    def test_record_labeling_task_completed(self, metrics):
        """记录标注任务完成"""
        metrics.record_labeling_task_completed("project_1", 120.0)

    def test_record_annotation_submitted(self, metrics):
        """记录标注提交"""
        metrics.record_annotation_submitted("project_1", "user_1")
        metrics.record_annotation_submitted("project_1", "user_2")

    def test_set_labeling_projects_active(self, metrics):
        """设置活跃项目数"""
        metrics.set_labeling_projects_active(5)

    def test_set_labeling_tasks_pending(self, metrics):
        """设置待处理任务数"""
        metrics.set_labeling_tasks_pending("project_1", 50)


class TestIntegrationMetricsMasking:
    """透明脱敏指标记录测试"""

    @pytest.fixture
    def metrics(self):
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_record_masking_query(self, metrics):
        """记录脱敏查询"""
        metrics.record_masking_query("test_db", "users", 0.05)
        metrics.record_masking_query("test_db", "orders", 0.03)

    def test_set_masking_rules_active(self, metrics):
        """设置活跃脱敏规则数"""
        metrics.set_masking_rules_active("test_db", 15)

    def test_set_masking_columns_protected(self, metrics):
        """设置受保护列数"""
        metrics.set_masking_columns_protected("test_db", "users", 5)

    def test_set_masking_proxy_health(self, metrics):
        """设置脱敏代理健康状态"""
        metrics.set_masking_proxy_health(True)
        metrics.set_masking_proxy_health(False)


class TestIntegrationMetricsLLM:
    """LLM 推理指标记录测试"""

    @pytest.fixture
    def metrics(self):
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_record_llm_request_success(self, metrics):
        """记录成功的 LLM 请求"""
        from integration_metrics import LLMMetrics

        llm_data = LLMMetrics(
            backend="ollama",
            model="qwen2.5:7b",
            duration_seconds=2.5,
            input_tokens=100,
            output_tokens=150,
            success=True
        )

        metrics.record_llm_request(llm_data)

    def test_record_llm_request_failure(self, metrics):
        """记录失败的 LLM 请求"""
        from integration_metrics import LLMMetrics

        llm_data = LLMMetrics(
            backend="vllm",
            model="Qwen2.5-1.5B-Instruct",
            duration_seconds=30.0,
            input_tokens=500,
            output_tokens=0,
            success=False
        )

        metrics.record_llm_request(llm_data)

    def test_set_llm_backend_health(self, metrics):
        """设置 LLM 后端健康状态"""
        metrics.set_llm_backend_health("ollama", True)
        metrics.set_llm_backend_health("vllm", True)
        metrics.set_llm_backend_health("openai", False)

    def test_set_llm_queue_size(self, metrics):
        """设置 LLM 请求队列大小"""
        metrics.set_llm_queue_size("ollama", 0)
        metrics.set_llm_queue_size("vllm", 5)


class TestMetricsDecorators:
    """指标装饰器测试"""

    @pytest.fixture
    def metrics(self):
        from integration_metrics import IntegrationMetrics
        return IntegrationMetrics()

    def test_etl_metrics_decorator_success(self, metrics):
        """ETL 指标装饰器 - 成功场景"""
        from integration_metrics import etl_metrics

        @etl_metrics(metrics, "hop", "test_pipeline")
        def run_pipeline():
            return {"rows_processed": 100}

        result = run_pipeline()
        assert result["rows_processed"] == 100

    def test_etl_metrics_decorator_failure(self, metrics):
        """ETL 指标装饰器 - 失败场景"""
        from integration_metrics import etl_metrics

        @etl_metrics(metrics, "hop", "failing_pipeline")
        def run_failing_pipeline():
            raise RuntimeError("Pipeline failed")

        with pytest.raises(RuntimeError):
            run_failing_pipeline()

    def test_quality_metrics_decorator(self, metrics):
        """质量指标装饰器"""
        from integration_metrics import quality_metrics

        @quality_metrics(metrics, "ge", "not_null", "users")
        def validate_data():
            return {
                "pass_count": 90,
                "fail_count": 10,
                "rows_validated": 100
            }

        result = validate_data()
        assert result["pass_count"] == 90

    def test_llm_metrics_decorator_success(self, metrics):
        """LLM 指标装饰器 - 成功场景"""
        from integration_metrics import llm_metrics

        @llm_metrics(metrics, "ollama", "qwen2.5")
        def generate_text():
            return {
                "text": "Hello world",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5
                }
            }

        result = generate_text()
        assert result["text"] == "Hello world"

    def test_llm_metrics_decorator_failure(self, metrics):
        """LLM 指标装饰器 - 失败场景"""
        from integration_metrics import llm_metrics

        @llm_metrics(metrics, "vllm", "test-model")
        def failing_generation():
            raise ConnectionError("Backend unavailable")

        with pytest.raises(ConnectionError):
            failing_generation()


class TestGlobalMetricsInstance:
    """全局指标实例测试"""

    def test_get_integration_metrics(self):
        """获取全局指标实例"""
        from integration_metrics import get_integration_metrics

        metrics1 = get_integration_metrics()
        metrics2 = get_integration_metrics()

        # 应该返回同一个实例
        assert metrics1 is metrics2

    def test_get_integration_metrics_with_registry(self):
        """使用自定义 registry 获取指标实例"""
        from integration_metrics import IntegrationMetrics

        # 创建新实例
        metrics = IntegrationMetrics(registry=None)
        assert metrics is not None


class TestEnumValues:
    """枚举值测试"""

    def test_etl_engine_enum(self):
        """ETL 引擎枚举"""
        from integration_metrics import ETLEngine

        assert ETLEngine.KETTLE.value == "kettle"
        assert ETLEngine.HOP.value == "hop"

    def test_llm_backend_enum(self):
        """LLM 后端枚举"""
        from integration_metrics import LLMBackend

        assert LLMBackend.VLLM.value == "vllm"
        assert LLMBackend.OLLAMA.value == "ollama"
        assert LLMBackend.OPENAI.value == "openai"


class TestLabelingMetricsDataclass:
    """LabelingMetrics 数据类测试"""

    def test_labeling_metrics_creation(self):
        """创建标注指标数据"""
        from integration_metrics import LabelingMetrics

        metrics = LabelingMetrics(
            project_id="project_123",
            task_count=100,
            completed_count=75,
            duration_seconds=3600.0
        )

        assert metrics.project_id == "project_123"
        assert metrics.task_count == 100
        assert metrics.completed_count == 75
        assert metrics.duration_seconds == 3600.0


class TestMaskingMetricsDataclass:
    """MaskingMetrics 数据类测试"""

    def test_masking_metrics_creation(self):
        """创建脱敏指标数据"""
        from integration_metrics import MaskingMetrics

        metrics = MaskingMetrics(
            database="production",
            table="customers",
            query_count=1000,
            duration_seconds=5.5
        )

        assert metrics.database == "production"
        assert metrics.table == "customers"
        assert metrics.query_count == 1000
        assert metrics.duration_seconds == 5.5
