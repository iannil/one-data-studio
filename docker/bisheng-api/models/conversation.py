"""
会话和消息模型
Sprint 4.2: Conversation, Message 模型
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Conversation(Base):
    """会话表"""
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), unique=True, nullable=False, comment='会话唯一标识')
    user_id = Column(String(128), comment='用户ID')
    title = Column(String(255), comment='会话标题')
    model = Column(String(64), comment='使用的模型')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def to_dict(self, include_messages=False):
        """转换为字典"""
        result = {
            "id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            result["messages"] = [m.to_dict() for m in self.messages]
        return result


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, comment='所属会话ID')
    role = Column(String(32), nullable=False, comment='角色: user, assistant, system')
    content = Column(Text, nullable=False, comment='消息内容')
    tokens = Column(Integer, comment='Token 数量')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 外键
    __table_args__ = (
        ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
    )

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "tokens": self.tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
