"""
视觉嵌入服务
Sprint 15: 多模态支持 - CLIP 视觉嵌入

使用 CLIP 模型生成图片的向量嵌入，支持多模态检索
"""

import logging
from typing import Optional, List, Union, Dict, Any
from dataclasses import dataclass
import io
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VisionEmbeddingResult:
    """视觉嵌入结果"""
    embedding: List[float]
    model: str
    dimension: int
    image_hash: str


@dataclass
class MultimodalSearchResult:
    """多模态搜索结果"""
    id: str
    score: float
    content_type: str  # 'text' or 'image'
    content: str  # 文本内容或图片 URL
    metadata: Dict[str, Any]


class VisionEmbeddingService:
    """
    视觉嵌入服务

    Sprint 15: 多模态支持

    使用 CLIP 模型生成图片向量嵌入，支持:
    - 图片到向量嵌入
    - 文本到向量嵌入（用于图片搜索）
    - 图文混合检索
    """

    # 支持的模型
    SUPPORTED_MODELS = {
        'clip-vit-base-patch32': {
            'name': 'openai/clip-vit-base-patch32',
            'dimension': 512,
            'description': 'CLIP ViT-B/32 - 快速，适合一般用途'
        },
        'clip-vit-large-patch14': {
            'name': 'openai/clip-vit-large-patch14',
            'dimension': 768,
            'description': 'CLIP ViT-L/14 - 更高精度'
        },
        'chinese-clip-vit-base': {
            'name': 'OFA-Sys/chinese-clip-vit-base-patch16',
            'dimension': 512,
            'description': 'Chinese-CLIP - 支持中文'
        }
    }

    DEFAULT_MODEL = 'clip-vit-base-patch32'

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        use_cpu_fallback: bool = True
    ):
        """
        初始化视觉嵌入服务

        Args:
            model_name: 模型名称
            device: 设备 ('cuda', 'cpu', 'mps')
            use_cpu_fallback: GPU 不可用时是否回退到 CPU
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_cpu_fallback = use_cpu_fallback

        # 延迟加载模型
        self._model = None
        self._processor = None
        self._tokenizer = None
        self._device = device

        # 验证模型名称
        if self.model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {self.model_name}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        self._model_config = self.SUPPORTED_MODELS[self.model_name]

    @property
    def dimension(self) -> int:
        """返回嵌入维度"""
        return self._model_config['dimension']

    @property
    def device(self) -> str:
        """获取当前设备"""
        if self._device is None:
            self._device = self._detect_device()
        return self._device

    def _detect_device(self) -> str:
        """检测可用设备"""
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'
            else:
                return 'cpu'
        except ImportError:
            return 'cpu'

    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return

        try:
            from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
            import torch
        except ImportError:
            raise ImportError(
                "transformers and torch are required for vision embedding. "
                "Install with: pip install transformers torch"
            )

        model_id = self._model_config['name']
        logger.info(f"Loading vision model: {model_id} on {self.device}")

        try:
            self._model = CLIPModel.from_pretrained(model_id)
            self._processor = CLIPProcessor.from_pretrained(model_id)
            self._tokenizer = CLIPTokenizer.from_pretrained(model_id)

            # 移动到设备
            if self.device != 'cpu':
                try:
                    self._model = self._model.to(self.device)
                except Exception as e:
                    if self.use_cpu_fallback:
                        logger.warning(f"Failed to use {self.device}, falling back to CPU: {e}")
                        self._device = 'cpu'
                    else:
                        raise

            # 设置为评估模式
            self._model.eval()

            logger.info(f"Vision model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load vision model: {e}")
            raise

    def embed_image(
        self,
        image_data: bytes,
        normalize: bool = True
    ) -> VisionEmbeddingResult:
        """
        生成图片嵌入向量

        Args:
            image_data: 图片二进制数据
            normalize: 是否归一化向量

        Returns:
            VisionEmbeddingResult
        """
        self._load_model()

        try:
            from PIL import Image
            import torch
            import hashlib
        except ImportError:
            raise ImportError("PIL and torch are required")

        # 计算图片哈希
        image_hash = hashlib.md5(image_data).hexdigest()

        # 打开图片
        img = Image.open(io.BytesIO(image_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 处理图片
        inputs = self._processor(images=img, return_tensors="pt")

        # 移动到设备
        if self.device != 'cpu':
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 生成嵌入
        with torch.no_grad():
            image_features = self._model.get_image_features(**inputs)

        # 归一化
        if normalize:
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        # 转换为列表
        embedding = image_features.cpu().numpy().flatten().tolist()

        return VisionEmbeddingResult(
            embedding=embedding,
            model=self.model_name,
            dimension=len(embedding),
            image_hash=image_hash
        )

    def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> List[float]:
        """
        生成文本嵌入向量（用于图片搜索）

        Args:
            text: 搜索文本
            normalize: 是否归一化向量

        Returns:
            嵌入向量列表
        """
        self._load_model()

        try:
            import torch
        except ImportError:
            raise ImportError("torch is required")

        # 处理文本
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77  # CLIP 最大长度
        )

        # 移动到设备
        if self.device != 'cpu':
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 生成嵌入
        with torch.no_grad():
            text_features = self._model.get_text_features(**inputs)

        # 归一化
        if normalize:
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy().flatten().tolist()

    def embed_batch_images(
        self,
        images_data: List[bytes],
        normalize: bool = True,
        batch_size: int = 32
    ) -> List[VisionEmbeddingResult]:
        """
        批量生成图片嵌入

        Args:
            images_data: 图片数据列表
            normalize: 是否归一化
            batch_size: 批处理大小

        Returns:
            VisionEmbeddingResult 列表
        """
        self._load_model()

        try:
            from PIL import Image
            import torch
            import hashlib
        except ImportError:
            raise ImportError("PIL and torch are required")

        results = []

        for i in range(0, len(images_data), batch_size):
            batch = images_data[i:i + batch_size]

            # 准备图片
            images = []
            hashes = []
            for img_data in batch:
                hashes.append(hashlib.md5(img_data).hexdigest())
                img = Image.open(io.BytesIO(img_data))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)

            # 处理
            inputs = self._processor(images=images, return_tensors="pt", padding=True)

            if self.device != 'cpu':
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 生成嵌入
            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)

            if normalize:
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # 转换结果
            embeddings = image_features.cpu().numpy()
            for j, (embedding, img_hash) in enumerate(zip(embeddings, hashes)):
                results.append(VisionEmbeddingResult(
                    embedding=embedding.tolist(),
                    model=self.model_name,
                    dimension=len(embedding),
                    image_hash=img_hash
                ))

            logger.debug(f"Processed batch {i // batch_size + 1}, images: {len(batch)}")

        return results

    def compute_similarity(
        self,
        image_embedding: List[float],
        text_embedding: List[float]
    ) -> float:
        """
        计算图文相似度

        Args:
            image_embedding: 图片嵌入
            text_embedding: 文本嵌入

        Returns:
            相似度分数 (0-1)
        """
        # 余弦相似度
        img_vec = np.array(image_embedding)
        txt_vec = np.array(text_embedding)

        similarity = np.dot(img_vec, txt_vec) / (np.linalg.norm(img_vec) * np.linalg.norm(txt_vec))

        # 转换到 0-1 范围
        return float((similarity + 1) / 2)


class MultimodalRetriever:
    """
    多模态检索器

    Sprint 15: 支持文本+图片混合检索
    """

    def __init__(
        self,
        vision_service: VisionEmbeddingService = None,
        vector_store_client = None,
        text_collection: str = "documents",
        image_collection: str = "images"
    ):
        """
        初始化多模态检索器

        Args:
            vision_service: 视觉嵌入服务
            vector_store_client: 向量存储客户端
            text_collection: 文本向量集合名
            image_collection: 图片向量集合名
        """
        self.vision = vision_service or VisionEmbeddingService()
        self.vector_store = vector_store_client
        self.text_collection = text_collection
        self.image_collection = image_collection

        # 确保图片向量集合存在（使用正确的CLIP维度）
        self._ensure_image_collection()

    def _ensure_image_collection(self):
        """确保图片向量集合存在且使用正确的维度"""
        if self.vector_store is None:
            return

        try:
            from pymilvus import utility

            # 检查集合是否存在
            if not utility.has_collection(self.image_collection):
                # 使用CLIP模型的维度创建集合
                self.vector_store.create_collection(
                    name=self.image_collection,
                    dimension=self.vision.dimension,
                    drop_existing=False
                )
                logger.info(f"Created image collection '{self.image_collection}' with dimension {self.vision.dimension}")
        except Exception as e:
            logger.error(f"Failed to ensure image collection: {e}")

    def search(
        self,
        query: str,
        top_k: int = 10,
        include_text: bool = True,
        include_images: bool = True,
        text_weight: float = 0.5,
        image_weight: float = 0.5
    ) -> List[MultimodalSearchResult]:
        """
        多模态搜索

        Args:
            query: 查询文本
            top_k: 返回结果数
            include_text: 是否搜索文本
            include_images: 是否搜索图片
            text_weight: 文本结果权重
            image_weight: 图片结果权重

        Returns:
            排序后的搜索结果
        """
        results = []

        if include_text and self.vector_store:
            # 使用文本嵌入搜索文档
            text_results = self._search_text(query, top_k)
            for r in text_results:
                r['score'] *= text_weight
            results.extend(text_results)

        if include_images and self.vector_store:
            # 使用视觉嵌入搜索图片
            image_results = self._search_images(query, top_k)
            for r in image_results:
                r['score'] *= image_weight
            results.extend(image_results)

        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)

        # 转换为结果对象
        return [
            MultimodalSearchResult(
                id=r['id'],
                score=r['score'],
                content_type=r['type'],
                content=r['content'],
                metadata=r.get('metadata', {})
            )
            for r in results[:top_k]
        ]

    def _search_text(self, query: str, top_k: int) -> List[Dict]:
        """
        搜索文本

        使用文本嵌入在文档向量集合中搜索相关内容

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            搜索结果列表，每个结果包含 id, score, type, content, metadata
        """
        if self.vector_store is None:
            logger.warning("Vector store not configured for text search")
            return []

        try:
            # 生成查询文本的嵌入向量
            query_embedding = self.vision.embed_text(query)

            # 在文本向量集合中搜索
            search_result = self.vector_store.search(
                collection_name=self.text_collection,
                query_embedding=query_embedding,
                top_k=top_k,
                output_fields=["text", "metadata"]
            )

            # 转换结果格式
            results = []
            for item in search_result.get("results", []):
                metadata = item.get("metadata", {})
                results.append({
                    "id": item.get("id", ""),
                    "score": item.get("score", 0.0),
                    "type": "text",
                    "content": item.get("text", ""),
                    "metadata": metadata
                })

            logger.debug(f"Text search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []

    def _search_images(self, query: str, top_k: int) -> List[Dict]:
        """
        搜索图片

        使用视觉嵌入在图片向量集合中搜索相关图片

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            搜索结果列表，每个结果包含 id, score, type, content, metadata
        """
        if self.vector_store is None:
            logger.warning("Vector store not configured for image search")
            return []

        try:
            # 生成查询文本的视觉嵌入向量（CLIP支持图文跨模态检索）
            query_embedding = self.vision.embed_text(query)

            # 在图片向量集合中搜索
            search_result = self.vector_store.search(
                collection_name=self.image_collection,
                query_embedding=query_embedding,
                top_k=top_k,
                output_fields=["text", "metadata"]
            )

            # 转换结果格式
            results = []
            for item in search_result.get("results", []):
                metadata = item.get("metadata", {})
                # 从 metadata 中提取图片 URL 或路径
                image_url = metadata.get("url") or metadata.get("path") or item.get("text", "")
                results.append({
                    "id": item.get("id", ""),
                    "score": item.get("score", 0.0),
                    "type": "image",
                    "content": image_url,
                    "metadata": metadata
                })

            logger.debug(f"Image search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []

    def index_image(
        self,
        image_id: str,
        image_data: bytes,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        索引图片

        生成图片的视觉嵌入并存储到向量数据库中

        Args:
            image_id: 图片 ID（用作文档标识）
            image_data: 图片二进制数据
            metadata: 元数据（可包含 url, path, caption, tags 等信息）

        Returns:
            是否成功
        """
        if self.vector_store is None:
            logger.warning("Vector store not configured for image indexing")
            return False

        try:
            # 生成图片嵌入向量
            embed_result = self.vision.embed_image(image_data)

            # 准备元数据，包含图片 ID 和原始元数据
            enhanced_metadata = {
                "doc_id": image_id,
                "image_hash": embed_result.image_hash,
                "model": embed_result.model,
                **(metadata or {})
            }

            # 准备文本描述（用于结果显示）
            text_description = metadata.get("caption") or metadata.get("description") or ""

            # 存储到向量数据库
            # 注意：需要使用正确的图片向量维度（CLIP模型可能需要创建新集合）
            count = self.vector_store.insert(
                collection_name=self.image_collection,
                texts=[text_description],
                embeddings=[embed_result.embedding],
                metadata=[enhanced_metadata]
            )

            logger.info(f"Indexed image: {image_id}, embedding dimension: {embed_result.dimension}")
            return count > 0

        except Exception as e:
            logger.error(f"Failed to index image {image_id}: {e}")
            return False


# 全局实例
_vision_service: Optional[VisionEmbeddingService] = None


def get_vision_service() -> VisionEmbeddingService:
    """获取全局视觉嵌入服务实例"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionEmbeddingService()
    return _vision_service
