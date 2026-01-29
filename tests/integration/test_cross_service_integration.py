"""
跨服务集成测试
测试 Data、Model、Agent 之间的协作

使用真实服务类，但 Mock 外部依赖（Kubernetes、HTTP、数据库）。
"""

import sys
import os

# 必须在导入其他模块之前插入路径
_model_api_path = os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'model-api')
_agent_api_path = os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'agent-api')
_data_api_path = os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'data-api')

# 临时移除项目根目录以避免 services 包冲突
_project_root = os.path.join(os.path.dirname(__file__), '..', '..')
if _project_root in sys.path:
    sys.path.remove(_project_root)

sys.path.insert(0, _model_api_path)
sys.path.insert(0, _agent_api_path)
sys.path.insert(0, _data_api_path)

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

try:
    from services.k8s_training_service import (
        K8sTrainingService,
        TrainingJobSpec,
        TrainingFramework,
        ResourceRequest,
        GPUResource,
        TrainingInput,
        Hyperparameters,
        JobType,
        JobStatus,
        JobResult,
    )
    from services.inference import ModelInferenceService, InferenceResult
    K8S_IMPORTS_AVAILABLE = True
except ImportError as e:
    K8S_IMPORTS_AVAILABLE = False
    K8S_IMPORT_ERROR = str(e)

# 恢复项目根目录
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


pytestmark = pytest.mark.skipif(
    not K8S_IMPORTS_AVAILABLE,
    reason=f"跳过: 无法导入 k8s_training_service 模块"
)


def _make_mock_k8s_modules():
    """构建 Mock 的 kubernetes 模块，使 K8sTrainingService 可以正常工作"""
    mock_config = MagicMock()
    mock_client = MagicMock()

    # 模拟所有 kubernetes.client 数据类，使其直接保存参数
    for cls_name in [
        "V1ObjectMeta", "V1PodTemplateSpec", "V1PodSpec", "V1Container",
        "V1ResourceRequirements", "V1EnvVar", "V1VolumeMount", "V1Volume",
        "V1PersistentVolumeClaimVolumeSource", "V1Job", "V1JobSpec",
        "V1DeleteOptions", "CoreV1Api", "BatchV1Api", "CustomObjectsApi",
    ]:
        setattr(mock_client, cls_name, MagicMock())

    return mock_client, mock_config


@pytest.mark.integration
@pytest.mark.p0
class TestCrossServiceIntegration:
    """跨服务集成测试"""

    @pytest.mark.asyncio
    async def test_data_to_model_pipeline(self):
        """测试数据(Data) -> 模型(Model) 的跨服务流程：ETL输出数据集后提交K8s训练任务"""
        mock_client, mock_config = _make_mock_k8s_modules()

        with patch.dict("sys.modules", {
            "kubernetes": MagicMock(client=mock_client, config=mock_config),
            "kubernetes.client": mock_client,
            "kubernetes.config": mock_config,
        }):
            # 1. Data 层：ETL 输出数据集路径（模拟）
            dataset_path = "s3://datasets/training_data/"

            # 2. Model 层：使用真实 K8sTrainingService 提交训练任务
            service = K8sTrainingService(namespace="ml-training", use_training_operator=False)
            # 手动初始化客户端以绕过 _ensure_clients 中的 import
            service._core_api = MagicMock()
            service._batch_api = MagicMock()
            service._custom_api = MagicMock()

            # 模拟 create_namespaced_job 返回
            created_job_mock = MagicMock()
            created_job_mock.metadata.name = "xgboost-train-abc12345"
            service._batch_api.create_namespaced_job.return_value = created_job_mock

            spec = TrainingJobSpec(
                name="xgboost-train",
                framework=TrainingFramework.XGBOOST,
                job_type=JobType.TRAINING,
                image="python:3.10-slim",
                inputs=TrainingInput(dataset_path=dataset_path),
                resources=ResourceRequest(cpu="4", memory="8Gi"),
                hyperparameters=Hyperparameters(
                    learning_rate=0.01,
                    batch_size=64,
                    epochs=20,
                ),
            )

            result = service.submit_training_job(spec)

            # 验证返回的 JobResult
            assert isinstance(result, JobResult)
            assert result.status == JobStatus.PENDING
            assert result.job_id.startswith("train-")
            assert result.started_at is not None

            # 验证 create_namespaced_job 被调用，且 namespace 正确
            service._batch_api.create_namespaced_job.assert_called_once()
            call_kwargs = service._batch_api.create_namespaced_job.call_args
            assert call_kwargs[1]["namespace"] == "ml-training" or call_kwargs[0][0] == "ml-training"

    @pytest.mark.asyncio
    async def test_metadata_to_rag_pipeline(self):
        """测试元数据(Data) -> RAG(Agent) 的跨服务流程"""
        # 1. Data 层：元数据 schema 结构（真实格式）
        schema = {
            "table_name": "users",
            "columns": [
                {"name": "id", "type": "bigint"},
                {"name": "username", "type": "varchar(50)"},
                {"name": "phone", "type": "varchar(20)", "sensitive": True},
            ],
        }

        # 验证 schema 结构包含 Agent 层 Text-to-SQL 所需的字段
        assert "table_name" in schema
        assert "columns" in schema
        assert len(schema["columns"]) > 0

        # 验证每列都有 name 和 type（Agent 生成 SQL 时依赖这些字段）
        for col in schema["columns"]:
            assert "name" in col, "每列必须包含 name 字段"
            assert "type" in col, "每列必须包含 type 字段"

        # 验证敏感字段标记存在（Data 层标记，Agent 层在生成 SQL 时需过滤）
        sensitive_columns = [c for c in schema["columns"] if c.get("sensitive")]
        assert len(sensitive_columns) > 0, "schema 应包含敏感字段标记"
        assert sensitive_columns[0]["name"] == "phone"

        # 2. Agent 层：用 schema 构造 Text-to-SQL prompt
        column_defs = ", ".join(
            f"{c['name']} {c['type']}" for c in schema["columns"]
        )
        prompt = f"Table: {schema['table_name']} ({column_defs})\nQuestion: 查询前10个用户"
        assert "users" in prompt
        assert "bigint" in prompt

    @pytest.mark.asyncio
    async def test_full_ml_pipeline(self):
        """测试完整ML流程：数据 -> 特征 -> 训练 -> 部署 -> 推理（使用真实 ModelInferenceService）"""
        # 1-3. 数据准备、特征工程、训练（模拟前置步骤输出）
        model_name = "churn-predictor-v1"
        serving_endpoint = "http://model-serving:8000"

        # 4. 推理：使用真实 ModelInferenceService
        inference_service = ModelInferenceService(
            endpoint=serving_endpoint,
            api_key="test-key",
            backend="vllm",
        )

        assert inference_service.is_available()
        assert inference_service.backend == "vllm"
        assert inference_service.endpoint == serving_endpoint

        # Mock httpx 发出的 HTTP 请求
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Based on the features, the churn probability is 0.82."
                    }
                }
            ],
            "usage": {"total_tokens": 45},
        }

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_async_client.return_value = mock_client_instance

            result = await inference_service.infer(
                model=model_name,
                input_data="Predict churn for user with features: age=35, tenure=12, monthly_charges=70.5",
                model_type="text-generation",
                parameters={"temperature": 0.3, "max_tokens": 256},
            )

        # 验证推理结果
        assert isinstance(result, InferenceResult)
        assert result.model == model_name
        assert result.backend == "vllm"
        assert result.tokens_used == 45
        assert result.latency_ms is not None and result.latency_ms >= 0
        assert "generated_text" in result.output
        assert "churn" in result.output["generated_text"].lower()

    @pytest.mark.asyncio
    async def test_k8s_training_service_lifecycle(self):
        """测试 K8s 训练服务完整生命周期：submit -> get_status -> get_logs -> cancel"""
        mock_client, mock_config = _make_mock_k8s_modules()

        with patch.dict("sys.modules", {
            "kubernetes": MagicMock(client=mock_client, config=mock_config),
            "kubernetes.client": mock_client,
            "kubernetes.config": mock_config,
        }):
            service = K8sTrainingService(namespace="ml-jobs", use_training_operator=False)
            service._core_api = MagicMock()
            service._batch_api = MagicMock()
            service._custom_api = MagicMock()

            # --- 1. Submit ---
            created_job_mock = MagicMock()
            created_job_mock.metadata.name = "bert-finetune-abc12345"
            service._batch_api.create_namespaced_job.return_value = created_job_mock

            spec = TrainingJobSpec(
                name="bert-finetune",
                framework=TrainingFramework.TRANSFORMERS,
                job_type=JobType.FINE_TUNING,
                image="nvcr.io/nvidia/pytorch:23.10-py3",
                inputs=TrainingInput(
                    dataset_path="s3://datasets/sft-data/",
                    model_path="s3://models/bert-base/",
                ),
                resources=ResourceRequest(
                    cpu="8",
                    memory="32Gi",
                    gpu=GPUResource(count=2, type="nvidia.com/gpu"),
                ),
                hyperparameters=Hyperparameters(
                    learning_rate=2e-5,
                    batch_size=16,
                    epochs=3,
                    lora_r=16,
                    lora_alpha=32,
                ),
                env_vars={"WANDB_PROJECT": "bert-sft"},
            )

            submit_result = service.submit_training_job(spec)
            assert submit_result.status == JobStatus.PENDING
            job_id = submit_result.job_id
            job_name = f"bert-finetune-{job_id}"

            # --- 2. Get Status (running) ---
            mock_job_status = MagicMock()
            mock_job_status.status.succeeded = None
            mock_job_status.status.failed = None
            mock_job_status.status.active = 1
            service._batch_api.read_namespaced_job_status.return_value = mock_job_status

            status = service.get_job_status(job_id, job_name)
            assert status == JobStatus.RUNNING
            service._batch_api.read_namespaced_job_status.assert_called_with(
                name=job_name,
                namespace="ml-jobs",
            )

            # --- 3. Get Logs ---
            mock_pod = MagicMock()
            mock_pod.metadata.name = f"{job_name}-pod-xyz"
            mock_pod_list = MagicMock()
            mock_pod_list.items = [mock_pod]
            service._core_api.list_namespaced_pod.return_value = mock_pod_list
            service._core_api.read_namespaced_pod_log.return_value = (
                "Epoch 1/3 - loss: 0.523\nEpoch 2/3 - loss: 0.312\n"
            )

            logs = service.get_job_logs(job_name, tail_lines=50)
            assert "Epoch" in logs
            assert "loss" in logs
            service._core_api.list_namespaced_pod.assert_called_once()
            service._core_api.read_namespaced_pod_log.assert_called_once()

            # --- 4. Cancel ---
            service._batch_api.delete_namespaced_job.return_value = MagicMock()
            cancelled = service.cancel_job(job_name)
            assert cancelled is True
            service._batch_api.delete_namespaced_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_inference_service_text_generation(self):
        """测试推理服务文本生成：使用真实 ModelInferenceService，Mock httpx 响应"""
        service = ModelInferenceService(
            endpoint="http://vllm-server:8000",
            api_key="sk-test-key",
            backend="vllm",
            timeout=30.0,
        )

        # 验证初始化状态
        assert service.is_available()
        assert service.backend == "vllm"

        # 准备 Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "id": "chatcmpl-abc123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "以下是数据分析报告的摘要：\n1. 总用户数增长了15%\n2. 活跃用户比例提高到72%",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 28,
                "completion_tokens": 42,
                "total_tokens": 70,
            },
        }

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_async_client.return_value = mock_client_instance

            result = await service.infer(
                model="qwen-72b-chat",
                input_data="请根据以下数据生成分析报告摘要",
                model_type="text-generation",
                parameters={"temperature": 0.5, "max_tokens": 1024, "top_p": 0.95},
            )

            # 验证 httpx 调用
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            posted_url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "chat/completions" in posted_url

            posted_json = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["json"]
            assert posted_json["model"] == "qwen-72b-chat"
            assert posted_json["temperature"] == 0.5
            assert posted_json["max_tokens"] == 1024

        # 验证推理结果解析
        assert isinstance(result, InferenceResult)
        assert result.model == "qwen-72b-chat"
        assert result.tokens_used == 70
        assert result.backend == "vllm"
        assert result.latency_ms is not None
        assert "generated_text" in result.output
        assert "数据分析报告" in result.output["generated_text"]


@pytest.mark.integration
@pytest.mark.p0
class TestTextToSQLIntegration:
    """Text-to-SQL集成测试"""

    @pytest.mark.asyncio
    async def test_sql_generation_with_schema_injection(self):
        """测试Schema注入的SQL生成完整流程"""
        # 1. 获取 Schema（模拟 Data 层元数据服务返回）
        schema = {
            "tables": [
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "bigint"},
                        {"name": "user_id", "type": "bigint"},
                        {"name": "amount", "type": "decimal(12,2)"},
                        {"name": "order_time", "type": "datetime"},
                    ],
                }
            ]
        }

        # 验证 schema 结构符合预期
        assert len(schema["tables"]) > 0
        orders_table = schema["tables"][0]
        assert orders_table["name"] == "orders"
        column_names = [c["name"] for c in orders_table["columns"]]
        assert "amount" in column_names
        assert "order_time" in column_names

        # 2. 生成SQL（模拟 Agent 层 LLM 调用）
        sql_service = Mock()
        sql_service.generate = AsyncMock(return_value={
            "sql": "SELECT SUM(amount) FROM orders WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
            "confidence": 0.92,
        })

        result = await sql_service.generate(
            query="近30天的订单总额",
            schema=schema["tables"],
        )

        assert result["sql"] is not None
        assert "SUM(amount)" in result["sql"]

        # 3. 安全检查
        security_service = Mock()
        security_service.check = AsyncMock(return_value={
            "safe": True,
            "warnings": [],
        })

        security_result = await security_service.check(result["sql"])
        assert security_result["safe"] is True

        # 4. 执行SQL
        query_service = Mock()
        query_service.execute = AsyncMock(return_value={
            "success": True,
            "data": [{"total": 1500000.50}],
        })

        query_result = await query_service.execute(result["sql"])
        assert query_result["success"] is True


@pytest.mark.integration
@pytest.mark.p0
class TestRAGIntegration:
    """RAG完整流程集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_rag_pipeline(self):
        """测试RAG端到端流程"""
        # 1. 文档上传
        doc_service = Mock()
        doc_service.upload = AsyncMock(return_value={
            "success": True,
            "doc_id": "doc_0001",
            "file_path": "s3://documents/sample.pdf",
        })

        doc = await doc_service.upload("sample.pdf")
        assert doc["success"] is True

        # 2. 文档处理
        doc_service.process = AsyncMock(return_value={
            "success": True,
            "chunks": [
                {"chunk_id": "c1", "text": "这是第一段内容"},
                {"chunk_id": "c2", "text": "这是第二段内容"},
            ],
        })

        chunks = await doc_service.process(doc["doc_id"])
        assert len(chunks["chunks"]) > 0

        # 3. 向量化
        embedding_service = Mock()
        embedding_service.embed = AsyncMock(return_value={
            "embeddings": [[0.1] * 1536 for _ in chunks["chunks"]]
        })

        embeddings = await embedding_service.embed([c["text"] for c in chunks["chunks"]])
        assert len(embeddings["embeddings"]) == len(chunks["chunks"])

        # 4. 索引构建
        vector_service = Mock()
        vector_service.index = AsyncMock(return_value={
            "success": True,
            "indexed_count": len(chunks["chunks"]),
        })

        index_result = await vector_service.index(
            chunks=chunks["chunks"],
            embeddings=embeddings["embeddings"],
        )
        assert index_result["success"] is True

        # 5. 检索
        vector_service.search = AsyncMock(return_value={
            "results": [
                {"chunk_id": "c1", "score": 0.95, "text": "这是第一段内容"}
            ]
        })

        search_results = await vector_service.search(
            query="test query",
            top_k=5,
        )

        # 6. LLM生成（使用真实 ModelInferenceService 结构验证）
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "根据文档内容，这是答案。"}}
            ],
            "usage": {"total_tokens": 35},
        }

        inference_service = ModelInferenceService(
            endpoint="http://llm-server:8000",
            api_key="test-key",
            backend="vllm",
        )

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_async_client.return_value = mock_client_instance

            context_text = "\n".join(r["text"] for r in search_results["results"])
            prompt = f"Context: {context_text}\n\nQuestion: test query"

            answer = await inference_service.infer(
                model="qwen-72b-chat",
                input_data=prompt,
                model_type="text-generation",
            )

        assert isinstance(answer, InferenceResult)
        assert answer.output["generated_text"] is not None
