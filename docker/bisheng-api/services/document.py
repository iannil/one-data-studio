"""
文档处理服务
支持加载、切分文档
Phase 6: Sprint 6.3
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class Document:
    """文档对象"""

    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.page_content,
            "metadata": self.metadata
        }


class DocumentService:
    """文档处理服务"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文档服务

        Args:
            chunk_size: 文档块大小
            chunk_overlap: 文档块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 中文和英文分隔符
        self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def load_from_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """
        从文本加载文档

        Args:
            text: 输入文本
            metadata: 元数据

        Returns:
            文档列表
        """
        if not text:
            return []

        if metadata is None:
            metadata = {}

        return [Document(page_content=text, metadata=metadata)]

    def load_from_file(self, file_path: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """
        从文件加载文档

        Args:
            file_path: 文件路径
            metadata: 元数据

        Returns:
            文档列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if metadata is None:
            metadata = {}

        # 添加文件信息到元数据
        metadata.update({
            "source": file_path,
            "file_name": os.path.basename(file_path),
            "file_type": os.path.splitext(file_path)[1],
            "loaded_at": datetime.now().isoformat()
        })

        return [Document(page_content=content, metadata=metadata)]

    def split_text(self, text: str) -> List[str]:
        """
        切分文本

        Args:
            text: 输入文本

        Returns:
            文本块列表
        """
        if not text:
            return []

        chunks = []
        current_position = 0
        text_length = len(text)

        while current_position < text_length:
            # 计算当前块的结束位置
            end_position = min(current_position + self.chunk_size, text_length)

            # 如果不是最后一块，尝试在分隔符处切分
            if end_position < text_length:
                # 在分隔符处寻找最佳切分点
                best_split = end_position
                for sep in self.separators:
                    # 在当前窗口内查找分隔符
                    split_pos = text.rfind(sep, current_position, end_position)
                    if split_pos > current_position and split_pos < end_position:
                        best_split = split_pos + len(sep)
                        break

                end_position = best_split

            # 提取文本块
            chunk = text[current_position:end_position].strip()
            if chunk:
                chunks.append(chunk)

            # 移动到下一个位置，考虑重叠
            current_position = end_position - self.chunk_overlap
            if current_position < 0:
                current_position = end_position

        return chunks

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        切分文档

        Args:
            documents: 文档列表

        Returns:
            切分后的文档列表
        """
        split_docs = []

        for doc in documents:
            chunks = self.split_text(doc.page_content)

            for i, chunk in enumerate(chunks):
                # 创建新的元数据
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "chunk_count": len(chunks)
                })

                split_docs.append(Document(page_content=chunk, metadata=chunk_metadata))

        return split_docs

    def create_document_from_upload(self, filename: str, content: str,
                                    metadata: Dict[str, Any] = None) -> List[Document]:
        """
        从上传的文件创建文档

        Args:
            filename: 文件名
            content: 文件内容
            metadata: 额外元数据

        Returns:
            文档列表
        """
        if metadata is None:
            metadata = {}

        metadata.update({
            "source": filename,
            "file_name": filename,
            "uploaded_at": datetime.now().isoformat()
        })

        docs = self.load_from_text(content, metadata)
        return self.split_documents(docs)

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量

        Args:
            text: 输入文本

        Returns:
            估算的 token 数量
        """
        # 简单估算：中文约1字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        return chinese_chars + (other_chars // 4)

    def get_document_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """
        获取文档统计信息

        Args:
            documents: 文档列表

        Returns:
            统计信息
        """
        total_chars = sum(len(doc.page_content) for doc in documents)
        total_tokens = sum(self.estimate_tokens(doc.page_content) for doc in documents)

        return {
            "document_count": len(documents),
            "total_characters": total_chars,
            "total_tokens": total_tokens,
            "avg_characters_per_doc": total_chars // len(documents) if documents else 0,
            "avg_tokens_per_doc": total_tokens // len(documents) if documents else 0,
        }
