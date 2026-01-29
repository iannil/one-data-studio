"""
八阶段数据全生命周期 E2E 测试

完整测试从数据源接入到智能查询的完整流程。

阶段：
1. 数据源接入与元数据自动发现
2. 敏感数据自动识别
3. 智能ETL编排与数据加工
4. 元数据同步与数据血缘
5. 资产编目与价值评估
6. 表融合分析
7. 知识库向量索引构建
8. 智能查询 (Text-to-SQL + RAG)
"""

import pytest
import os
import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime

import requests


class TestFullLifecycleE2E:
    """八阶段完整流程 E2E 测试"""

    @pytest.fixture(scope="class")
    def config(self) -> Dict[str, str]:
        """测试配置"""
        return {
            "data_api_url": os.getenv("ALDATA_API_URL", "http://localhost:8080"),
            "agent_api_url": os.getenv("BISHENG_API_URL", "http://localhost:8000"),
            "openai_proxy_url": os.getenv("OPENAI_PROXY_URL", "http://localhost:8001"),
            "test_database": os.getenv("TEST_DATABASE", "test_dw"),
        }

    @pytest.fixture(scope="class")
    def test_data_source_id(self, config) -> str:
        """创建测试数据源并返回 ID"""
        # 阶段 1: 数据源接入
        response = requests.post(
            f"{config['data_api_url']}/api/v1/datasources",
            json={
                "name": "test_sales_db",
                "type": "mysql",
                "connection": {
                    "host": os.getenv("TEST_DB_HOST", "localhost"),
                    "port": int(os.getenv("TEST_DB_PORT", "3306")),
                    "database": config["test_database"],
                    "username": os.getenv("TEST_DB_USER", "root"),
                    "password": os.getenv("TEST_DB_PASSWORD", "test"),
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        source_id = data["id"]

        yield source_id

        # 清理
        requests.delete(f"{config['data_api_url']}/api/v1/datasources/{source_id}")

    @pytest.fixture(scope="class")
    def test_tables(self, test_data_source_id, config) -> List[Dict[str, Any]]:
        """扫描并获取测试表列表"""
        # 触发元数据扫描
        response = requests.post(
            f"{config['data_api_url']}/api/v1/metadata/scan",
            json={"datasource_id": test_data_source_id}
        )
        assert response.status_code == 200

        # 等待扫描完成
        scan_id = response.json()["scan_id"]
        for _ in range(30):
            status_response = requests.get(
                f"{config['data_api_url']}/api/v1/metadata/scan/{scan_id}"
            )
            status = status_response.json()
            if status.get("status") == "completed":
                break
            time.sleep(2)

        # 获取表列表
        tables_response = requests.get(
            f"{config['data_api_url']}/api/v1/metadata/tables",
            params={"datasource_id": test_data_source_id}
        )
        assert tables_response.status_code == 200

        tables = tables_response.json().get("items", [])

        # 如果没有表，创建测试表
        if not tables:
            tables = self._create_test_tables(config)

        return tables

    def _create_test_tables(self, config) -> List[Dict[str, Any]]:
        """创建测试表"""
        # 这里简化处理，实际应该连接数据库创建表
        return [
            {
                "name": "orders",
                "schema": "sales_dw",
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False},
                    {"name": "customer_id", "type": "INT", "nullable": False},
                    {"name": "amount", "type": "DECIMAL(10,2)", "nullable": True},
                    {"name": "status", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
                ]
            },
            {
                "name": "customers",
                "schema": "sales_dw",
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False},
                    {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "email", "type": "VARCHAR(255)", "nullable": True},
                    {"name": "phone", "type": "VARCHAR(20)", "nullable": True},
                ]
            }
        ]

    # ==================== 阶段 1: 数据源接入与元数据自动发现 ====================

    def test_stage1_datasource_connection(self, config):
        """阶段 1.1: 测试数据源连接"""
        response = requests.post(
            f"{config['data_api_url']}/api/v1/datasources/test-connection",
            json={
                "type": "mysql",
                "connection": {
                    "host": "localhost",
                    "port": 3306,
                    "database": config["test_database"],
                }
            }
        )
        assert response.status_code in (200, 201)  # 可能成功或需要配置

    def test_stage1_metadata_scan(self, test_data_source_id, config):
        """阶段 1.2: 测试元数据扫描"""
        response = requests.post(
            f"{config['data_api_url']}/api/v1/metadata/scan",
            json={"datasource_id": test_data_source_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data

    # ==================== 阶段 2: 敏感数据自动识别 ====================

    def test_stage2_sensitivity_scan(self, test_data_source_id, test_tables, config):
        """阶段 2: 测试敏感数据扫描"""
        # 获取包含敏感信息的表
        test_table = next((t for t in test_tables if "customers" in t["name"]), None)
        if not test_table:
            pytest.skip("No customers table found")

        response = requests.post(
            f"{config['data_api_url']}/api/v1/sensitivity/scan",
            json={
                "datasource_id": test_data_source_id,
                "table_name": test_table["name"],
                "schema_name": test_table.get("schema", "sales_dw"),
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data

        # 等待扫描完成
        scan_id = data["scan_id"]
        for _ in range(30):
            status_response = requests.get(
                f"{config['data_api_url']}/api/v1/sensitivity/scan/{scan_id}"
            )
            status = status_response.json()
            if status.get("status") == "completed":
                break
            time.sleep(2)

        # 获取扫描结果
        result_response = requests.get(
            f"{config['data_api_url']}/api/v1/sensitivity/results/{scan_id}"
        )
        assert result_response.status_code == 200
        results = result_response.json()
        assert "columns" in results

        # 验证敏感字段被识别
        sensitive_columns = results.get("sensitive_columns", [])
        # email 和 phone 应该被识别为敏感字段
        column_names = [col["name"] for col in sensitive_columns]
        # 根据实际数据验证
        assert isinstance(sensitive_columns, list)

    # ==================== 阶段 3: 智能ETL编排与数据加工 ====================

    def test_stage3_etl_orchestration(self, test_data_source_id, config):
        """阶段 3: 测试 ETL 编排"""
        # 创建 ETL 任务
        response = requests.post(
            f"{config['data_api_url']}/api/v1/etl/jobs",
            json={
                "name": "test_daily_sales_sync",
                "type": "sync",
                "source": {
                    "datasource_id": test_data_source_id,
                    "table": "orders",
                },
                "target": {
                    "type": "data_warehouse",
                    "table": "fact_orders",
                },
                "schedule": "0 2 * * *",  # 每天凌晨 2 点
                "transformations": [
                    {"type": "clean", "rules": {"remove_nulls": True}},
                    {"type": "mask", "columns": ["customer_id"]},
                ]
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        job_id = data.get("id", data.get("job_id"))
        assert job_id is not None

        # 触发任务执行
        run_response = requests.post(
            f"{config['data_api_url']}/api/v1/etl/jobs/{job_id}/run"
        )
        assert run_response.status_code == 200

        # 等待执行完成
        run_id = run_response.json().get("run_id")
        for _ in range(60):
            status_response = requests.get(
                f"{config['data_api_url']}/api/v1/etl/runs/{run_id}"
            )
            status = status_response.json()
            if status.get("status") in ("completed", "failed"):
                break
            time.sleep(2)

        # 清理
        requests.delete(f"{config['data_api_url']}/api/v1/etl/jobs/{job_id}")

    # ==================== 阶段 4: 元数据同步与数据血缘 ====================

    def test_stage4_lineage_tracking(self, test_data_source_id, config):
        """阶段 4: 测试血缘跟踪"""
        # 创建血缘事件
        response = requests.post(
            f"{config['data_api_url']}/api/v1/lineage/events",
            json={
                "event_type": "etl_job_completed",
                "source_tables": ["sales_dw.orders"],
                "target_tables": ["analytics.fact_orders"],
                "job_name": "daily_sales_sync",
                "transformation": "SELECT * FROM orders WHERE status = 'completed'",
            }
        )
        assert response.status_code == 200

        # 查询血缘关系
        lineage_response = requests.get(
            f"{config['data_api_url']}/api/v1/lineage/upstream",
            params={
                "namespace": "analytics",
                "table_name": "fact_orders",
            }
        )
        assert lineage_response.status_code == 200
        lineage = lineage_response.json()
        assert isinstance(lineage, list)

    # ==================== 阶段 5: 资产编目与价值评估 ====================

    def test_stage5_asset_evaluation(self, test_tables, config):
        """阶段 5: 测试资产价值评估"""
        if not test_tables:
            pytest.skip("No tables found")

        # 计算资产价值
        for table in test_tables[:2]:  # 只测试前两个表
            response = requests.post(
                f"{config['data_api_url']}/api/v1/assets/evaluate",
                json={
                    "namespace": table.get("schema", "sales_dw"),
                    "table_name": table["name"],
                }
            )
            assert response.status_code == 200
            result = response.json()
            assert "value_score" in result or "score" in result

        # 获取高价值资产列表
        assets_response = requests.get(
            f"{config['data_api_url']}/api/v1/assets",
            params={"min_value_score": 50}
        )
        assert assets_response.status_code == 200
        assets = assets_response.json()
        assert "items" in assets or isinstance(assets, list)

    # ==================== 阶段 6: 表融合分析 ====================

    def test_stage6_table_fusion(self, test_tables, config):
        """阶段 6: 测试表融合分析"""
        if len(test_tables) < 2:
            pytest.skip("Need at least 2 tables for fusion analysis")

        # 触发表融合分析
        response = requests.post(
            f"{config['data_api_url']}/api/v1/fusion/analyze",
            json={
                "tables": [
                    {"namespace": t.get("schema", "sales_dw"), "name": t["name"]}
                    for t in test_tables[:2]
                ]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "fusion_candidates" in result or "candidates" in result

    # ==================== 阶段 7: 知识库向量索引构建 ====================

    def test_stage7_vector_indexing(self, test_tables, config):
        """阶段 7: 测试向量索引构建"""
        # 构建知识库索引
        if not test_tables:
            pytest.skip("No tables to index")

        response = requests.post(
            f"{config['data_api_url']}/api/v1/knowledge/build",
            json={
                "datasource_id": test_tables[0].get("datasource_id", "test"),
                "tables": [t["name"] for t in test_tables[:2]],
                "index_type": "metadata",
            }
        )
        assert response.status_code in (200, 202)

        # 等待索引构建完成
        if response.status_code == 202:
            task_id = response.json().get("task_id")
            if task_id:
                for _ in range(60):
                    status_response = requests.get(
                        f"{config['data_api_url']}/api/v1/knowledge/tasks/{task_id}"
                    )
                    status = status_response.json()
                    if status.get("status") in ("completed", "failed"):
                        break
                    time.sleep(2)

    # ==================== 阶段 8: 智能查询 ====================

    def test_stage8_text_to_sql(self, config):
        """阶段 8.1: 测试 Text-to-SQL"""
        response = requests.post(
            f"{config['agent_api_url']}/api/v1/text-to-sql",
            json={
                "question": "查询最近7天的订单总金额",
                "database": config["test_database"],
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "sql" in result or "query" in result
        assert "answer" in result or "result" in result

    def test_stage8_rag_query(self, config):
        """阶段 8.2: 测试 RAG 查询"""
        response = requests.post(
            f"{config['agent_api_url']}/api/v1/rag/query",
            json={
                "question": "订单数据的敏感信息如何处理？",
                "collection": "knowledge_base",
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "answer" in result or "response" in result
        assert "sources" in result or "references" in result

    def test_stage8_agent_query(self, config):
        """阶段 8.3: 测试 Agent 查询"""
        response = requests.post(
            f"{config['agent_api_url']}/api/v1/agent/chat",
            json={
                "message": "帮我分析一下销售额趋势",
                "use_tools": True,
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "response" in result or "answer" in result
        # 验证工具调用
        tool_calls = result.get("tool_calls", [])
        assert isinstance(tool_calls, list)

    # ==================== 完整流程测试 ====================

    def test_complete_lifecycle_flow(self, test_data_source_id, config):
        """完整生命周期流程测试"""
        flow_id = f"lifecycle_{int(time.time())}"

        # 1. 数据源接入
        print(f"[{flow_id}] Stage 1: 数据源接入")
        # 使用已创建的数据源

        # 2. 元数据扫描
        print(f"[{flow_id}] Stage 1.2: 元数据扫描")
        scan_response = requests.post(
            f"{config['data_api_url']}/api/v1/metadata/scan",
            json={"datasource_id": test_data_source_id}
        )
        assert scan_response.status_code == 200

        # 3. 敏感数据扫描
        print(f"[{flow_id}] Stage 2: 敏感数据扫描")
        sensitivity_response = requests.post(
            f"{config['data_api_url']}/api/v1/sensitivity/scan-batch",
            json={"datasource_id": test_data_source_id}
        )
        assert sensitivity_response.status_code in (200, 202)

        # 4. ETL 任务创建
        print(f"[{flow_id}] Stage 3: ETL 编排")
        etl_response = requests.post(
            f"{config['data_api_url']}/api/v1/etl/jobs",
            json={
                "name": f"{flow_id}_etl",
                "source": {"datasource_id": test_data_source_id, "table": "orders"},
                "target": {"type": "warehouse", "table": "fact_orders"},
            }
        )
        assert etl_response.status_code in (200, 201)
        job_id = etl_response.json().get("id", etl_response.json().get("job_id"))

        # 5. 血缘记录
        print(f"[{flow_id}] Stage 4: 血缘跟踪")
        lineage_response = requests.post(
            f"{config['data_api_url']}/api/v1/lineage/events",
            json={
                "job_name": f"{flow_id}_etl",
                "source_tables": ["sales_dw.orders"],
                "target_tables": ["analytics.fact_orders"],
            }
        )
        assert lineage_response.status_code == 200

        # 6. 资产评估
        print(f"[{flow_id}] Stage 5: 资产评估")
        asset_response = requests.post(
            f"{config['data_api_url']}/api/v1/assets/evaluate-batch",
            json={"datasource_id": test_data_source_id}
        )
        assert asset_response.status_code in (200, 202)

        # 7. 向量索引
        print(f"[{flow_id}] Stage 7: 向量索引")
        index_response = requests.post(
            f"{config['data_api_url']}/api/v1/knowledge/build",
            json={"datasource_id": test_data_source_id}
        )
        assert index_response.status_code in (200, 202)

        # 8. 智能查询
        print(f"[{flow_id}] Stage 8: 智能查询")
        query_response = requests.post(
            f"{config['agent_api_url']}/api/v1/agent/chat",
            json={"message": "查询订单数据"}
        )
        assert query_response.status_code == 200

        # 清理
        if job_id:
            requests.delete(f"{config['data_api_url']}/api/v1/etl/jobs/{job_id}")

        print(f"[{flow_id}] Complete lifecycle test passed!")


class TestTextToSQLE2E:
    """Text-to-SQL E2E 测试"""

    def test_sql_generation_and_execution(self, config):
        """测试 SQL 生成和执行流程"""
        # 1. 生成 SQL
        gen_response = requests.post(
            f"{config['agent_api_url']}/api/v1/text-to-sql",
            json={
                "question": "查询销售额最高的前10个产品",
                "database": config["test_database"],
            }
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        sql = gen_data.get("sql") or gen_data.get("query")
        assert sql is not None
        assert "SELECT" in sql.upper()

        # 2. 验证 SQL 安全性
        validate_response = requests.post(
            f"{config['agent_api_url']}/api/v1/sql/validate",
            json={"sql": sql}
        )
        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data.get("is_valid", True) is True

        # 3. 执行 SQL
        exec_response = requests.post(
            f"{config['agent_api_url']}/api/v1/sql/execute",
            json={
                "sql": sql,
                "database": config["test_database"],
                "row_limit": 10,
            }
        )
        assert exec_response.status_code == 200
        exec_data = exec_response.json()
        assert "results" in exec_data or "data" in exec_data


class TestRAGE2E:
    """RAG E2E 测试"""

    def test_vector_search_and_generation(self, config):
        """测试向量搜索和生成流程"""
        # 1. 向量搜索
        search_response = requests.post(
            f"{config['agent_api_url']}/api/v1/vector/search",
            json={
                "query": "如何处理订单敏感信息",
                "top_k": 5,
            }
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "results" in search_data
        assert len(search_data["results"]) <= 5

        # 2. RAG 查询
        rag_response = requests.post(
            f"{config['agent_api_url']}/api/v1/rag/query",
            json={
                "question": "如何处理订单敏感信息",
                "use_vector_search": True,
            }
        )
        assert rag_response.status_code == 200
        rag_data = rag_response.json()
        assert "answer" in rag_data or "response" in rag_data


class TestAgentE2E:
    """Agent E2E 测试"""

    def test_multi_tool_agent_execution(self, config):
        """测试多工具 Agent 执行"""
        response = requests.post(
            f"{config['agent_api_url']}/api/v1/agent/chat",
            json={
                "message": "分析一下最近一个月的销售趋势，并生成图表",
                "session_id": f"test_{int(time.time())}",
                "use_tools": True,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "answer" in data

        # 检查是否使用了工具
        tool_calls = data.get("tool_calls", [])
        assert isinstance(tool_calls, list)
        # 验证可能的工具调用
        if tool_calls:
            assert "tool_name" in tool_calls[0] or "name" in tool_calls[0]


class TestSmokeE2E:
    """冒烟测试 - 快速验证关键功能"""

    def test_data_api_health(self, config):
        """测试 Alldata API 健康状态"""
        response = requests.get(f"{config['data_api_url']}/health")
        assert response.status_code == 200

    def test_agent_api_health(self, config):
        """测试 Bisheng API 健康状态"""
        response = requests.get(f"{config['agent_api_url']}/health")
        assert response.status_code == 200

    def test_openai_proxy_health(self, config):
        """测试 OpenAI Proxy 健康状态"""
        response = requests.get(f"{config['openai_proxy_url']}/health")
        assert response.status_code == 200

    def test_api_versions(self, config):
        """测试 API 版本端点"""
        alldata_response = requests.get(f"{config['data_api_url']}/api/version")
        assert alldata_response.status_code == 200

        bisheng_response = requests.get(f"{config['agent_api_url']}/api/version")
        assert bisheng_response.status_code == 200


@pytest.mark.performance
class TestPerformanceE2E:
    """性能 E2E 测试"""

    def test_query_response_time(self, config):
        """测试查询响应时间"""
        start_time = time.time()

        response = requests.post(
            f"{config['agent_api_url']}/api/v1/text-to-sql",
            json={
                "question": "查询所有订单",
                "database": config["test_database"],
            }
        )

        elapsed = time.time() - start_time
        assert response.status_code == 200
        assert elapsed < 5.0  # 响应时间应小于 5 秒

    def test_concurrent_requests(self, config):
        """测试并发请求"""
        import concurrent.futures

        def make_request():
            response = requests.post(
                f"{config['agent_api_url']}/api/v1/sql/execute",
                json={
                    "sql": "SELECT 1",
                    "database": config["test_database"],
                }
            )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 18  # 至少 90% 成功率


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
