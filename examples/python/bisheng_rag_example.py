#!/usr/bin/env python3
"""
Bisheng RAG 应用示例
演示如何整合 Alldata + Cube + Bisheng 实现知识问答
"""

import requests
from typing import List, Dict, Optional
import json


class RAGApplication:
    """RAG（检索增强生成）应用类"""

    def __init__(
        self,
        alldata_url: str = "http://localhost:8080",
        cube_url: str = "http://localhost:8000",
        bisheng_url: str = "http://localhost:8081",
    ):
        self.alldata_url = alldata_url.rstrip("/")
        self.cube_url = cube_url.rstrip("/")
        self.bisheng_url = bisheng_url.rstrip("/")
        self.session = requests.Session()

    def health_check(self) -> Dict:
        """检查所有服务健康状态"""
        status = {}

        # Alldata
        try:
            r = self.session.get(f"{self.alldata_url}/api/v1/health", timeout=5)
            status["alldata"] = "OK" if r.status_code == 200 else "ERROR"
        except Exception as e:
            status["alldata"] = f"ERROR: {e}"

        # Cube
        try:
            r = self.session.get(f"{self.cube_url}/v1/models", timeout=5)
            status["cube"] = "OK" if r.status_code == 200 else "ERROR"
        except Exception as e:
            status["cube"] = f"ERROR: {e}"

        # Bisheng
        try:
            r = self.session.get(f"{self.bisheng_url}/api/v1/health", timeout=5)
            status["bisheng"] = "OK" if r.status_code == 200 else "ERROR"
        except Exception as e:
            status["bisheng"] = f"ERROR: {e}"

        return status

    def query_with_context(
        self, question: str, context: Optional[str] = None
    ) -> Dict:
        """使用上下文进行查询"""
        system_prompt = "你是一个智能助手。请根据以下上下文回答用户问题。"
        if context:
            system_prompt += f"\n\n上下文信息：\n{context}"

        response = self.session.post(
            f"{self.cube_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen-0.5B-Chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                "max_tokens": 500,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def rag_query(self, question: str) -> Dict:
        """RAG 查询 - 通过 Bisheng"""
        response = self.session.post(
            f"{self.bisheng_url}/api/v1/rag/query",
            json={"question": question},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def sql_query(self, question: str) -> Dict:
        """Text-to-SQL 查询"""
        # 1. 从 Alldata 获取表结构
        response = self.session.get(
            f"{self.alldata_url}/api/v1/metadata/databases/sales_dw/tables/orders"
        )
        table_info = response.json()["data"]

        # 2. 构建包含表结构的 Prompt
        columns = "\n".join(
            f"    - {c['name']} ({c['type']}): {c['description']}"
            for c in table_info["columns"]
        )
        schema_prompt = f"""请根据以下表结构，将用户问题转换为 SQL 查询：

表名: orders (订单表)
字段:
{columns}

用户问题: {question}

请只返回 SQL 查询语句，不要其他内容。"""

        # 3. 调用模型生成 SQL
        response = self.session.post(
            f"{self.cube_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen-0.5B-Chat",
                "messages": [{"role": "user", "content": schema_prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=30,
        )
        response.raise_for_status()
        sql = response.json()["choices"][0]["message"]["content"]

        return {"question": question, "sql": sql}

    def list_datasets(self) -> List[Dict]:
        """获取可用数据集列表"""
        response = self.session.get(f"{self.alldata_url}/api/v1/datasets")
        response.raise_for_status()
        return response.json()["data"]


class KnowledgeBase:
    """知识库类 - 管理用于 RAG 的文档"""

    def __init__(self):
        self.documents = [
            {
                "id": "doc-001",
                "title": "ONE-DATA-STUDIO 平台概述",
                "content": """
                ONE-DATA-STUDIO 是一个企业级 AI 平台，整合了三个核心组件：
                1. Alldata - 数据治理与开发平台，负责数据的采集、清洗、治理和存储
                2. Cube Studio - 云原生 MLOps 平台，提供模型训练、部署和服务化能力
                3. Bisheng - 大模型应用开发平台，支持 RAG、Agent 等应用编排

                平台采用四层架构：L1 基础设施层（K8s）、L2 数据底座层、L3 算法引擎层、L4 应用编排层。
                """,
                "tags": ["platform", "overview"],
            },
            {
                "id": "doc-002",
                "title": "Alldata 数据治理",
                "content": """
                Alldata 是数据底座层，提供以下核心能力：
                - 数据集成：支持多种异构数据源的接入
                - 数据开发：基于 Flink/Spark 的 ETL 能力
                - 数据治理：元数据管理、数据质量、数据血缘
                - 特征存储：为模型训练提供特征数据
                - 向量存储：为 RAG 应用提供向量检索能力
                """,
                "tags": ["alldata", "data"],
            },
            {
                "id": "doc-003",
                "title": "Cube Studio 模型服务",
                "content": """
                Cube Studio 是算法引擎层，提供：
                - Notebook 开发环境：基于 JupyterHub 的多用户开发环境
                - 分布式训练：支持 Volcano 调度和 Ray 分布式计算
                - 模型服务：基于 vLLM/TGI 的高性能推理服务
                - 实验管理：MLflow 实验追踪和模型管理

                模型服务提供 OpenAI 兼容的 API，方便应用集成。
                """,
                "tags": ["cube", "ml"],
            },
            {
                "id": "doc-004",
                "title": "Bisheng 应用编排",
                "content": """
                Bisheng 是应用编排层，专注于 LLM 应用开发：
                - RAG 流水线：支持文档加载、切分、向量化和检索
                - Agent 编排：支持 ReAct、Function Calling 等模式
                - Prompt 管理：版本管理和 A/B 测试
                - 应用发布：一键发布为 REST API

                可与 Alldata（元数据）和 Cube（模型服务）无缝集成。
                """,
                "tags": ["bisheng", "llm"],
            },
        ]

    def search(self, query: str, top_k: int = 2) -> List[Dict]:
        """简单关键词搜索（实际应使用向量检索）"""
        query_lower = query.lower()
        scored = []

        for doc in self.documents:
            score = 0
            if query_lower in doc["title"].lower():
                score += 10
            for word in query_lower.split():
                if word in doc["content"].lower():
                    score += 1
            if score > 0:
                scored.append({"doc": doc, "score": score})

        # 按分数排序
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in scored[:top_k]]


def main():
    """示例用法"""
    print("=" * 60)
    print("ONE-DATA-STUDIO RAG 应用示例")
    print("=" * 60)

    # 初始化应用
    app = RAGApplication()
    kb = KnowledgeBase()

    # 1. 健康检查
    print("\n=== 服务健康检查 ===")
    status = app.health_check()
    for service, state in status.items():
        print(f"  {service}: {state}")

    # 2. 知识检索
    print("\n=== 知识检索 ===")
    question = "ONE-DATA-STUDIO 有哪些组件？"
    docs = kb.search(question, top_k=2)
    print(f"问题: {question}")
    print("相关文档:")
    for doc in docs:
        print(f"  - {doc['title']}")
    context = docs[0]["content"] if docs else ""

    # 3. RAG 查询
    print("\n=== RAG 查询 ===")
    result = app.query_with_context(question, context)
    answer = result["choices"][0]["message"]["content"]
    print(f"回答: {answer}")

    # 4. Text-to-SQL
    print("\n=== Text-to-SQL ===")
    sql_question = "查询订单总额超过1000元的客户"
    sql_result = app.sql_query(sql_question)
    print(f"问题: {sql_question}")
    print(f"生成的 SQL: {sql_result['sql']}")

    # 5. 数据集列表
    print("\n=== 可用数据集 ===")
    datasets = app.list_datasets()
    for ds in datasets:
        print(f"  - {ds['name']}: {ds.get('description', 'N/A')}")

    print("\n=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
