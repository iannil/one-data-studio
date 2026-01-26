"""
提取规则/模板模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean

from models.base import Base


class ExtractionTemplate(Base):
    """提取模板表"""
    __tablename__ = "extraction_templates"

    id = Column(String(64), primary_key=True, comment="模板ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(64), comment="创建用户ID")

    # 模板基本信息
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    template_type = Column(String(20), nullable=False, comment="模板类型: invoice/contract/report/table/general")
    category = Column(String(50), comment="分类")

    # 文档类型支持
    supported_formats = Column(JSON, comment="支持的文档格式列表")

    # 提取规则配置
    extraction_rules = Column(JSON, nullable=False, comment="提取规则配置")
    # 规则结构示例:
    # {
    #     "fields": [
    #         {
    #             "name": "发票号码",
    #             "key": "invoice_number",
    #             "required": true,
    #             "extraction_method": "regex|keyword|position|ai",
    #             "pattern": "发票号码[:：]\\s*([\\d]+)",
    #             "keywords": ["发票号码", "No."],
    #             "validation": {"type": "regex", "pattern": "^\\d{8,20}$"}
    #         }
    #     ],
    #     "tables": [
    #         {
    #             "name": "商品明细",
    #             "key": "items",
    #             "required": true,
    #             "header_keywords": ["商品", "数量", "单价", "金额"]
    #         }
    #     ]
    # }

    # AI提示词模板
    ai_prompt_template = Column(Text, comment="AI提取提示词模板")

    # 后处理规则
    post_processing = Column(JSON, comment="后处理规则")
    # 示例: {"date_format": "YYYY-MM-DD", "amount_format": "number"}

    # 模板状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_public = Column(Boolean, default=False, comment="是否公开(跨租户)")
    version = Column(Integer, default=1, comment="版本号")

    # 使用统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    success_rate = Column(Integer, default=0, comment="成功率(百分比)")

    # 质量指标
    avg_confidence = Column(Integer, comment="平均置信度")
    last_used_at = Column(DateTime, comment="最后使用时间")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type,
            "category": self.category,
            "supported_formats": self.supported_formats,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "version": self.version,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "avg_confidence": self.avg_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ExtractionTemplate(id={self.id}, name={self.name}, type={self.template_type})>"


class ExtractionRule(Base):
    """通用提取规则表"""
    __tablename__ = "extraction_rules"

    id = Column(String(64), primary_key=True, comment="规则ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户ID")

    # 规则基本信息
    name = Column(String(100), nullable=False, comment="规则名称")
    rule_type = Column(String(20), nullable=False, comment="规则类型: regex/keyword/layout/ai")
    field_name = Column(String(50), comment="适用字段名")

    # 规则配置
    pattern = Column(Text, comment="正则表达式模式")
    keywords = Column(JSON, comment="关键词列表")
    position_hint = Column(JSON, comment="位置提示")
    confidence_threshold = Column(Integer, default=70, comment="置信度阈值")

    # 规则状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级，数字越大优先级越高")

    # 统计信息
    match_count = Column(Integer, default=0, comment="匹配次数")
    false_positive_count = Column(Integer, default=0, comment="误报次数")

    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "field_name": self.field_name,
            "pattern": self.pattern,
            "keywords": self.keywords,
            "position_hint": self.position_hint,
            "confidence_threshold": self.confidence_threshold,
            "is_active": self.is_active,
            "priority": self.priority,
            "match_count": self.match_count,
            "false_positive_count": self.false_positive_count,
        }
