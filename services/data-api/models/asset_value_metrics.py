"""
资产价值评估指标模型
Phase 1.1: 资产使用指标、业务价值评估
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Float, Integer, TIMESTAMP, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class AssetValueMetrics(Base):
    """资产价值评估指标表"""
    __tablename__ = "asset_value_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metrics_id = Column(String(64), unique=True, nullable=False, index=True, comment='指标ID')

    # 关联资产
    asset_id = Column(String(64), nullable=False, index=True, comment='关联的资产ID')
    asset_type = Column(String(32), default='table', comment='资产类型: table, column, dataset, api')

    # ==================== 使用指标 ====================
    # 使用频率评分 (0-100)
    usage_frequency_score = Column(Float, default=0.0, comment='使用频率评分')
    daily_query_count = Column(Integer, default=0, comment='日均查询次数')
    weekly_active_users = Column(Integer, default=0, comment='周活跃用户数')
    monthly_access_count = Column(Integer, default=0, comment='月访问次数')

    # 复用率
    reuse_rate = Column(Float, default=0.0, comment='复用率 (0-1)')
    dependent_asset_count = Column(Integer, default=0, comment='依赖此资产的下游资产数')
    referencing_job_count = Column(Integer, default=0, comment='引用此资产的作业数')
    referencing_report_count = Column(Integer, default=0, comment='引用此资产的报表数')

    # ==================== 业务指标 ====================
    # 业务重要度评分 (0-100)
    business_importance_score = Column(Float, default=0.0, comment='业务重要度评分')
    business_domain = Column(String(64), comment='所属业务域')
    is_core_indicator = Column(Integer, default=0, comment='是否核心指标: 0-否, 1-是')
    business_owner = Column(String(128), comment='业务负责人')
    sla_level = Column(String(16), comment='SLA级别: gold, silver, bronze')

    # ==================== 质量指标 ====================
    # 数据质量评分 (0-100)
    quality_score = Column(Float, default=0.0, comment='数据质量评分')
    completeness_score = Column(Float, default=0.0, comment='完整性评分')
    accuracy_score = Column(Float, default=0.0, comment='准确性评分')
    consistency_score = Column(Float, default=0.0, comment='一致性评分')
    timeliness_score = Column(Float, default=0.0, comment='时效性评分')

    # ==================== 治理指标 ====================
    # 治理成熟度评分 (0-100)
    governance_score = Column(Float, default=0.0, comment='治理成熟度评分')
    has_owner = Column(Integer, default=0, comment='是否有负责人')
    has_description = Column(Integer, default=0, comment='是否有描述')
    has_lineage = Column(Integer, default=0, comment='是否有血缘')
    has_quality_rules = Column(Integer, default=0, comment='是否有质量规则')
    security_level = Column(String(16), comment='安全级别')

    # ==================== 综合评分 ====================
    # 综合价值评分 (0-100)
    overall_value_score = Column(Float, default=0.0, comment='综合价值评分')
    # 价值等级
    asset_value_level = Column(String(8), default='C', comment='价值等级: S/A/B/C')
    # 评分权重配置
    weight_config = Column(JSON, comment='评分权重配置')

    # 计算详情
    calculation_details = Column(JSON, comment='计算详情（JSON）')

    # 时间戳
    calculated_at = Column(TIMESTAMP, comment='计算时间')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "metrics_id": self.metrics_id,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            # 使用指标
            "usage_metrics": {
                "usage_frequency_score": self.usage_frequency_score,
                "daily_query_count": self.daily_query_count,
                "weekly_active_users": self.weekly_active_users,
                "monthly_access_count": self.monthly_access_count,
                "reuse_rate": self.reuse_rate,
                "dependent_asset_count": self.dependent_asset_count,
                "referencing_job_count": self.referencing_job_count,
                "referencing_report_count": self.referencing_report_count,
            },
            # 业务指标
            "business_metrics": {
                "business_importance_score": self.business_importance_score,
                "business_domain": self.business_domain,
                "is_core_indicator": bool(self.is_core_indicator),
                "business_owner": self.business_owner,
                "sla_level": self.sla_level,
            },
            # 质量指标
            "quality_metrics": {
                "quality_score": self.quality_score,
                "completeness_score": self.completeness_score,
                "accuracy_score": self.accuracy_score,
                "consistency_score": self.consistency_score,
                "timeliness_score": self.timeliness_score,
            },
            # 治理指标
            "governance_metrics": {
                "governance_score": self.governance_score,
                "has_owner": bool(self.has_owner),
                "has_description": bool(self.has_description),
                "has_lineage": bool(self.has_lineage),
                "has_quality_rules": bool(self.has_quality_rules),
                "security_level": self.security_level,
            },
            # 综合评分
            "overall_value_score": self.overall_value_score,
            "asset_value_level": self.asset_value_level,
            "weight_config": self.weight_config,
            "calculation_details": self.calculation_details,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AssetValueHistory(Base):
    """资产价值历史记录表"""
    __tablename__ = "asset_value_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    history_id = Column(String(64), unique=True, nullable=False, index=True, comment='历史记录ID')

    asset_id = Column(String(64), nullable=False, index=True, comment='资产ID')
    overall_value_score = Column(Float, comment='综合价值评分')
    asset_value_level = Column(String(8), comment='价值等级')

    # 各维度评分快照
    usage_frequency_score = Column(Float, comment='使用频率评分')
    business_importance_score = Column(Float, comment='业务重要度评分')
    quality_score = Column(Float, comment='数据质量评分')
    governance_score = Column(Float, comment='治理成熟度评分')

    # 评估时间
    evaluated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='评估时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "history_id": self.history_id,
            "asset_id": self.asset_id,
            "overall_value_score": self.overall_value_score,
            "asset_value_level": self.asset_value_level,
            "usage_frequency_score": self.usage_frequency_score,
            "business_importance_score": self.business_importance_score,
            "quality_score": self.quality_score,
            "governance_score": self.governance_score,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


class AssetUsageLog(Base):
    """资产使用日志表 - 用于计算使用指标"""
    __tablename__ = "asset_usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    asset_id = Column(String(64), nullable=False, index=True, comment='资产ID')
    asset_type = Column(String(32), comment='资产类型')

    # 使用信息
    usage_type = Column(String(32), nullable=False, comment='使用类型: query, download, api_call, reference')
    user_id = Column(String(128), comment='使用者ID')
    user_name = Column(String(128), comment='使用者名称')

    # 来源信息
    source_type = Column(String(32), comment='来源类型: dashboard, report, etl_job, api, adhoc')
    source_id = Column(String(128), comment='来源ID')
    source_name = Column(String(255), comment='来源名称')

    # 时间
    usage_time = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='使用时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "usage_type": self.usage_type,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "usage_time": self.usage_time.isoformat() if self.usage_time else None,
        }
