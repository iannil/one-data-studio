"""
知识库向量生成器

生成：
- 知识库（3个库）
- 索引文档（15个文档）
- 向量数据（150+向量）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import BaseGenerator, generate_id, random_date, random_chinese_description
from ..config import GeneratorQuantities


# 知识库类型
KB_TYPES = [
    "产品文档", "技术文档", "API文档", "FAQ",
    "数据字典", "操作手册", "培训资料"
]

# 文档标题模板
DOC_TITLE_TEMPLATES = {
    "产品文档": ["产品功能介绍", "快速开始指南", "用户手册", "产品更新日志"],
    "技术文档": ["架构设计文档", "API接口文档", "数据库设计", "部署指南"],
    "FAQ": ["常见问题解答", "故障排查指南", "使用技巧", "FAQ集合"],
    "数据字典": ["数据字典说明", "表结构定义", "字段说明文档", "数据标准"],
}


class KnowledgeGenerator(BaseGenerator):
    """
    知识库生成器

    生成知识库、文档和向量
    """

    # 文本分段模板
    CHUNK_TEMPLATES = [
        "本文介绍了{}的基本概念和使用方法。首先，我们需要了解其核心功能，然后按照步骤进行操作。",
        "在使用{}时，需要注意以下几点：1. 确保环境配置正确；2. 检查依赖项；3. 遵循最佳实践。",
        "关于{}的技术细节，主要包括以下几个方面：架构设计、接口定义、数据流程和错误处理。",
        "{}是一个重要的功能，它可以帮助用户快速完成相关操作。下面我们详细介绍其使用方法。",
        "在实现{}的过程中，我们采用了模块化设计，主要包括以下几个组件：输入处理、核心逻辑、输出渲染。",
    ]

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None,
                 minio_manager=None, milvus_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()
        self.minio = minio_manager
        self.milvus = milvus_manager

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有知识库数据

        Returns:
            包含knowledge_bases, documents, vectors的字典
        """
        self.log("Generating knowledge bases and vectors...", "info")

        # 生成知识库
        knowledge_bases = self._generate_knowledge_bases()
        self.store_data("knowledge_bases", knowledge_bases)

        # 生成文档
        documents = self._generate_documents(knowledge_bases)
        self.store_data("documents", documents)

        # 生成向量
        vectors = self._generate_vectors(documents, knowledge_bases)
        self.store_data("vectors", vectors)

        self.log(
            f"Generated {len(knowledge_bases)} knowledge bases, {len(documents)} documents, "
            f"{len(vectors)} vectors",
            "success"
        )

        return self.get_all_data()

    def _generate_knowledge_bases(self) -> List[Dict[str, Any]]:
        """生成知识库"""
        kbs = []

        kb_names = [
            "产品知识库",
            "技术文档库",
            "FAQ知识库",
        ]

        for i, name in enumerate(kb_names):
            kb_type = KB_TYPES[i % len(KB_TYPES)]

            kb = {
                "kb_id": generate_id("kb_", 8),
                "name": name,
                "code": f"kb_{i+1:02d}",
                "type": kb_type,
                "description": f"存储{name.replace('库', '')}相关的文档和知识",
                "collection_name": f"collection_{i+1:02d}",
                "embedding_model": random.choice([
                    "text-embedding-ada-002",
                    "text-embedding-3-small",
                    "bge-large-zh"
                ]),
                "dimension": random.choice([768, 1024, 1536]),
                "chunk_size": random.randint(300, 800),
                "chunk_overlap": random.randint(50, 200),
                "document_count": self.quantities.documents_per_kb,
                "vector_count": 0,  # 将在生成向量后更新
                "status": random.choice(["active", "active", "active", "indexing"]),
                "created_by": random.choice(["admin", "ai-dev-01", "data-analyst-01"]),
                "created_at": random_date(90),
                "updated_at": random_date(30),
            }
            kbs.append(kb)

        return kbs

    def _generate_documents(self, knowledge_bases: List[Dict]) -> List[Dict[str, Any]]:
        """生成文档"""
        documents = []

        for kb in knowledge_bases:
            doc_templates = DOC_TITLE_TEMPLATES.get(
                kb["type"],
                [f"{kb['name']}文档_{i}" for i in range(1, 10)]
            )

            for i in range(self.quantities.documents_per_kb):
                # 生成文档内容
                title = doc_templates[i % len(doc_templates)]
                content = self._generate_document_content(title)

                doc = {
                    "doc_id": generate_id("doc_", 8),
                    "kb_id": kb["kb_id"],
                    "collection_name": kb["collection_name"],
                    "title": f"{title}_{i+1}",
                    "content": content,
                    "content_type": "text/markdown",
                    "chunk_count": random.randint(3, 10),
                    "source": random.choice(["upload", "import", "api"]),
                    "file_path": f"/documents/{kb['code']}/doc_{i+1}.md" if random.random() > 0.3 else None,
                    "file_size": len(content.encode('utf-8')),
                    "tags": random.sample(["重要", "常用", "文档", "指南", "参考"], k=random.randint(1, 3)),
                    "status": random.choice(["indexed", "indexed", "pending", "error"]),
                    "created_by": kb["created_by"],
                    "created_at": random_date(60),
                    "updated_at": random_date(30),
                }
                documents.append(doc)

                # 上传到MinIO（如果可用）
                if self.minio and doc["file_path"]:
                    self.minio.upload_document(
                        doc["doc_id"],
                        content,
                        title,
                        "md"
                    )

        return documents

    def _generate_document_content(self, title: str) -> str:
        """生成文档内容"""
        sections = []

        # 添加标题
        sections.append(f"# {title}\n")

        # 添加概述
        sections.append(f"## 概述\n\n{title}是系统中的重要组成部分。本文档将详细介绍相关内容。\n")

        # 添加几个章节
        for i in range(1, 4):
            sections.append(f"## 第{i}节\n\n")
            # 添加段落
            for j in range(2, 4):
                template = random.choice(self.CHUNK_TEMPLATES)
                sections.append(template.format(title) + "\n\n")

        return "".join(sections)

    def _generate_vectors(self, documents: List[Dict], knowledge_bases: List[Dict]) -> List[Dict[str, Any]]:
        """生成向量"""
        vectors = []
        kb_vector_counts = {kb["kb_id"]: 0 for kb in knowledge_bases}

        for doc in documents:
            # 获取知识库的维度
            kb = next((k for k in knowledge_bases if k["kb_id"] == doc["kb_id"]), None)
            dimension = kb["dimension"] if kb else 1536

            # 生成文档分块
            chunks = self._split_text(doc["content"], kb["chunk_size"] if kb else 500)

            for i, chunk_text in enumerate(chunks):
                vector_id = f"{doc['doc_id']}_chunk_{i}"
                embedding = self._generate_embedding(dimension)

                vector = {
                    "vector_id": vector_id,
                    "doc_id": doc["doc_id"],
                    "kb_id": doc["kb_id"],
                    "collection_name": doc["collection_name"],
                    "chunk_index": i,
                    "chunk_text": chunk_text,
                    "embedding": embedding,
                    "dimension": dimension,
                    "created_at": doc["created_at"],
                }
                vectors.append(vector)
                kb_vector_counts[doc["kb_id"]] += 1

                # 插入到Milvus（如果可用）
                if self.milvus:
                    self.milvus.insert_vector(
                        doc["collection_name"],
                        embedding,
                        vector_id,
                        chunk_text,
                        {"doc_id": doc["doc_id"], "chunk_index": i}
                    )

        # 更新知识库的向量计数
        for kb in knowledge_bases:
            kb["vector_count"] = kb_vector_counts.get(kb["kb_id"], 0)

        return vectors

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """简单的文本分块"""
        chunks = []
        current = ""
        sentences = text.split("。")

        for sentence in sentences:
            if len(current) + len(sentence) < chunk_size:
                current += sentence + "。"
            else:
                if current:
                    chunks.append(current)
                current = sentence + "。"

        if current:
            chunks.append(current)

        return chunks[:10]  # 最多10个分块

    def _generate_embedding(self, dimension: int) -> List[float]:
        """生成模拟向量"""
        import random
        # 归一化随机向量
        vec = [random.uniform(-1, 1) for _ in range(dimension)]
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec]

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving knowledge bases to database...", "info")

        # 保存知识库
        knowledge_bases = self.get_data("knowledge_bases")
        if knowledge_bases and self.storage.table_exists("knowledge_bases"):
            self.storage.batch_insert(
                "knowledge_bases",
                ["kb_id", "name", "code", "type", "description", "collection_name",
                 "embedding_model", "dimension", "chunk_size", "chunk_overlap",
                 "document_count", "vector_count", "status", "created_by", "created_at", "updated_at"],
                knowledge_bases,
                idempotent=True,
                idempotent_columns=["kb_id"]
            )
            self.log(f"Saved {len(knowledge_bases)} knowledge bases", "success")

        # 保存文档
        documents = self.get_data("documents")
        if documents and self.storage.table_exists("indexed_documents"):
            self.storage.batch_insert(
                "indexed_documents",
                ["doc_id", "kb_id", "collection_name", "title", "content", "content_type",
                 "chunk_count", "source", "file_path", "file_size", "tags", "status",
                 "created_by", "created_at", "updated_at"],
                documents,
                idempotent=True,
                idempotent_columns=["doc_id"]
            )
            self.log(f"Saved {len(documents)} documents", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up knowledge base data...", "info")

        # 清理Milvus
        if self.milvus:
            knowledge_bases = self.get_data("knowledge_bases")
            for kb in knowledge_bases:
                self.milvus.drop_collection(kb["collection_name"])

        # 清理MinIO
        if self.minio:
            self.minio.remove_objects("documents/")
            self.minio.remove_objects("chunks/")

        # 清理数据库
        if self.storage.table_exists("indexed_documents"):
            self.storage.cleanup_by_prefix("indexed_documents", "doc_id", "doc_")

        if self.storage.table_exists("knowledge_bases"):
            self.storage.cleanup_by_prefix("knowledge_bases", "kb_id", "kb_")


def generate_knowledge_data(config: GeneratorQuantities = None,
                           minio_manager=None, milvus_manager=None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成知识库数据

    Args:
        config: 生成配置
        minio_manager: MinIO管理器
        milvus_manager: Milvus管理器

    Returns:
        知识库数据字典
    """
    generator = KnowledgeGenerator(config, minio_manager=minio_manager, milvus_manager=milvus_manager)
    return generator.generate()
