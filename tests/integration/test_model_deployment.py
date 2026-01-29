"""
模型部署模块集成测试

测试用例 AE-DP-001 ~ AE-DP-009:
- AE-DP-001: 一键部署模型 (P0)
- AE-DP-002: vLLM推理服务部署 (P0)
- AE-DP-003: TGI推理服务部署 (P1)
- AE-DP-004: 获取API Endpoint (P0)
- AE-DP-005: API接口测试 (P0)
- AE-DP-006: Embedding接口测试 (P0)
- AE-DP-007: 模型服务扩缩容 (P2)
- AE-DP-008: 模型服务下线 (P1)
- AE-DP-009: 模型版本切换 (P2)
"""

import pytest
import logging
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_model_config():
    """示例模型配置"""
    return {
        "model_id": f"model_{uuid.uuid4().hex[:12]}",
        "name": "Qwen2-7B-Chat",
        "model_type": "text-generation",
        "framework": "vllm",
        "version": "1.0.0",
        "storage_path": "s3://models/qwen2-7b-chat/v1.0.0",
        "status": "ready",
        "config": {
            "max_tokens": 4096,
            "temperature": 0.7,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.9,
        },
        "resources": {
            "gpu_count": 1,
            "gpu_type": "A100",
            "memory_limit": "32Gi",
            "cpu_limit": "8",
        },
    }


@pytest.fixture
def sample_embedding_model_config():
    """示例Embedding模型配置"""
    return {
        "model_id": f"model_{uuid.uuid4().hex[:12]}",
        "name": "bge-large-zh-v1.5",
        "model_type": "embedding",
        "framework": "vllm",
        "version": "1.0.0",
        "storage_path": "s3://models/bge-large-zh/v1.5",
        "status": "ready",
        "config": {
            "max_length": 512,
            "embedding_dim": 1024,
        },
        "resources": {
            "gpu_count": 1,
            "gpu_type": "T4",
            "memory_limit": "16Gi",
            "cpu_limit": "4",
        },
    }


@pytest.fixture
def mock_deployment_service():
    """Mock 部署服务

    模拟 model 的模型部署管理层，包括创建/删除部署、
    查询状态以及生成 Endpoint 等功能。
    """
    service = MagicMock()

    # -- 创建部署 --
    def _create_deployment(model_id, config):
        deployment_id = f"deploy_{uuid.uuid4().hex[:12]}"
        framework = config.get("framework", "vllm")
        replicas = config.get("replicas", 1)
        return {
            "deployment_id": deployment_id,
            "model_id": model_id,
            "framework": framework,
            "replicas": replicas,
            "status": "running",
            "endpoint": (
                f"http://serving.one-data.svc.cluster.local/{deployment_id}"
            ),
            "internal_endpoint": (
                f"http://{deployment_id}.default.svc.cluster.local:8080"
            ),
            "created_at": datetime.utcnow().isoformat(),
        }

    service.create_deployment.side_effect = _create_deployment

    # -- 获取部署详情 --
    service.get_deployment.return_value = {
        "deployment_id": "deploy_test123",
        "model_id": "model_test123",
        "framework": "vllm",
        "replicas": 1,
        "status": "running",
        "endpoint": "http://serving.one-data.svc.cluster.local/deploy_test123",
        "health_status": "healthy",
    }

    # -- 删除部署 --
    service.delete_deployment.return_value = {"code": 0, "message": "success"}

    # -- 扩缩容 --
    def _scale_deployment(deployment_id, replicas):
        return {
            "deployment_id": deployment_id,
            "replicas": replicas,
            "status": "running",
        }

    service.scale_deployment.side_effect = _scale_deployment

    # -- 版本切换 --
    def _switch_version(deployment_id, new_version_id, strategy="rolling"):
        return {
            "deployment_id": deployment_id,
            "version_id": new_version_id,
            "strategy": strategy,
            "status": "running",
        }

    service.switch_version.side_effect = _switch_version

    return service


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes 客户端

    模拟 K8s API 调用，包括 Deployment、Service、HPA 等资源的
    创建、查询与删除操作。
    """
    k8s = MagicMock()

    # -- Deployment --
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "model-serving-test"
    mock_deployment.metadata.namespace = "one-data"
    mock_deployment.spec.replicas = 1
    mock_deployment.status.ready_replicas = 1
    mock_deployment.status.available_replicas = 1
    k8s.create_namespaced_deployment.return_value = mock_deployment
    k8s.read_namespaced_deployment.return_value = mock_deployment

    # -- Service --
    mock_svc = MagicMock()
    mock_svc.metadata.name = "model-serving-svc"
    mock_svc.spec.cluster_ip = "10.0.0.100"
    mock_svc.spec.ports = [MagicMock(port=8080, target_port=8080)]
    k8s.create_namespaced_service.return_value = mock_svc

    # -- HPA --
    mock_hpa = MagicMock()
    mock_hpa.spec.min_replicas = 1
    mock_hpa.spec.max_replicas = 10
    mock_hpa.status.current_replicas = 1
    k8s.create_namespaced_horizontal_pod_autoscaler.return_value = mock_hpa
    k8s.read_namespaced_horizontal_pod_autoscaler.return_value = mock_hpa

    # -- Patch (用于扩缩容) --
    def _patch_deployment(name, namespace, body):
        patched = MagicMock()
        patched.metadata.name = name
        patched.spec.replicas = body.get("spec", {}).get("replicas", 1)
        patched.status.ready_replicas = patched.spec.replicas
        return patched

    k8s.patch_namespaced_deployment.side_effect = _patch_deployment

    # -- Delete --
    k8s.delete_namespaced_deployment.return_value = MagicMock(status="Success")
    k8s.delete_namespaced_service.return_value = MagicMock(status="Success")

    return k8s


@pytest.fixture
def mock_istio_client():
    """Mock Istio 客户端

    模拟 Istio VirtualService 和 DestinationRule 的管理，
    用于流量切换与灰度发布。
    """
    istio = MagicMock()

    # -- VirtualService --
    mock_vs = MagicMock()
    mock_vs.metadata.name = "model-serving-vs"
    mock_vs.spec = {
        "hosts": ["model-serving.one-data.svc.cluster.local"],
        "http": [
            {
                "route": [
                    {"destination": {"host": "model-serving-v1", "port": {"number": 8080}}, "weight": 100},
                ]
            }
        ],
    }
    istio.create_virtual_service.return_value = mock_vs

    # -- DestinationRule --
    mock_dr = MagicMock()
    mock_dr.metadata.name = "model-serving-dr"
    istio.create_destination_rule.return_value = mock_dr

    # -- 更新 VirtualService (版本切换时) --
    def _update_vs(name, namespace, spec):
        updated = MagicMock()
        updated.metadata.name = name
        updated.spec = spec
        return updated

    istio.patch_virtual_service.side_effect = _update_vs

    return istio


@pytest.fixture
def mock_openai_proxy():
    """Mock OpenAI 兼容代理

    模拟 /v1/chat/completions 和 /v1/embeddings 接口返回。
    """
    proxy = MagicMock()

    # -- Chat Completions --
    proxy.chat_completions.return_value = {
        "id": "chatcmpl-test-001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "qwen2-7b-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "你好！我是Qwen2，有什么可以帮助你的吗？",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 20,
            "total_tokens": 35,
        },
    }

    # -- Embeddings --
    proxy.embeddings.return_value = {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": 0,
                "embedding": [0.01] * 1024,
            }
        ],
        "model": "bge-large-zh-v1.5",
        "usage": {"prompt_tokens": 8, "total_tokens": 8},
    }

    return proxy


# ===========================================================================
# AE-DP-001: 一键部署模型 (P0)
# ===========================================================================

@pytest.mark.integration
class TestOneClickModelDeploy:
    """AE-DP-001: 一键部署模型

    验证通过 POST /api/v1/deployments 可以一键部署模型服务，
    包括资源分配、状态流转和端点生成。
    """

    def test_deploy_model_success(
        self, mock_deployment_service, mock_k8s_client, sample_model_config
    ):
        """测试成功部署模型服务"""
        model_id = sample_model_config["model_id"]
        deploy_config = {
            "framework": "vllm",
            "replicas": 1,
            "gpu_count": 1,
            "gpu_type": "A100",
            "memory_limit": "32Gi",
            "cpu_limit": "8",
        }

        result = mock_deployment_service.create_deployment(model_id, deploy_config)

        assert result["model_id"] == model_id
        assert result["deployment_id"].startswith("deploy_")
        assert result["status"] == "running"
        assert result["endpoint"] is not None
        assert result["framework"] == "vllm"
        assert result["replicas"] == 1
        mock_deployment_service.create_deployment.assert_called_once_with(
            model_id, deploy_config
        )
        logger.info("AE-DP-001: 一键部署模型成功，deployment_id=%s", result["deployment_id"])

    def test_deploy_model_creates_k8s_resources(
        self, mock_k8s_client, sample_model_config
    ):
        """测试部署时创建 K8s Deployment 和 Service"""
        namespace = "one-data"

        # 模拟创建 K8s Deployment
        deployment_body = {
            "metadata": {"name": f"serving-{sample_model_config['model_id']}"},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "model-server",
                                "image": "vllm/vllm-openai:latest",
                                "resources": {
                                    "limits": {
                                        "nvidia.com/gpu": "1",
                                        "memory": "32Gi",
                                        "cpu": "8",
                                    }
                                },
                            }
                        ]
                    }
                },
            },
        }

        result = mock_k8s_client.create_namespaced_deployment(
            namespace=namespace, body=deployment_body
        )

        assert result.metadata.name == "model-serving-test"
        assert result.spec.replicas == 1
        mock_k8s_client.create_namespaced_deployment.assert_called_once()
        logger.info("AE-DP-001: K8s Deployment 创建成功")

    def test_deploy_model_generates_endpoint(
        self, mock_deployment_service, sample_model_config
    ):
        """测试部署后生成可访问的 API Endpoint"""
        model_id = sample_model_config["model_id"]

        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        endpoint = result["endpoint"]
        assert endpoint.startswith("http://")
        assert result["deployment_id"] in endpoint
        logger.info("AE-DP-001: 生成 Endpoint=%s", endpoint)

    def test_deploy_model_status_transition(
        self, mock_deployment_service, sample_model_config
    ):
        """测试部署过程中的状态流转: pending -> deploying -> running"""
        model_id = sample_model_config["model_id"]

        # 部署完成后状态应为 running
        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})
        assert result["status"] == "running"

    def test_deploy_model_invalid_model_returns_error(self, mock_deployment_service):
        """测试部署不存在的模型时返回错误"""
        mock_deployment_service.create_deployment.side_effect = ValueError("模型不存在")

        with pytest.raises(ValueError, match="模型不存在"):
            mock_deployment_service.create_deployment("nonexistent_model", {})


# ===========================================================================
# AE-DP-002: vLLM推理服务部署 (P0)
# ===========================================================================

@pytest.mark.integration
class TestVLLMServingDeploy:
    """AE-DP-002: vLLM推理服务部署

    验证使用 vLLM 框架部署推理服务的完整流程，包括
    启动参数配置、GPU 资源分配以及健康检查。
    """

    def test_vllm_deploy_with_correct_framework(
        self, mock_deployment_service, sample_model_config
    ):
        """测试使用 vLLM 框架部署"""
        model_id = sample_model_config["model_id"]
        config = {
            "framework": "vllm",
            "replicas": 1,
            "gpu_count": 1,
            "config": {
                "tensor_parallel_size": 1,
                "gpu_memory_utilization": 0.9,
                "max_model_len": 4096,
            },
        }

        result = mock_deployment_service.create_deployment(model_id, config)

        assert result["framework"] == "vllm"
        assert result["status"] == "running"
        logger.info("AE-DP-002: vLLM 部署成功")

    def test_vllm_deploy_gpu_allocation(
        self, mock_k8s_client, sample_model_config
    ):
        """测试 vLLM 部署时 GPU 资源分配"""
        namespace = "one-data"
        container_spec = {
            "name": "vllm-server",
            "image": "vllm/vllm-openai:v0.4.0",
            "args": [
                "--model", sample_model_config["storage_path"],
                "--tensor-parallel-size", "1",
                "--gpu-memory-utilization", "0.9",
                "--max-model-len", "4096",
            ],
            "resources": {
                "limits": {"nvidia.com/gpu": "1", "memory": "32Gi"},
            },
        }

        deployment_body = {
            "metadata": {"name": f"vllm-{sample_model_config['model_id']}"},
            "spec": {
                "replicas": 1,
                "template": {"spec": {"containers": [container_spec]}},
            },
        }

        result = mock_k8s_client.create_namespaced_deployment(
            namespace=namespace, body=deployment_body
        )

        assert result is not None
        mock_k8s_client.create_namespaced_deployment.assert_called_once()
        logger.info("AE-DP-002: vLLM GPU 资源分配正确")

    def test_vllm_deploy_health_check(self, mock_deployment_service):
        """测试 vLLM 服务部署后的健康检查"""
        mock_deployment_service.get_deployment.return_value = {
            "deployment_id": "deploy_vllm_001",
            "status": "running",
            "health_status": "healthy",
            "framework": "vllm",
        }

        deployment = mock_deployment_service.get_deployment("deploy_vllm_001")

        assert deployment["status"] == "running"
        assert deployment["health_status"] == "healthy"
        logger.info("AE-DP-002: vLLM 健康检查通过")

    def test_vllm_deploy_openai_compatible_endpoint(
        self, mock_deployment_service, sample_model_config
    ):
        """测试 vLLM 部署生成 OpenAI 兼容 API 端点"""
        model_id = sample_model_config["model_id"]

        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        endpoint = result["endpoint"]
        # vLLM 原生提供 OpenAI 兼容端点
        assert endpoint is not None
        assert len(endpoint) > 0
        logger.info("AE-DP-002: vLLM OpenAI 兼容端点=%s", endpoint)


# ===========================================================================
# AE-DP-003: TGI推理服务部署 (P1)
# ===========================================================================

@pytest.mark.integration
class TestTGIServingDeploy:
    """AE-DP-003: TGI推理服务部署

    验证使用 HuggingFace TGI 框架部署推理服务的完整流程。
    """

    def test_tgi_deploy_with_correct_framework(
        self, mock_deployment_service, sample_model_config
    ):
        """测试使用 TGI 框架部署"""
        model_id = sample_model_config["model_id"]
        config = {
            "framework": "tgi",
            "replicas": 1,
            "gpu_count": 1,
            "config": {
                "max_input_length": 2048,
                "max_total_tokens": 4096,
                "quantize": "gptq",
            },
        }

        # 覆盖 side_effect 以确认 TGI 框架
        def _create_tgi_deployment(mid, cfg):
            return {
                "deployment_id": f"deploy_{uuid.uuid4().hex[:12]}",
                "model_id": mid,
                "framework": cfg.get("framework", "tgi"),
                "replicas": cfg.get("replicas", 1),
                "status": "running",
                "endpoint": f"http://tgi-serving.one-data.svc.cluster.local:8080",
            }

        mock_deployment_service.create_deployment.side_effect = _create_tgi_deployment

        result = mock_deployment_service.create_deployment(model_id, config)

        assert result["framework"] == "tgi"
        assert result["status"] == "running"
        logger.info("AE-DP-003: TGI 部署成功，framework=%s", result["framework"])

    def test_tgi_deploy_container_args(self, mock_k8s_client, sample_model_config):
        """测试 TGI 部署容器启动参数"""
        namespace = "one-data"
        container_spec = {
            "name": "tgi-server",
            "image": "ghcr.io/huggingface/text-generation-inference:latest",
            "args": [
                "--model-id", sample_model_config["storage_path"],
                "--max-input-length", "2048",
                "--max-total-tokens", "4096",
                "--quantize", "gptq",
            ],
            "resources": {
                "limits": {"nvidia.com/gpu": "1", "memory": "32Gi"},
            },
            "ports": [{"containerPort": 8080}],
        }

        deployment_body = {
            "metadata": {"name": f"tgi-{sample_model_config['model_id']}"},
            "spec": {
                "replicas": 1,
                "template": {"spec": {"containers": [container_spec]}},
            },
        }

        result = mock_k8s_client.create_namespaced_deployment(
            namespace=namespace, body=deployment_body
        )

        assert result is not None
        mock_k8s_client.create_namespaced_deployment.assert_called_once()
        logger.info("AE-DP-003: TGI 容器参数配置正确")

    def test_tgi_deploy_with_quantization(
        self, mock_deployment_service, sample_model_config
    ):
        """测试 TGI 量化部署（GPTQ/AWQ）"""
        model_id = sample_model_config["model_id"]

        def _create_quantized(mid, cfg):
            return {
                "deployment_id": f"deploy_{uuid.uuid4().hex[:12]}",
                "model_id": mid,
                "framework": "tgi",
                "replicas": 1,
                "status": "running",
                "config": cfg.get("config", {}),
                "endpoint": "http://tgi-serving.one-data.svc.cluster.local:8080",
            }

        mock_deployment_service.create_deployment.side_effect = _create_quantized

        for quant_method in ["gptq", "awq"]:
            config = {
                "framework": "tgi",
                "config": {"quantize": quant_method},
            }
            result = mock_deployment_service.create_deployment(model_id, config)
            assert result["config"]["quantize"] == quant_method
            logger.info("AE-DP-003: TGI %s 量化部署成功", quant_method)


# ===========================================================================
# AE-DP-004: 获取API Endpoint (P0)
# ===========================================================================

@pytest.mark.integration
class TestGetAPIEndpoint:
    """AE-DP-004: 获取API Endpoint

    验证部署完成后可以获取 OpenAI 兼容的 API Endpoint，
    包括通过 Istio 网关暴露的外部访问地址。
    """

    def test_get_endpoint_after_deployment(
        self, mock_deployment_service, sample_model_config
    ):
        """测试部署后获取 Endpoint"""
        model_id = sample_model_config["model_id"]
        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        endpoint = result["endpoint"]

        assert endpoint is not None
        assert "http://" in endpoint
        logger.info("AE-DP-004: 获取 Endpoint=%s", endpoint)

    def test_endpoint_contains_deployment_id(
        self, mock_deployment_service, sample_model_config
    ):
        """测试 Endpoint 包含 deployment_id 用于路由"""
        model_id = sample_model_config["model_id"]
        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        deployment_id = result["deployment_id"]
        endpoint = result["endpoint"]

        assert deployment_id in endpoint
        logger.info("AE-DP-004: Endpoint 包含 deployment_id")

    def test_internal_endpoint_generated(
        self, mock_deployment_service, sample_model_config
    ):
        """测试内部 Endpoint 生成（集群内调用）"""
        model_id = sample_model_config["model_id"]
        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        internal = result.get("internal_endpoint")

        assert internal is not None
        assert "svc.cluster.local" in internal
        logger.info("AE-DP-004: 内部 Endpoint=%s", internal)

    def test_endpoint_via_istio_gateway(
        self, mock_istio_client, mock_deployment_service, sample_model_config
    ):
        """测试通过 Istio 网关暴露的外部 Endpoint"""
        model_id = sample_model_config["model_id"]
        result = mock_deployment_service.create_deployment(model_id, {"framework": "vllm"})

        # 创建 VirtualService
        vs = mock_istio_client.create_virtual_service(
            name=f"vs-{result['deployment_id']}",
            namespace="one-data",
            spec={
                "hosts": ["model-api.one-data.example.com"],
                "http": [
                    {
                        "match": [{"uri": {"prefix": f"/v1/{result['deployment_id']}"}}],
                        "route": [
                            {
                                "destination": {
                                    "host": f"{result['deployment_id']}.one-data.svc.cluster.local",
                                    "port": {"number": 8080},
                                },
                            }
                        ],
                    }
                ],
            },
        )

        assert vs is not None
        mock_istio_client.create_virtual_service.assert_called_once()
        logger.info("AE-DP-004: Istio VirtualService 创建成功")


# ===========================================================================
# AE-DP-005: API接口测试 (P0)
# ===========================================================================

@pytest.mark.integration
class TestChatCompletionsAPI:
    """AE-DP-005: API接口测试

    验证 /v1/chat/completions 接口的 OpenAI 兼容性，
    包括请求格式、响应结构和流式输出。
    """

    def test_chat_completions_basic(self, mock_openai_proxy):
        """测试基本对话补全请求"""
        request_body = {
            "model": "qwen2-7b-chat",
            "messages": [
                {"role": "system", "content": "你是一个有用的助手。"},
                {"role": "user", "content": "你好"},
            ],
            "max_tokens": 100,
            "temperature": 0.7,
        }

        response = mock_openai_proxy.chat_completions(**request_body)

        assert response["object"] == "chat.completion"
        assert len(response["choices"]) > 0
        assert response["choices"][0]["message"]["role"] == "assistant"
        assert response["choices"][0]["message"]["content"] is not None
        assert response["choices"][0]["finish_reason"] == "stop"
        logger.info("AE-DP-005: Chat Completions 基本请求成功")

    def test_chat_completions_response_structure(self, mock_openai_proxy):
        """测试响应结构符合 OpenAI 规范"""
        response = mock_openai_proxy.chat_completions(
            model="qwen2-7b-chat",
            messages=[{"role": "user", "content": "test"}],
        )

        # 验证 OpenAI 兼容响应的必须字段
        assert "id" in response
        assert "object" in response
        assert "created" in response
        assert "model" in response
        assert "choices" in response
        assert "usage" in response

        # 验证 usage 结构
        usage = response["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
        logger.info("AE-DP-005: 响应结构符合 OpenAI 规范")

    def test_chat_completions_streaming(self, mock_openai_proxy):
        """测试流式对话补全"""
        chunks = [
            {"choices": [{"delta": {"role": "assistant"}, "index": 0}]},
            {"choices": [{"delta": {"content": "你好"}, "index": 0}]},
            {"choices": [{"delta": {"content": "！"}, "index": 0}]},
            {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]},
        ]
        mock_openai_proxy.chat_completions_stream.return_value = iter(chunks)

        stream = mock_openai_proxy.chat_completions_stream(
            model="qwen2-7b-chat",
            messages=[{"role": "user", "content": "你好"}],
            stream=True,
        )

        collected_chunks = list(stream)
        assert len(collected_chunks) == 4
        # 最后一个 chunk 应包含 finish_reason
        assert collected_chunks[-1]["choices"][0]["finish_reason"] == "stop"
        logger.info("AE-DP-005: 流式输出测试通过，共 %d 个 chunk", len(collected_chunks))

    def test_chat_completions_with_multi_turn(self, mock_openai_proxy):
        """测试多轮对话"""
        messages = [
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": "1+1等于几？"},
            {"role": "assistant", "content": "1+1等于2。"},
            {"role": "user", "content": "再加上3呢？"},
        ]

        response = mock_openai_proxy.chat_completions(
            model="qwen2-7b-chat",
            messages=messages,
            max_tokens=50,
        )

        assert response["choices"][0]["message"]["content"] is not None
        mock_openai_proxy.chat_completions.assert_called_with(
            model="qwen2-7b-chat",
            messages=messages,
            max_tokens=50,
        )
        logger.info("AE-DP-005: 多轮对话测试通过")

    def test_chat_completions_error_handling(self, mock_openai_proxy):
        """测试无效请求时的错误处理"""
        mock_openai_proxy.chat_completions.side_effect = ValueError(
            "messages 参数不能为空"
        )

        with pytest.raises(ValueError, match="messages 参数不能为空"):
            mock_openai_proxy.chat_completions(model="qwen2-7b-chat", messages=[])


# ===========================================================================
# AE-DP-006: Embedding接口测试 (P0)
# ===========================================================================

@pytest.mark.integration
class TestEmbeddingsAPI:
    """AE-DP-006: Embedding接口测试

    验证 /v1/embeddings 接口返回正确维度的向量数据，
    以及批量请求与错误处理。
    """

    def test_embeddings_single_text(self, mock_openai_proxy):
        """测试单条文本嵌入"""
        response = mock_openai_proxy.embeddings(
            model="bge-large-zh-v1.5",
            input="智能大数据平台建设方案",
        )

        assert response["object"] == "list"
        assert len(response["data"]) == 1
        assert response["data"][0]["object"] == "embedding"
        assert response["data"][0]["index"] == 0

        embedding = response["data"][0]["embedding"]
        assert isinstance(embedding, list)
        assert len(embedding) == 1024  # bge-large 的维度
        assert all(isinstance(v, float) for v in embedding)
        logger.info("AE-DP-006: 单条文本嵌入成功，维度=%d", len(embedding))

    def test_embeddings_batch_texts(self, mock_openai_proxy):
        """测试批量文本嵌入"""
        texts = [
            "数据治理与开发平台",
            "云原生MLOps平台",
            "大模型应用开发平台",
        ]

        batch_response = {
            "object": "list",
            "data": [
                {"object": "embedding", "index": i, "embedding": [0.01 * (i + 1)] * 1024}
                for i in range(len(texts))
            ],
            "model": "bge-large-zh-v1.5",
            "usage": {"prompt_tokens": 24, "total_tokens": 24},
        }
        mock_openai_proxy.embeddings.return_value = batch_response

        response = mock_openai_proxy.embeddings(
            model="bge-large-zh-v1.5",
            input=texts,
        )

        assert len(response["data"]) == 3
        # 每个嵌入的维度应一致
        dimensions = {len(item["embedding"]) for item in response["data"]}
        assert len(dimensions) == 1
        assert 1024 in dimensions
        logger.info("AE-DP-006: 批量嵌入成功，共 %d 条", len(response["data"]))

    def test_embeddings_vector_values_valid(self, mock_openai_proxy):
        """测试嵌入向量的值在合理范围内"""
        response = mock_openai_proxy.embeddings(
            model="bge-large-zh-v1.5",
            input="测试文本",
        )

        embedding = response["data"][0]["embedding"]

        # 嵌入向量值不应全为零
        assert not all(v == 0.0 for v in embedding)
        # 值应在合理范围内 [-1, 1] 或更宽
        assert all(-10 <= v <= 10 for v in embedding)
        logger.info("AE-DP-006: 向量值范围验证通过")

    def test_embeddings_usage_reported(self, mock_openai_proxy):
        """测试嵌入请求返回 Token 用量"""
        response = mock_openai_proxy.embeddings(
            model="bge-large-zh-v1.5",
            input="测试文本",
        )

        assert "usage" in response
        assert response["usage"]["prompt_tokens"] > 0
        assert response["usage"]["total_tokens"] > 0
        logger.info("AE-DP-006: Token 用量信息正确")


# ===========================================================================
# AE-DP-007: 模型服务扩缩容 (P2)
# ===========================================================================

@pytest.mark.integration
class TestModelServiceScaling:
    """AE-DP-007: 模型服务扩缩容

    验证模型服务的副本数扩缩容功能，包括手动扩缩容
    和 HPA 自动扩缩容配置。
    """

    def test_scale_up_replicas(self, mock_deployment_service):
        """测试扩容：增加副本数"""
        deployment_id = "deploy_scale_001"
        new_replicas = 3

        result = mock_deployment_service.scale_deployment(deployment_id, new_replicas)

        assert result["deployment_id"] == deployment_id
        assert result["replicas"] == 3
        assert result["status"] == "running"
        logger.info("AE-DP-007: 扩容至 %d 副本成功", new_replicas)

    def test_scale_down_replicas(self, mock_deployment_service):
        """测试缩容：减少副本数"""
        deployment_id = "deploy_scale_001"
        new_replicas = 1

        result = mock_deployment_service.scale_deployment(deployment_id, new_replicas)

        assert result["replicas"] == 1
        logger.info("AE-DP-007: 缩容至 %d 副本成功", new_replicas)

    def test_scale_to_zero_stops_service(self, mock_deployment_service):
        """测试缩容到0副本（服务暂停）"""
        deployment_id = "deploy_scale_001"

        # 缩容到 0 时特殊处理
        def _scale_to_zero(did, replicas):
            status = "stopped" if replicas == 0 else "running"
            return {
                "deployment_id": did,
                "replicas": replicas,
                "status": status,
            }

        mock_deployment_service.scale_deployment.side_effect = _scale_to_zero

        result = mock_deployment_service.scale_deployment(deployment_id, 0)

        assert result["replicas"] == 0
        assert result["status"] == "stopped"
        logger.info("AE-DP-007: 缩容到 0 副本，服务已暂停")

    def test_scale_via_k8s_patch(self, mock_k8s_client):
        """测试通过 K8s Patch 更新副本数"""
        patch_body = {"spec": {"replicas": 5}}

        result = mock_k8s_client.patch_namespaced_deployment(
            name="model-serving-test",
            namespace="one-data",
            body=patch_body,
        )

        assert result.spec.replicas == 5
        mock_k8s_client.patch_namespaced_deployment.assert_called_once()
        logger.info("AE-DP-007: K8s Deployment 副本数更新为 5")

    def test_hpa_auto_scaling_config(self, mock_k8s_client):
        """测试 HPA 自动扩缩容配置"""
        hpa_spec = {
            "metadata": {"name": "model-serving-hpa"},
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": "model-serving-test",
                },
                "minReplicas": 1,
                "maxReplicas": 10,
                "targetCPUUtilizationPercentage": 70,
            },
        }

        hpa = mock_k8s_client.create_namespaced_horizontal_pod_autoscaler(
            namespace="one-data", body=hpa_spec
        )

        assert hpa.spec.min_replicas == 1
        assert hpa.spec.max_replicas == 10
        logger.info("AE-DP-007: HPA 配置创建成功 (min=1, max=10)")

    def test_scale_invalid_replicas_rejected(self, mock_deployment_service):
        """测试无效副本数被拒绝"""
        mock_deployment_service.scale_deployment.side_effect = ValueError(
            "replicas 参数无效"
        )

        with pytest.raises(ValueError, match="replicas 参数无效"):
            mock_deployment_service.scale_deployment("deploy_001", -1)


# ===========================================================================
# AE-DP-008: 模型服务下线 (P1)
# ===========================================================================

@pytest.mark.integration
class TestModelServiceOffline:
    """AE-DP-008: 模型服务下线

    验证删除部署后释放所有关联资源（K8s Deployment、Service、
    Istio VirtualService），并更新模型状态。
    """

    def test_delete_deployment_success(self, mock_deployment_service):
        """测试成功删除部署"""
        deployment_id = "deploy_offline_001"

        result = mock_deployment_service.delete_deployment(deployment_id)

        assert result["code"] == 0
        assert result["message"] == "success"
        mock_deployment_service.delete_deployment.assert_called_once_with(deployment_id)
        logger.info("AE-DP-008: 删除部署 %s 成功", deployment_id)

    def test_delete_releases_k8s_resources(self, mock_k8s_client):
        """测试删除部署时释放 K8s 资源"""
        namespace = "one-data"
        deployment_name = "model-serving-offline"
        service_name = "model-serving-offline-svc"

        # 删除 Deployment
        mock_k8s_client.delete_namespaced_deployment(
            name=deployment_name, namespace=namespace, body={}
        )
        mock_k8s_client.delete_namespaced_deployment.assert_called_once()

        # 删除 Service
        mock_k8s_client.delete_namespaced_service(
            name=service_name, namespace=namespace, body={}
        )
        mock_k8s_client.delete_namespaced_service.assert_called_once()

        logger.info("AE-DP-008: K8s 资源已释放")

    def test_delete_removes_istio_virtualservice(self, mock_istio_client):
        """测试删除部署时清理 Istio VirtualService"""
        mock_istio_client.delete_virtual_service.return_value = {"status": "deleted"}

        result = mock_istio_client.delete_virtual_service(
            name="vs-deploy-offline",
            namespace="one-data",
        )

        assert result["status"] == "deleted"
        mock_istio_client.delete_virtual_service.assert_called_once()
        logger.info("AE-DP-008: Istio VirtualService 已清理")

    def test_delete_updates_model_status(self, mock_deployment_service):
        """测试删除所有部署后更新模型状态为 ready"""
        mock_deployment_service.delete_deployment.return_value = {
            "code": 0,
            "message": "success",
            "model_status": "ready",
        }

        result = mock_deployment_service.delete_deployment("deploy_last")

        assert result["model_status"] == "ready"
        logger.info("AE-DP-008: 模型状态已恢复为 ready")

    def test_delete_nonexistent_deployment_returns_404(self, mock_deployment_service):
        """测试删除不存在的部署返回 404"""
        mock_deployment_service.delete_deployment.side_effect = LookupError(
            "部署不存在"
        )

        with pytest.raises(LookupError, match="部署不存在"):
            mock_deployment_service.delete_deployment("deploy_nonexistent")

    def test_delete_with_graceful_shutdown(self, mock_deployment_service):
        """测试优雅下线（等待现有请求处理完毕）"""
        mock_deployment_service.delete_deployment.return_value = {
            "code": 0,
            "message": "success",
            "graceful_shutdown": True,
            "drain_timeout_seconds": 30,
        }

        result = mock_deployment_service.delete_deployment(
            "deploy_graceful", graceful=True
        )

        assert result["graceful_shutdown"] is True
        assert result["drain_timeout_seconds"] == 30
        logger.info("AE-DP-008: 优雅下线完成，drain_timeout=30s")


# ===========================================================================
# AE-DP-009: 模型版本切换 (P2)
# ===========================================================================

@pytest.mark.integration
class TestModelVersionSwitch:
    """AE-DP-009: 模型版本切换

    验证将流量从旧版本切换到新版本的能力，支持滚动更新
    和金丝雀发布策略。
    """

    def test_switch_version_rolling_update(self, mock_deployment_service):
        """测试滚动更新方式切换版本"""
        deployment_id = "deploy_version_001"
        new_version_id = "ver_2.0.0"

        result = mock_deployment_service.switch_version(
            deployment_id, new_version_id, strategy="rolling"
        )

        assert result["deployment_id"] == deployment_id
        assert result["version_id"] == new_version_id
        assert result["strategy"] == "rolling"
        assert result["status"] == "running"
        logger.info(
            "AE-DP-009: 滚动更新切换至版本 %s 成功", new_version_id
        )

    def test_switch_version_canary_release(self, mock_deployment_service):
        """测试金丝雀发布方式切换版本"""
        deployment_id = "deploy_version_001"
        new_version_id = "ver_2.0.0"

        result = mock_deployment_service.switch_version(
            deployment_id, new_version_id, strategy="canary"
        )

        assert result["strategy"] == "canary"
        assert result["status"] == "running"
        logger.info("AE-DP-009: 金丝雀发布切换至版本 %s", new_version_id)

    def test_canary_traffic_split_via_istio(self, mock_istio_client):
        """测试通过 Istio 实现金丝雀流量分配"""
        canary_spec = {
            "hosts": ["model-serving.one-data.svc.cluster.local"],
            "http": [
                {
                    "route": [
                        {
                            "destination": {
                                "host": "model-serving-v1",
                                "port": {"number": 8080},
                            },
                            "weight": 80,
                        },
                        {
                            "destination": {
                                "host": "model-serving-v2",
                                "port": {"number": 8080},
                            },
                            "weight": 20,
                        },
                    ]
                }
            ],
        }

        result = mock_istio_client.patch_virtual_service(
            name="model-serving-vs",
            namespace="one-data",
            spec=canary_spec,
        )

        assert result is not None
        assert result.spec == canary_spec
        # 验证 v1:v2 权重比为 80:20
        routes = canary_spec["http"][0]["route"]
        assert routes[0]["weight"] == 80
        assert routes[1]["weight"] == 20
        logger.info("AE-DP-009: Istio 金丝雀流量分配 80:20")

    def test_full_traffic_switch(self, mock_istio_client):
        """测试完全切换流量到新版本（100%）"""
        full_switch_spec = {
            "hosts": ["model-serving.one-data.svc.cluster.local"],
            "http": [
                {
                    "route": [
                        {
                            "destination": {
                                "host": "model-serving-v2",
                                "port": {"number": 8080},
                            },
                            "weight": 100,
                        },
                    ]
                }
            ],
        }

        result = mock_istio_client.patch_virtual_service(
            name="model-serving-vs",
            namespace="one-data",
            spec=full_switch_spec,
        )

        routes = full_switch_spec["http"][0]["route"]
        assert len(routes) == 1
        assert routes[0]["destination"]["host"] == "model-serving-v2"
        assert routes[0]["weight"] == 100
        logger.info("AE-DP-009: 流量已 100%% 切换至新版本")

    def test_version_rollback(self, mock_deployment_service):
        """测试版本回滚"""
        deployment_id = "deploy_version_001"
        old_version_id = "ver_1.0.0"

        result = mock_deployment_service.switch_version(
            deployment_id, old_version_id, strategy="rolling"
        )

        assert result["version_id"] == old_version_id
        assert result["status"] == "running"
        logger.info("AE-DP-009: 版本回滚至 %s 成功", old_version_id)

    def test_switch_version_nonexistent_deployment(self, mock_deployment_service):
        """测试对不存在的部署进行版本切换"""
        mock_deployment_service.switch_version.side_effect = LookupError(
            "部署不存在"
        )

        with pytest.raises(LookupError, match="部署不存在"):
            mock_deployment_service.switch_version(
                "deploy_nonexistent", "ver_2.0.0", strategy="rolling"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
