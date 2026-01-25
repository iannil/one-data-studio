"""
模型推理服务
支持多种推理后端：vLLM, TGI, Triton, OpenAI兼容API
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
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
        timeout: float = 120.0
    ):
        """
        初始化推理服务

        Args:
            endpoint: 推理服务端点 URL
            api_key: API 密钥
            backend: 推理后端类型 (vllm, tgi, openai, custom, auto)
            timeout: 请求超时时间（秒）
        """
        self.endpoint = endpoint or os.getenv("MODEL_SERVING_ENDPOINT", "")
        self.api_key = api_key or os.getenv("MODEL_SERVING_API_KEY", "")
        self.backend = backend
        self.timeout = timeout

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

    async def _text_generation(
        self,
        model: str,
        input_data: Union[str, List[str], List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> InferenceResult:
        """文本生成推理"""
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
