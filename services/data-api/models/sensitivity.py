"""
敏感数据扫描模型
Phase 1.1: 敏感数据扫描任务、模式、识别结果
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


def generate_scan_id() -> str:
    """生成扫描任务ID"""
    import uuid
    return f"scan_{uuid.uuid4().hex[:12]}"


class SensitivityScanTask(Base):
    """敏感数据扫描任务表"""
    __tablename__ = "sensitivity_scan_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment='扫描任务ID')

    # 扫描目标
    target_type = Column(String(32), nullable=False, comment='扫描目标类型: database, table, column, dataset')
    target_id = Column(String(128), comment='目标ID（数据源/表/数据集ID）')
    target_name = Column(String(255), comment='目标名称（用于显示）')

    # 扫描配置
    scan_mode = Column(String(32), default='full', comment='扫描模式: full(全量), incremental(增量), sampling(采样)')
    sample_rate = Column(Integer, default=100, comment='采样率（百分比）')
    confidence_threshold = Column(Integer, default=70, comment='置信度阈值 0-100')

    # 扫描范围
    databases = Column(Text, comment='扫描的数据库列表 (JSON)')
    tables = Column(Text, comment='扫描的表列表 (JSON)')
    exclude_patterns = Column(Text, comment='排除的表/列模式 (JSON)')

    # 状态
    status = Column(String(32), default='pending', comment='状态: pending, running, completed, failed, cancelled')
    progress = Column(Integer, default=0, comment='进度百分比 0-100')

    # 扫描结果统计
    total_columns = Column(Integer, default=0, comment='总列数')
    scanned_columns = Column(Integer, default=0, comment='已扫描列数')
    sensitive_found = Column(Integer, default=0, comment='发现敏感字段数')

    # 详细结果（按类型）
    pii_count = Column(Integer, default=0, comment='PII类型数量')
    financial_count = Column(Integer, default=0, comment='财务类型数量')
    health_count = Column(Integer, default=0, comment='健康类型数量')
    credential_count = Column(Integer, default=0, comment='凭证类型数量')

    # 时间信息
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')
    estimated_duration = Column(Integer, comment='预估耗时（秒）')

    # 执行信息
    created_by = Column(String(128), comment='创建者')
    error_message = Column(Text, comment='错误信息')

    # 关联结果
    results = relationship("SensitivityScanResult", back_populates="task", cascade="all, delete-orphan")

    def get_databases(self) -> list:
        """获取数据库列表"""
        if not self.databases:
            return []
        import json
        try:
            return json.loads(self.databases)
        except json.JSONDecodeError:
            return []

    def set_databases(self, databases: list):
        """设置数据库列表"""
        import json
        self.databases = json.dumps(databases, ensure_ascii=False)

    def get_tables(self) -> list:
        """获取表列表"""
        if not self.tables:
            return []
        import json
        try:
            return json.loads(self.tables)
        except json.JSONDecodeError:
            return []

    def set_tables(self, tables: list):
        """设置表列表"""
        import json
        self.tables = json.dumps(tables, ensure_ascii=False)

    def get_exclude_patterns(self) -> list:
        """获取排除模式"""
        if not self.exclude_patterns:
            return []
        import json
        try:
            return json.loads(self.exclude_patterns)
        except json.JSONDecodeError:
            return []

    def set_exclude_patterns(self, patterns: list):
        """设置排除模式"""
        import json
        self.exclude_patterns = json.dumps(patterns, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "scan_mode": self.scan_mode,
            "sample_rate": self.sample_rate,
            "confidence_threshold": self.confidence_threshold,
            "databases": self.get_databases(),
            "tables": self.get_tables(),
            "exclude_patterns": self.get_exclude_patterns(),
            "status": self.status,
            "progress": self.progress,
            "total_columns": self.total_columns,
            "scanned_columns": self.scanned_columns,
            "sensitive_found": self.sensitive_found,
            "pii_count": self.pii_count,
            "financial_count": self.financial_count,
            "health_count": self.health_count,
            "credential_count": self.credential_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration": self.estimated_duration,
            "created_by": self.created_by,
            "error_message": self.error_message,
        }


class SensitivityScanResult(Base):
    """敏感数据扫描结果表"""
    __tablename__ = "sensitivity_scan_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    result_id = Column(String(64), unique=True, nullable=False, index=True, comment='结果ID')

    # 所属任务
    task_id = Column(String(64), ForeignKey('sensitivity_scan_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)

    # 扫描对象
    database_name = Column(String(128), comment='数据库名')
    table_name = Column(String(128), comment='表名')
    column_name = Column(String(128), nullable=False, comment='列名')

    # 识别结果
    sensitivity_type = Column(String(64), comment='敏感类型: pii, financial, health, credential')
    sensitivity_sub_type = Column(String(64), comment='敏感子类型: phone, email, id_card, bank_card, etc.')
    sensitivity_level = Column(String(32), comment='敏感级别: public, internal, confidential, restricted')

    # AI 识别信息
    confidence = Column(Integer, comment='置信度 0-100')
    matched_pattern = Column(String(255), comment='匹配的模式')
    sample_values = Column(Text, comment='样本值 (JSON)')

    # 校验状态
    verified = Column(Boolean, default=False, comment='是否已人工校验')
    verified_by = Column(String(128), comment='校验人')
    verified_at = Column(TIMESTAMP, comment='校验时间')
    verified_result = Column(String(16), comment='校验结果: confirmed, rejected, modified')

    # 修正后的结果
    original_type = Column(String(64), comment='原始识别类型（修正前）')
    original_level = Column(String(32), comment='原始敏感级别（修正前）')
    original_confidence = Column(Integer, comment='原始置信度（修正前）')

    # 脱敏建议
    masking_strategy = Column(String(64), comment='推荐脱敏策略: mask, hash, encrypt, redact')
    is_masked = Column(Boolean, default=False, comment='是否已应用脱敏')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    task = relationship("SensitivityScanTask", back_populates="results")

    def get_sample_values(self) -> list:
        """获取样本值"""
        if not self.sample_values:
            return []
        import json
        try:
            return json.loads(self.sample_values)
        except json.JSONDecodeError:
            return []

    def set_sample_values(self, values: list):
        """设置样本值"""
        import json
        # 限制样本值数量，避免存储过大
        limited_values = values[:10]
        self.sample_values = json.dumps(limited_values, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "sensitivity_type": self.sensitivity_type,
            "sensitivity_sub_type": self.sensitivity_sub_type,
            "sensitivity_level": self.sensitivity_level,
            "confidence": self.confidence,
            "matched_pattern": self.matched_pattern,
            "sample_values": self.get_sample_values(),
            "verified": self.verified,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_result": self.verified_result,
            "original_type": self.original_type,
            "original_level": self.original_level,
            "original_confidence": self.original_confidence,
            "masking_strategy": self.masking_strategy,
            "is_masked": self.is_masked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SensitivityPattern(Base):
    """敏感数据模式库表（动态模式）"""
    __tablename__ = "sensitivity_patterns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    pattern_id = Column(String(64), unique=True, nullable=False, index=True, comment='模式ID')

    # 模式分类
    category = Column(String(64), nullable=False, comment='分类: pii, financial, health, credential')
    sub_type = Column(String(64), nullable=False, comment='子类型: phone, email, id_card, etc.')
    name = Column(String(128), nullable=False, comment='模式名称')

    # 模式定义
    pattern_type = Column(String(32), default='regex', comment='模式类型: regex, keyword, llm')
    pattern = Column(String(512), comment='正则表达式模式')
    keywords = Column(Text, comment='关键词列表 (JSON)')
    description = Column(Text, comment='模式描述')

    # 检测配置
    confidence_weight = Column(Integer, default=80, comment='置信度权重')
    sensitivity_level = Column(String(32), default='confidential', comment='默认敏感级别')
    masking_strategy = Column(String(64), default='mask', comment='推荐脱敏策略')

    # 示例
    examples = Column(Text, comment='匹配示例 (JSON)')
    counter_examples = Column(Text, comment='不匹配示例 (JSON)')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_system = Column(Boolean, default=False, comment='是否系统预置')

    # 统计
    match_count = Column(Integer, default=0, comment='匹配次数')
    false_positive_count = Column(Integer, default=0, comment='误报次数')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    created_by = Column(String(128), comment='创建者')

    def get_keywords(self) -> list:
        """获取关键词列表"""
        if not self.keywords:
            return []
        import json
        try:
            return json.loads(self.keywords)
        except json.JSONDecodeError:
            return []

    def set_keywords(self, keywords: list):
        """设置关键词列表"""
        import json
        self.keywords = json.dumps(keywords, ensure_ascii=False)

    def get_examples(self) -> list:
        """获取示例"""
        if not self.examples:
            return []
        import json
        try:
            return json.loads(self.examples)
        except json.JSONDecodeError:
            return []

    def set_examples(self, examples: list):
        """设置示例"""
        import json
        self.examples = json.dumps(examples, ensure_ascii=False)

    def get_counter_examples(self) -> list:
        """获取反例"""
        if not self.counter_examples:
            return []
        import json
        try:
            return json.loads(self.counter_examples)
        except json.JSONDecodeError:
            return []

    def set_counter_examples(self, examples: list):
        """设置反例"""
        import json
        self.counter_examples = json.dumps(examples, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category,
            "sub_type": self.sub_type,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "pattern": self.pattern,
            "keywords": self.get_keywords(),
            "description": self.description,
            "confidence_weight": self.confidence_weight,
            "sensitivity_level": self.sensitivity_level,
            "masking_strategy": self.masking_strategy,
            "examples": self.get_examples(),
            "counter_examples": self.get_counter_examples(),
            "is_active": self.is_active,
            "is_system": self.is_system,
            "match_count": self.match_count,
            "false_positive_count": self.false_positive_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }
