"""
服务模块
Phase 6: Sprint 6.2-6.3
Phase 7: Sprint 7.4 - 调度服务
P1 - Agent 模板管理
"""

from .vector_store import VectorStore
from .embedding import EmbeddingService
from .document import DocumentService

try:
    from .scheduler import WorkflowScheduler, get_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

try:
    from .agent_template import AgentTemplateService, get_agent_template_service
    AGENT_TEMPLATE_AVAILABLE = True
except ImportError:
    AGENT_TEMPLATE_AVAILABLE = False

__all__ = [
    'VectorStore',
    'EmbeddingService',
    'DocumentService',
]

if SCHEDULER_AVAILABLE:
    __all__.extend(['WorkflowScheduler', 'get_scheduler'])

if AGENT_TEMPLATE_AVAILABLE:
    __all__.extend(['AgentTemplateService', 'get_agent_template_service'])
