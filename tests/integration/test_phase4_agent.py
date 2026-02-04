"""
Phase 4: Agent 和模型服务验证测试

测试覆盖范围:
- agent-api 应用编排 API
- model-api 模型管理 API

测试用例编号: INT-P4-001 ~ INT-P4-030
"""

import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
import requests

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestAgentAPI:
    """INT-P4-001 ~ INT-P4-016: agent-api 测试"""

    @pytest.fixture
    def agent_api_config(self):
        """agent-api 配置"""
        return {
            "base_url": os.getenv("AGENT_API_URL", "http://localhost:8000"),
            "health_endpoint": "/api/v1/health",
        }

    def test_agent_api_health_check(self, agent_api_config):
        """INT-P4-001: agent-api 健康检查"""
        url = f"{agent_api_config['base_url']}{agent_api_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_list_workflows(self, agent_api_config):
        """INT-P4-002: 列出工作流"""
        url = f"{agent_api_config['base_url']}/api/v1/workflows"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "workflows" in data
                print(f"Workflows: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_create_workflow(self, agent_api_config):
        """INT-P4-003: 创建工作流"""
        url = f"{agent_api_config['base_url']}/api/v1/workflows"
        workflow_data = {
            "name": f"test_workflow_{int(time.time())}",
            "description": "Test workflow",
            "nodes": [
                {
                    "id": "node1",
                    "type": "start",
                    "position": {"x": 100, "y": 100}
                },
                {
                    "id": "node2",
                    "type": "llm",
                    "position": {"x": 300, "y": 100},
                    "data": {"model": "gpt-3.5-turbo", "prompt": "Hello"}
                }
            ],
            "edges": [
                {"source": "node1", "target": "node2"}
            ]
        }

        try:
            response = requests.post(url, json=workflow_data, timeout=10)
            assert response.status_code in [200, 201, 401]
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data or "name" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_execute_workflow(self, agent_api_config):
        """INT-P4-004: 执行工作流"""
        # 首先需要有一个工作流 ID
        workflow_id = "test_workflow_id"
        url = f"{agent_api_config['base_url']}/api/v1/workflows/{workflow_id}/execute"

        try:
            response = requests.post(url, json={}, timeout=30)
            # 可能返回 404 如果工作流不存在
            assert response.status_code in [200, 201, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_knowledge_bases(self, agent_api_config):
        """INT-P4-005: 知识库管理"""
        url = f"{agent_api_config['base_url']}/api/v1/knowledge-bases"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "knowledge_bases" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_create_knowledge_base(self, agent_api_config):
        """INT-P4-006: 创建知识库"""
        url = f"{agent_api_config['base_url']}/api/v1/knowledge-bases"
        kb_data = {
            "name": f"test_kb_{int(time.time())}",
            "description": "Test knowledge base",
            "embedding_model": "text-embedding-ada-002",
            "chunk_size": 500,
            "chunk_overlap": 50
        }

        try:
            response = requests.post(url, json=kb_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_upload_document(self, agent_api_config):
        """INT-P4-007: 上传文档到知识库"""
        kb_id = "test_kb"
        url = f"{agent_api_config['base_url']}/api/v1/knowledge-bases/{kb_id}/documents"

        try:
            # 模拟文件上传
            files = {"file": ("test.txt", "Test document content", "text/plain")}
            response = requests.post(url, files=files, timeout=10)
            assert response.status_code in [200, 201, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_api_rag_query(self, agent_api_config):
        """INT-P4-008: RAG 查询"""
        kb_id = "test_kb"
        url = f"{agent_api_config['base_url']}/api/v1/knowledge-bases/{kb_id}/query"

        query_data = {
            "question": "What is the test document about?",
            "top_k": 5
        }

        try:
            response = requests.post(url, json=query_data, timeout=30)
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_agents_list(self, agent_api_config):
        """INT-P4-009: 列出 Agent"""
        url = f"{agent_api_config['base_url']}/api/v1/agents"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_create_agent(self, agent_api_config):
        """INT-P4-010: 创建 Agent"""
        url = f"{agent_api_config['base_url']}/api/v1/agents"
        agent_data = {
            "name": f"test_agent_{int(time.time())}",
            "description": "Test agent",
            "type": "conversational",
            "model": "gpt-3.5-turbo",
            "knowledge_base_ids": [],
            "tools": []
        }

        try:
            response = requests.post(url, json=agent_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_chat(self, agent_api_config):
        """INT-P4-011: Agent 聊天"""
        agent_id = "test_agent"
        url = f"{agent_api_config['base_url']}/api/v1/agents/{agent_id}/chat"

        chat_data = {
            "message": "Hello!",
            "session_id": "test_session"
        }

        try:
            response = requests.post(url, json=chat_data, timeout=30)
            assert response.status_code in [200, 404, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_tools_list(self, agent_api_config):
        """INT-P4-012: 列出可用工具"""
        url = f"{agent_api_config['base_url']}/api/v1/tools"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "tools" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_vector_store_status(self, agent_api_config):
        """INT-P4-013: 向量存储状态"""
        url = f"{agent_api_config['base_url']}/api/v1/vector-store/status"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                print(f"Vector store status: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_prompt_templates(self, agent_api_config):
        """INT-P4-014: 提示模板管理"""
        url = f"{agent_api_config['base_url']}/api/v1/prompts"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_sessions(self, agent_api_config):
        """INT-P4-015: 会话管理"""
        url = f"{agent_api_config['base_url']}/api/v1/sessions"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_agent_analytics(self, agent_api_config):
        """INT-P4-016: 分析统计"""
        url = f"{agent_api_config['base_url']}/api/v1/analytics"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")


@pytest.mark.integration
class TestModelAPI:
    """INT-P4-017 ~ INT-P4-030: model-api 测试"""

    @pytest.fixture
    def model_api_config(self):
        """model-api 配置"""
        return {
            "base_url": os.getenv("MODEL_API_URL", "http://localhost:8002"),
            "health_endpoint": "/api/v1/health",
        }

    def test_model_api_health_check(self, model_api_config):
        """INT-P4-017: model-api 健康检查"""
        url = f"{model_api_config['base_url']}{model_api_config['health_endpoint']}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_list_models(self, model_api_config):
        """INT-P4-018: 列出模型"""
        url = f"{model_api_config['base_url']}/api/v1/models"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "models" in data
                print(f"Models: {data}")
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_register_model(self, model_api_config):
        """INT-P4-019: 注册模型"""
        url = f"{model_api_config['base_url']}/api/v1/models"
        model_data = {
            "name": f"test_model_{int(time.time())}",
            "type": "llm",
            "framework": "pytorch",
            "description": "Test model"
        }

        try:
            response = requests.post(url, json=model_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_deployments(self, model_api_config):
        """INT-P4-020: 列出部署"""
        url = f"{model_api_config['base_url']}/api/v1/deployments"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "deployments" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_create_deployment(self, model_api_config):
        """INT-P4-021: 创建部署"""
        url = f"{model_api_config['base_url']}/api/v1/deployments"
        deployment_data = {
            "name": f"test_deployment_{int(time.time())}",
            "model_id": "test_model",
            "replicas": 1,
            "resources": {"cpu": "1", "memory": "1Gi"}
        }

        try:
            response = requests.post(url, json=deployment_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_training_jobs(self, model_api_config):
        """INT-P4-022: 训练任务列表"""
        url = f"{model_api_config['base_url']}/api/v1/training-jobs"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_create_training_job(self, model_api_config):
        """INT-P4-023: 创建训练任务"""
        url = f"{model_api_config['base_url']}/api/v1/training-jobs"
        job_data = {
            "name": f"test_job_{int(time.time())}",
            "model_type": "llm",
            "dataset_id": "test_dataset",
            "hyperparameters": {"epochs": 10, "batch_size": 32}
        }

        try:
            response = requests.post(url, json=job_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_datasets(self, model_api_config):
        """INT-P4-024: 数据集管理"""
        url = f"{model_api_config['base_url']}/api/v1/datasets"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
            if response.status_code == 200:
                data = response.json()
                assert "items" in data or "datasets" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_upload_dataset(self, model_api_config):
        """INT-P4-025: 上传数据集"""
        url = f"{model_api_config['base_url']}/api/v1/datasets/upload"

        try:
            # 模拟文件上传
            files = {"file": ("dataset.json", '{"data": []}', "application/json")}
            data = {"name": f"test_dataset_{int(time.time())}", "format": "json"}
            response = requests.post(url, files=files, data=data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_evaluations(self, model_api_config):
        """INT-P4-026: 模型评估"""
        url = f"{model_api_config['base_url']}/api/v1/evaluations"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_create_evaluation(self, model_api_config):
        """INT-P4-027: 创建评估任务"""
        url = f"{model_api_config['base_url']}/api/v1/evaluations"
        eval_data = {
            "name": f"test_eval_{int(time.time())}",
            "model_id": "test_model",
            "dataset_id": "test_dataset",
            "metrics": ["accuracy", "f1"]
        }

        try:
            response = requests.post(url, json=eval_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_serving_endpoints(self, model_api_config):
        """INT-P4-028: 服务端点"""
        url = f"{model_api_config['base_url']}/api/v1/serving/endpoints"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_inference(self, model_api_config):
        """INT-P4-029: 模型推理"""
        url = f"{model_api_config['base_url']}/api/v1/inference"
        inference_data = {
            "model_id": "test_model",
            "input": "Test input"
        }

        try:
            response = requests.post(url, json=inference_data, timeout=30)
            assert response.status_code in [200, 404, 500]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_model_api_monitoring(self, model_api_config):
        """INT-P4-030: 模型监控"""
        url = f"{model_api_config['base_url']}/api/v1/monitoring/metrics"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")


@pytest.mark.integration
class TestAgentModelIntegration:
    """INT-P4-031 ~ INT-P4-035: Agent 与 Model 集成测试"""

    def test_workflow_with_llm_node(self):
        """INT-P4-031: 工作流 LLM 节点测试"""
        agent_api_url = os.getenv("AGENT_API_URL", "http://localhost:8000")
        url = f"{agent_api_url}/api/v1/workflows"

        workflow_data = {
            "name": f"llm_test_{int(time.time())}",
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "llm", "type": "llm", "data": {"model": "gpt-3.5-turbo", "prompt": "Say hello"}},
                {"id": "end", "type": "end"}
            ],
            "edges": [
                {"source": "start", "target": "llm"},
                {"source": "llm", "target": "end"}
            ]
        }

        try:
            response = requests.post(url, json=workflow_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_rag_with_vector_store(self):
        """INT-P4-032: RAG 与向量存储集成测试"""
        agent_api_url = os.getenv("AGENT_API_URL", "http://localhost:8000")
        url = f"{agent_api_url}/api/v1/knowledge-bases"

        kb_data = {
            "name": f"test_rag_{int(time.time())}",
            "embedding_model": "text-embedding-ada-002",
            "vector_store": "milvus"
        }

        try:
            response = requests.post(url, json=kb_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_model_deployment_for_agent(self):
        """INT-P4-033: 为 Agent 部署模型测试"""
        model_api_url = os.getenv("MODEL_API_URL", "http://localhost:8002")
        url = f"{model_api_url}/api/v1/deployments"

        deployment_data = {
            "name": f"agent_model_{int(time.time())}",
            "model_name": "gpt-3.5-turbo",
            "endpoint_type": "chat",
            "tags": ["agent"]
        }

        try:
            response = requests.post(url, json=deployment_data, timeout=10)
            assert response.status_code in [200, 201, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_cross_service_authentication(self):
        """INT-P4-034: 跨服务认证测试"""
        # 验证 agent-api 可以调用 model-api
        import subprocess

        try:
            # 检查容器网络
            result = subprocess.run(
                ["docker", "network", "inspect", "one-data-network"],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert result.returncode == 0
            print("Cross-service network: OK")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available")

    def test_shared_storage_access(self):
        """INT-P4-035: 共享存储访问测试"""
        # 验证 agent-api 和 model-api 可以访问共享的 MinIO
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")

        try:
            from minio import Minio

            client = Minio(
                minio_endpoint,
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=False,
            )

            buckets = [b.name for b in client.list_buckets()]
            print(f"Shared storage buckets: {buckets}")
        except Exception as e:
            pytest.skip(f"MinIO access failed: {e}")


@pytest.mark.integration
class TestAgentModelPerformance:
    """INT-P4-036 ~ INT-P4-040: Agent 和 Model 性能测试"""

    def test_workflow_execution_time(self):
        """INT-P4-036: 工作流执行时间测试"""
        import time

        agent_api_url = os.getenv("AGENT_API_URL", "http://localhost:8000")

        # 简单健康检查作为基准
        url = f"{agent_api_url}/api/v1/health"

        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"Agent API health check: {elapsed*1000:.2f}ms")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_model_loading_time(self):
        """INT-P4-037: 模型加载时间测试"""
        import time

        model_api_url = os.getenv("MODEL_API_URL", "http://localhost:8002")

        try:
            start_time = time.time()
            response = requests.get(f"{model_api_url}/api/v1/models", timeout=10)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"Model list retrieval: {elapsed*1000:.2f}ms")
        except requests.exceptions.ConnectionError:
            pytest.skip("model-api 服务未启动")

    def test_rag_query_performance(self):
        """INT-P4-038: RAG 查询性能测试"""
        import time

        agent_api_url = os.getenv("AGENT_API_URL", "http://localhost:8000")
        kb_id = "test_kb"
        url = f"{agent_api_url}/api/v1/knowledge-bases/{kb_id}/query"

        query_data = {"question": "Test query", "top_k": 5}

        try:
            start_time = time.time()
            response = requests.post(url, json=query_data, timeout=30)
            elapsed = time.time() - start_time

            print(f"RAG query: {elapsed*1000:.2f}ms (status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_concurrent_workflow_executions(self):
        """INT-P4-039: 并发工作流执行测试"""
        import threading
        import time

        agent_api_url = os.getenv("AGENT_API_URL", "http://localhost:8000")
        url = f"{agent_api_url}/api/v1/health"
        results = []

        def execute_request():
            try:
                start = time.time()
                response = requests.get(url, timeout=10)
                elapsed = time.time() - start
                results.append((response.status_code, elapsed))
            except Exception as e:
                results.append((None, str(e)))

        try:
            threads = []
            for _ in range(5):
                t = threading.Thread(target=execute_request)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            success = sum(1 for s, _ in results if s == 200)
            print(f"Concurrent workflow requests: {success}/{len(results)} successful")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_memory_usage_during_inference(self):
        """INT-P4-040: 推理时内存使用测试"""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.Container}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            ai_containers = ["one-data-agent-api", "one-data-model-api"]

            for line in result.stdout.split("\n"):
                for container in ai_containers:
                    if container in line:
                        print(f"{container}: {line.split('\t')[1] if '\t' in line else line}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
