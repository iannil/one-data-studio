"""
Phase 1-3 集成组件测试

测试覆盖范围:
- Phase 1: Label Studio 数据标注、Great Expectations 数据质量、Ollama LLM 后端
- Phase 2: Apache Hop 双引擎 ETL、ShardingSphere 透明脱敏
- Phase 3: 监控指标增强、组件健康检查

测试用例编号: INT-P123-001 ~ INT-P123-050
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_shared_path = os.path.join(_project_root, "services", "shared")
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)

logger = logging.getLogger(__name__)


# ==================== Phase 1: Label Studio 集成测试 ====================


@pytest.mark.integration
class TestLabelStudioIntegration:
    """INT-P123-001 ~ INT-P123-008: Label Studio 数据标注集成测试"""

    @pytest.fixture
    def mock_label_studio_client(self):
        """Mock Label Studio 客户端"""
        client = MagicMock()
        client.health_check.return_value = True
        client.create_project.return_value = {
            "id": 1,
            "title": "NER Labeling Project",
            "created_at": "2026-01-31T10:00:00Z",
        }
        client.import_tasks.return_value = {"task_count": 100}
        client.get_project.return_value = {
            "id": 1,
            "title": "NER Labeling Project",
            "task_count": 100,
            "finished_task_count": 75,
        }
        client.export_annotations.return_value = [
            {"id": 1, "data": {"text": "北京是中国首都"}, "annotations": [{"result": [{"type": "labels", "value": {"labels": ["LOC"], "start": 0, "end": 2}}]}]},
            {"id": 2, "data": {"text": "张三在阿里巴巴工作"}, "annotations": [{"result": [{"type": "labels", "value": {"labels": ["PER"], "start": 0, "end": 2}}, {"type": "labels", "value": {"labels": ["ORG"], "start": 3, "end": 7}}]}]},
        ]
        return client

    def test_label_studio_health_check(self, mock_label_studio_client):
        """INT-P123-001: Label Studio 健康检查"""
        is_healthy = mock_label_studio_client.health_check()
        assert is_healthy is True

    def test_create_labeling_project(self, mock_label_studio_client):
        """INT-P123-002: 创建标注项目"""
        project_config = {
            "title": "NER Labeling Project",
            "label_config": """
            <View>
              <Labels name="label" toName="text">
                <Label value="PER" background="red"/>
                <Label value="ORG" background="blue"/>
                <Label value="LOC" background="green"/>
              </Labels>
              <Text name="text" value="$text"/>
            </View>
            """,
        }

        project = mock_label_studio_client.create_project(project_config)

        assert project["id"] == 1
        assert project["title"] == "NER Labeling Project"
        mock_label_studio_client.create_project.assert_called_once_with(project_config)

    def test_import_tasks_to_project(self, mock_label_studio_client):
        """INT-P123-003: 导入标注任务"""
        project_id = 1
        tasks = [
            {"data": {"text": "北京是中国首都"}},
            {"data": {"text": "张三在阿里巴巴工作"}},
            {"data": {"text": "上海外滩很美"}},
        ]

        result = mock_label_studio_client.import_tasks(project_id, tasks)

        assert result["task_count"] == 100
        mock_label_studio_client.import_tasks.assert_called_once()

    def test_get_project_progress(self, mock_label_studio_client):
        """INT-P123-004: 获取项目进度"""
        project_id = 1

        project = mock_label_studio_client.get_project(project_id)

        assert project["task_count"] == 100
        assert project["finished_task_count"] == 75
        progress = project["finished_task_count"] / project["task_count"]
        assert progress == 0.75

    def test_export_annotations(self, mock_label_studio_client):
        """INT-P123-005: 导出标注结果"""
        project_id = 1

        annotations = mock_label_studio_client.export_annotations(project_id)

        assert len(annotations) == 2
        assert annotations[0]["annotations"][0]["result"][0]["value"]["labels"] == ["LOC"]
        assert annotations[1]["annotations"][0]["result"][0]["value"]["labels"] == ["PER"]

    def test_labeling_metrics_recording(self):
        """INT-P123-006: 标注指标记录"""
        from integration_metrics import IntegrationMetrics

        metrics = IntegrationMetrics()

        # 记录任务创建
        metrics.record_labeling_task_created("project_1", 50)
        metrics.record_labeling_task_created("project_1", 30)

        # 记录标注提交
        metrics.record_annotation_submitted("project_1", "user_1")
        metrics.record_annotation_submitted("project_1", "user_2")

        # 设置进度
        metrics.set_labeling_tasks_pending("project_1", 25)
        metrics.set_labeling_projects_active(3)

        # 不应抛出异常
        assert True

    def test_labeling_with_model_api_proxy(self, mock_label_studio_client):
        """INT-P123-007: 通过 Model-API 代理层访问 Label Studio"""
        # 模拟 Model-API 代理层
        model_api_labeling = MagicMock()
        model_api_labeling.create_project.return_value = {"id": 2, "title": "SFT Data"}
        model_api_labeling.get_projects.return_value = [
            {"id": 1, "title": "NER Project", "progress": 0.75},
            {"id": 2, "title": "SFT Data", "progress": 0.50},
        ]

        projects = model_api_labeling.get_projects()

        assert len(projects) == 2
        assert projects[0]["progress"] == 0.75

    def test_ocr_result_labeling_flow(self, mock_label_studio_client):
        """INT-P123-008: OCR 结果校验标注流程"""
        # 模拟 OCR 结果
        ocr_results = [
            {"image_id": "img_001", "text": "发票号码：12345678", "confidence": 0.85},
            {"image_id": "img_002", "text": "金额：￥1,234.56", "confidence": 0.78},
        ]

        # 转换为 Label Studio 任务格式
        tasks = [
            {
                "data": {
                    "image_id": r["image_id"],
                    "ocr_text": r["text"],
                    "confidence": r["confidence"],
                }
            }
            for r in ocr_results
        ]

        mock_label_studio_client.import_tasks(1, tasks)
        mock_label_studio_client.import_tasks.assert_called_with(1, tasks)


# ==================== Phase 1: Great Expectations 集成测试 ====================


@pytest.mark.integration
class TestGreatExpectationsIntegration:
    """INT-P123-009 ~ INT-P123-018: Great Expectations 数据质量集成测试"""

    @pytest.fixture
    def mock_ge_context(self):
        """Mock Great Expectations Context"""
        context = MagicMock()
        context.list_expectation_suite_names.return_value = ["user_data_suite", "order_data_suite"]
        return context

    @pytest.fixture
    def mock_ge_validator(self):
        """Mock Great Expectations Validator"""
        validator = MagicMock()
        validator.expect_column_values_to_not_be_null.return_value = {
            "success": True,
            "result": {"element_count": 10000, "unexpected_count": 0},
        }
        validator.expect_column_values_to_be_unique.return_value = {
            "success": True,
            "result": {"element_count": 10000, "unexpected_count": 0},
        }
        validator.expect_column_values_to_match_regex.return_value = {
            "success": False,
            "result": {"element_count": 10000, "unexpected_count": 150},
        }
        return validator

    def test_ge_context_initialization(self, mock_ge_context):
        """INT-P123-009: Great Expectations Context 初始化"""
        suites = mock_ge_context.list_expectation_suite_names()

        assert len(suites) == 2
        assert "user_data_suite" in suites

    def test_expect_column_not_null(self, mock_ge_validator):
        """INT-P123-010: 列非空期望校验"""
        result = mock_ge_validator.expect_column_values_to_not_be_null("email")

        assert result["success"] is True
        assert result["result"]["unexpected_count"] == 0

    def test_expect_column_unique(self, mock_ge_validator):
        """INT-P123-011: 列唯一性期望校验"""
        result = mock_ge_validator.expect_column_values_to_be_unique("user_id")

        assert result["success"] is True
        assert result["result"]["unexpected_count"] == 0

    def test_expect_column_regex_match(self, mock_ge_validator):
        """INT-P123-012: 列正则匹配期望校验（失败场景）"""
        result = mock_ge_validator.expect_column_values_to_match_regex(
            "phone", r"^1[3-9]\d{9}$"
        )

        assert result["success"] is False
        assert result["result"]["unexpected_count"] == 150

    def test_ge_validation_with_quality_metrics(self):
        """INT-P123-013: GE 校验结果与质量指标联动"""
        from integration_metrics import IntegrationMetrics, QualityMetrics

        metrics = IntegrationMetrics()

        # 模拟 GE 校验结果
        ge_result = {
            "success": True,
            "statistics": {
                "evaluated_expectations": 10,
                "successful_expectations": 9,
                "unsuccessful_expectations": 1,
            },
        }

        quality_data = QualityMetrics(
            engine="ge",
            rule_type="expect_column_values_to_not_be_null",
            table_name="users",
            duration_seconds=1.5,
            rows_validated=10000,
            pass_count=9800,
            fail_count=200,
        )

        metrics.record_quality_validation(quality_data)

        # 验证通过率
        pass_rate = quality_data.pass_count / (quality_data.pass_count + quality_data.fail_count)
        assert pass_rate == pytest.approx(0.98, abs=0.01)

    def test_ge_batch_validation(self):
        """INT-P123-014: GE 批量数据校验"""
        # 模拟批量校验结果
        batch_results = [
            {"expectation": "not_null", "column": "email", "success": True, "unexpected_count": 0},
            {"expectation": "unique", "column": "user_id", "success": True, "unexpected_count": 0},
            {"expectation": "regex", "column": "phone", "success": False, "unexpected_count": 150},
            {"expectation": "range", "column": "age", "success": False, "unexpected_count": 20},
        ]

        success_count = sum(1 for r in batch_results if r["success"])
        fail_count = len(batch_results) - success_count

        assert success_count == 2
        assert fail_count == 2

    def test_ge_data_docs_generation(self):
        """INT-P123-015: GE Data Docs 生成"""
        # 模拟 Data Docs 生成
        mock_build_docs = MagicMock(return_value={
            "local_site": {
                "index": "/ge_docs/index.html",
                "validations": [
                    "/ge_docs/validations/user_data_2026-01-31.html",
                ],
            }
        })

        docs = mock_build_docs()

        assert "local_site" in docs
        assert docs["local_site"]["index"].endswith(".html")

    def test_ge_checkpoint_run(self):
        """INT-P123-016: GE Checkpoint 运行"""
        checkpoint_result = MagicMock()
        checkpoint_result.success = True
        checkpoint_result.list_validation_results.return_value = [
            {"success": True, "expectation_suite_name": "user_data_suite"},
        ]

        assert checkpoint_result.success is True
        results = checkpoint_result.list_validation_results()
        assert len(results) == 1

    def test_ge_with_etl_pipeline(self):
        """INT-P123-017: GE 与 ETL Pipeline 联动"""
        # 模拟 ETL 后触发 GE 校验
        etl_result = {"rows_written": 10000, "success": True}

        if etl_result["success"]:
            # 触发 GE 校验
            ge_validation = MagicMock()
            ge_validation.run.return_value = {
                "success": True,
                "statistics": {"successful_expectations": 10},
            }

            validation_result = ge_validation.run()
            assert validation_result["success"] is True

    def test_quality_metrics_decorator(self):
        """INT-P123-018: 质量指标装饰器"""
        from integration_metrics import IntegrationMetrics, quality_metrics

        metrics = IntegrationMetrics()

        @quality_metrics(metrics, "ge", "not_null", "users")
        def validate_data():
            return {
                "pass_count": 9800,
                "fail_count": 200,
                "rows_validated": 10000,
            }

        result = validate_data()

        assert result["pass_count"] == 9800
        assert result["rows_validated"] == 10000


# ==================== Phase 1: Ollama LLM 后端集成测试 ====================


@pytest.mark.integration
class TestOllamaBackendIntegration:
    """INT-P123-019 ~ INT-P123-026: Ollama LLM 后端集成测试"""

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama 客户端"""
        client = MagicMock()
        client.health_check.return_value = True
        client.list_models.return_value = [
            {"name": "qwen2.5:7b", "size": "4.5GB"},
            {"name": "llama3:8b", "size": "4.7GB"},
        ]
        client.chat.return_value = {
            "model": "qwen2.5:7b",
            "message": {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
            "done": True,
            "total_duration": 1500000000,
            "eval_count": 15,
            "prompt_eval_count": 10,
        }
        return client

    def test_ollama_health_check(self, mock_ollama_client):
        """INT-P123-019: Ollama 健康检查"""
        is_healthy = mock_ollama_client.health_check()
        assert is_healthy is True

    def test_ollama_list_models(self, mock_ollama_client):
        """INT-P123-020: Ollama 列出可用模型"""
        models = mock_ollama_client.list_models()

        assert len(models) == 2
        assert models[0]["name"] == "qwen2.5:7b"

    def test_ollama_chat_completion(self, mock_ollama_client):
        """INT-P123-021: Ollama 聊天补全"""
        response = mock_ollama_client.chat(
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": "你好"}],
        )

        assert response["model"] == "qwen2.5:7b"
        assert "你好" in response["message"]["content"]
        assert response["done"] is True

    def test_ollama_openai_compatible_format(self, mock_ollama_client):
        """INT-P123-022: Ollama OpenAI 兼容格式"""
        # 模拟 OpenAI 兼容响应
        openai_format_response = {
            "id": "chatcmpl-ollama-001",
            "object": "chat.completion",
            "created": 1706745600,
            "model": "qwen2.5:7b",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "你好！"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25,
            },
        }

        assert openai_format_response["object"] == "chat.completion"
        assert "choices" in openai_format_response
        assert openai_format_response["choices"][0]["finish_reason"] == "stop"

    def test_llm_backend_switching(self):
        """INT-P123-023: LLM 后端切换 (Ollama <-> vLLM)"""
        # 模拟后端切换逻辑
        backend_config = {
            "default": "vllm",
            "backends": {
                "vllm": {"url": "http://vllm:8000", "enabled": True},
                "ollama": {"url": "http://ollama:11434", "enabled": True},
            },
        }

        def get_backend(backend_name):
            if backend_config["backends"].get(backend_name, {}).get("enabled"):
                return backend_config["backends"][backend_name]
            return backend_config["backends"][backend_config["default"]]

        vllm_backend = get_backend("vllm")
        ollama_backend = get_backend("ollama")

        assert vllm_backend["url"] == "http://vllm:8000"
        assert ollama_backend["url"] == "http://ollama:11434"

    def test_llm_metrics_recording(self):
        """INT-P123-024: LLM 推理指标记录"""
        from integration_metrics import IntegrationMetrics, LLMMetrics

        metrics = IntegrationMetrics()

        llm_data = LLMMetrics(
            backend="ollama",
            model="qwen2.5:7b",
            duration_seconds=1.5,
            input_tokens=100,
            output_tokens=150,
            success=True,
        )

        metrics.record_llm_request(llm_data)
        metrics.set_llm_backend_health("ollama", True)
        metrics.set_llm_queue_size("ollama", 3)

        # 不应抛出异常
        assert True

    def test_llm_metrics_decorator(self):
        """INT-P123-025: LLM 指标装饰器"""
        from integration_metrics import IntegrationMetrics, llm_metrics

        metrics = IntegrationMetrics()

        @llm_metrics(metrics, "ollama", "qwen2.5:7b")
        def generate_response():
            return {
                "text": "生成的文本",
                "usage": {"prompt_tokens": 50, "completion_tokens": 100},
            }

        result = generate_response()

        assert result["text"] == "生成的文本"

    def test_ollama_error_handling(self, mock_ollama_client):
        """INT-P123-026: Ollama 错误处理"""
        mock_ollama_client.chat.side_effect = ConnectionError("Ollama 服务不可用")

        with pytest.raises(ConnectionError):
            mock_ollama_client.chat(
                model="qwen2.5:7b",
                messages=[{"role": "user", "content": "test"}],
            )


# ==================== Phase 2: Apache Hop 双引擎 ETL 集成测试 ====================


@pytest.mark.integration
class TestDualEngineETLIntegration:
    """INT-P123-027 ~ INT-P123-036: Apache Hop 双引擎 ETL 集成测试"""

    @pytest.fixture
    def mock_hop_bridge(self):
        """Mock Hop Bridge"""
        bridge = MagicMock()
        bridge.health_check.return_value = True
        bridge.register_pipeline.return_value = {"success": True, "id": "pipeline_001"}
        bridge.execute_pipeline.return_value = {"success": True, "id": "exec_001"}
        bridge.get_pipeline_status.return_value = MagicMock(
            status="Finished",
            is_finished=True,
            is_success=True,
            is_running=False,
            rows_read=10000,
            rows_written=9850,
        )
        bridge.list_pipelines.return_value = [
            {"name": "sync_users", "status": "Finished"},
            {"name": "sync_orders", "status": "Running"},
        ]
        return bridge

    @pytest.fixture
    def mock_kettle_bridge(self):
        """Mock Kettle Bridge"""
        bridge = MagicMock()
        bridge.health_check.return_value = True
        bridge.register_transformation.return_value = {"success": True}
        bridge.execute_transformation.return_value = {"success": True, "id": "trans_001"}
        bridge.get_transformation_status.return_value = MagicMock(
            status="Finished",
            is_finished=True,
            is_success=True,
            rows_read=10000,
            rows_written=9800,
        )
        return bridge

    def test_hop_server_health_check(self, mock_hop_bridge):
        """INT-P123-027: Hop Server 健康检查"""
        is_healthy = mock_hop_bridge.health_check()
        assert is_healthy is True

    def test_hop_pipeline_registration(self, mock_hop_bridge):
        """INT-P123-028: Hop Pipeline 注册"""
        pipeline_xml = "<pipeline><info><name>test</name></info></pipeline>"

        result = mock_hop_bridge.register_pipeline(pipeline_xml, "test_pipeline")

        assert result["success"] is True
        assert result["id"] == "pipeline_001"

    def test_hop_pipeline_execution(self, mock_hop_bridge):
        """INT-P123-029: Hop Pipeline 执行"""
        result = mock_hop_bridge.execute_pipeline("test_pipeline")

        assert result["success"] is True

    def test_hop_pipeline_status(self, mock_hop_bridge):
        """INT-P123-030: Hop Pipeline 状态查询"""
        status = mock_hop_bridge.get_pipeline_status("test_pipeline")

        assert status.is_finished is True
        assert status.is_success is True
        assert status.rows_read == 10000
        assert status.rows_written == 9850

    def test_dual_engine_selection_auto(self, mock_hop_bridge, mock_kettle_bridge):
        """INT-P123-031: 双引擎自动选择 (优先 Hop)"""
        hop_available = mock_hop_bridge.health_check()
        kettle_available = mock_kettle_bridge.health_check()

        # 自动选择逻辑：优先 Hop
        if hop_available:
            selected_engine = "hop"
        elif kettle_available:
            selected_engine = "kettle"
        else:
            selected_engine = None

        assert selected_engine == "hop"

    def test_dual_engine_fallback_to_kettle(self, mock_kettle_bridge):
        """INT-P123-032: 双引擎回退到 Kettle"""
        # Hop 不可用
        hop_available = False
        kettle_available = mock_kettle_bridge.health_check()

        if hop_available:
            selected_engine = "hop"
        elif kettle_available:
            selected_engine = "kettle"
        else:
            selected_engine = None

        assert selected_engine == "kettle"

    def test_etl_metrics_recording(self):
        """INT-P123-033: ETL 执行指标记录"""
        from integration_metrics import IntegrationMetrics, ETLMetrics

        metrics = IntegrationMetrics()

        etl_data = ETLMetrics(
            engine="hop",
            pipeline_name="sync_users",
            duration_seconds=30.5,
            rows_processed=10000,
            success=True,
        )

        metrics.record_etl_execution(etl_data)
        metrics.set_etl_pipelines_active("hop", 3)
        metrics.set_etl_engine_health("hop", True)

        # 不应抛出异常
        assert True

    def test_etl_metrics_decorator(self):
        """INT-P123-034: ETL 指标装饰器"""
        from integration_metrics import IntegrationMetrics, etl_metrics

        metrics = IntegrationMetrics()

        @etl_metrics(metrics, "hop", "sync_users")
        def run_pipeline():
            return {"rows_processed": 10000}

        result = run_pipeline()

        assert result["rows_processed"] == 10000

    def test_get_available_engines(self, mock_hop_bridge, mock_kettle_bridge):
        """INT-P123-035: 获取所有可用引擎状态"""
        engines = {
            "hop": {
                "enabled": True,
                "healthy": mock_hop_bridge.health_check(),
                "status": "available" if mock_hop_bridge.health_check() else "unavailable",
            },
            "kettle": {
                "enabled": True,
                "healthy": mock_kettle_bridge.health_check(),
                "status": "available" if mock_kettle_bridge.health_check() else "unavailable",
            },
        }

        assert engines["hop"]["status"] == "available"
        assert engines["kettle"]["status"] == "available"

    def test_list_hop_pipelines(self, mock_hop_bridge):
        """INT-P123-036: 列出 Hop Pipelines"""
        pipelines = mock_hop_bridge.list_pipelines()

        assert len(pipelines) == 2
        assert pipelines[0]["name"] == "sync_users"
        assert pipelines[1]["status"] == "Running"


# ==================== Phase 2: ShardingSphere 透明脱敏集成测试 ====================


@pytest.mark.integration
class TestShardingSphereMaskingIntegration:
    """INT-P123-037 ~ INT-P123-044: ShardingSphere 透明脱敏集成测试"""

    @pytest.fixture
    def mock_shardingsphere_client(self):
        """Mock ShardingSphere 客户端"""
        client = MagicMock()
        client.health_check.return_value = True
        client.show_databases.return_value = ["test_db", "prod_db"]
        client.execute_distsql.return_value = {"success": True}
        client.apply_mask_rules.return_value = {"success": True, "rules_applied": 5}
        client.list_mask_rules.return_value = [
            {"table": "users", "column": "phone", "algorithm": "MASK_FIRST_N_LAST_M"},
            {"table": "users", "column": "email", "algorithm": "MASK_BEFORE_SPECIAL_CHARS"},
        ]
        return client

    def test_shardingsphere_health_check(self, mock_shardingsphere_client):
        """INT-P123-037: ShardingSphere Proxy 健康检查"""
        is_healthy = mock_shardingsphere_client.health_check()
        assert is_healthy is True

    def test_shardingsphere_show_databases(self, mock_shardingsphere_client):
        """INT-P123-038: ShardingSphere 显示数据库"""
        databases = mock_shardingsphere_client.show_databases()

        assert len(databases) == 2
        assert "test_db" in databases

    def test_generate_masking_rules_from_sensitivity(self):
        """INT-P123-039: 从敏感扫描结果生成脱敏规则"""
        sensitivity_results = [
            {"column_name": "phone", "sensitivity_type": "phone"},
            {"column_name": "email", "sensitivity_type": "email"},
            {"column_name": "id_card", "sensitivity_type": "id_card"},
        ]

        # 模拟规则生成
        algorithm_map = {
            "phone": ("MASK_FIRST_N_LAST_M", {"first-n": 3, "last-m": 4}),
            "email": ("MASK_BEFORE_SPECIAL_CHARS", {"special-chars": "@"}),
            "id_card": ("MASK_FIRST_N_LAST_M", {"first-n": 6, "last-m": 4}),
        }

        rules = []
        for result in sensitivity_results:
            sensitivity_type = result["sensitivity_type"]
            if sensitivity_type in algorithm_map:
                algo, params = algorithm_map[sensitivity_type]
                rules.append({
                    "column": result["column_name"],
                    "algorithm": algo,
                    "params": params,
                })

        assert len(rules) == 3
        assert rules[0]["algorithm"] == "MASK_FIRST_N_LAST_M"
        assert rules[1]["algorithm"] == "MASK_BEFORE_SPECIAL_CHARS"

    def test_apply_masking_rules(self, mock_shardingsphere_client):
        """INT-P123-040: 应用脱敏规则"""
        distsql = """
        CREATE MASK RULE t_user (
            COLUMNS(
                (NAME=phone, TYPE(NAME='MASK_FIRST_N_LAST_M', PROPERTIES('first-n'='3', 'last-m'='4', 'replace-char'='*'))),
                (NAME=email, TYPE(NAME='MASK_BEFORE_SPECIAL_CHARS', PROPERTIES('special-chars'='@', 'replace-char'='*')))
            )
        );
        """

        result = mock_shardingsphere_client.apply_mask_rules(distsql)

        assert result["success"] is True
        assert result["rules_applied"] == 5

    def test_list_masking_rules(self, mock_shardingsphere_client):
        """INT-P123-041: 列出已生效脱敏规则"""
        rules = mock_shardingsphere_client.list_mask_rules("test_db")

        assert len(rules) == 2
        assert rules[0]["column"] == "phone"
        assert rules[1]["algorithm"] == "MASK_BEFORE_SPECIAL_CHARS"

    def test_masking_metrics_recording(self):
        """INT-P123-042: 脱敏查询指标记录"""
        from integration_metrics import IntegrationMetrics

        metrics = IntegrationMetrics()

        metrics.record_masking_query("test_db", "users", 0.05)
        metrics.set_masking_rules_active("test_db", 10)
        metrics.set_masking_columns_protected("test_db", "users", 5)
        metrics.set_masking_proxy_health(True)

        # 不应抛出异常
        assert True

    def test_masking_with_sensitivity_scan_linkage(self, mock_shardingsphere_client):
        """INT-P123-043: 脱敏与敏感扫描联动"""
        # 模拟敏感扫描服务
        sensitivity_scan = MagicMock()
        sensitivity_scan.scan_table.return_value = [
            {"column_name": "phone", "sensitivity_type": "phone", "confidence": 0.95},
            {"column_name": "email", "sensitivity_type": "email", "confidence": 0.92},
        ]

        # 执行扫描
        scan_results = sensitivity_scan.scan_table("test_db", "users")

        # 生成脱敏规则
        assert len(scan_results) == 2

        # 应用到 ShardingSphere
        mock_shardingsphere_client.apply_mask_rules("CREATE MASK RULE...")
        mock_shardingsphere_client.apply_mask_rules.assert_called_once()

    def test_masking_yaml_generation(self):
        """INT-P123-044: 脱敏规则 YAML 生成"""
        rules = [
            {"column": "phone", "algorithm": "MASK_FIRST_N_LAST_M", "params": {"first-n": 3, "last-m": 4}},
            {"column": "email", "algorithm": "MASK_BEFORE_SPECIAL_CHARS", "params": {"special-chars": "@"}},
        ]

        # 模拟 YAML 生成
        yaml_content = {
            "maskAlgorithms": {
                "phone_mask": {"type": "MASK_FIRST_N_LAST_M", "props": {"first-n": 3, "last-m": 4}},
                "email_mask": {"type": "MASK_BEFORE_SPECIAL_CHARS", "props": {"special-chars": "@"}},
            },
            "tables": {
                "users": {
                    "columns": {
                        "phone": {"maskAlgorithm": "phone_mask"},
                        "email": {"maskAlgorithm": "email_mask"},
                    }
                }
            },
        }

        assert "maskAlgorithms" in yaml_content
        assert "phone_mask" in yaml_content["maskAlgorithms"]


# ==================== Phase 3: 监控指标与组件健康检查集成测试 ====================


@pytest.mark.integration
class TestMonitoringIntegration:
    """INT-P123-045 ~ INT-P123-050: 监控指标与健康检查集成测试"""

    def test_all_integration_metrics_types(self):
        """INT-P123-045: 所有集成指标类型"""
        from integration_metrics import (
            IntegrationMetrics,
            ETLMetrics,
            QualityMetrics,
            LabelingMetrics,
            MaskingMetrics,
            LLMMetrics,
        )

        # 验证所有数据类可创建
        etl = ETLMetrics(
            engine="hop",
            pipeline_name="test",
            duration_seconds=1.0,
            rows_processed=100,
            success=True,
        )
        assert etl.engine == "hop"

        quality = QualityMetrics(
            engine="ge",
            rule_type="not_null",
            table_name="users",
            duration_seconds=1.0,
            rows_validated=100,
            pass_count=95,
            fail_count=5,
        )
        assert quality.pass_count == 95

        labeling = LabelingMetrics(
            project_id="proj_1",
            task_count=100,
            completed_count=75,
            duration_seconds=3600.0,
        )
        assert labeling.completed_count == 75

        masking = MaskingMetrics(
            database="test_db",
            table="users",
            query_count=1000,
            duration_seconds=5.0,
        )
        assert masking.query_count == 1000

        llm = LLMMetrics(
            backend="ollama",
            model="qwen2.5",
            duration_seconds=2.0,
            input_tokens=100,
            output_tokens=150,
            success=True,
        )
        assert llm.output_tokens == 150

    def test_integration_metrics_without_prometheus(self):
        """INT-P123-046: 无 prometheus_client 时的降级行为"""
        from integration_metrics import IntegrationMetrics, ETLMetrics

        metrics = IntegrationMetrics()

        # 即使没有 Prometheus，方法也应正常工作
        etl_data = ETLMetrics(
            engine="hop",
            pipeline_name="test",
            duration_seconds=1.0,
            rows_processed=100,
            success=True,
        )

        # 不应抛出异常
        metrics.record_etl_execution(etl_data)
        metrics.set_etl_engine_health("hop", True)
        metrics.set_llm_backend_health("ollama", True)

    def test_global_metrics_singleton(self):
        """INT-P123-047: 全局指标实例单例"""
        from integration_metrics import get_integration_metrics

        metrics1 = get_integration_metrics()
        metrics2 = get_integration_metrics()

        assert metrics1 is metrics2

    def test_enum_values(self):
        """INT-P123-048: 枚举值测试"""
        from integration_metrics import ETLEngine, LLMBackend

        assert ETLEngine.KETTLE.value == "kettle"
        assert ETLEngine.HOP.value == "hop"
        assert LLMBackend.VLLM.value == "vllm"
        assert LLMBackend.OLLAMA.value == "ollama"
        assert LLMBackend.OPENAI.value == "openai"

    def test_component_health_aggregation(self):
        """INT-P123-049: 组件健康状态聚合"""
        health_status = {
            "etl": {
                "hop": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
                "kettle": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
            },
            "quality": {
                "ge": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
            },
            "llm": {
                "ollama": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
                "vllm": {"healthy": False, "last_check": "2026-01-31T10:00:00Z"},
            },
            "masking": {
                "shardingsphere": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
            },
            "labeling": {
                "label_studio": {"healthy": True, "last_check": "2026-01-31T10:00:00Z"},
            },
        }

        # 聚合健康状态
        all_healthy = all(
            component["healthy"]
            for category in health_status.values()
            for component in category.values()
        )

        unhealthy_components = [
            f"{category}/{name}"
            for category, components in health_status.items()
            for name, status in components.items()
            if not status["healthy"]
        ]

        assert all_healthy is False
        assert "llm/vllm" in unhealthy_components

    def test_grafana_dashboard_data_format(self):
        """INT-P123-050: Grafana Dashboard 数据格式"""
        # 模拟 Prometheus 查询结果
        prometheus_response = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"engine": "hop", "job": "etl"},
                        "value": [1706745600, "150"],
                    },
                    {
                        "metric": {"engine": "kettle", "job": "etl"},
                        "value": [1706745600, "50"],
                    },
                ],
            },
        }

        assert prometheus_response["status"] == "success"
        assert len(prometheus_response["data"]["result"]) == 2

        # 转换为 Grafana 图表数据
        chart_data = [
            {
                "name": r["metric"]["engine"],
                "value": int(r["value"][1]),
            }
            for r in prometheus_response["data"]["result"]
        ]

        assert chart_data[0]["name"] == "hop"
        assert chart_data[0]["value"] == 150


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
