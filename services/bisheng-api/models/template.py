"""
模板管理模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func

from .base import Base


class Template(Base):
    """工作流模板表"""
    __tablename__ = "templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, comment='模板唯一标识')
    name = Column(String(255), nullable=False, comment='模板名称')
    description = Column(Text, comment='模板描述')
    category = Column(String(64), default='general', comment='分类: rag, agent, sql, general')
    thumbnail = Column(String(512), comment='缩略图URL')
    definition = Column(Text, comment='工作流定义 (JSON)')
    nodes = Column(Text, comment='节点定义 (JSON)')
    edges = Column(Text, comment='边定义 (JSON)')
    created_by = Column(String(128), comment='创建者')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    tags = Column(Text, comment='标签 (JSON数组字符串)')
    is_public = Column(Boolean, default=True, comment='是否公开')

    def get_nodes(self) -> list:
        """获取节点列表"""
        if not self.nodes:
            return []
        import json
        try:
            return json.loads(self.nodes)
        except json.JSONDecodeError:
            return []

    def set_nodes(self, nodes: list):
        """设置节点列表"""
        import json
        self.nodes = json.dumps(nodes, ensure_ascii=False)

    def get_edges(self) -> list:
        """获取边列表"""
        if not self.edges:
            return []
        import json
        try:
            return json.loads(self.edges)
        except json.JSONDecodeError:
            return []

    def set_edges(self, edges: list):
        """设置边列表"""
        import json
        self.edges = json.dumps(edges, ensure_ascii=False)

    def get_tags(self) -> list:
        """获取标签列表"""
        if not self.tags:
            return []
        import json
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list):
        """设置标签列表"""
        import json
        self.tags = json.dumps(tags, ensure_ascii=False)

    def to_dict(self, include_definition: bool = False) -> dict:
        """转换为字典"""
        result = {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description or "",
            "category": self.category,
            "thumbnail": self.thumbnail,
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
            "created_by": self.created_by or "unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.get_tags(),
            "is_public": getattr(self, 'is_public', True)
        }
        if include_definition and self.definition:
            import json
            try:
                result["definition"] = json.loads(self.definition)
            except json.JSONDecodeError:
                result["definition"] = {}
        return result
