"""
模型推理服务
支持多种推理后端：vLLM, TGI, Triton, OpenAI兼容API
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union, AsyncIterator
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """推理结果"""
    output: Any
    model: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    backend: str = ""


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    connected: bool
    latency_ms: float
    model_loaded: bool = False
    backend: str = ""
    endpoint: str = ""
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


# 可重试的 HTTP 状态码
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


class ModelInferenceService:
    """
    模型推理服务

    支持的推理后端：
    - vLLM: OpenAI 兼容 API
    - TGI (Text Generation Inference): OpenAI 兼容 API
    - OpenAI API: 官方 API
    - 自定义 HTTP 端点
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        backend: str = "auto",
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0
    ):
        """
        初始化推理服务

        Args:
            endpoint: 推理服务端点 URL
            api_key: API 密钥
            backend: 推理后端类型 (vllm, tgi, openai, custom, auto)
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数（针对 429/500/502/503 错误）
            retry_backoff: 重试退避基数（秒），实际等待 = backoff * 2^attempt
        """
        self.endpoint = endpoint or os.getenv("MODEL_SERVING_ENDPOINT", "")
        self.api_key = api_key or os.getenv("MODEL_SERVING_API_KEY", "")
        self.backend = backend
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # OpenAI 配置
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # 自动检测后端
        if backend == "auto" and self.endpoint:
            self.backend = self._detect_backend(self.endpoint)

        self._headers = {}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"ModelInferenceService initialized: backend={self.backend}, endpoint={self.endpoint}")

    def _detect_backend(self, endpoint: str) -> str:
        """根据端点 URL 自动检测后端类型"""
        endpoint_lower = endpoint.lower()
        if "vllm" in endpoint_lower or ":8000" in endpoint_lower:
            return "vllm"
        elif "tgi" in endpoint_lower or ":3000" in endpoint_lower:
            return "tgi"
        elif "openai" in endpoint_lower:
            return "openai"
        else:
            return "custom"  # 假设是 OpenAI 兼容的 API

    def is_available(self) -> bool:
        """检查推理服务是否可用"""
        return bool(self.endpoint) or bool(self.openai_api_key)

    async def health_check(self, model: Optional[str] = None) -> HealthCheckResult:
        """
        对推理端点执行健康检查

        通过请求 /v1/models 端点来检测连接性、延迟和模型加载状态。
        如果指定了 model 参数，还会验证该模型是否已加载。

        Args:
            model: 可选的模型名称，用于验证模型是否已加载

        Returns:
            HealthCheckResult
        """
        import time

        if not self.is_available():
            return HealthCheckResult(
                connected=False,
                latency_ms=0.0,
                backend=self.backend,
                endpoint=self.endpoint,
                error="推理服务未配置"
            )

        endpoint = self._get_endpoint("models")
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 10.0)) as client:
                response = await client.get(endpoint, headers=self._get_headers())
                latency_ms = (time.time() - start_time) * 1000
                response.raise_for_status()
                data = response.json()

            # 检测模型是否已加载
            model_loaded = False
            available_models = []
            if "data" in data:
                available_models = [m.get("id", "") for m in data["data"]]
                if model:
                    model_loaded = model in available_models
                else:
                    model_loaded = len(available_models) > 0

            return HealthCheckResult(
                connected=True,
                latency_ms=latency_ms,
                model_loaded=model_loaded,
                backend=self.backend,
                endpoint=self.endpoint,
                details={
                    "status_code": response.status_code,
                    "available_models": available_models,
                }
            )
        except httpx.TimeoutException:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                connected=False,
                latency_ms=latency_ms,
                backend=self.backend,
                endpoint=self.endpoint,
                error="连接超时"
            )
        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                connected=True,
                latency_ms=latency_ms,
                backend=self.backend,
                endpoint=self.endpoint,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                connected=False,
                latency_ms=latency_ms,
                backend=self.backend,
                endpoint=self.endpoint,
                error=str(e)
            )

    async def infer(
        self,
        model: str,
        input_data: Union[str, List[str], List[Dict[str, Any]]],
        model_type: str = "text-generation",
        parameters: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """
        执行模型推理

        Args:
            model: 模型名称或 ID
            input_data: 输入数据
            model_type: 模型类型
            parameters: 推理参数

        Returns:
            InferenceResult
        """
        if not self.is_available():
            raise RuntimeError("Model inference service not configured. Please set MODEL_SERVING_ENDPOINT or OPENAI_API_KEY.")

        parameters = parameters or {}

        # 根据模型类型选择推理方式
        if model_type == "text-generation":
            return await self._text_generation(model, input_data, parameters)
        elif model_type == "text-classification":
            return await self._text_classification(model, input_data, parameters)
        elif model_type == "text2text-generation":
            return await self._text2text_generation(model, input_data, parameters)
        elif model_type == "embeddings":
            return await self._embeddings(model, input_data, parameters)
        else:
            return await self._generic_inference(model, input_data, model_type, parameters)

    async def infer_batch(
        self,
        model: str,
        inputs: List[Union[str, List[Dict[str, Any]]]],
        model_type: str = "text-generation",
        parameters: Optional[Dict[str, Any]] = None,
        batch_size: int = 8,
        max_concurrency: int = 4
    ) -> List[InferenceResult]:
        """
        批量执行模型推理

        将输入列表按 batch_size 分组，使用信号量控制并发数，
        异步并行处理每个输入并返回结果列表。

        Args:
            model: 模型名称或 ID
            inputs: 输入数据列表
            model_type: 模型类型
            parameters: 推理参数
            batch_size: 每批处理的输入数量
            max_concurrency: 最大并发请求数

        Returns:
            与 inputs 顺序对应的 InferenceResult 列表
        """
        if not inputs:
            return []

        parameters = parameters or {}
        semaphore = asyncio.Semaphore(max_concurrency)
        results: List[Optional[InferenceResult]] = [None] * len(inputs)

        async def _process_single(index: int, input_data: Union[str, List[Dict[str, Any]]]) -> None:
            async with semaphore:
                try:
                    result = await self.infer(model, input_data, model_type, parameters)
                    results[index] = result
                except Exception as e:
                    logger.error(f"批量推理第 {index} 项失败: {e}")
                    results[index] = InferenceResult(
                        output={"error": str(e)},
                        model=model,
                        backend=self.backend
                    )

        # 按 batch_size 分批处理
        for batch_start in range(0, len(inputs), batch_size):
            batch_end = min(batch_start + batch_size, len(inputs))
            batch_tasks = [
                _process_single(i, inputs[i])
                for i in range(batch_start, batch_end)
            ]
            await asyncio.gather(*batch_tasks)
            logger.info(f"批量推理进度: {batch_end}/{len(inputs)}")

        return results

    async def _text_generation(
        self,
        model: str,
        input_data: Union[str, List[str], List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """
        文本生成推理

        包含自动重试逻辑：对 429/500/502/503 状态码使用指数退避重试。
        重试次数和退避基数通过实例属性 max_retries / retry_backoff 配置。
        """
        import time
        start_time = time.time()

        # 准备消息格式
        messages = self._prepare_messages(input_data)

        # 选择端点
        endpoint = self._get_endpoint("chat/completions")

        # 准备请求体
        payload = {
            "model": model,
            "messages": messages,
            "temperature": parameters.get("temperature", 0.7),
            "max_tokens": parameters.get("max_tokens", parameters.get("max_new_tokens", 512)),
            "top_p": parameters.get("top_p", 0.9),
            "stream": False
        }

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    data = response.json()

                latency_ms = (time.time() - start_time) * 1000

                # 解析响应
                generated_text = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens")

                return InferenceResult(
                    output={"generated_text": generated_text},
                    model=model,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    backend=self.backend
                )
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"文本生成请求失败 (HTTP {e.response.status_code})，"
                        f"第 {attempt + 1}/{self.max_retries} 次重试，等待 {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"文本生成请求连接异常 ({type(e).__name__})，"
                        f"第 {attempt + 1}/{self.max_retries} 次重试，等待 {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

        # 所有重试用尽后抛出最后的异常
        raise last_exception

    async def _text_classification(
        self,
        model: str,
        input_data: Union[str, List[str]],
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """文本分类推理"""
        import time
        start_time = time.time()

        # 对于分类任务，使用 text2text 或零样本格式
        if isinstance(input_data, str):
            text = input_data
        else:
            text = input_data[0] if input_data else ""

        # 使用零样本分类提示
        messages = [{
            "role": "user",
            "content": f'Classify the sentiment of this text as "positive", "negative", or "neutral".\n\nText: {text}\n\nAnswer:'
        }]

        endpoint = self._get_endpoint("chat/completions")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 10,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.time() - start_time) * 1000

        result_text = data["choices"][0]["message"]["content"].strip().lower()

        # 解析结果
        labels = ["positive", "negative", "neutral"]
        scores = [0.1, 0.1, 0.1]

        for i, label in enumerate(labels):
            if label in result_text:
                scores[i] = 0.8

        # 归一化分数
        total = sum(scores)
        scores = [s / total for s in scores]

        return InferenceResult(
            output={"labels": labels, "scores": scores},
            model=model,
            latency_ms=latency_ms,
            backend=self.backend
        )

    async def _text2text_generation(
        self,
        model: str,
        input_data: Union[str, List[str]],
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """文本到文本生成推理（翻译、摘要等）"""
        import time
        start_time = time.time()

        if isinstance(input_data, str):
            text = input_data
        else:
            text = input_data[0] if input_data else ""

        messages = [{
            "role": "user",
            "content": text
        }]

        endpoint = self._get_endpoint("chat/completions")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": parameters.get("temperature", 0.3),
            "max_tokens": parameters.get("max_tokens", 256),
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.time() - start_time) * 1000

        generated_text = data["choices"][0]["message"]["content"]

        return InferenceResult(
            output={"generated_text": generated_text},
            model=model,
            latency_ms=latency_ms,
            backend=self.backend
        )

    async def _embeddings(
        self,
        model: str,
        input_data: Union[str, List[str]],
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """嵌入向量生成"""
        import time
        start_time = time.time()

        if isinstance(input_data, str):
            texts = [input_data]
        else:
            texts = input_data

        endpoint = self._get_endpoint("embeddings")

        payload = {
            "model": model,
            "input": texts
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.time() - start_time) * 1000

        return InferenceResult(
            output=data["data"],
            model=model,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            latency_ms=latency_ms,
            backend=self.backend
        )

    async def _generic_inference(
        self,
        model: str,
        input_data: Any,
        model_type: str,
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """通用推理接口"""
        import time
        start_time = time.time()

        # 尝试使用 completions 端点
        endpoint = self._get_endpoint("completions")

        payload = {
            "model": model,
            "prompt": str(input_data),
            "max_tokens": parameters.get("max_tokens", 128),
            "temperature": parameters.get("temperature", 0.7),
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            return InferenceResult(
                output=data,
                model=model,
                latency_ms=latency_ms,
                backend=self.backend
            )
        except Exception as e:
            # 如果失败，返回格式化的错误
            return InferenceResult(
                output={"error": str(e), "output": f"Unable to process model type: {model_type}"},
                model=model,
                latency_ms=(time.time() - start_time) * 1000,
                backend=self.backend
            )

    async def stream_generate(
        self,
        model: str,
        input_data: Union[str, List[str], List[Dict[str, Any]]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        流式文本生成（异步生成器）

        连接 OpenAI 兼容 API 的 SSE 流式端点，逐 token 返回生成内容。
        每次 yield 一个部分 token 字符串；流结束时自动退出。

        Args:
            model: 模型名称或 ID
            input_data: 输入数据（字符串、字符串列表或消息列表）
            parameters: 推理参数（temperature, max_tokens, top_p 等）

        Yields:
            str: 每次生成的部分 token 文本
        """
        if not self.is_available():
            raise RuntimeError("Model inference service not configured. Please set MODEL_SERVING_ENDPOINT or OPENAI_API_KEY.")

        parameters = parameters or {}
        messages = self._prepare_messages(input_data)
        endpoint = self._get_endpoint("chat/completions")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": parameters.get("temperature", 0.7),
            "max_tokens": parameters.get("max_tokens", parameters.get("max_new_tokens", 512)),
            "top_p": parameters.get("top_p", 0.9),
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                endpoint,
                json=payload,
                headers=self._get_headers()
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    # SSE 格式：以 "data: " 开头
                    if not line.startswith("data: "):
                        continue

                    data_str = line[len("data: "):]

                    # 流结束标记
                    if data_str.strip() == "[DONE]":
                        return

                    try:
                        import json
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (ValueError, KeyError, IndexError) as e:
                        logger.debug(f"跳过无法解析的 SSE 数据块: {e}")
                        continue

    def _prepare_messages(
        self,
        input_data: Union[str, List[str], List[Dict[str, Any]]]
    ) -> List[Dict[str, str]]:
        """准备聊天消息格式"""
        if isinstance(input_data, str):
            return [{"role": "user", "content": input_data}]
        elif isinstance(input_data, list) and input_data:
            if isinstance(input_data[0], dict):
                # 已经是消息格式
                return input_data
            else:
                # 是字符串列表
                return [{"role": "user", "content": str(text)} for text in input_data]
        else:
            return [{"role": "user", "content": ""}]

    def _get_endpoint(self, path: str) -> str:
        """获取完整的 API 端点"""
        if self.endpoint:
            base = self.endpoint.rstrip("/")
            return f"{base}/v1/{path}"
        else:
            # 使用 OpenAI
            return f"{self.openai_base_url.rstrip('/')}/{path}"

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }

        # 使用可用的 API 密钥
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        return headers


# 全局实例
_inference_service: Optional[ModelInferenceService] = None


def get_inference_service() -> ModelInferenceService:
    """获取全局推理服务实例"""
    global _inference_service
    if _inference_service is None:
        _inference_service = ModelInferenceService()
    return _inference_service
