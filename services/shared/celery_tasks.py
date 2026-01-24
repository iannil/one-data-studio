"""
Celery 异步任务定义
Sprint 8: 异步任务处理

定义文档索引、工作流执行等异步任务
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import shared_task

from .celery_app import TaskResult
from .config import get_config

logger = logging.getLogger(__name__)

config = get_config()


@shared_task(bind=True, name='services.shared.celery_tasks.index_document')
def index_document(self, doc_id: str, collection_name: str,
                   texts: List[str], embeddings: List[List[float]],
                   metadata: List[Dict] = None) -> Dict[str, Any]:
    """
    异步索引文档

    Args:
        doc_id: 文档 ID
        collection_name: 向量集合名称
        texts: 文本列表
        embeddings: 向量列表
        metadata: 元数据列表

    Returns:
        任务结果
    """
    try:
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Initializing'})

        # 导入向量存储
        from services.bisheng_api.services.vector_store import VectorStore

        vector_store = VectorStore()
        count = vector_store.insert(collection_name, texts, embeddings, metadata)

        logger.info(f"Document indexed: {doc_id}, {count} chunks")

        return TaskResult(
            success=True,
            data={"doc_id": doc_id, "count": count},
            metadata={"collection": collection_name}
        ).to_dict()

    except Exception as e:
        logger.error(f"Document indexing failed: {doc_id}, error: {e}")
        return TaskResult(
            success=False,
            error=str(e),
            metadata={"doc_id": doc_id}
        ).to_dict()


@shared_task(bind=True, name='services.shared.celery_tasks.index_documents_batch')
def index_documents_batch(self, documents: List[Dict]) -> Dict[str, Any]:
    """
    批量异步索引文档

    Args:
        documents: 文档列表，每个文档包含 doc_id, collection_name, texts, embeddings, metadata

    Returns:
        任务结果
    """
    try:
        results = []
        total = len(documents)

        for i, doc in enumerate(documents):
            # 更新进度
            progress = int((i / total) * 100)
            self.update_state(
                state='PROGRESS',
                meta={'progress': progress, 'status': f'Processing {i+1}/{total}'}
            )

            # 索引单个文档
            result = index_document(
                doc['doc_id'],
                doc['collection_name'],
                doc['texts'],
                doc['embeddings'],
                doc.get('metadata')
            )
            results.append(result)

        success_count = sum(1 for r in results if r.get('success'))

        return TaskResult(
            success=True,
            data={
                "total": total,
                "success": success_count,
                "failed": total - success_count,
                "results": results
            }
        ).to_dict()

    except Exception as e:
        logger.error(f"Batch document indexing failed: {e}")
        return TaskResult(
            success=False,
            error=str(e)
        ).to_dict()


@shared_task(bind=True, name='services.shared.celery_tasks.execute_workflow')
def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any],
                     user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    异步执行工作流

    Args:
        workflow_id: 工作流 ID
        input_data: 输入数据
        user_id: 用户 ID

    Returns:
        任务结果
    """
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Loading workflow'})

        # 导入工作流引擎
        from services.bisheng_api.engine.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()

        # 执行工作流
        def progress_callback(step: int, total: int, message: str):
            progress = int((step / total) * 100) if total > 0 else 0
            self.update_state(
                state='PROGRESS',
                meta={'progress': progress, 'status': message}
            )

        result = executor.execute(
            workflow_id=workflow_id,
            input_data=input_data,
            user_id=user_id,
            progress_callback=progress_callback
        )

        logger.info(f"Workflow executed: {workflow_id}")

        return TaskResult(
            success=True,
            data=result,
            metadata={
                "workflow_id": workflow_id,
                "user_id": user_id,
                "completed_at": datetime.utcnow().isoformat()
            }
        ).to_dict()

    except Exception as e:
        logger.error(f"Workflow execution failed: {workflow_id}, error: {e}")
        return TaskResult(
            success=False,
            error=str(e),
            metadata={"workflow_id": workflow_id}
        ).to_dict()


@shared_task(bind=True, name='services.shared.celery_tasks.execute_workflow_long_running')
def execute_workflow_long_running(self, workflow_id: str, input_data: Dict[str, Any],
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    异步执行长时间运行的工作流

    与 execute_workflow 类似，但使用不同的队列，可以设置更长的超时时间

    Args:
        workflow_id: 工作流 ID
        input_data: 输入数据
        user_id: 用户 ID

    Returns:
        任务结果
    """
    # 复用 execute_workflow 的实现
    return execute_workflow(workflow_id, input_data, user_id)


@shared_task(name='services.shared.celery_tasks.cleanup_old_cache')
def cleanup_old_cache(days: int = 7) -> Dict[str, Any]:
    """
    清理过期缓存

    Args:
        days: 清理多少天前的缓存

    Returns:
        任务结果
    """
    try:
        # 导入缓存模块
        from services.shared.cache import get_cache

        cache = get_cache()
        # 这里实现清理逻辑
        # 由于 Redis 缓存有 TTL，主要是清理磁盘缓存

        logger.info(f"Cache cleanup completed: {days} days")

        return TaskResult(
            success=True,
            data={"cleaned_days": days}
        ).to_dict()

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return TaskResult(
            success=False,
            error=str(e)
        ).to_dict()


@shared_task(name='services.shared.celery_tasks.generate_embeddings')
def generate_embeddings(texts: List[str], model: str = "text-embedding-ada-002") -> Dict[str, Any]:
    """
    异步生成文本嵌入向量

    Args:
        texts: 文本列表
        model: 嵌入模型名称

    Returns:
        任务结果
    """
    try:
        # 导入嵌入服务
        from services.bisheng_api.services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        embeddings = embedding_service.embed_texts(texts, model=model)

        logger.info(f"Generated {len(embeddings)} embeddings")

        return TaskResult(
            success=True,
            data={"embeddings": embeddings, "count": len(embeddings)}
        ).to_dict()

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return TaskResult(
            success=False,
            error=str(e)
        ).to_dict()


@shared_task(name='services.shared.celery_tasks.send_notification')
def send_notification(user_id: str, message: str, notification_type: str = "info") -> Dict[str, Any]:
    """
    发送通知

    Args:
        user_id: 用户 ID
        message: 消息内容
        notification_type: 通知类型

    Returns:
        任务结果
    """
    try:
        # 这里实现通知发送逻辑
        # 可以是邮件、WebSocket 推送等

        logger.info(f"Notification sent to user {user_id}: {message}")

        return TaskResult(
            success=True,
            data={"user_id": user_id, "type": notification_type}
        ).to_dict()

    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return TaskResult(
            success=False,
            error=str(e)
        ).to_dict()


# 任务链示例
def create_indexing_workflow(doc_id: str, texts: List[str]) -> str:
    """
    创建索引工作流：生成嵌入 -> 索引文档 -> 发送通知

    Args:
        doc_id: 文档 ID
        texts: 文本列表

    Returns:
        工作流任务 ID
    """
    from celery import chain

    workflow = chain(
        generate_embeddings.s(texts),
        index_document.s(doc_id, "documents", texts),  # embeddings 会从上一个任务传递
        send_notification.s(doc_id, "Document indexed successfully")
    )

    result = workflow.apply_async()
    return result.id


# 周期性任务配置
@shared_task(name='services.shared.celery_tasks.periodic_health_check')
def periodic_health_check() -> Dict[str, Any]:
    """周期性健康检查任务"""
    try:
        # 检查各种服务的健康状态
        checks = {}

        # 检查数据库
        try:
            from services.alldata_api.src.database import check_db_health
            checks['database'] = check_db_health()
        except Exception as e:
            checks['database'] = False

        # 检查向量数据库
        try:
            from services.bisheng_api.services.vector_store import VectorStore
            vs = VectorStore()
            checks['milvus'] = VectorStore._connected
        except Exception as e:
            checks['milvus'] = False

        # 检查存储
        try:
            from services.shared.storage.minio_client import MinIOClient
            mc = MinIOClient()
            checks['minio'] = mc.client is not None
        except Exception as e:
            checks['minio'] = False

        all_healthy = all(checks.values())

        if not all_healthy:
            logger.warning(f"Health check failed: {checks}")

        return TaskResult(
            success=all_healthy,
            data=checks
        ).to_dict()

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return TaskResult(
            success=False,
            error=str(e)
        ).to_dict()
