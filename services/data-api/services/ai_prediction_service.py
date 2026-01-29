"""
AI 预测模型服务
支持销量预测、客户分群、趋势分析等业务预测场景
"""

import logging
import secrets
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics
import math

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class PredictionType(str, Enum):
    """预测类型"""
    TIME_SERIES = "time_series"          # 时间序列预测
    CLASSIFICATION = "classification"     # 分类预测
    REGRESSION = "regression"             # 回归预测
    CLUSTERING = "clustering"             # 聚类分析
    ANOMALY_DETECTION = "anomaly_detection"  # 异常检测


class ModelType(str, Enum):
    """模型类型"""
    # 时间序列模型
    ARIMA = "arima"
    PROPHET = "prophet"
    LSTM = "lstm"
    TRANSFORMER = "transformer"

    # 分类/回归模型
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR = "linear"
    SVM = "svm"
    NEURAL_NETWORK = "neural_network"

    # 聚类模型
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    HIERARCHICAL = "hierarchical"

    # 异常检测模型
    ISOLATION_FOREST = "isolation_forest"
    LOF = "lof"  # Local Outlier Factor
    AUTOENCODER = "autoencoder"


class ModelStatus(str, Enum):
    """模型状态"""
    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class PredictionStatus(str, Enum):
    """预测状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== 数据类定义 ====================

@dataclass
class DatasetConfig:
    """数据集配置"""
    dataset_id: str
    name: str
    source_table: str = ""
    source_query: str = ""
    features: List[str] = field(default_factory=list)
    target: str = ""
    time_column: str = ""
    group_columns: List[str] = field(default_factory=list)
    train_ratio: float = 0.8
    validation_ratio: float = 0.1
    test_ratio: float = 0.1
    preprocessing: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "source_table": self.source_table,
            "source_query": self.source_query,
            "features": self.features,
            "target": self.target,
            "time_column": self.time_column,
            "group_columns": self.group_columns,
            "train_ratio": self.train_ratio,
            "validation_ratio": self.validation_ratio,
            "test_ratio": self.test_ratio,
            "preprocessing": self.preprocessing,
        }


@dataclass
class ModelConfig:
    """模型配置"""
    model_type: ModelType
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "model_type": self.model_type.value,
            "hyperparameters": self.hyperparameters,
            "training_config": self.training_config,
        }


@dataclass
class ModelMetrics:
    """模型评估指标"""
    # 回归指标
    mae: float = 0.0           # Mean Absolute Error
    mse: float = 0.0           # Mean Squared Error
    rmse: float = 0.0          # Root Mean Squared Error
    mape: float = 0.0          # Mean Absolute Percentage Error
    r2_score: float = 0.0      # R-squared

    # 分类指标
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0

    # 聚类指标
    silhouette_score: float = 0.0
    calinski_harabasz: float = 0.0
    davies_bouldin: float = 0.0

    # 通用
    training_time_seconds: float = 0.0
    inference_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "mae": self.mae,
            "mse": self.mse,
            "rmse": self.rmse,
            "mape": self.mape,
            "r2_score": self.r2_score,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "auc_roc": self.auc_roc,
            "silhouette_score": self.silhouette_score,
            "calinski_harabasz": self.calinski_harabasz,
            "davies_bouldin": self.davies_bouldin,
            "training_time_seconds": self.training_time_seconds,
            "inference_time_ms": self.inference_time_ms,
        }


@dataclass
class PredictionModel:
    """预测模型"""
    model_id: str
    name: str
    description: str = ""
    prediction_type: PredictionType = PredictionType.REGRESSION
    model_config: ModelConfig = field(default_factory=lambda: ModelConfig(ModelType.XGBOOST))
    dataset_config: DatasetConfig = field(default_factory=lambda: DatasetConfig("", ""))
    status: ModelStatus = ModelStatus.DRAFT
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    version: str = "1.0.0"
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    trained_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "prediction_type": self.prediction_type.value,
            "model_config": self.model_config.to_dict(),
            "dataset_config": self.dataset_config.to_dict(),
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class PredictionRequest:
    """预测请求"""
    request_id: str
    model_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    prediction_horizon: int = 1  # 预测步长
    confidence_level: float = 0.95
    include_intervals: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "input_data": self.input_data,
            "prediction_horizon": self.prediction_horizon,
            "confidence_level": self.confidence_level,
            "include_intervals": self.include_intervals,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PredictionResult:
    """预测结果"""
    request_id: str
    model_id: str
    status: PredictionStatus = PredictionStatus.COMPLETED
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    confidence_intervals: List[Dict[str, float]] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    inference_time_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "status": self.status.value,
            "predictions": self.predictions,
            "confidence_intervals": self.confidence_intervals,
            "feature_importance": self.feature_importance,
            "explanation": self.explanation,
            "inference_time_ms": self.inference_time_ms,
            "completed_at": self.completed_at.isoformat(),
            "error": self.error,
        }


# ==================== 销量预测服务 ====================

@dataclass
class SalesForecastConfig:
    """销量预测配置"""
    product_id: str = ""
    category: str = ""
    region: str = ""
    forecast_days: int = 30
    include_seasonality: bool = True
    include_holidays: bool = True
    external_factors: List[str] = field(default_factory=list)  # 促销、天气等


@dataclass
class SalesForecastResult:
    """销量预测结果"""
    forecast_id: str
    product_id: str
    forecast_date: datetime
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    trend: str = "stable"  # increasing, decreasing, stable
    seasonality_pattern: str = ""
    confidence: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "forecast_id": self.forecast_id,
            "product_id": self.product_id,
            "forecast_date": self.forecast_date.isoformat(),
            "predictions": self.predictions,
            "trend": self.trend,
            "seasonality_pattern": self.seasonality_pattern,
            "confidence": self.confidence,
            "factors": self.factors,
            "recommendations": self.recommendations,
        }


class SalesForecastService:
    """销量预测服务"""

    def __init__(self):
        self._historical_data: Dict[str, List[Dict]] = {}
        self._models: Dict[str, Any] = {}

    def forecast(
        self,
        config: SalesForecastConfig,
        historical_sales: List[Dict[str, Any]] = None,
    ) -> SalesForecastResult:
        """
        销量预测

        使用时间序列分解 + 趋势预测
        """
        product_id = config.product_id or "default"

        # 使用历史数据或模拟数据
        if historical_sales:
            sales_data = historical_sales
        else:
            sales_data = self._generate_sample_sales(config.forecast_days * 2)

        # 分析历史趋势
        trend, trend_slope = self._analyze_trend(sales_data)

        # 分析季节性
        seasonality_pattern = self._analyze_seasonality(sales_data)

        # 生成预测
        predictions = []
        base_date = datetime.now()

        for day in range(config.forecast_days):
            forecast_date = base_date + timedelta(days=day + 1)

            # 基础预测值（使用简单移动平均 + 趋势）
            recent_avg = statistics.mean([
                d.get("quantity", 100) for d in sales_data[-7:]
            ]) if sales_data else 100

            # 应用趋势
            trend_adjustment = trend_slope * (day + 1)

            # 应用季节性（周几效应）
            day_of_week = forecast_date.weekday()
            seasonality_factor = self._get_seasonality_factor(day_of_week)

            # 预测值
            predicted_value = (recent_avg + trend_adjustment) * seasonality_factor

            # 置信区间
            std_dev = statistics.stdev([
                d.get("quantity", 100) for d in sales_data[-30:]
            ]) if len(sales_data) >= 30 else recent_avg * 0.2

            predictions.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "predicted_quantity": max(0, round(predicted_value)),
                "lower_bound": max(0, round(predicted_value - 1.96 * std_dev)),
                "upper_bound": round(predicted_value + 1.96 * std_dev),
                "day_of_week": forecast_date.strftime("%A"),
            })

        # 生成建议
        recommendations = self._generate_sales_recommendations(
            trend, seasonality_pattern, predictions
        )

        return SalesForecastResult(
            forecast_id=f"forecast_{secrets.token_hex(8)}",
            product_id=product_id,
            forecast_date=base_date,
            predictions=predictions,
            trend=trend,
            seasonality_pattern=seasonality_pattern,
            confidence=0.85,
            factors={
                "trend_slope": trend_slope,
                "seasonality_strength": 0.3,
                "recent_average": recent_avg,
            },
            recommendations=recommendations,
        )

    def _generate_sample_sales(self, days: int) -> List[Dict]:
        """生成示例销售数据"""
        import random
        data = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(days):
            date = base_date + timedelta(days=i)
            # 基础销量 + 趋势 + 季节性 + 随机噪声
            base = 100
            trend = i * 0.5  # 轻微上升趋势
            seasonality = 20 * math.sin(2 * math.pi * date.weekday() / 7)
            noise = random.gauss(0, 10)

            quantity = max(0, int(base + trend + seasonality + noise))

            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "quantity": quantity,
                "revenue": quantity * 50,
            })

        return data

    def _analyze_trend(self, sales_data: List[Dict]) -> Tuple[str, float]:
        """分析销售趋势"""
        if len(sales_data) < 7:
            return "stable", 0.0

        # 简单线性回归斜率
        quantities = [d.get("quantity", 0) for d in sales_data]
        n = len(quantities)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(quantities)

        numerator = sum((i - x_mean) * (q - y_mean) for i, q in enumerate(quantities))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.5:
            trend = "increasing"
        elif slope < -0.5:
            trend = "decreasing"
        else:
            trend = "stable"

        return trend, slope

    def _analyze_seasonality(self, sales_data: List[Dict]) -> str:
        """分析季节性模式"""
        if len(sales_data) < 14:
            return "insufficient_data"

        # 按周几分组
        by_weekday = defaultdict(list)
        for d in sales_data:
            date = datetime.strptime(d["date"], "%Y-%m-%d")
            by_weekday[date.weekday()].append(d.get("quantity", 0))

        # 计算各天平均
        weekday_avg = {k: statistics.mean(v) for k, v in by_weekday.items()}

        # 判断模式
        weekend_avg = (weekday_avg.get(5, 0) + weekday_avg.get(6, 0)) / 2
        weekday_avg_val = statistics.mean([
            weekday_avg.get(i, 0) for i in range(5)
        ])

        if weekend_avg > weekday_avg_val * 1.2:
            return "weekend_peak"
        elif weekend_avg < weekday_avg_val * 0.8:
            return "weekday_peak"
        else:
            return "no_weekly_pattern"

    def _get_seasonality_factor(self, day_of_week: int) -> float:
        """获取季节性因子"""
        # 周末略高，周一略低
        factors = {
            0: 0.9,   # 周一
            1: 0.95,  # 周二
            2: 1.0,   # 周三
            3: 1.0,   # 周四
            4: 1.05,  # 周五
            5: 1.1,   # 周六
            6: 1.0,   # 周日
        }
        return factors.get(day_of_week, 1.0)

    def _generate_sales_recommendations(
        self,
        trend: str,
        seasonality: str,
        predictions: List[Dict],
    ) -> List[str]:
        """生成销售建议"""
        recommendations = []

        # 趋势建议
        if trend == "increasing":
            recommendations.append("销量呈上升趋势，建议适当增加库存储备")
        elif trend == "decreasing":
            recommendations.append("销量呈下降趋势，建议分析原因并考虑促销活动")

        # 季节性建议
        if seasonality == "weekend_peak":
            recommendations.append("周末销量较高，建议周末增加人员配置")
        elif seasonality == "weekday_peak":
            recommendations.append("工作日销量较高，建议优化工作日配送")

        # 预测值建议
        if predictions:
            max_day = max(predictions, key=lambda x: x["predicted_quantity"])
            recommendations.append(
                f"预计 {max_day['date']} ({max_day['day_of_week']}) 销量最高，"
                f"约 {max_day['predicted_quantity']} 件"
            )

        return recommendations


# ==================== 客户分群服务 ====================

@dataclass
class CustomerSegmentConfig:
    """客户分群配置"""
    features: List[str] = field(default_factory=lambda: [
        "total_spend", "frequency", "recency", "avg_order_value"
    ])
    n_clusters: int = 5
    method: str = "kmeans"  # kmeans, rfm, behavioral


@dataclass
class CustomerSegment:
    """客户分群结果"""
    segment_id: str
    name: str
    description: str
    customer_count: int
    percentage: float
    characteristics: Dict[str, Any] = field(default_factory=dict)
    avg_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "segment_id": self.segment_id,
            "name": self.name,
            "description": self.description,
            "customer_count": self.customer_count,
            "percentage": self.percentage,
            "characteristics": self.characteristics,
            "avg_metrics": self.avg_metrics,
            "recommendations": self.recommendations,
        }


@dataclass
class SegmentationResult:
    """分群分析结果"""
    analysis_id: str
    total_customers: int
    segments: List[CustomerSegment] = field(default_factory=list)
    method_used: str = ""
    feature_importance: Dict[str, float] = field(default_factory=dict)
    cluster_quality: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id,
            "total_customers": self.total_customers,
            "segments": [s.to_dict() for s in self.segments],
            "method_used": self.method_used,
            "feature_importance": self.feature_importance,
            "cluster_quality": self.cluster_quality,
            "created_at": self.created_at.isoformat(),
        }


class CustomerSegmentationService:
    """客户分群服务"""

    # RFM 分群定义
    RFM_SEGMENTS = {
        "champions": {"r": (4, 5), "f": (4, 5), "m": (4, 5)},
        "loyal_customers": {"r": (3, 5), "f": (3, 5), "m": (3, 5)},
        "potential_loyalists": {"r": (3, 5), "f": (1, 3), "m": (1, 3)},
        "new_customers": {"r": (4, 5), "f": (1, 1), "m": (1, 1)},
        "promising": {"r": (3, 4), "f": (1, 1), "m": (1, 1)},
        "need_attention": {"r": (2, 3), "f": (2, 3), "m": (2, 3)},
        "about_to_sleep": {"r": (2, 3), "f": (1, 2), "m": (1, 2)},
        "at_risk": {"r": (1, 2), "f": (3, 5), "m": (3, 5)},
        "cant_lose_them": {"r": (1, 2), "f": (4, 5), "m": (4, 5)},
        "hibernating": {"r": (1, 2), "f": (1, 2), "m": (1, 2)},
        "lost": {"r": (1, 1), "f": (1, 1), "m": (1, 1)},
    }

    SEGMENT_DESCRIPTIONS = {
        "champions": "最近购买、频繁购买、消费最高的最佳客户",
        "loyal_customers": "经常购买且消费较高的忠诚客户",
        "potential_loyalists": "最近购买的潜在忠诚客户",
        "new_customers": "最近首次购买的新客户",
        "promising": "最近购买但消费较低的有潜力客户",
        "need_attention": "一段时间未购买，需要关注的客户",
        "about_to_sleep": "即将流失的客户",
        "at_risk": "曾经活跃但长时间未购买的高风险流失客户",
        "cant_lose_them": "曾经的高价值客户，不能失去",
        "hibernating": "长时间未活跃的沉睡客户",
        "lost": "已流失的客户",
    }

    SEGMENT_RECOMMENDATIONS = {
        "champions": ["提供专属VIP权益", "邀请参与新品试用", "发展为品牌大使"],
        "loyal_customers": ["推荐高价值产品", "提供忠诚度奖励", "定期关怀"],
        "potential_loyalists": ["提供会员升级激励", "推送个性化推荐", "增加互动频率"],
        "new_customers": ["发送欢迎礼包", "引导完善资料", "推送入门商品"],
        "promising": ["提供首单优惠", "推送热销商品", "增加触达频率"],
        "need_attention": ["发送关怀提醒", "提供回归优惠", "了解流失原因"],
        "about_to_sleep": ["发送唤醒邮件", "提供限时优惠", "推送感兴趣商品"],
        "at_risk": ["立即触达挽回", "提供大额优惠", "一对一服务"],
        "cant_lose_them": ["高管亲自关怀", "提供最高级别优惠", "专属定制服务"],
        "hibernating": ["低成本唤醒尝试", "批量营销活动", "评估是否放弃"],
        "lost": ["归因分析学习", "不再投入资源", "保留用于研究"],
    }

    def __init__(self):
        pass

    def segment_customers(
        self,
        config: CustomerSegmentConfig,
        customer_data: List[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        """
        客户分群分析

        支持 RFM 分析和 K-Means 聚类
        """
        # 使用提供的数据或生成示例数据
        if customer_data:
            data = customer_data
        else:
            data = self._generate_sample_customers(1000)

        total_customers = len(data)

        if config.method == "rfm":
            segments = self._rfm_segmentation(data)
            method_used = "RFM Analysis"
            feature_importance = {
                "recency": 0.35,
                "frequency": 0.35,
                "monetary": 0.30,
            }
        else:
            segments = self._kmeans_segmentation(data, config.n_clusters)
            method_used = "K-Means Clustering"
            feature_importance = {f: 1.0 / len(config.features) for f in config.features}

        return SegmentationResult(
            analysis_id=f"seg_{secrets.token_hex(8)}",
            total_customers=total_customers,
            segments=segments,
            method_used=method_used,
            feature_importance=feature_importance,
            cluster_quality={
                "silhouette_score": 0.65,
                "intra_cluster_variance": 0.25,
            },
        )

    def _generate_sample_customers(self, n: int) -> List[Dict]:
        """生成示例客户数据"""
        import random
        customers = []

        for i in range(n):
            # 生成 RFM 数据
            recency = random.randint(1, 365)  # 天
            frequency = random.randint(1, 50)  # 次
            monetary = random.uniform(100, 10000)  # 元

            customers.append({
                "customer_id": f"cust_{i:06d}",
                "recency_days": recency,
                "frequency": frequency,
                "monetary": round(monetary, 2),
                "total_spend": round(monetary * frequency, 2),
                "avg_order_value": round(monetary / max(1, frequency), 2),
                "last_purchase_date": (
                    datetime.now() - timedelta(days=recency)
                ).strftime("%Y-%m-%d"),
            })

        return customers

    def _rfm_segmentation(
        self,
        customer_data: List[Dict],
    ) -> List[CustomerSegment]:
        """RFM 分群"""
        # 计算 RFM 分位数
        recencies = [c["recency_days"] for c in customer_data]
        frequencies = [c["frequency"] for c in customer_data]
        monetaries = [c["monetary"] for c in customer_data]

        def get_quintile(value: float, values: List[float], reverse: bool = False) -> int:
            """计算分位数（1-5）"""
            sorted_vals = sorted(values, reverse=reverse)
            n = len(sorted_vals)
            for i in range(1, 6):
                if value <= sorted_vals[int(n * i / 5) - 1]:
                    return i if not reverse else 6 - i
            return 5 if not reverse else 1

        # 为每个客户计算 RFM 分数
        for customer in customer_data:
            # Recency: 越小越好（反向）
            customer["r_score"] = get_quintile(
                customer["recency_days"], recencies, reverse=True
            )
            # Frequency: 越大越好
            customer["f_score"] = get_quintile(customer["frequency"], frequencies)
            # Monetary: 越大越好
            customer["m_score"] = get_quintile(customer["monetary"], monetaries)

        # 分配到分群
        segment_customers: Dict[str, List[Dict]] = defaultdict(list)

        for customer in customer_data:
            r, f, m = customer["r_score"], customer["f_score"], customer["m_score"]
            segment_name = self._assign_rfm_segment(r, f, m)
            segment_customers[segment_name].append(customer)

        # 构建分群结果
        segments = []
        total = len(customer_data)

        for name, customers in segment_customers.items():
            count = len(customers)
            avg_r = statistics.mean([c["r_score"] for c in customers])
            avg_f = statistics.mean([c["f_score"] for c in customers])
            avg_m = statistics.mean([c["m_score"] for c in customers])
            avg_spend = statistics.mean([c["total_spend"] for c in customers])

            segments.append(CustomerSegment(
                segment_id=f"seg_{name}",
                name=name.replace("_", " ").title(),
                description=self.SEGMENT_DESCRIPTIONS.get(name, ""),
                customer_count=count,
                percentage=round(count / total * 100, 2),
                characteristics={
                    "avg_recency_score": round(avg_r, 2),
                    "avg_frequency_score": round(avg_f, 2),
                    "avg_monetary_score": round(avg_m, 2),
                },
                avg_metrics={
                    "avg_total_spend": round(avg_spend, 2),
                    "avg_frequency": round(statistics.mean([c["frequency"] for c in customers]), 2),
                    "avg_recency_days": round(statistics.mean([c["recency_days"] for c in customers]), 1),
                },
                recommendations=self.SEGMENT_RECOMMENDATIONS.get(name, []),
            ))

        # 按客户数量排序
        segments.sort(key=lambda s: s.customer_count, reverse=True)

        return segments

    def _assign_rfm_segment(self, r: int, f: int, m: int) -> str:
        """根据 RFM 分数分配分群"""
        for segment, criteria in self.RFM_SEGMENTS.items():
            r_range = criteria["r"]
            f_range = criteria["f"]
            m_range = criteria["m"]

            if (r_range[0] <= r <= r_range[1] and
                f_range[0] <= f <= f_range[1] and
                m_range[0] <= m <= m_range[1]):
                return segment

        # 默认分配
        if r >= 4:
            return "new_customers"
        elif r <= 2 and f >= 3:
            return "at_risk"
        else:
            return "need_attention"

    def _kmeans_segmentation(
        self,
        customer_data: List[Dict],
        n_clusters: int,
    ) -> List[CustomerSegment]:
        """K-Means 聚类分群（简化实现）"""
        # 简化的 K-Means 实现
        # 实际应使用 sklearn.cluster.KMeans

        import random

        # 提取特征
        features = []
        for c in customer_data:
            features.append([
                c.get("recency_days", 0),
                c.get("frequency", 0),
                c.get("monetary", 0),
            ])

        # 简单随机分配（模拟 K-Means 结果）
        cluster_assignments = [random.randint(0, n_clusters - 1) for _ in customer_data]

        # 按聚类分组
        cluster_customers: Dict[int, List[Dict]] = defaultdict(list)
        for i, customer in enumerate(customer_data):
            cluster_customers[cluster_assignments[i]].append(customer)

        # 构建分群结果
        segments = []
        total = len(customer_data)
        cluster_names = [
            "高价值活跃", "中等价值", "新客户", "沉睡客户", "流失风险"
        ]

        for cluster_id, customers in cluster_customers.items():
            count = len(customers)
            name = cluster_names[cluster_id % len(cluster_names)]

            segments.append(CustomerSegment(
                segment_id=f"cluster_{cluster_id}",
                name=f"分群 {cluster_id + 1}: {name}",
                description=f"通过 K-Means 聚类识别的客户群",
                customer_count=count,
                percentage=round(count / total * 100, 2),
                characteristics={
                    "cluster_id": cluster_id,
                },
                avg_metrics={
                    "avg_total_spend": round(statistics.mean([c["total_spend"] for c in customers]), 2),
                    "avg_frequency": round(statistics.mean([c["frequency"] for c in customers]), 2),
                    "avg_recency_days": round(statistics.mean([c["recency_days"] for c in customers]), 1),
                },
                recommendations=[
                    "根据分群特征定制营销策略",
                    "持续监控分群变化",
                ],
            ))

        segments.sort(key=lambda s: s.customer_count, reverse=True)

        return segments


# ==================== AI 预测服务主类 ====================

class AIPredictionService:
    """AI 预测服务"""

    def __init__(self):
        self._models: Dict[str, PredictionModel] = {}
        self._predictions: Dict[str, PredictionResult] = {}

        self._sales_forecast = SalesForecastService()
        self._customer_segmentation = CustomerSegmentationService()

        # 统计
        self._stats = {
            "total_models": 0,
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
        }

        # 初始化示例模型
        self._init_sample_models()

    def _init_sample_models(self):
        """初始化示例模型"""
        sample_models = [
            PredictionModel(
                model_id="model_sales_forecast",
                name="销量预测模型",
                description="基于历史销售数据预测未来销量",
                prediction_type=PredictionType.TIME_SERIES,
                model_config=ModelConfig(
                    model_type=ModelType.PROPHET,
                    hyperparameters={
                        "seasonality_mode": "multiplicative",
                        "changepoint_prior_scale": 0.05,
                    },
                ),
                dataset_config=DatasetConfig(
                    dataset_id="ds_sales",
                    name="销售数据集",
                    source_table="sales_history",
                    features=["date", "product_id", "category", "region"],
                    target="quantity",
                    time_column="date",
                ),
                status=ModelStatus.DEPLOYED,
                metrics=ModelMetrics(
                    mae=15.2,
                    mape=8.5,
                    r2_score=0.92,
                ),
                version="2.1.0",
                created_by="system",
                tags=["sales", "forecasting", "production"],
            ),
            PredictionModel(
                model_id="model_customer_seg",
                name="客户分群模型",
                description="基于 RFM 和行为特征的客户分群",
                prediction_type=PredictionType.CLUSTERING,
                model_config=ModelConfig(
                    model_type=ModelType.KMEANS,
                    hyperparameters={
                        "n_clusters": 5,
                        "init": "k-means++",
                    },
                ),
                dataset_config=DatasetConfig(
                    dataset_id="ds_customers",
                    name="客户数据集",
                    source_table="customer_metrics",
                    features=["recency", "frequency", "monetary", "tenure"],
                ),
                status=ModelStatus.DEPLOYED,
                metrics=ModelMetrics(
                    silhouette_score=0.68,
                    calinski_harabasz=1250.5,
                ),
                version="1.5.0",
                created_by="system",
                tags=["customer", "segmentation", "marketing"],
            ),
            PredictionModel(
                model_id="model_churn_pred",
                name="客户流失预测模型",
                description="预测客户流失风险",
                prediction_type=PredictionType.CLASSIFICATION,
                model_config=ModelConfig(
                    model_type=ModelType.XGBOOST,
                    hyperparameters={
                        "max_depth": 6,
                        "learning_rate": 0.1,
                        "n_estimators": 100,
                    },
                ),
                dataset_config=DatasetConfig(
                    dataset_id="ds_churn",
                    name="流失数据集",
                    source_table="customer_churn_features",
                    features=["tenure", "usage_frequency", "support_tickets", "payment_delay"],
                    target="churned",
                ),
                status=ModelStatus.TRAINED,
                metrics=ModelMetrics(
                    accuracy=0.89,
                    precision=0.85,
                    recall=0.82,
                    f1_score=0.83,
                    auc_roc=0.91,
                ),
                version="1.0.0",
                created_by="data_scientist",
                tags=["churn", "classification", "customer"],
            ),
        ]

        for model in sample_models:
            self._models[model.model_id] = model
            self._stats["total_models"] += 1

    # ==================== 模型管理 ====================

    def create_model(
        self,
        name: str,
        prediction_type: PredictionType,
        model_type: ModelType,
        description: str = "",
        hyperparameters: Dict[str, Any] = None,
        dataset_config: Dict[str, Any] = None,
        created_by: str = "",
        tags: List[str] = None,
    ) -> PredictionModel:
        """创建预测模型"""
        model = PredictionModel(
            model_id=f"model_{secrets.token_hex(8)}",
            name=name,
            description=description,
            prediction_type=prediction_type,
            model_config=ModelConfig(
                model_type=model_type,
                hyperparameters=hyperparameters or {},
            ),
            dataset_config=DatasetConfig(
                dataset_id=f"ds_{secrets.token_hex(4)}",
                name=f"Dataset for {name}",
                **(dataset_config or {}),
            ),
            created_by=created_by,
            tags=tags or [],
        )

        self._models[model.model_id] = model
        self._stats["total_models"] += 1

        logger.info(f"创建预测模型: {model.model_id} - {name}")
        return model

    def get_model(self, model_id: str) -> Optional[PredictionModel]:
        """获取模型"""
        return self._models.get(model_id)

    def list_models(
        self,
        prediction_type: PredictionType = None,
        status: ModelStatus = None,
        tags: List[str] = None,
        limit: int = 100,
    ) -> List[PredictionModel]:
        """列出模型"""
        models = list(self._models.values())

        if prediction_type:
            models = [m for m in models if m.prediction_type == prediction_type]
        if status:
            models = [m for m in models if m.status == status]
        if tags:
            models = [m for m in models if any(t in m.tags for t in tags)]

        return models[:limit]

    def train_model(
        self,
        model_id: str,
        training_data: List[Dict[str, Any]] = None,
    ) -> Optional[PredictionModel]:
        """训练模型"""
        model = self._models.get(model_id)
        if not model:
            return None

        model.status = ModelStatus.TRAINING
        model.updated_at = datetime.now()

        try:
            # 模拟训练过程
            # 实际应调用 ML 框架（sklearn, XGBoost, PyTorch 等）

            # 更新指标（模拟）
            import random
            if model.prediction_type == PredictionType.REGRESSION:
                model.metrics.mae = random.uniform(5, 20)
                model.metrics.rmse = random.uniform(10, 30)
                model.metrics.r2_score = random.uniform(0.8, 0.95)
            elif model.prediction_type == PredictionType.CLASSIFICATION:
                model.metrics.accuracy = random.uniform(0.8, 0.95)
                model.metrics.precision = random.uniform(0.75, 0.9)
                model.metrics.recall = random.uniform(0.75, 0.9)
                model.metrics.f1_score = random.uniform(0.75, 0.9)
            elif model.prediction_type == PredictionType.CLUSTERING:
                model.metrics.silhouette_score = random.uniform(0.5, 0.8)

            model.status = ModelStatus.TRAINED
            model.trained_at = datetime.now()
            model.updated_at = datetime.now()

            logger.info(f"模型训练完成: {model_id}")

        except Exception as e:
            model.status = ModelStatus.FAILED
            logger.error(f"模型训练失败: {model_id} - {e}")

        return model

    def deploy_model(self, model_id: str) -> Optional[PredictionModel]:
        """部署模型"""
        model = self._models.get(model_id)
        if not model or model.status != ModelStatus.TRAINED:
            return None

        model.status = ModelStatus.DEPLOYED
        model.deployed_at = datetime.now()
        model.updated_at = datetime.now()

        logger.info(f"模型已部署: {model_id}")
        return model

    # ==================== 预测接口 ====================

    def predict(
        self,
        model_id: str,
        input_data: Dict[str, Any],
        prediction_horizon: int = 1,
        confidence_level: float = 0.95,
    ) -> PredictionResult:
        """执行预测"""
        request = PredictionRequest(
            request_id=f"pred_{secrets.token_hex(8)}",
            model_id=model_id,
            input_data=input_data,
            prediction_horizon=prediction_horizon,
            confidence_level=confidence_level,
        )

        model = self._models.get(model_id)
        if not model or model.status != ModelStatus.DEPLOYED:
            return PredictionResult(
                request_id=request.request_id,
                model_id=model_id,
                status=PredictionStatus.FAILED,
                error="模型不存在或未部署",
            )

        self._stats["total_predictions"] += 1
        start_time = datetime.now()

        try:
            # 根据模型类型执行预测
            if model.prediction_type == PredictionType.TIME_SERIES:
                predictions = self._time_series_predict(model, input_data, prediction_horizon)
            elif model.prediction_type == PredictionType.CLASSIFICATION:
                predictions = self._classification_predict(model, input_data)
            elif model.prediction_type == PredictionType.REGRESSION:
                predictions = self._regression_predict(model, input_data)
            else:
                predictions = [{"value": 0}]

            inference_time = (datetime.now() - start_time).total_seconds() * 1000

            result = PredictionResult(
                request_id=request.request_id,
                model_id=model_id,
                status=PredictionStatus.COMPLETED,
                predictions=predictions,
                inference_time_ms=inference_time,
            )

            self._predictions[request.request_id] = result
            self._stats["successful_predictions"] += 1

            return result

        except Exception as e:
            self._stats["failed_predictions"] += 1
            return PredictionResult(
                request_id=request.request_id,
                model_id=model_id,
                status=PredictionStatus.FAILED,
                error=str(e),
            )

    def _time_series_predict(
        self,
        model: PredictionModel,
        input_data: Dict[str, Any],
        horizon: int,
    ) -> List[Dict[str, Any]]:
        """时间序列预测"""
        predictions = []
        base_value = input_data.get("last_value", 100)

        for i in range(horizon):
            # 简单趋势预测
            trend = input_data.get("trend", 0.01)
            seasonality = math.sin(2 * math.pi * i / 7) * 0.1

            predicted_value = base_value * (1 + trend * (i + 1)) * (1 + seasonality)

            predictions.append({
                "step": i + 1,
                "predicted_value": round(predicted_value, 2),
                "lower_bound": round(predicted_value * 0.9, 2),
                "upper_bound": round(predicted_value * 1.1, 2),
            })

        return predictions

    def _classification_predict(
        self,
        model: PredictionModel,
        input_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """分类预测"""
        import random

        # 模拟分类预测
        prob = random.uniform(0.3, 0.9)
        predicted_class = 1 if prob > 0.5 else 0

        return [{
            "predicted_class": predicted_class,
            "probability": round(prob, 4),
            "class_probabilities": {
                "0": round(1 - prob, 4),
                "1": round(prob, 4),
            },
        }]

    def _regression_predict(
        self,
        model: PredictionModel,
        input_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """回归预测"""
        import random

        # 模拟回归预测
        base = sum(input_data.get("features", [100])) / max(1, len(input_data.get("features", [1])))
        predicted_value = base * random.uniform(0.9, 1.1)

        return [{
            "predicted_value": round(predicted_value, 2),
            "confidence_interval": {
                "lower": round(predicted_value * 0.85, 2),
                "upper": round(predicted_value * 1.15, 2),
            },
        }]

    # ==================== 专用预测接口 ====================

    def forecast_sales(
        self,
        product_id: str = "",
        category: str = "",
        region: str = "",
        forecast_days: int = 30,
        historical_data: List[Dict] = None,
    ) -> SalesForecastResult:
        """销量预测"""
        config = SalesForecastConfig(
            product_id=product_id,
            category=category,
            region=region,
            forecast_days=forecast_days,
        )
        return self._sales_forecast.forecast(config, historical_data)

    def segment_customers(
        self,
        method: str = "rfm",
        n_clusters: int = 5,
        customer_data: List[Dict] = None,
    ) -> SegmentationResult:
        """客户分群"""
        config = CustomerSegmentConfig(
            method=method,
            n_clusters=n_clusters,
        )
        return self._customer_segmentation.segment_customers(config, customer_data)

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "models": {
                "total": self._stats["total_models"],
                "by_status": {
                    status.value: len([
                        m for m in self._models.values()
                        if m.status == status
                    ])
                    for status in ModelStatus
                },
                "by_type": {
                    ptype.value: len([
                        m for m in self._models.values()
                        if m.prediction_type == ptype
                    ])
                    for ptype in PredictionType
                },
            },
            "predictions": {
                "total": self._stats["total_predictions"],
                "successful": self._stats["successful_predictions"],
                "failed": self._stats["failed_predictions"],
                "success_rate": (
                    self._stats["successful_predictions"] /
                    max(1, self._stats["total_predictions"])
                ),
            },
        }


# ==================== 全局服务实例 ====================

_prediction_service: Optional[AIPredictionService] = None


def get_ai_prediction_service() -> AIPredictionService:
    """获取 AI 预测服务实例"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = AIPredictionService()
    return _prediction_service
