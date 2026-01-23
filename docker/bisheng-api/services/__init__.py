"""
服务模块
Phase 6: Sprint 6.2-6.3
Phase 7: Sprint 7.4 - 调度服务
"""

from .vector_store import VectorStore
from .embedding import EmbeddingService
from .document import DocumentService

try:
    from .scheduler import WorkflowScheduler, get_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

__all__ = [
    'VectorStore',
    'EmbeddingService',
    'DocumentService',
]

if SCHEDULER_AVAILABLE:
    __all__.extend(['WorkflowScheduler', 'get_scheduler'])
