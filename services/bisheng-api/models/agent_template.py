"""
Agent 模板模型
P1 - Agent 模板管理功能

支持保存和复用常用 Agent 配置
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, BigInteger

from .base import Base


class AgentTemplate(Base):
    """Agent 模板表

    用于保存常用的 Agent 配置，方便快速复用
    """

    __tablename__ = "agent_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True)

    # 基本信息
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Agent 配置
    agent_type = Column(String(32), nullable=False, default="react")  # react, function_calling, plan_execute
    model = Column(String(64), nullable=False, default="gpt-4o-mini")
    max_iterations = Column(Integer, nullable=True, default=10)

    # Prompt 配置
    system_prompt = Column(Text, nullable=True)

    # 工具配置 (JSON 字符串存储工具名称列表)
    selected_tools = Column(Text, nullable=True)  # JSON array of tool names

    # 元数据
    created_by = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        """转换为字典"""
        import json

        selected_tools_list = []
        if self.selected_tools:
            try:
                selected_tools_list = json.loads(self.selected_tools)
            except json.JSONDecodeError:
                selected_tools_list = []

        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "model": self.model,
            "max_iterations": self.max_iterations,
            "system_prompt": self.system_prompt,
            "selected_tools": selected_tools_list,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_tools_list(self) -> list:
        """获取工具列表"""
        if not self.selected_tools:
            return []
        try:
            return json.loads(self.selected_tools)
        except json.JSONDecodeError:
            return []

    def set_tools_list(self, tools: list):
        """设置工具列表"""
        self.selected_tools = json.dumps(tools, ensure_ascii=False)
