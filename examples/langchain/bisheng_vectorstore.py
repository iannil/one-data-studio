"""
Bisheng VectorStore 适配器 for LangChain

将 ONE-DATA-STUDIO (Bisheng) 的向量存储服务封装为 LangChain 兼容的 VectorStore 类，
使用户可以在 LangChain RAG 应用中无缝使用平台的向量检索能力。

用法示例：
    from bisheng_vectorstore import BishengVectorStore
    from langchain_openai import OpenAIEmbeddings

    # 创建向量存储
    vectorstore = BishengVectorStore(
        api_base="http://localhost:8000",
        collection_name="my_documents",
        embedding=OpenAIEmbeddings()
    )

    # 添加文档
    texts = ["Document 1 content", "Document 2 content"]
    vectorstore.add_texts(texts)

    # 相似性搜索
    results = vectorstore.similarity_search("query text", k=5)

    # 作为检索器使用
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # 在 RAG Chain 中使用
    from langchain.chains import RetrievalQA
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever
    )
"""

import os
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import requests
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

logger = logging.getLogger(__name__)


class BishengVectorStore(VectorStore):
    """
    Bisheng (ONE-DATA-STUDIO) VectorStore 适配器

    通过 Bisheng API 连接到 Milvus 向量存储服务。

    Attributes:
        api_base: Bisheng API 基础 URL
        collection_name: 向量集合名称
        embedding: 嵌入模型
        api_key: API 密钥
        timeout: 请求超时时间
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        collection_name: str = "default",
        embedding: Optional[Embeddings] = None,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        初始化 Bisheng VectorStore

        Args:
            api_base: Bisheng API 基础 URL
            collection_name: 向量集合名称
            embedding: 嵌入模型 (可选，如果不提供则使用服务端嵌入)
            api_key: API 密钥
            timeout: 请求超时时间（秒）
        """
        self.api_base = api_base or os.getenv("BISHENG_API_BASE", "http://localhost:8000")
        self.collection_name = collection_name
        self._embedding = embedding
        self.api_key = api_key or os.getenv("BISHENG_API_KEY")
        self.timeout = timeout

    @property
    def embeddings(self) -> Optional[Embeddings]:
        """返回嵌入模型"""
        return self._embedding

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        添加文本到向量存储

        Args:
            texts: 文本列表
            metadatas: 元数据列表
            **kwargs: 其他参数

        Returns:
            文档 ID 列表
        """
        texts_list = list(texts)
        if not texts_list:
            return []

        # 如果有本地嵌入模型，先计算嵌入
        embeddings = None
        if self._embedding:
            embeddings = self._embedding.embed_documents(texts_list)

        payload = {
            "collection_name": self.collection_name,
            "texts": texts_list,
            "metadatas": metadatas or [{}] * len(texts_list),
        }

        if embeddings:
            payload["embeddings"] = embeddings

        try:
            response = requests.post(
                f"{self.api_base}/api/v1/vectors/add",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("ids", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add texts: {e}")
            raise ValueError(f"Failed to add texts to Bisheng: {e}")

    def add_documents(
        self,
        documents: List[Document],
        **kwargs: Any,
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: LangChain Document 列表
            **kwargs: 其他参数

        Returns:
            文档 ID 列表
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas, **kwargs)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        相似性搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            相似文档列表
        """
        docs_and_scores = self.similarity_search_with_score(query, k, filter, **kwargs)
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Tuple[Document, float]]:
        """
        带分数的相似性搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            (文档, 分数) 元组列表
        """
        # 如果有本地嵌入模型，计算查询嵌入
        query_embedding = None
        if self._embedding:
            query_embedding = self._embedding.embed_query(query)

        payload = {
            "collection_name": self.collection_name,
            "query": query,
            "k": k,
        }

        if query_embedding:
            payload["query_embedding"] = query_embedding

        if filter:
            payload["filter"] = filter

        try:
            response = requests.post(
                f"{self.api_base}/api/v1/vectors/search",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            docs_and_scores = []
            for item in result.get("results", []):
                doc = Document(
                    page_content=item.get("content", ""),
                    metadata=item.get("metadata", {}),
                )
                score = item.get("score", 0.0)
                docs_and_scores.append((doc, score))

            return docs_and_scores

        except requests.exceptions.RequestException as e:
            logger.error(f"Similarity search failed: {e}")
            raise ValueError(f"Similarity search failed: {e}")

    def similarity_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        通过向量进行相似性搜索

        Args:
            embedding: 查询向量
            k: 返回结果数量
            filter: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            相似文档列表
        """
        payload = {
            "collection_name": self.collection_name,
            "query_embedding": embedding,
            "k": k,
        }

        if filter:
            payload["filter"] = filter

        try:
            response = requests.post(
                f"{self.api_base}/api/v1/vectors/search",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            documents = []
            for item in result.get("results", []):
                doc = Document(
                    page_content=item.get("content", ""),
                    metadata=item.get("metadata", {}),
                )
                documents.append(doc)

            return documents

        except requests.exceptions.RequestException as e:
            logger.error(f"Vector search failed: {e}")
            raise ValueError(f"Vector search failed: {e}")

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        最大边际相关性搜索 (MMR)

        用于获取多样化的搜索结果。

        Args:
            query: 查询文本
            k: 返回结果数量
            fetch_k: 初始获取数量
            lambda_mult: 多样性参数 (0-1)
            filter: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            文档列表
        """
        query_embedding = None
        if self._embedding:
            query_embedding = self._embedding.embed_query(query)

        payload = {
            "collection_name": self.collection_name,
            "query": query,
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": lambda_mult,
            "mmr": True,
        }

        if query_embedding:
            payload["query_embedding"] = query_embedding

        if filter:
            payload["filter"] = filter

        try:
            response = requests.post(
                f"{self.api_base}/api/v1/vectors/search",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            documents = []
            for item in result.get("results", []):
                doc = Document(
                    page_content=item.get("content", ""),
                    metadata=item.get("metadata", {}),
                )
                documents.append(doc)

            return documents

        except requests.exceptions.RequestException as e:
            logger.error(f"MMR search failed: {e}")
            raise ValueError(f"MMR search failed: {e}")

    def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[bool]:
        """
        删除文档

        Args:
            ids: 文档 ID 列表
            filter: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        payload = {
            "collection_name": self.collection_name,
        }

        if ids:
            payload["ids"] = ids
        if filter:
            payload["filter"] = filter

        try:
            response = requests.post(
                f"{self.api_base}/api/v1/vectors/delete",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete failed: {e}")
            return False

    @classmethod
    def from_texts(
        cls: Type["BishengVectorStore"],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        collection_name: str = "default",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> "BishengVectorStore":
        """
        从文本创建向量存储

        Args:
            texts: 文本列表
            embedding: 嵌入模型
            metadatas: 元数据列表
            collection_name: 集合名称
            api_base: API 基础 URL
            api_key: API 密钥
            **kwargs: 其他参数

        Returns:
            BishengVectorStore 实例
        """
        vectorstore = cls(
            api_base=api_base,
            collection_name=collection_name,
            embedding=embedding,
            api_key=api_key,
        )
        vectorstore.add_texts(texts, metadatas)
        return vectorstore

    @classmethod
    def from_documents(
        cls: Type["BishengVectorStore"],
        documents: List[Document],
        embedding: Embeddings,
        collection_name: str = "default",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> "BishengVectorStore":
        """
        从文档创建向量存储

        Args:
            documents: LangChain Document 列表
            embedding: 嵌入模型
            collection_name: 集合名称
            api_base: API 基础 URL
            api_key: API 密钥
            **kwargs: 其他参数

        Returns:
            BishengVectorStore 实例
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return cls.from_texts(
            texts,
            embedding,
            metadatas,
            collection_name=collection_name,
            api_base=api_base,
            api_key=api_key,
            **kwargs,
        )

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息字典
        """
        try:
            response = requests.get(
                f"{self.api_base}/api/v1/vectors/collections/{self.collection_name}/stats",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

    def list_collections(self) -> List[str]:
        """
        列出所有集合

        Returns:
            集合名称列表
        """
        try:
            response = requests.get(
                f"{self.api_base}/api/v1/vectors/collections",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("collections", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list collections: {e}")
            return []


# 便捷函数
def create_bisheng_vectorstore(
    collection_name: str = "default",
    api_base: Optional[str] = None,
    embedding: Optional[Embeddings] = None,
    api_key: Optional[str] = None,
) -> BishengVectorStore:
    """
    创建 Bisheng VectorStore 实例

    Args:
        collection_name: 集合名称
        api_base: API 基础 URL
        embedding: 嵌入模型
        api_key: API 密钥

    Returns:
        BishengVectorStore 实例
    """
    return BishengVectorStore(
        api_base=api_base,
        collection_name=collection_name,
        embedding=embedding,
        api_key=api_key,
    )


if __name__ == "__main__":
    # 简单测试
    vectorstore = BishengVectorStore(
        api_base="http://localhost:8000",
        collection_name="test_collection",
    )
    print(f"Collection: {vectorstore.collection_name}")
    print(f"API Base: {vectorstore.api_base}")
