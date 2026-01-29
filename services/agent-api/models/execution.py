"""
工作流执行记录模型
Phase 6: Sprint 6.1
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Integer, Index
from sqlalchemy.sql import func

from .base import Base


class WorkflowExecution(Base):
    """工作流执行记录表"""
    __tablename__ = "workflow_executions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, comment='执行唯一标识')
    workflow_id = Column(String(64), nullable=False, index=True, comment='工作流ID')
    status = Column(String(32), nullable=False, default='pending', index=True, comment='状态: pending, running, completed, failed, stopped')
    inputs = Column(Text, comment='输入数据 (JSON)')
    outputs = Column(Text, comment='输出数据 (JSON)')
    node_results = Column(Text, comment='节点执行结果 (JSON)')
    error = Column(Text, comment='错误信息')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')
    duration_ms = Column(Integer, comment='执行时长（毫秒）')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 复合索引用于常见查询
    __table_args__ = (
        Index('ix_workflow_executions_workflow_status', 'workflow_id', 'status'),
        Index('ix_workflow_executions_created_at', 'created_at'),
    )

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            "id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "inputs": json.loads(self.inputs) if self.inputs else None,
            "outputs": json.loads(self.outputs) if self.outputs else None,
            "node_results": json.loads(self.node_results) if self.node_results else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
