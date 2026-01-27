"""
资产价值计算器服务
Phase 1.1: 综合价值评分模型、价值等级分配、价值排序
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc

logger = logging.getLogger(__name__)


class ValueLevel(str, Enum):
    """价值等级"""
    S = "S"  # 战略级 (>=80)
    A = "A"  # 核心级 (>=60)
    B = "B"  # 重要级 (>=40)
    C = "C"  # 基础级 (<40)


@dataclass
class ValueScoreBreakdown:
    """价值评分分解"""
    usage_score: float = 0.0
    business_score: float = 0.0
    quality_score: float = 0.0
    governance_score: float = 0.0
    overall_score: float = 0.0
    value_level: str = "C"
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "usage_score": round(self.usage_score, 2),
            "business_score": round(self.business_score, 2),
            "quality_score": round(self.quality_score, 2),
            "governance_score": round(self.governance_score, 2),
            "overall_score": round(self.overall_score, 2),
            "value_level": self.value_level,
            "details": self.details,
        }


@dataclass
class AssetValueReport:
    """资产价值报告"""
    asset_id: str
    asset_name: str
    asset_type: str
    score_breakdown: ValueScoreBreakdown
    ranking: int = 0
    trend: str = "stable"  # up, down, stable
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "score_breakdown": self.score_breakdown.to_dict(),
            "ranking": self.ranking,
            "trend": self.trend,
            "recommendations": self.recommendations,
        }


class AssetValueCalculator:
    """资产价值计算器"""

    # 默认权重配置
    DEFAULT_WEIGHTS = {
        "usage": 0.35,      # 使用指标权重
        "business": 0.30,   # 业务指标权重
        "quality": 0.20,    # 质量指标权重
        "governance": 0.15, # 治理指标权重
    }

    # 价值等级阈值
    LEVEL_THRESHOLDS = {
        ValueLevel.S: 80,   # >=80 为S级
        ValueLevel.A: 60,   # >=60 为A级
        ValueLevel.B: 40,   # >=40 为B级
        ValueLevel.C: 0,    # <40 为C级
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化价值计算器

        Args:
            weights: 自定义权重配置
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def _normalize_weights(self):
        """归一化权重，确保总和为1"""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def calculate_usage_score(
        self,
        db: Session,
        asset_id: str,
        lookback_days: int = 30
    ) -> Tuple[float, Dict]:
        """
        计算使用指标评分

        基于：
        - 日均查询次数
        - 活跃用户数
        - 下游依赖数
        - 复用率

        Returns:
            (评分, 详情字典)
        """
        from models.asset_value_metrics import AssetUsageLog
        from models.lineage import LineageEdge

        details = {
            "daily_query_count": 0,
            "active_users": 0,
            "dependent_count": 0,
            "reuse_rate": 0.0,
        }

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            # 计算日均查询次数
            usage_count = db.query(func.count(AssetUsageLog.id)).filter(
                AssetUsageLog.asset_id == asset_id,
                AssetUsageLog.usage_time >= cutoff_date
            ).scalar() or 0

            details["daily_query_count"] = usage_count / lookback_days if lookback_days > 0 else 0

            # 计算活跃用户数
            active_users = db.query(func.count(func.distinct(AssetUsageLog.user_id))).filter(
                AssetUsageLog.asset_id == asset_id,
                AssetUsageLog.usage_time >= cutoff_date
            ).scalar() or 0

            details["active_users"] = active_users

            # 计算下游依赖数（血缘关系）
            dependent_count = db.query(func.count(LineageEdge.id)).filter(
                LineageEdge.source_id == asset_id
            ).scalar() or 0

            details["dependent_count"] = dependent_count

            # 计算复用率（被多个来源使用的比例）
            source_types = db.query(func.count(func.distinct(AssetUsageLog.source_type))).filter(
                AssetUsageLog.asset_id == asset_id,
                AssetUsageLog.usage_time >= cutoff_date
            ).scalar() or 0

            details["reuse_rate"] = min(source_types / 5.0, 1.0)  # 假设5种以上来源为100%复用

            # 计算综合使用评分
            # 日均查询贡献 (0-40分)
            query_score = min(details["daily_query_count"] / 100, 1.0) * 40

            # 活跃用户贡献 (0-30分)
            user_score = min(active_users / 50, 1.0) * 30

            # 下游依赖贡献 (0-20分)
            dependent_score = min(dependent_count / 20, 1.0) * 20

            # 复用率贡献 (0-10分)
            reuse_score = details["reuse_rate"] * 10

            score = query_score + user_score + dependent_score + reuse_score

        except Exception as e:
            logger.warning(f"计算使用评分失败 {asset_id}: {e}")
            score = 0.0

        return score, details

    def calculate_business_score(
        self,
        db: Session,
        asset_id: str,
        business_config: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        计算业务重要度评分

        基于：
        - 是否核心指标
        - SLA级别
        - 业务域重要性
        - 业务负责人级别

        Returns:
            (评分, 详情字典)
        """
        from models.assets import DataAsset
        from models.asset_value_metrics import AssetValueMetrics

        details = {
            "is_core_indicator": False,
            "sla_level": None,
            "business_domain": None,
            "has_owner": False,
        }

        try:
            # 获取资产信息
            asset = db.query(DataAsset).filter(
                DataAsset.asset_id == asset_id
            ).first()

            if not asset:
                return 0.0, details

            # 获取已有的价值指标
            metrics = db.query(AssetValueMetrics).filter(
                AssetValueMetrics.asset_id == asset_id
            ).first()

            score = 0.0

            # 核心指标加分 (0-30分)
            if metrics and metrics.is_core_indicator:
                score += 30
                details["is_core_indicator"] = True

            # SLA级别加分 (0-25分)
            sla_scores = {"gold": 25, "silver": 15, "bronze": 5}
            if metrics and metrics.sla_level:
                score += sla_scores.get(metrics.sla_level, 0)
                details["sla_level"] = metrics.sla_level

            # 业务域重要性 (0-25分)
            # 如果有配置的业务域权重
            if business_config and metrics and metrics.business_domain:
                domain_weights = business_config.get("domain_weights", {})
                domain_score = domain_weights.get(metrics.business_domain, 0.5) * 25
                score += domain_score
                details["business_domain"] = metrics.business_domain
            else:
                score += 12.5  # 默认中等重要性

            # 有业务负责人 (0-20分)
            if asset.owner or (metrics and metrics.business_owner):
                score += 20
                details["has_owner"] = True

        except Exception as e:
            logger.warning(f"计算业务评分失败 {asset_id}: {e}")
            score = 0.0

        return score, details

    def calculate_quality_score(
        self,
        db: Session,
        asset_id: str
    ) -> Tuple[float, Dict]:
        """
        计算数据质量评分

        基于：
        - 完整性
        - 准确性
        - 一致性
        - 时效性

        Returns:
            (评分, 详情字典)
        """
        from models.quality import QualityReport
        from models.asset_value_metrics import AssetValueMetrics

        details = {
            "completeness": 0.0,
            "accuracy": 0.0,
            "consistency": 0.0,
            "timeliness": 0.0,
            "has_quality_reports": False,
        }

        try:
            # 获取最近的质量报告
            recent_report = db.query(QualityReport).filter(
                QualityReport.target_id == asset_id
            ).order_by(desc(QualityReport.created_at)).first()

            if recent_report:
                details["has_quality_reports"] = True

                # 从报告中提取质量指标
                if recent_report.result_data:
                    result_data = recent_report.result_data
                    details["completeness"] = result_data.get("completeness", 0.0)
                    details["accuracy"] = result_data.get("accuracy", 0.0)
                    details["consistency"] = result_data.get("consistency", 0.0)
                    details["timeliness"] = result_data.get("timeliness", 0.0)

                # 计算综合质量评分
                score = (
                    details["completeness"] * 0.3 +
                    details["accuracy"] * 0.3 +
                    details["consistency"] * 0.2 +
                    details["timeliness"] * 0.2
                )
            else:
                # 获取已保存的指标
                metrics = db.query(AssetValueMetrics).filter(
                    AssetValueMetrics.asset_id == asset_id
                ).first()

                if metrics:
                    details["completeness"] = metrics.completeness_score or 0.0
                    details["accuracy"] = metrics.accuracy_score or 0.0
                    details["consistency"] = metrics.consistency_score or 0.0
                    details["timeliness"] = metrics.timeliness_score or 0.0

                    score = (
                        details["completeness"] * 0.3 +
                        details["accuracy"] * 0.3 +
                        details["consistency"] * 0.2 +
                        details["timeliness"] * 0.2
                    )
                else:
                    score = 50.0  # 默认中等质量

        except Exception as e:
            logger.warning(f"计算质量评分失败 {asset_id}: {e}")
            score = 50.0

        return score, details

    def calculate_governance_score(
        self,
        db: Session,
        asset_id: str
    ) -> Tuple[float, Dict]:
        """
        计算治理成熟度评分

        基于：
        - 是否有负责人
        - 是否有描述
        - 是否有血缘
        - 是否有质量规则
        - 安全级别

        Returns:
            (评分, 详情字典)
        """
        from models.assets import DataAsset
        from models.lineage import LineageEdge
        from models.quality import QualityRule

        details = {
            "has_owner": False,
            "has_description": False,
            "has_lineage": False,
            "has_quality_rules": False,
            "security_level": None,
        }

        try:
            # 获取资产信息
            asset = db.query(DataAsset).filter(
                DataAsset.asset_id == asset_id
            ).first()

            score = 0.0

            if asset:
                # 有负责人 (0-20分)
                if asset.owner:
                    score += 20
                    details["has_owner"] = True

                # 有描述 (0-20分)
                if asset.description:
                    score += 20
                    details["has_description"] = True

            # 有血缘关系 (0-20分)
            lineage_count = db.query(func.count(LineageEdge.id)).filter(
                (LineageEdge.source_id == asset_id) |
                (LineageEdge.target_id == asset_id)
            ).scalar() or 0

            if lineage_count > 0:
                score += 20
                details["has_lineage"] = True

            # 有质量规则 (0-20分)
            rule_count = db.query(func.count(QualityRule.id)).filter(
                QualityRule.target_id == asset_id
            ).scalar() or 0

            if rule_count > 0:
                score += 20
                details["has_quality_rules"] = True

            # 安全级别加分 (0-20分)
            if asset and hasattr(asset, 'security_level') and asset.security_level:
                security_scores = {
                    "public": 5,
                    "internal": 10,
                    "confidential": 15,
                    "restricted": 20
                }
                score += security_scores.get(asset.security_level, 5)
                details["security_level"] = asset.security_level
            else:
                score += 5  # 默认

        except Exception as e:
            logger.warning(f"计算治理评分失败 {asset_id}: {e}")
            score = 0.0

        return score, details

    def calculate_overall_score(
        self,
        usage_score: float,
        business_score: float,
        quality_score: float,
        governance_score: float
    ) -> float:
        """
        计算综合价值评分

        Args:
            usage_score: 使用评分 (0-100)
            business_score: 业务评分 (0-100)
            quality_score: 质量评分 (0-100)
            governance_score: 治理评分 (0-100)

        Returns:
            综合评分 (0-100)
        """
        overall = (
            usage_score * self.weights["usage"] +
            business_score * self.weights["business"] +
            quality_score * self.weights["quality"] +
            governance_score * self.weights["governance"]
        )
        return min(max(overall, 0), 100)

    def assign_value_level(self, score: float) -> str:
        """
        分配价值等级

        Args:
            score: 综合评分 (0-100)

        Returns:
            价值等级 (S/A/B/C)
        """
        if score >= self.LEVEL_THRESHOLDS[ValueLevel.S]:
            return ValueLevel.S.value
        elif score >= self.LEVEL_THRESHOLDS[ValueLevel.A]:
            return ValueLevel.A.value
        elif score >= self.LEVEL_THRESHOLDS[ValueLevel.B]:
            return ValueLevel.B.value
        else:
            return ValueLevel.C.value

    def evaluate_asset(
        self,
        db: Session,
        asset_id: str,
        business_config: Optional[Dict] = None,
        save_result: bool = True
    ) -> ValueScoreBreakdown:
        """
        评估单个资产的价值

        Args:
            db: 数据库会话
            asset_id: 资产ID
            business_config: 业务配置
            save_result: 是否保存结果

        Returns:
            价值评分分解
        """
        # 计算各维度评分
        usage_score, usage_details = self.calculate_usage_score(db, asset_id)
        business_score, business_details = self.calculate_business_score(
            db, asset_id, business_config
        )
        quality_score, quality_details = self.calculate_quality_score(db, asset_id)
        governance_score, governance_details = self.calculate_governance_score(db, asset_id)

        # 计算综合评分
        overall_score = self.calculate_overall_score(
            usage_score, business_score, quality_score, governance_score
        )

        # 分配价值等级
        value_level = self.assign_value_level(overall_score)

        breakdown = ValueScoreBreakdown(
            usage_score=usage_score,
            business_score=business_score,
            quality_score=quality_score,
            governance_score=governance_score,
            overall_score=overall_score,
            value_level=value_level,
            details={
                "usage": usage_details,
                "business": business_details,
                "quality": quality_details,
                "governance": governance_details,
                "weights": self.weights,
            }
        )

        # 保存结果
        if save_result:
            self._save_metrics(db, asset_id, breakdown)

        return breakdown

    def _save_metrics(
        self,
        db: Session,
        asset_id: str,
        breakdown: ValueScoreBreakdown
    ):
        """保存评估结果到数据库"""
        from models.asset_value_metrics import AssetValueMetrics, AssetValueHistory

        try:
            # 更新或创建指标记录
            metrics = db.query(AssetValueMetrics).filter(
                AssetValueMetrics.asset_id == asset_id
            ).first()

            if not metrics:
                metrics = AssetValueMetrics(
                    metrics_id=f"vm_{uuid.uuid4().hex[:12]}",
                    asset_id=asset_id,
                )
                db.add(metrics)

            # 更新评分
            metrics.usage_frequency_score = breakdown.usage_score
            metrics.business_importance_score = breakdown.business_score
            metrics.quality_score = breakdown.quality_score
            metrics.governance_score = breakdown.governance_score
            metrics.overall_value_score = breakdown.overall_score
            metrics.asset_value_level = breakdown.value_level
            metrics.weight_config = self.weights
            metrics.calculation_details = breakdown.details
            metrics.calculated_at = datetime.utcnow()

            # 更新详细指标
            usage_details = breakdown.details.get("usage", {})
            metrics.daily_query_count = int(usage_details.get("daily_query_count", 0))
            metrics.weekly_active_users = usage_details.get("active_users", 0)
            metrics.dependent_asset_count = usage_details.get("dependent_count", 0)
            metrics.reuse_rate = usage_details.get("reuse_rate", 0.0)

            business_details = breakdown.details.get("business", {})
            metrics.is_core_indicator = 1 if business_details.get("is_core_indicator") else 0
            metrics.sla_level = business_details.get("sla_level")
            metrics.business_domain = business_details.get("business_domain")

            quality_details = breakdown.details.get("quality", {})
            metrics.completeness_score = quality_details.get("completeness", 0.0)
            metrics.accuracy_score = quality_details.get("accuracy", 0.0)
            metrics.consistency_score = quality_details.get("consistency", 0.0)
            metrics.timeliness_score = quality_details.get("timeliness", 0.0)

            governance_details = breakdown.details.get("governance", {})
            metrics.has_owner = 1 if governance_details.get("has_owner") else 0
            metrics.has_description = 1 if governance_details.get("has_description") else 0
            metrics.has_lineage = 1 if governance_details.get("has_lineage") else 0
            metrics.has_quality_rules = 1 if governance_details.get("has_quality_rules") else 0
            metrics.security_level = governance_details.get("security_level")

            # 添加历史记录
            history = AssetValueHistory(
                history_id=f"vh_{uuid.uuid4().hex[:12]}",
                asset_id=asset_id,
                overall_value_score=breakdown.overall_score,
                asset_value_level=breakdown.value_level,
                usage_frequency_score=breakdown.usage_score,
                business_importance_score=breakdown.business_score,
                quality_score=breakdown.quality_score,
                governance_score=breakdown.governance_score,
            )
            db.add(history)

            db.commit()

        except Exception as e:
            logger.error(f"保存价值指标失败 {asset_id}: {e}")
            db.rollback()

    def get_asset_ranking(
        self,
        db: Session,
        limit: int = 100,
        offset: int = 0,
        asset_type: Optional[str] = None,
        value_level: Optional[str] = None
    ) -> List[Dict]:
        """
        获取资产价值排名

        Args:
            db: 数据库会话
            limit: 限制数量
            offset: 偏移量
            asset_type: 资产类型筛选
            value_level: 价值等级筛选

        Returns:
            排名列表
        """
        from models.asset_value_metrics import AssetValueMetrics
        from models.assets import DataAsset

        try:
            query = db.query(
                AssetValueMetrics,
                DataAsset.name.label("asset_name"),
                DataAsset.type.label("asset_type_name")
            ).outerjoin(
                DataAsset,
                DataAsset.asset_id == AssetValueMetrics.asset_id
            )

            if asset_type:
                query = query.filter(AssetValueMetrics.asset_type == asset_type)

            if value_level:
                query = query.filter(AssetValueMetrics.asset_value_level == value_level)

            results = query.order_by(
                desc(AssetValueMetrics.overall_value_score)
            ).limit(limit).offset(offset).all()

            ranking = []
            for i, (metrics, asset_name, asset_type_name) in enumerate(results):
                ranking.append({
                    "rank": offset + i + 1,
                    "asset_id": metrics.asset_id,
                    "asset_name": asset_name or metrics.asset_id,
                    "asset_type": asset_type_name or metrics.asset_type,
                    "overall_score": metrics.overall_value_score,
                    "value_level": metrics.asset_value_level,
                    "usage_score": metrics.usage_frequency_score,
                    "business_score": metrics.business_importance_score,
                    "quality_score": metrics.quality_score,
                    "governance_score": metrics.governance_score,
                    "calculated_at": metrics.calculated_at.isoformat() if metrics.calculated_at else None,
                })

            return ranking

        except Exception as e:
            logger.error(f"获取资产排名失败: {e}")
            return []

    def get_value_distribution(self, db: Session) -> Dict:
        """
        获取价值等级分布

        Returns:
            分布统计
        """
        from models.asset_value_metrics import AssetValueMetrics

        try:
            distribution = db.query(
                AssetValueMetrics.asset_value_level,
                func.count(AssetValueMetrics.id).label('count')
            ).group_by(
                AssetValueMetrics.asset_value_level
            ).all()

            result = {
                "S": 0,
                "A": 0,
                "B": 0,
                "C": 0,
            }
            total = 0

            for level, count in distribution:
                if level in result:
                    result[level] = count
                    total += count

            # 计算百分比
            percentages = {
                level: round(count / total * 100, 2) if total > 0 else 0
                for level, count in result.items()
            }

            return {
                "counts": result,
                "percentages": percentages,
                "total": total,
            }

        except Exception as e:
            logger.error(f"获取价值分布失败: {e}")
            return {"counts": {}, "percentages": {}, "total": 0}

    def get_value_trend(
        self,
        db: Session,
        asset_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        获取资产价值趋势

        Args:
            db: 数据库会话
            asset_id: 资产ID
            days: 查看天数

        Returns:
            趋势数据列表
        """
        from models.asset_value_metrics import AssetValueHistory

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            history = db.query(AssetValueHistory).filter(
                AssetValueHistory.asset_id == asset_id,
                AssetValueHistory.evaluated_at >= cutoff_date
            ).order_by(AssetValueHistory.evaluated_at).all()

            return [h.to_dict() for h in history]

        except Exception as e:
            logger.error(f"获取价值趋势失败 {asset_id}: {e}")
            return []

    def generate_recommendations(
        self,
        breakdown: ValueScoreBreakdown
    ) -> List[str]:
        """
        根据评分生成改进建议

        Args:
            breakdown: 评分分解

        Returns:
            建议列表
        """
        recommendations = []

        # 使用指标建议
        if breakdown.usage_score < 40:
            recommendations.append("提升资产曝光度：考虑在数据目录中增加资产描述和标签，提高可发现性")
            if breakdown.details.get("usage", {}).get("active_users", 0) < 5:
                recommendations.append("增加用户触达：组织培训或分享会，让更多业务用户了解此数据资产")

        # 业务指标建议
        if breakdown.business_score < 40:
            if not breakdown.details.get("business", {}).get("has_owner"):
                recommendations.append("指定业务负责人：为资产分配明确的业务Owner，提升治理水平")
            if not breakdown.details.get("business", {}).get("sla_level"):
                recommendations.append("定义SLA级别：根据业务重要性为资产设定服务级别协议")

        # 质量指标建议
        if breakdown.quality_score < 60:
            quality_details = breakdown.details.get("quality", {})
            if quality_details.get("completeness", 100) < 80:
                recommendations.append("提升数据完整性：检查并修复空值率较高的字段")
            if quality_details.get("accuracy", 100) < 80:
                recommendations.append("提升数据准确性：建立数据校验规则，定期检测异常值")
            if not quality_details.get("has_quality_reports"):
                recommendations.append("建立质量监控：配置数据质量规则并启用定期检测")

        # 治理指标建议
        if breakdown.governance_score < 60:
            governance_details = breakdown.details.get("governance", {})
            if not governance_details.get("has_description"):
                recommendations.append("补充资产描述：添加详细的业务含义说明和使用说明")
            if not governance_details.get("has_lineage"):
                recommendations.append("建立数据血缘：记录数据来源和流转关系，提升可追溯性")
            if not governance_details.get("has_quality_rules"):
                recommendations.append("配置质量规则：为关键字段设置数据质量校验规则")

        return recommendations

    def batch_evaluate(
        self,
        db: Session,
        asset_ids: List[str],
        business_config: Optional[Dict] = None
    ) -> List[ValueScoreBreakdown]:
        """
        批量评估资产价值

        Args:
            db: 数据库会话
            asset_ids: 资产ID列表
            business_config: 业务配置

        Returns:
            评分列表
        """
        results = []
        for asset_id in asset_ids:
            try:
                breakdown = self.evaluate_asset(db, asset_id, business_config)
                results.append(breakdown)
            except Exception as e:
                logger.error(f"评估资产失败 {asset_id}: {e}")
                results.append(ValueScoreBreakdown())
        return results


# 全局实例
_asset_value_calculator = None


def get_asset_value_calculator() -> AssetValueCalculator:
    """获取资产价值计算器单例"""
    global _asset_value_calculator
    if _asset_value_calculator is None:
        _asset_value_calculator = AssetValueCalculator()
    return _asset_value_calculator
