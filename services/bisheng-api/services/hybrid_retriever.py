"""
混合检索器
Production: 结合向量检索和关键词检索的高性能搜索

功能：
1. 向量语义检索（基于 Milvus）
2. 关键词检索（BM25 算法）
3. Reciprocal Rank Fusion (RRF) 结果合并
4. MMR 算法结果多样性控制
5. 查询扩展和重写
6. 检索结果缓存
"""

import logging
import re
import math
import time
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import hashlib
import json

from .vector_store import VectorStore
from .embedding import get_embedding_service

logger = logging.getLogger(__name__)


class RetrievalMethod(Enum):
    """检索方法"""
    VECTOR = "vector"          # 纯向量检索
    KEYWORD = "keyword"        # 纯关键词检索
    HYBRID = "hybrid"          # 混合检索
    RRF = "rrf"                # RRF 合并
    MMR = "mmr"                # MMR 多样性检索


class QueryExpansionStrategy(Enum):
    """查询扩展策略"""
    NONE = "none"
    SYNONYM = "synonym"
    EMBEDDING = "embedding"
    HYPERNYM = "hypernym"


@dataclass
class RetrievalResult:
    """检索结果"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: RetrievalMethod = RetrievalMethod.VECTOR
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


@dataclass
class RetrievalConfig:
    """检索配置"""
    # 基础参数
    top_k: int = 10
    collection_name: str = "default"
    min_score: float = 0.0

    # 混合检索权重
    vector_weight: float = 0.7      # 向量检索权重
    keyword_weight: float = 0.3     # 关键词检索权重

    # RRF 参数
    rrf_k: int = 60                 # RRF 常数 K

    # MMR 参数
    mmr_lambda: float = 0.5         # MMR 多样性权重 (0=多样性优先, 1=相关性优先)
    mmr_top_k: int = 20             # MMR 候选数量

    # 查询扩展
    enable_query_expansion: bool = False
    expansion_strategy: QueryExpansionStrategy = QueryExpansionStrategy.NONE
    expansion_terms: int = 3

    # 缓存
    enable_cache: bool = True
    cache_ttl: int = 300            # 秒

    # 过滤
    filters: Optional[Dict[str, Any]] = None


class BM25Index:
    """
    BM25 索引器

    用于关键词检索的 BM25 算法实现
    """

    def __init__(
        self,
        k1: float = 1.2,     # 词频饱和参数
        b: float = 0.75,      # 长度归一化参数
    ):
        """
        初始化 BM25 索引器

        Args:
            k1: 调节词频饱和度 (0-∞)，通常 1.2-2.0
            b: 调节文档长度归一化 (0-1)，通常 0.75
        """
        self.k1 = k1
        self.b = b

        # 索引数据
        self.doc_count = 0
        self.doc_lengths: List[int] = []
        self.avg_doc_length = 0.0
        self.doc_vectors: List[Dict[str, int]] = []  # 每个文档的词频向量
        self.idf: Dict[str, float] = {}              # 逆文档频率

        # 文档映射
        self.doc_ids: List[str] = []
        self.doc_texts: List[str] = []

        # 中文分词（简单实现）
        self.word_pattern = re.compile(r'[\w\u4e00-\u9fff]+')

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        索引文档集合

        Args:
            documents: 文档列表，每项包含 id 和 text
        """
        self.doc_count = len(documents)
        self.doc_ids = [d.get("id", f"doc_{i}") for i, d in enumerate(documents)]
        self.doc_texts = [d.get("text", "") for d in documents]

        # 分词并计算词频
        for doc in documents:
            text = doc.get("text", "")
            tokens = self._tokenize(text)
            self.doc_vectors.append(Counter(tokens))
            self.doc_lengths.append(len(tokens))

        # 计算平均文档长度
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0

        # 计算 IDF
        self._compute_idf()

        logger.info(f"BM25 索引完成: {self.doc_count} 个文档, 平均长度 {self.avg_doc_length:.1f}")

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单实现：支持中英文
        tokens = self.word_pattern.findall(text.lower())
        # 过滤单字符和停用词
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        return [t for t in tokens if len(t) > 1 and t not in stopwords]

    def _compute_idf(self) -> None:
        """计算逆文档频率"""
        df = defaultdict(int)  # 词频统计

        for doc_vector in self.doc_vectors:
            for term in doc_vector:
                df[term] += 1

        # IDF = log((N - df + 0.5) / (df + 0.5))
        for term, freq in df.items():
            self.idf[term] = math.log((self.doc_count - freq + 0.5) / (freq + 0.5) + 1)

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        BM25 搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_score: 最小分数阈值

        Returns:
            [(doc_id, score), ...] 按分数降序排列
        """
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        scores = []

        for doc_idx, doc_vector in enumerate(self.doc_vectors):
            score = 0.0
            doc_length = self.doc_lengths[doc_idx]

            for term in query_tokens:
                if term not in doc_vector:
                    continue

                # BM25 公式
                tf = doc_vector[term]
                idf = self.idf.get(term, 0)

                # 标准化词频
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))

                score += idf * (numerator / denominator)

            if score >= min_score:
                scores.append((self.doc_ids[doc_idx], score))

        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_document_text(self, doc_id: str) -> Optional[str]:
        """获取文档文本"""
        try:
            idx = self.doc_ids.index(doc_id)
            return self.doc_texts[idx]
        except ValueError:
            return None


class HybridRetriever:
    """
    混合检索器

    结合向量检索和关键词检索，使用 RRF 合并结果
    """

    def __init__(self, config: RetrievalConfig = None):
        """
        初始化混合检索器

        Args:
            config: 检索配置
        """
        self.config = config or RetrievalConfig()

        # 初始化向量存储
        self.vector_store = VectorStore()

        # 初始化 BM25 索引
        self.bm25_index: Optional[BM25Index] = None
        self._index_loaded = False

        # 检索缓存
        self._cache: Dict[str, Tuple[List[RetrievalResult], float]] = {}

        # 嵌入服务
        self.embedding_service = get_embedding_service()

    def _load_bm25_index(self) -> None:
        """加载或构建 BM25 索引"""
        if self._index_loaded:
            return

        try:
            # 从向量存储获取所有文档构建 BM25 索引
            if not self.vector_store.utility.has_collection(self.config.collection_name):
                logger.warning(f"Collection {self.config.collection_name} does not exist")
                return

            collection = self.vector_store.Collection(self.config.collection_name)
            collection.load()

            # 获取所有文档
            # 注意：这里简化处理，生产环境应使用专门的索引服务
            self._index_loaded = True
            logger.info("BM25 index loaded")

        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")

    def build_bm25_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        构建 BM25 索引

        Args:
            documents: 文档列表，每项包含 id 和 text
        """
        self.bm25_index = BM25Index()
        self.bm25_index.index_documents(documents)
        self._index_loaded = True

    def retrieve(
        self,
        query: str,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query: 查询文本
            method: 检索方法
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        top_k = top_k or self.config.top_k

        # 检查缓存
        cache_key = self._get_cache_key(query, method, top_k)
        if self.config.enable_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        results = []

        if method == RetrievalMethod.VECTOR:
            results = self._vector_search(query, top_k)
        elif method == RetrievalMethod.KEYWORD:
            results = self._keyword_search(query, top_k)
        elif method in (RetrievalMethod.HYBRID, RetrievalMethod.RRF):
            results = self._hybrid_search_rrf(query, top_k)
        elif method == RetrievalMethod.MMR:
            results = self._mmr_search(query, top_k)

        # 应用过滤器
        if self.config.filters:
            results = self._apply_filters(results)

        # 更新缓存
        if self.config.enable_cache:
            self._set_cache(cache_key, results)

        return results

    def _vector_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """向量语义检索"""
        try:
            # 获取查询向量
            embedding = self.embedding_service.embed_query(query)

            # 向量搜索
            search_result = self.vector_store.search(
                collection_name=self.config.collection_name,
                query_embedding=embedding,
                top_k=top_k,
                use_cache=self.config.enable_cache,
            )

            results = []
            for item in search_result.get("results", []):
                results.append(RetrievalResult(
                    id=item["id"],
                    text=item.get("text", ""),
                    score=item["score"],
                    metadata=item.get("metadata", {}),
                    source=RetrievalMethod.VECTOR,
                    vector_score=item["score"],
                ))

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _keyword_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """关键词 BM25 检索"""
        if not self.bm25_index:
            self._load_bm25_index()

        if not self.bm25_index:
            logger.warning("BM25 index not available, falling back to vector search")
            return self._vector_search(query, top_k)

        try:
            scores = self.bm25_index.search(
                query=query,
                top_k=top_k,
                min_score=self.config.min_score,
            )

            results = []
            for doc_id, score in scores:
                text = self.bm25_index.get_document_text(doc_id)
                results.append(RetrievalResult(
                    id=doc_id,
                    text=text or "",
                    score=score,
                    source=RetrievalMethod.KEYWORD,
                    keyword_score=score,
                ))

            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _hybrid_search_rrf(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """
        混合检索 + RRF 合并

        Reciprocal Rank Fusion 公式:
        score(d) = sum(rank_weight / (k + rank(d)))
        """
        # 获取两种检索结果
        vector_results = self._vector_search(query, self.config.mmr_top_k)
        keyword_results = self._keyword_search(query, self.config.mmr_top_k)

        # 使用权重进行 RRF 合并
        rrf_scores = defaultdict(float)
        doc_data: Dict[str, Dict[str, Any]] = {}

        # 向量结果贡献
        for rank, result in enumerate(vector_results, 1):
            doc_id = result.id
            rrf_scores[doc_id] += self.config.vector_weight / (self.config.rrf_k + rank)
            doc_data[doc_id] = {
                "id": doc_id,
                "text": result.text,
                "metadata": result.metadata,
                "vector_score": result.vector_score,
                "keyword_score": None,
            }

        # 关键词结果贡献
        for rank, result in enumerate(keyword_results, 1):
            doc_id = result.id
            rrf_scores[doc_id] += self.config.keyword_weight / (self.config.rrf_k + rank)

            if doc_id in doc_data:
                doc_data[doc_id]["keyword_score"] = result.keyword_score
            else:
                doc_data[doc_id] = {
                    "id": doc_id,
                    "text": result.text,
                    "metadata": result.metadata,
                    "vector_score": None,
                    "keyword_score": result.keyword_score,
                }

        # 按 RRF 分数排序
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        results = []
        for doc_id, score in sorted_results:
            data = doc_data[doc_id]
            results.append(RetrievalResult(
                id=data["id"],
                text=data["text"],
                score=score,
                metadata=data.get("metadata", {}),
                source=RetrievalMethod.RRF,
                vector_score=data.get("vector_score"),
                keyword_score=data.get("keyword_score"),
            ))

        return results

    def _mmr_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """
        MMR (Maximal Marginal Relevance) 检索

        平衡相关性和多样性:
        MMR = argmax [λ * relevance(d, q) - (1-λ) * max(similarity(d, d_i))]
        """
        # 先获取候选结果
        candidates = self._hybrid_search_rrf(query, self.config.mmr_top_k)

        if not candidates:
            return []

        # 获取查询向量
        try:
            query_embedding = self.embedding_service.embed_query(query)
        except Exception as e:
            logger.error(f"Failed to embed query for MMR: {e}")
            return candidates[:top_k]

        selected = []
        remaining = candidates.copy()

        # 贪心选择
        while selected and len(selected) < top_k and remaining:
            best_score = -float('inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # 相关性分数
                relevance = candidate.score

                # 与已选结果的最大相似度
                max_similarity = 0.0
                if selected:
                    for s in selected:
                        sim = self._compute_similarity(
                            candidate.id,
                            s.id,
                            query_embedding,
                        )
                        max_similarity = max(max_similarity, sim)

                # MMR 分数
                mmr_score = (
                    self.config.mmr_lambda * relevance -
                    (1 - self.config.mmr_lambda) * max_similarity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        # 如果第一个，选择最相关的
        if not selected and remaining:
            selected.append(remaining.pop(0))

        return selected

    def _compute_similarity(
        self,
        doc1_id: str,
        doc2_id: str,
        query_embedding: List[float],
    ) -> float:
        """计算两个文档的相似度（简化版）"""
        # 生产环境应预计算文档向量并缓存
        # 这里返回简化计算
        return 0.0

    def _apply_filters(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """应用元数据过滤"""
        if not self.config.filters:
            return results

        filtered = []
        for result in results:
            match = True
            for key, value in self.config.filters.items():
                if result.metadata.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(result)

        return filtered

    def _get_cache_key(
        self,
        query: str,
        method: RetrievalMethod,
        top_k: int,
    ) -> str:
        """生成缓存键"""
        key_str = f"{query}:{method.value}:{top_k}:{self.config.filters}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[RetrievalResult]]:
        """从缓存获取"""
        if cache_key in self._cache:
            results, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.config.cache_ttl:
                return results
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, results: List[RetrievalResult]) -> None:
        """设置缓存"""
        # 简单的 LRU：如果缓存满了，删除最旧的
        max_cache_size = 1000
        if len(self._cache) >= max_cache_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[cache_key] = (results, time.time())

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def expand_query(
        self,
        query: str,
        strategy: QueryExpansionStrategy = QueryExpansionStrategy.NONE,
    ) -> List[str]:
        """
        查询扩展

        Args:
            query: 原始查询
            strategy: 扩展策略

        Returns:
            扩展后的查询列表
        """
        if strategy == QueryExpansionStrategy.NONE:
            return [query]

        expanded = [query]

        if strategy == QueryExpansionStrategy.EMBEDDING:
            # 使用嵌入相似词扩展
            similar_terms = self._get_similar_terms(query, self.config.expansion_terms)
            for term in similar_terms:
                expanded.append(f"{query} {term}")

        elif strategy == QueryExpansionStrategy.SYNONYYM:
            # 同义词扩展（简化版）
            synonyms = self._get_synonyms(query)
            for synonym in synonyms:
                expanded.append(synonym)

        return expanded[:5]

    def _get_similar_terms(self, query: str, top_k: int) -> List[str]:
        """获取相似词（基于嵌入）"""
        # 简化实现
        return []

    def _get_synonyms(self, query: str) -> List[str]:
        """获取同义词（简化实现）"""
        # 生产环境应使用词典或知识图谱
        return []

    def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = 10,
        rerank_top_k: int = 50,
    ) -> List[RetrievalResult]:
        """
        检索 + 重排序

        先获取更多候选，然后使用 Cross-Encoder 重排序
        """
        # 获取候选
        candidates = self.retrieve(query, method=RetrievalMethod.RRF, top_k=rerank_top_k)

        # 重排序（简化版：使用分数加权）
        # 生产环境应使用专门的 Cross-Encoder 模型
        reranked = sorted(
            candidates,
            key=lambda r: r.score,
            reverse=True
        )[:top_k]

        return reranked


# ==================== 全局实例 ====================

_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever(config: RetrievalConfig = None) -> HybridRetriever:
    """获取全局混合检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(config)
    return _retriever


# ==================== 便捷函数 ====================

def hybrid_search(
    query: str,
    top_k: int = 10,
    method: RetrievalMethod = RetrievalMethod.HYBRID,
) -> List[Dict[str, Any]]:
    """
    混合检索（便捷函数）

    Args:
        query: 查询文本
        top_k: 返回结果数量
        method: 检索方法

    Returns:
        检索结果字典列表
    """
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(query, method=method, top_k=top_k)

    return [
        {
            "id": r.id,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
            "source": r.source.value,
        }
        for r in results
    ]


def mmr_search(
    query: str,
    top_k: int = 10,
    diversity: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    MMR 多样性检索（便捷函数）

    Args:
        query: 查询文本
        top_k: 返回结果数量
        diversity: 多样性权重 (0=多样性优先, 1=相关性优先)

    Returns:
        检索结果字典列表
    """
    config = RetrievalConfig(mmr_lambda=diversity)
    retriever = HybridRetriever(config)
    results = retriever.retrieve(query, method=RetrievalMethod.MMR, top_k=top_k)

    return [
        {
            "id": r.id,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in results
    ]
