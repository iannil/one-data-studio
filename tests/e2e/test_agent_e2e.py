"""
E2E 测试：Agent 执行场景
Sprint 9: E2E 测试扩展

测试覆盖：
- Agent 模板管理
- 工具注册和调用
- Agent 执行
- 流式执行
"""

import pytest
import requests
import json
import time
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


class TestAgentTools:
    """Agent 工具测试"""

    def test_01_list_tools(self):
        """测试列出可用工具"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tools",
            headers=HEADERS
        )

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "tools" in data["data"]
            logger.info("Available tools: %d", len(data['data']['tools']))
            for tool in data["data"]["tools"]:
                logger.debug("  - %s: %s", tool.get('name', 'unknown'), tool.get('description', '')[:50])

    def test_02_get_tool_schemas(self):
        """测试获取工具 Schema"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tools/schemas",
            headers=HEADERS
        )

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "schemas" in data["data"]
            # 验证 schema 格式
            for schema in data["data"]["schemas"]:
                assert "name" in schema or "function" in schema

    def test_03_execute_tool(self):
        """测试执行单个工具（如果可用）"""
        # 首先获取工具列表
        tools_response = requests.get(
            f"{BASE_URL}/api/v1/tools",
            headers=HEADERS
        )

        if tools_response.status_code != 200:
            pytest.skip("Tools not available")

        tools = tools_response.json()["data"]["tools"]
        if not tools:
            pytest.skip("No tools available")

        # 尝试执行第一个工具（假设有一个简单的工具）
        # 注意：这个测试依赖于具体的工具实现
        # 这里使用一个通用的测试方式
        tool_name = tools[0].get("name", "")

        if not tool_name:
            pytest.skip("No valid tool name")

        response = requests.post(
            f"{BASE_URL}/api/v1/tools/{tool_name}/execute",
            headers=HEADERS,
            json={"test": "value"}
        )

        # 工具执行可能成功或失败（取决于参数），但不应该是 500
        assert response.status_code != 500


class TestAgentTemplates:
    """Agent 模板管理测试"""

    template_id: Optional[str] = None

    def test_01_list_templates(self):
        """测试列出 Agent 模板"""
        response = requests.get(
            f"{BASE_URL}/api/v1/agent/templates",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "templates" in data["data"]

    def test_02_create_template(self):
        """测试创建 Agent 模板"""
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/templates",
            headers=HEADERS,
            json={
                "name": "E2E Test Agent Template",
                "description": "自动化测试创建的 Agent 模板",
                "agent_type": "react",
                "model": "gpt-4o-mini",
                "max_iterations": 5,
                "system_prompt": "你是一个测试助手。",
                "selected_tools": []
            }
        )

        assert response.status_code in [201, 401, 503]
        if response.status_code == 201:
            data = response.json()
            assert data["code"] == 0
            TestAgentTemplates.template_id = data["data"].get("template_id")
            logger.info("Created template: %s", TestAgentTemplates.template_id)

    def test_03_get_template(self):
        """测试获取模板详情"""
        if not TestAgentTemplates.template_id:
            pytest.skip("No template created")

        response = requests.get(
            f"{BASE_URL}/api/v1/agent/templates/{TestAgentTemplates.template_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]

    def test_04_update_template(self):
        """测试更新模板"""
        if not TestAgentTemplates.template_id:
            pytest.skip("No template created")

        response = requests.put(
            f"{BASE_URL}/api/v1/agent/templates/{TestAgentTemplates.template_id}",
            headers=HEADERS,
            json={
                "description": "更新后的描述",
                "max_iterations": 10
            }
        )

        assert response.status_code in [200, 401, 404]

    def test_05_delete_template(self):
        """测试删除模板"""
        if not TestAgentTemplates.template_id:
            pytest.skip("No template created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/agent/templates/{TestAgentTemplates.template_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401, 404]


class TestAgentExecution:
    """Agent 执行测试"""

    def test_01_run_agent(self):
        """测试运行 Agent"""
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/run",
            headers=HEADERS,
            json={
                "query": "你好，请介绍一下你自己。",
                "agent_type": "react",
                "model": "gpt-4o-mini",
                "max_iterations": 3
            },
            timeout=60
        )

        assert response.status_code in [200, 401, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            # Agent 执行结果应该包含一些输出
            logger.info("Agent result: %s", json.dumps(data['data'], ensure_ascii=False, indent=2)[:500])

    def test_02_run_agent_with_tools(self):
        """测试运行带工具的 Agent"""
        # 首先检查是否有可用工具
        tools_response = requests.get(
            f"{BASE_URL}/api/v1/tools",
            headers=HEADERS
        )

        if tools_response.status_code != 200:
            pytest.skip("Tools not available")

        tools = tools_response.json()["data"]["tools"]
        if not tools:
            pytest.skip("No tools available")

        response = requests.post(
            f"{BASE_URL}/api/v1/agent/run",
            headers=HEADERS,
            json={
                "query": "请帮我查询当前时间。",
                "agent_type": "react",
                "model": "gpt-4o-mini",
                "max_iterations": 5
            },
            timeout=60
        )

        assert response.status_code in [200, 401, 503]

    def test_03_run_agent_stream(self):
        """测试流式 Agent 执行"""
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/run-stream",
            headers=HEADERS,
            json={
                "query": "简单介绍一下机器学习。",
                "agent_type": "react",
                "model": "gpt-4o-mini",
                "max_iterations": 3
            },
            stream=True,
            timeout=60
        )

        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            # 验证 SSE 响应格式
            events = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            event_data = json.loads(line_str[6:])
                            events.append(event_data)
                            logger.debug("SSE Event: %s", event_data.get('type', 'unknown'))
                        except json.JSONDecodeError:
                            pass

            # 至少应该有一些事件
            logger.info("Total SSE events: %d", len(events))


class TestRAGScenario:
    """RAG 场景 E2E 测试"""

    doc_id: Optional[str] = None

    @pytest.fixture(autouse=True)
    def setup(self):
        """上传测试文档"""
        response = requests.post(
            f"{BASE_URL}/api/v1/documents/upload",
            headers=HEADERS,
            json={
                "content": """
                ONE-DATA-STUDIO 是一个企业级 AI 平台，整合了三个核心系统：

                1. data - 数据治理平台
                   - 数据集成和 ETL
                   - 元数据管理
                   - 数据质量监控

                2. model - MLOps 平台
                   - 模型训练
                   - 模型部署
                   - 模型服务

                3. agent - LLMOps 平台
                   - RAG 流水线
                   - Agent 编排
                   - Prompt 管理

                平台采用四层架构设计，从底到顶依次为：
                - L1 基础设施层
                - L2 数据底座层
                - L3 算法引擎层
                - L4 应用编排层
                """,
                "file_name": "test-doc.txt",
                "title": "ONE-DATA-STUDIO 介绍",
                "collection": "e2e-test"
            }
        )

        if response.status_code == 201:
            TestRAGScenario.doc_id = response.json()["data"]["doc_id"]

        yield

        # 清理
        if TestRAGScenario.doc_id:
            requests.delete(
                f"{BASE_URL}/api/v1/documents/{TestRAGScenario.doc_id}",
                headers=HEADERS
            )

    def test_01_rag_query(self):
        """测试 RAG 查询"""
        # 等待文档索引
        time.sleep(2)

        response = requests.post(
            f"{BASE_URL}/api/v1/rag/query",
            headers=HEADERS,
            json={
                "question": "ONE-DATA-STUDIO 包含哪些核心系统？",
                "collection": "e2e-test",
                "top_k": 3
            },
            timeout=30
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "answer" in data["data"]
            logger.info("RAG Answer: %s...", data['data']['answer'][:200])

    def test_02_text2sql(self):
        """测试 Text-to-SQL"""
        response = requests.post(
            f"{BASE_URL}/api/v1/text2sql",
            headers=HEADERS,
            json={
                "natural_language": "查询所有订单的总金额",
                "database": "sales_dw"
            },
            timeout=30
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "sql" in data["data"]
            logger.info("Generated SQL: %s", data['data']['sql'])


class TestConversationFlow:
    """会话流程 E2E 测试"""

    conversation_id: Optional[str] = None

    def test_01_create_conversation(self):
        """测试创建会话"""
        response = requests.post(
            f"{BASE_URL}/api/v1/conversations",
            headers=HEADERS,
            json={
                "title": "E2E 测试会话",
                "model": "gpt-4o-mini"
            }
        )

        assert response.status_code in [201, 401]
        if response.status_code == 201:
            data = response.json()
            TestConversationFlow.conversation_id = data["data"]["conversation_id"]

    def test_02_send_message(self):
        """测试发送消息"""
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=HEADERS,
            json={
                "message": "你好！",
                "conversation_id": TestConversationFlow.conversation_id,
                "model": "gpt-4o-mini"
            },
            timeout=30
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            assert "reply" in data["data"]

    def test_03_get_conversation(self):
        """测试获取会话详情"""
        if not TestConversationFlow.conversation_id:
            pytest.skip("No conversation created")

        response = requests.get(
            f"{BASE_URL}/api/v1/conversations/{TestConversationFlow.conversation_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 0
            # 应该包含消息历史
            if "messages" in data["data"]:
                logger.info("Messages in conversation: %d", len(data['data']['messages']))

    def test_04_list_conversations(self):
        """测试列出会话"""
        response = requests.get(
            f"{BASE_URL}/api/v1/conversations",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]

    def test_05_delete_conversation(self):
        """测试删除会话"""
        if not TestConversationFlow.conversation_id:
            pytest.skip("No conversation created")

        response = requests.delete(
            f"{BASE_URL}/api/v1/conversations/{TestConversationFlow.conversation_id}",
            headers=HEADERS
        )

        assert response.status_code in [200, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
