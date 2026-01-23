"""
执行日志模型
Phase 6: Sprint 6.4
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from .base import Base


class ExecutionLog(Base):
    """执行日志表"""
    __tablename__ = "execution_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), nullable=False, comment='执行ID')
    node_id = Column(String(64), comment='节点ID')
    level = Column(String(16), nullable=False, default='info', comment='日志级别: info, warning, error')
    message = Column(Text, comment='日志消息')
    timestamp = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='时间戳')

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "node_id": self.node_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
