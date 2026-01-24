"""
Hugging Face Hub 集成服务

提供与 Hugging Face Hub 的集成功能：
- 模型搜索与发现
- 模型下载与缓存
- 模型信息获取
- 模型卡片解析
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from functools import lru_cache
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    author: str
    model_name: str
    sha: str
    last_modified: datetime
    private: bool
    pipeline_tag: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    likes: int = 0
    library_name: Optional[str] = None
    language: Optional[List[str]] = None
    license: Optional[str] = None
    card_data: Optional[Dict[str, Any]] = None


@dataclass
class DatasetInfo:
    """数据集信息"""
    id: str
    author: str
    dataset_name: str
    sha: str
    last_modified: datetime
    private: bool
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    likes: int = 0
    card_data: Optional[Dict[str, Any]] = None


class HuggingFaceService:
    """Hugging Face Hub 服务"""

    HF_API_URL = "https://huggingface.co/api"

    def __init__(
        self,
        token: Optional[str] = None,
        cache_dir: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化 Hugging Face 服务

        Args:
            token: Hugging Face API token (可选，用于访问私有模型)
            cache_dir: 模型缓存目录
            timeout: HTTP 请求超时时间
        """
        self.token = token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        self.cache_dir = cache_dir or os.getenv("HF_HOME", "/root/.cache/huggingface")
        self.timeout = timeout

        self._headers = {}
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

    async def search_models(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        filter_tags: Optional[List[str]] = None,
        pipeline_tag: Optional[str] = None,
        library: Optional[str] = None,
        language: Optional[str] = None,
        sort: str = "downloads",
        direction: str = "-1",
        limit: int = 20,
        offset: int = 0
    ) -> List[ModelInfo]:
        """
        搜索模型

        Args:
            query: 搜索关键词
            author: 作者/组织过滤
            filter_tags: 标签过滤
            pipeline_tag: Pipeline 类型 (text-generation, text-classification, etc.)
            library: 库过滤 (transformers, pytorch, tensorflow, etc.)
            language: 语言过滤
            sort: 排序字段 (downloads, likes, lastModified)
            direction: 排序方向 (-1 降序, 1 升序)
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            模型信息列表
        """
        params = {
            "sort": sort,
            "direction": direction,
            "limit": limit,
            "skip": offset,
        }

        if query:
            params["search"] = query
        if author:
            params["author"] = author
        if filter_tags:
            params["filter"] = ",".join(filter_tags)
        if pipeline_tag:
            params["pipeline_tag"] = pipeline_tag
        if library:
            params["library"] = library
        if language:
            params["language"] = language

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.HF_API_URL}/models",
                params=params,
                headers=self._headers
            )
            response.raise_for_status()

            models = []
            for item in response.json():
                models.append(self._parse_model_info(item))

            return models

    async def get_model_info(self, model_id: str) -> ModelInfo:
        """
        获取模型详细信息

        Args:
            model_id: 模型 ID (例如: meta-llama/Llama-2-7b-chat-hf)

        Returns:
            模型信息
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.HF_API_URL}/models/{model_id}",
                headers=self._headers
            )
            response.raise_for_status()
            return self._parse_model_info(response.json())

    async def get_model_card(self, model_id: str) -> str:
        """
        获取模型卡片 (README.md)

        Args:
            model_id: 模型 ID

        Returns:
            模型卡片内容 (Markdown)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"https://huggingface.co/{model_id}/raw/main/README.md",
                headers=self._headers
            )
            response.raise_for_status()
            return response.text

    async def search_datasets(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        filter_tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        sort: str = "downloads",
        direction: str = "-1",
        limit: int = 20,
        offset: int = 0
    ) -> List[DatasetInfo]:
        """
        搜索数据集

        Args:
            query: 搜索关键词
            author: 作者/组织过滤
            filter_tags: 标签过滤
            language: 语言过滤
            sort: 排序字段
            direction: 排序方向
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            数据集信息列表
        """
        params = {
            "sort": sort,
            "direction": direction,
            "limit": limit,
            "skip": offset,
        }

        if query:
            params["search"] = query
        if author:
            params["author"] = author
        if filter_tags:
            params["filter"] = ",".join(filter_tags)
        if language:
            params["language"] = language

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.HF_API_URL}/datasets",
                params=params,
                headers=self._headers
            )
            response.raise_for_status()

            datasets = []
            for item in response.json():
                datasets.append(self._parse_dataset_info(item))

            return datasets

    async def get_dataset_info(self, dataset_id: str) -> DatasetInfo:
        """
        获取数据集详细信息

        Args:
            dataset_id: 数据集 ID

        Returns:
            数据集信息
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.HF_API_URL}/datasets/{dataset_id}",
                headers=self._headers
            )
            response.raise_for_status()
            return self._parse_dataset_info(response.json())

    async def list_model_files(self, model_id: str, revision: str = "main") -> List[Dict[str, Any]]:
        """
        列出模型文件

        Args:
            model_id: 模型 ID
            revision: 版本/分支

        Returns:
            文件列表
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.HF_API_URL}/models/{model_id}/tree/{revision}",
                headers=self._headers
            )
            response.raise_for_status()
            return response.json()

    async def get_pipeline_tags(self) -> List[str]:
        """
        获取所有可用的 Pipeline 标签

        Returns:
            Pipeline 标签列表
        """
        # 常见的 pipeline 标签
        return [
            "text-generation",
            "text-classification",
            "text2text-generation",
            "token-classification",
            "question-answering",
            "fill-mask",
            "summarization",
            "translation",
            "conversational",
            "feature-extraction",
            "sentence-similarity",
            "zero-shot-classification",
            "image-classification",
            "object-detection",
            "image-segmentation",
            "image-to-text",
            "text-to-image",
            "text-to-speech",
            "automatic-speech-recognition",
            "audio-classification",
            "reinforcement-learning",
            "tabular-classification",
            "tabular-regression",
        ]

    async def get_popular_models(
        self,
        pipeline_tag: Optional[str] = None,
        limit: int = 10
    ) -> List[ModelInfo]:
        """
        获取热门模型

        Args:
            pipeline_tag: Pipeline 类型过滤
            limit: 返回数量

        Returns:
            热门模型列表
        """
        return await self.search_models(
            pipeline_tag=pipeline_tag,
            sort="downloads",
            direction="-1",
            limit=limit
        )

    async def get_trending_models(self, limit: int = 10) -> List[ModelInfo]:
        """
        获取趋势模型 (按最近更新排序)

        Args:
            limit: 返回数量

        Returns:
            趋势模型列表
        """
        return await self.search_models(
            sort="lastModified",
            direction="-1",
            limit=limit
        )

    def _parse_model_info(self, data: Dict[str, Any]) -> ModelInfo:
        """解析模型信息"""
        model_id = data.get("id", data.get("modelId", ""))
        parts = model_id.split("/", 1)

        return ModelInfo(
            id=model_id,
            author=parts[0] if len(parts) > 1 else "",
            model_name=parts[1] if len(parts) > 1 else parts[0],
            sha=data.get("sha", ""),
            last_modified=datetime.fromisoformat(
                data.get("lastModified", "").replace("Z", "+00:00")
            ) if data.get("lastModified") else datetime.now(),
            private=data.get("private", False),
            pipeline_tag=data.get("pipeline_tag"),
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            likes=data.get("likes", 0),
            library_name=data.get("library_name"),
            language=data.get("language"),
            license=data.get("license"),
            card_data=data.get("cardData"),
        )

    def _parse_dataset_info(self, data: Dict[str, Any]) -> DatasetInfo:
        """解析数据集信息"""
        dataset_id = data.get("id", data.get("datasetId", ""))
        parts = dataset_id.split("/", 1)

        return DatasetInfo(
            id=dataset_id,
            author=parts[0] if len(parts) > 1 else "",
            dataset_name=parts[1] if len(parts) > 1 else parts[0],
            sha=data.get("sha", ""),
            last_modified=datetime.fromisoformat(
                data.get("lastModified", "").replace("Z", "+00:00")
            ) if data.get("lastModified") else datetime.now(),
            private=data.get("private", False),
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            likes=data.get("likes", 0),
            card_data=data.get("cardData"),
        )


# 单例服务
_hf_service: Optional[HuggingFaceService] = None


def get_huggingface_service() -> HuggingFaceService:
    """获取 Hugging Face 服务单例"""
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFaceService()
    return _hf_service


# 便捷函数
async def search_hf_models(query: str, **kwargs) -> List[ModelInfo]:
    """搜索 Hugging Face 模型"""
    service = get_huggingface_service()
    return await service.search_models(query=query, **kwargs)


async def get_hf_model(model_id: str) -> ModelInfo:
    """获取 Hugging Face 模型信息"""
    service = get_huggingface_service()
    return await service.get_model_info(model_id)
