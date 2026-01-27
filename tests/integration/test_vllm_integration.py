"""
vLLM 服务集成测试

测试覆盖:
- vLLM Chat 服务健康检查
- Chat Completions API (流式/非流式)
- Embeddings API
- 模型列表 API
- Text-to-SQL 生成
- 敏感数据检测 (AI驱动)
"""

import os
import pytest
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)

# 测试配置
VLLM_CHAT_URL = os.getenv("TEST_VLLM_CHAT_URL", "http://localhost:8000")
VLLM_EMBED_URL = os.getenv("TEST_VLLM_EMBED_URL", "http://localhost:8001")
OPENAI_PROXY_URL = os.getenv("TEST_OPENAI_PROXY_URL", "http://localhost:8080")
PROXY_API_KEY = os.getenv("TEST_PROXY_API_KEY", "test-key")


class TestVLLMChatService:
    """vLLM Chat 服务测试"""

    @pytest.mark.integration
    def test_01_health_check(self):
        """测试 vLLM Chat 服务健康检查"""
        response = requests.get(f"{VLLM_CHAT_URL}/health", timeout=5)

        # 服务可能不可用，这是正常的
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    @pytest.mark.integration
    def test_02_list_models(self):
        """测试列出可用模型"""
        response = requests.get(f"{VLLM_CHAT_URL}/v1/models", timeout=10)

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "object" in data
            assert "data" in data
            assert isinstance(data["data"], list)

    @pytest.mark.integration
    def test_03_chat_completion_simple(self):
        """测试简单对话补全"""
        client = OpenAI(
            api_key="dummy",
            base_url=f"{VLLM_CHAT_URL}/v1",
        )

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Hello, vLLM!'"}
                ],
                max_tokens=50,
                temperature=0.7,
                timeout=30
            )

            assert response.choices is not None
            assert len(response.choices) > 0
            assert response.choices[0].message.content is not None
            logger.info(f"Chat response: {response.choices[0].message.content}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Chat service not available")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_04_chat_completion_streaming(self):
        """测试流式对话补全"""
        client = AsyncOpenAI(
            api_key="dummy",
            base_url=f"{VLLM_CHAT_URL}/v1",
        )

        try:
            stream = await client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "user", "content": "Count from 1 to 5"}
                ],
                max_tokens=100,
                stream=True,
                timeout=30
            )

            chunks = []
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)

            assert len(chunks) > 0
            logger.info(f"Received {len(chunks)} streaming chunks")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("vLLM Chat service not available or timeout")

    @pytest.mark.integration
    def test_05_chat_completion_with_functions(self):
        """测试带函数调用的对话补全"""
        client = OpenAI(
            api_key="dummy",
            base_url=f"{VLLM_CHAT_URL}/v1",
        )

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "user", "content": "What's the weather in Beijing?"}
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Get the current weather",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": "City name"
                                    }
                                },
                                "required": ["location"]
                            }
                        }
                    }
                ],
                timeout=30
            )

            assert response.choices is not None

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Chat service not available")


class TestVLLMEmbedService:
    """vLLM Embedding 服务测试"""

    @pytest.mark.integration
    def test_01_health_check(self):
        """测试 vLLM Embedding 服务健康检查"""
        response = requests.get(f"{VLLM_EMBED_URL}/health", timeout=5)

        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_02_create_embeddings_single(self):
        """测试单个文本嵌入"""
        client = OpenAI(
            api_key="dummy",
            base_url=f"{VLLM_EMBED_URL}/v1",
        )

        try:
            response = client.embeddings.create(
                model="default",
                input="Hello, world!",
                timeout=30
            )

            assert response.object == "list"
            assert len(response.data) > 0
            assert response.data[0].embedding is not None
            assert len(response.data[0].embedding) > 0

            logger.info(f"Embedding dimension: {len(response.data[0].embedding)}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Embedding service not available")

    @pytest.mark.integration
    def test_03_create_embeddings_batch(self):
        """测试批量文本嵌入"""
        client = OpenAI(
            api_key="dummy",
            base_url=f"{VLLM_EMBED_URL}/v1",
        )

        try:
            texts = [
                "Machine learning is a subset of artificial intelligence.",
                "Deep learning uses neural networks with multiple layers.",
                "Natural language processing deals with text data."
            ]

            response = client.embeddings.create(
                model="default",
                input=texts,
                timeout=60
            )

            assert len(response.data) == len(texts)

            # 验证嵌入向量维度一致
            dimensions = [len(item.embedding) for item in response.data]
            assert len(set(dimensions)) == 1

            logger.info(f"Generated {len(response.data)} embeddings")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Embedding service not available")

    @pytest.mark.integration
    def test_04_embedding_similarity(self):
        """测试嵌入向量相似度计算"""
        client = OpenAI(
            api_key="dummy",
            base_url=f"{VLLM_EMBED_URL}/v1",
        )

        try:
            # 相似文本
            response1 = client.embeddings.create(
                model="default",
                input="The cat sat on the mat",
                timeout=30
            )
            embedding1 = response1.data[0].embedding

            response2 = client.embeddings.create(
                model="default",
                input="A cat was sitting on a mat",
                timeout=30
            )
            embedding2 = response2.data[0].embedding

            # 计算余弦相似度
            def cosine_similarity(a: List[float], b: List[float]) -> float:
                dot_product = sum(x * y for x, y in zip(a, b))
                magnitude_a = sum(x * x for x in a) ** 0.5
                magnitude_b = sum(y * y for y in b) ** 0.5
                return dot_product / (magnitude_a * magnitude_b)

            similarity = cosine_similarity(embedding1, embedding2)

            # 相似文本应该有较高的相似度
            assert similarity > 0.7
            logger.info(f"Similarity: {similarity:.4f}")

        except requests.exceptions.ConnectionError:
            pytest.skip("vLLM Embedding service not available")


class TestOpenAIProxy:
    """OpenAI 代理服务测试"""

    @pytest.mark.integration
    def test_01_proxy_health_check(self):
        """测试代理服务健康检查"""
        response = requests.get(f"{OPENAI_PROXY_URL}/health", timeout=5)

        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_02_proxy_chat_completion(self):
        """测试通过代理调用对话补全"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "user", "content": "Say 'Proxy works!'"}
                ],
                max_tokens=20,
                timeout=60
            )

            assert response.choices is not None
            logger.info(f"Proxy chat response: {response.choices[0].message.content}")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_03_proxy_embeddings(self):
        """测试通过代理调用嵌入服务"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        try:
            response = client.embeddings.create(
                model="default",
                input="Test embedding through proxy",
                timeout=60
            )

            assert len(response.data) > 0
            assert response.data[0].embedding is not None

            logger.info(f"Proxy embedding dimension: {len(response.data[0].embedding)}")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")


class TestTextToSQL:
    """Text-to-SQL 生成测试"""

    @pytest.mark.integration
    def test_01_generate_simple_select(self):
        """测试生成简单 SELECT 查询"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        schema = """
        Table: customers
        Columns: id (INT), name (VARCHAR), email (VARCHAR), city (VARCHAR), created_at (TIMESTAMP)
        """

        prompt = f"""Given the following schema:
{schema}

Generate a SQL query to: Find all customers from Beijing
Return only the SQL query without explanation."""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Output only valid SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1,
                timeout=60
            )

            sql = response.choices[0].message.content.strip()
            logger.info(f"Generated SQL: {sql}")

            # 验证生成的 SQL 包含关键字
            assert "SELECT" in sql.upper()
            assert "customers" in sql.lower()
            assert "Beijing" in sql or "beijing" in sql

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_02_generate_join_query(self):
        """测试生成 JOIN 查询"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        schema = """
        Tables:
        - customers: id, name, email
        - orders: id, customer_id, total_amount, created_at
        """

        prompt = f"""Given the following schema:
{schema}

Generate a SQL query to: Find the total order amount for each customer
Return only the SQL query without explanation."""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Output only valid SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=60
            )

            sql = response.choices[0].message.content.strip()
            logger.info(f"Generated JOIN SQL: {sql}")

            assert "SELECT" in sql.upper()
            assert "JOIN" in sql.upper() or "customers" in sql.lower()

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_03_explain_sql(self):
        """测试解释 SQL 查询"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        sql = """
        SELECT c.name, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        WHERE c.created_at >= '2024-01-01'
        GROUP BY c.id, c.name
        HAVING total_spent > 1000
        ORDER BY total_spent DESC
        LIMIT 10
        """

        prompt = f"Explain what this SQL query does:\n\n{sql}"

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                timeout=60
            )

            explanation = response.choices[0].message.content
            logger.info(f"SQL explanation: {explanation}")

            assert len(explanation) > 50  # 应该有详细的解释

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")


class TestAISensitivityDetection:
    """AI 敏感数据检测测试"""

    @pytest.mark.integration
    def test_01_detect_email_addresses(self):
        """测试检测邮箱地址"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        text = """
        Contact information:
        - John Doe: john.doe@example.com
        - Jane Smith: jane.smith@company.org
        - Support: support@service.net
        """

        prompt = f"""Analyze the following text and identify any sensitive information.
Respond in JSON format with keys: sensitive_type, sensitivity_level, findings.

Text:
{text}"""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a data security expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=60
            )

            result = response.choices[0].message.content
            logger.info(f"Sensitivity detection result: {result}")

            # 验证返回包含敏感类型信息
            assert "email" in result.lower() or "contact" in result.lower()

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_02_detect_phone_numbers(self):
        """测试检测电话号码"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        text = """
        Customer records:
        - Alice: 138-1234-5678
        - Bob: +86 139 8765 4321
        - Charlie: 021-12345678
        """

        prompt = f"""Identify phone numbers in the following text.
Return a JSON list of found phone numbers with their positions.

Text:
{text}"""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=60
            )

            result = response.choices[0].message.content
            logger.info(f"Phone detection result: {result}")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_03_detect_id_numbers(self):
        """测试检测身份证号"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        text = """
        Employee information:
        - Name: Zhang San, ID: 110101199001011234
        - Name: Li Si, ID Card: 320102198505201234
        """

        prompt = f"""Detect any Chinese ID numbers in the text.
Mark each finding with the type and sensitivity level.

Text:
{text}"""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a data security expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=60
            )

            result = response.choices[0].message.content
            logger.info(f"ID number detection result: {result}")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")


class TestRAGRetrieval:
    """RAG 检索测试"""

    @pytest.mark.integration
    def test_01_generate_embedding_for_retrieval(self):
        """测试为检索生成嵌入"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        query = "What is the return policy for electronic items?"

        try:
            response = client.embeddings.create(
                model="default",
                input=query,
                timeout=60
            )

            query_embedding = response.data[0].embedding

            assert len(query_embedding) > 0
            logger.info(f"Query embedding dimension: {len(query_embedding)}")

            # 模拟文档嵌入
            docs = [
                "Our return policy allows returns within 30 days of purchase.",
                "Electronic items must be returned in original packaging.",
                "Refunds are processed within 5-7 business days."
            ]

            doc_response = client.embeddings.create(
                model="default",
                input=docs,
                timeout=60
            )

            # 计算相似度
            query_vec = query_embedding
            for i, doc in enumerate(doc_response.data):
                doc_vec = doc.embedding
                similarity = sum(q * d for q, d in zip(query_vec, doc_vec))
                logger.info(f"Doc {i} similarity: {similarity:.4f}")

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    def test_02_rag_question_answering(self):
        """测试 RAG 问答"""
        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        context = """
        Return Policy:
        - Items can be returned within 30 days of purchase
        - Original receipt is required
        - Electronic items must be unopened or in original packaging
        - Refunds are processed within 5-7 business days
        - Shipping costs are non-refundable
        """

        question = "Can I return a laptop after 20 days?"

        prompt = f"""Answer the question based on the given context.
If the answer is not in the context, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer:"""

        try:
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {"role": "system", "content": "You are a helpful customer service assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
                timeout=60
            )

            answer = response.choices[0].message.content
            logger.info(f"RAG answer: {answer}")

            assert "30 days" in answer or "20" in answer or "return" in answer.lower()

        except (requests.exceptions.ConnectionError, asyncio.TimeoutError):
            pytest.skip("OpenAI Proxy service not available")


class TestPerformance:
    """性能测试"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_01_concurrent_chat_requests(self):
        """测试并发对话请求"""
        import concurrent.futures
        import time

        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        def make_request(prompt_id: int) -> Dict[str, Any]:
            start = time.time()
            try:
                response = client.chat.completions.create(
                    model="default",
                    messages=[{"role": "user", "content": f"Say 'Request {prompt_id}'"}],
                    max_tokens=10,
                    timeout=60
                )
                elapsed = time.time() - start
                return {"success": True, "id": prompt_id, "time": elapsed}
            except Exception as e:
                elapsed = time.time() - start
                return {"success": False, "id": prompt_id, "error": str(e), "time": elapsed}

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, i) for i in range(10)]
                results = [f.result(timeout=120) for f in concurrent.futures.as_completed(futures)]

            successful = [r for r in results if r["success"]]
            logger.info(f"Successful requests: {len(successful)}/{len(results)}")

            if successful:
                avg_time = sum(r["time"] for r in successful) / len(successful)
                logger.info(f"Average response time: {avg_time:.2f}s")

        except requests.exceptions.ConnectionError:
            pytest.skip("OpenAI Proxy service not available")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_02_batch_embedding_throughput(self):
        """测试批量嵌入吞吐量"""
        import time

        client = OpenAI(
            api_key=PROXY_API_KEY,
            base_url=f"{OPENAI_PROXY_URL}/v1",
        )

        texts = [f"Sample text number {i}" for i in range(100)]

        try:
            start = time.time()
            response = client.embeddings.create(
                model="default",
                input=texts,
                timeout=120
            )
            elapsed = time.time() - start

            assert len(response.data) == len(texts)

            throughput = len(texts) / elapsed
            logger.info(f"Embedding throughput: {throughput:.2f} texts/second")

            assert throughput > 1  # 至少每秒处理一个文本

        except requests.exceptions.ConnectionError:
            pytest.skip("OpenAI Proxy service not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
