"""
E2E 测试：工作流执行场景
Sprint 9: E2E 测试扩展

测试覆盖：
- 工作流 CRUD 操作
- 工作流执行生命周期
- 执行状态监控
- 执行日志记录
"""

import pytest
import requests
import time
import json
import os
import logging
from typing import Optional

# 配置日志
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8081")
AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")

# 请求头
HEADERS = {
    "Content-Type": "application/json",
}

if AUTH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"


class TestWorkflowCRUD:
    """工作流 CRUD 操作测试"""

    workflow_id: Optional[str] = None

    def test_01_create_workflow(self):
        """测试创建工作流"""
        response = requests.post(
            f"{BASE_URL}/api/v1/workflows",
            headers=HEADERS,
            json={
                "name": "E2E Test Workflow",
                "description": "自动化测试创建的工作流",
                "type": "rag"
            }
        )

        # 允许 401（未认证）或 201（成功）
        assert response.status_code in [201, 401], f"Unexpected status: {response.status_code}"

        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            assert "workflow_id" in data["data"]
            TestWorkflowCRUD.workflow_id = data["data"]["workflow_id"]
            logger.info("Created workflow: %s", TestWorkflowCRUD.workflow_id)

    def test_02_list_workflows(self):
        """测试列出工作流"""
        response = requests.get(
            f"{BASE_URL}/api/v1/workflows",
            headers=HEADERS
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "workflows" in data["data"]
        assert isinstance(data["data"]["workflows"], list)

    def test_03_get_workflow(self):
        """测试获取工作流详情"""
        if not TestWorkflowCRUD.workflow_id:
            pytest.skip("No workflow created")

        response = requests.get(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowCRUD.workflow_id}",
            headers=HEADERS
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["workflow_id"] == TestWorkflowCRUD.workflow_id

    def test_04_update_workflow(self):
        """测试更新工作流"""
        if not TestWorkflowCRUD.workflow_id:
            pytest.skip("No workflow created")

        # 更新工作流定义
        workflow_definition = {
            "version": "1.0",
            "nodes": [
                {"id": "input", "type": "input", "config": {"key": "query"}},
                {"id": "output", "type": "output", "config": {"input_from": "input"}}
            ],
            "edges": [
                {"source": "input", "target": "output"}
            ]
        }

        response = requests.put(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowCRUD.workflow_id}",
            headers=HEADERS,
            json={
                "name": "E2E Test Workflow (Updated)",
                "definition": workflow_definition
            }
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0

    def test_05_delete_workflow(self):
        """测试删除工作流"""
        if not TestWorkflowCRUD.workflow_id:
            pytest.skip("No workflow created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowCRUD.workflow_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0


class TestWorkflowExecution:
    """工作流执行生命周期测试"""

    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """创建测试用工作流"""
        # 创建工作流
        response = requests.post(
            f"{BASE_URL}/api/v1/workflows",
            headers=HEADERS,
            json={
                "name": "Execution Test Workflow",
                "description": "用于测试执行的工作流",
                "type": "rag"
            }
        )

        if response.status_code == 201:
            TestWorkflowExecution.workflow_id = response.json()["data"]["workflow_id"]

            # 更新工作流定义
            workflow_definition = {
                "version": "1.0",
                "nodes": [
                    {"id": "input", "type": "input", "config": {"key": "query"}},
                    {"id": "output", "type": "output", "config": {"input_from": "input"}}
                ],
                "edges": [
                    {"source": "input", "target": "output"}
                ]
            }

            requests.put(
                f"{BASE_URL}/api/v1/workflows/{TestWorkflowExecution.workflow_id}",
                headers=HEADERS,
                json={"definition": workflow_definition}
            )

        yield

        # 清理
        if TestWorkflowExecution.workflow_id:
            requests.delete(
                f"{BASE_URL}/api/v1/workflows/{TestWorkflowExecution.workflow_id}",
                headers=HEADERS
            )

    def test_01_start_workflow(self):
        """测试启动工作流执行"""
        if not TestWorkflowExecution.workflow_id:
            pytest.skip("No workflow created")

        response = requests.post(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowExecution.workflow_id}/start",
            headers=HEADERS,
            json={
                "inputs": {
                    "query": "测试查询"
                }
            }
        )

        assert response.status_code in [202, 401, 400]
        if response.status_code == 202:
            data = response.json()
            assert data["code"] == 0
            assert "execution_id" in data["data"]
            TestWorkflowExecution.execution_id = data["data"]["execution_id"]
            logger.info("Started execution: %s", TestWorkflowExecution.execution_id)

    def test_02_get_execution_status(self):
        """测试获取执行状态"""
        if not TestWorkflowExecution.workflow_id or not TestWorkflowExecution.execution_id:
            pytest.skip("No execution started")

        # 等待执行开始
        time.sleep(2)

        response = requests.get(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowExecution.workflow_id}/status",
            headers=HEADERS,
            params={"execution_id": TestWorkflowExecution.execution_id}
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "status" in data["data"]
            logger.info("Execution status: %s", data['data']['status'])

    def test_03_get_execution_logs(self):
        """测试获取执行日志"""
        if not TestWorkflowExecution.execution_id:
            pytest.skip("No execution started")

        response = requests.get(
            f"{BASE_URL}/api/v1/executions/{TestWorkflowExecution.execution_id}/logs",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "logs" in data["data"]

    def test_04_list_executions(self):
        """测试列出执行记录"""
        response = requests.get(
            f"{BASE_URL}/api/v1/executions",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "executions" in data["data"]


class TestWorkflowScheduling:
    """工作流调度测试"""

    workflow_id: Optional[str] = None
    schedule_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """创建测试用工作流"""
        response = requests.post(
            f"{BASE_URL}/api/v1/workflows",
            headers=HEADERS,
            json={
                "name": "Schedule Test Workflow",
                "type": "rag"
            }
        )

        if response.status_code == 201:
            TestWorkflowScheduling.workflow_id = response.json()["data"]["workflow_id"]

        yield

        # 清理
        if TestWorkflowScheduling.schedule_id:
            requests.delete(
                f"{BASE_URL}/api/v1/schedules/{TestWorkflowScheduling.schedule_id}",
                headers=HEADERS
            )
        if TestWorkflowScheduling.workflow_id:
            requests.delete(
                f"{BASE_URL}/api/v1/workflows/{TestWorkflowScheduling.workflow_id}",
                headers=HEADERS
            )

    def test_01_create_schedule(self):
        """测试创建调度"""
        if not TestWorkflowScheduling.workflow_id:
            pytest.skip("No workflow created")

        response = requests.post(
            f"{BASE_URL}/api/v1/workflows/{TestWorkflowScheduling.workflow_id}/schedules",
            headers=HEADERS,
            json={
                "type": "cron",
                "cron_expression": "0 0 * * *",  # 每天午夜
                "enabled": False,  # 禁用以避免实际执行
                "max_retries": 3,
                "timeout_seconds": 3600
            }
        )

        assert response.status_code in [201, 401]
        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestWorkflowScheduling.schedule_id = data["data"]["schedule_id"]

    def test_02_list_schedules(self):
        """测试列出调度"""
        response = requests.get(
            f"{BASE_URL}/api/v1/schedules",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "schedules" in data["data"]

    def test_03_pause_resume_schedule(self):
        """测试暂停和恢复调度"""
        if not TestWorkflowScheduling.schedule_id:
            pytest.skip("No schedule created")

        # 暂停
        response = requests.post(
            f"{BASE_URL}/api/v1/schedules/{TestWorkflowScheduling.schedule_id}/pause",
            headers=HEADERS
        )
        assert response.status_code in [200, 401]

        # 恢复
        response = requests.post(
            f"{BASE_URL}/api/v1/schedules/{TestWorkflowScheduling.schedule_id}/resume",
            headers=HEADERS
        )
        # 可能返回 400（未暂停）或 200
        assert response.status_code in [200, 400, 401]

    def test_04_get_schedule_statistics(self):
        """测试获取调度统计"""
        if not TestWorkflowScheduling.schedule_id:
            pytest.skip("No schedule created")

        response = requests.get(
            f"{BASE_URL}/api/v1/schedules/{TestWorkflowScheduling.schedule_id}/statistics",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
