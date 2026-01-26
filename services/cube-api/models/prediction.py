"""
业务预测模型库
Phase 2.3: 销量预测、流失预测、转化预测等业务模板
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, TIMESTAMP, JSON, ForeignKey, Float
from sqlalchemy.sql import func

from .base import Base


def generate_template_id() -> str:
    """生成模板ID"""
    return f"tpl_{uuid.uuid4().hex[:8]}"


def generate_job_id() -> str:
    """生成任务ID"""
    return f"job_{uuid.uuid4().hex[:12]}"


class PredictionTemplate(Base):
    """预测模板表"""
    __tablename__ = "prediction_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True, comment='模板ID')

    # 基本信息
    name = Column(String(128), nullable=False, comment='模板名称')
    category = Column(String(64), nullable=False, comment='分类: sales, churn, conversion, demand_forecasting')
    description = Column(Text, comment='模板描述')

    # 目标变量配置
    target_variable = Column(String(128), nullable=False, comment='目标变量名')
    target_type = Column(String(32), nullable=False, comment='目标类型: binary, regression, count')
    prediction_horizon = Column(Integer, comment='预测时间窗口（天）')

    # 特征要求
    required_features = Column(JSON, comment='必需特征列表')
    optional_features = Column(JSON, comment='可选特征列表')

    # 模型配置
    default_model = Column(String(64), comment='默认模型类型')
    allowed_models = Column(JSON, comment='允许的模型类型')
    model_params = Column(JSON, comment='模型参数配置')

    # 数据要求
    min_rows = Column(Integer, default=1000, comment='最少数据行数')
    feature_importance_threshold = Column(Float, default=0.1, comment='特征重要性阈值')

    # 评估指标
    metrics = Column(JSON, comment='评估指标配置')
    success_threshold = Column(JSON, comment='成功阈值配置')

    # 可视化配置
    chart_type = Column(String(32), comment='推荐图表类型')
    chart_config = Column(JSON, comment='图表配置')

    # 模板状态
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_system = Column(Boolean, default=False, comment='是否系统预置')

    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    created_by = Column(String(128), comment='创建者')

    def get_required_features(self) -> list:
        """获取必需特征列表"""
        if not self.required_features:
            return []
        try:
            return json.loads(self.required_features)
        except json.JSONDecodeError:
            return []

    def set_required_features(self, features: list):
        """设置必需特征列表"""
        self.required_features = json.dumps(features, ensure_ascii=False)

    def get_optional_features(self) -> list:
        """获取可选特征列表"""
        if not self.optional_features:
            return []
        try:
            return json.loads(self.optional_features)
        except jsonDecodeError:
            return []

    def set_optional_features(self, features: list):
        """设置可选特征列表"""
        self.optional_features = json.dumps(features, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "target_variable": self.target_variable,
            "target_type": self.target_type,
            "prediction_horizon": self.prediction_horizon,
            "required_features": self.get_required_features(),
            "optional_features": self.get_optional_features(),
            "default_model": self.default_model,
            "allowed_models": self.allowed_models,
            "model_params": self.model_params,
            "min_rows": self.min_rows,
            "feature_importance_threshold": self.feature_importance_threshold,
            "metrics": self.metrics,
            "success_threshold": self.success_threshold,
            "chart_type": self.chart_type,
            "chart_config": self.chart_config,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TrainingJob(Base):
    """训练任务表"""
    __tablename__ = "prediction_training_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True, comment='任务ID')

    # 关联模板
    template_id = Column(String(64), ForeignKey('prediction_templates.template_id'), comment='模板ID')

    # 任务信息
    job_name = Column(String(255), comment='任务名称')
    description = Column(Text, comment='任务描述')
    category = Column(String(64), comment='分类')

    # 数据源
    dataset_id = Column(String(128), comment='数据集ID')
    table_name = Column(String(128), comment='表名')

    # 模型配置
    model_type = Column(String(64), comment='模型类型')
    model_params = Column(JSON, comment='模型参数')

    # 特征工程配置
    feature_config = Column(JSON, comment='特征工程配置')
    selected_features = Column(JSON, comment='选择的特征列表')

    # 训练配置
    train_test_split = Column(Float, default=0.8, comment='训练集比例')
    random_state = Column(Integer, comment='随机种子')
    max_epochs = Column(Integer, default=100, comment='最大训练轮数')
    early_stopping = Column(Boolean, default=True, comment='早停')

    # 状态
    status = Column(String(32), default='pending', comment='状态: pending, running, completed, failed, cancelled')
    progress = Column(Integer, default=0, comment='训练进度 0-100')

    # 训练结果
    model_path = Column(String(512), comment='模型保存路径')
    model_version = Column(String(64), comment='模型版本号')

    # 评估结果
    metrics = Column(JSON, comment='评估指标')
    feature_importance = Column(JSON, comment='特征重要性')

    # 错误信息
    error_message = Column(Text, comment='错误信息')

    # 创建者
    created_by = Column(String(128), comment='创建者')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')

    def get_metrics(self) -> Dict[str, float]:
        """获取评估指标"""
        if not self.metrics:
            return {}
        try:
            return json.loads(self.metrics)
        except json.JSONDecodeError:
            return {}

    def set_metrics(self, metrics: Dict[str, float]):
        """设置评估指标"""
        self.metrics = json.dumps(metrics, ensure_ascii=False)

    def get_feature_importance(self) -> List[Dict[str, Any]]:
        """获取特征重要性"""
        if not self.feature_importance:
            return []
        try:
            return json.loads(self.feature_importance)
        except json.JSONDecodeError:
            return []

    def set_feature_importance(self, importance: List[Dict[str, Any]]):
        """设置特征重要性"""
        self.feature_importance = json.dumps(importance, ensure_ascii=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "template_id": self.template_id,
            "job_name": self.job_name,
            "description": self.description,
            "category": self.category,
            "dataset_id": self.dataset_id,
            "table_name": self.table_name,
            "model_type": self.model_type,
            "model_params": self.model_params,
            "status": self.status,
            "progress": self.progress,
            "metrics": self.get_metrics(),
            "feature_importance": self.get_feature_importance(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class PredictionRecord(Base):
    """预测记录表"""
    __tablename__ = "prediction_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True, comment='记录ID')

    # 关联任务
    job_id = Column(String(64), ForeignKey('prediction_training_jobs.job_id'), comment='任务ID')

    # 输入数据
    input_data = Column(JSON, comment='输入数据')
    input_hash = Column(String(64), comment='输入数据哈希（用于缓存）')

    # 预测结果
    prediction = Column(JSON, comment='预测结果')
    prediction_probability = Column(Float, comment='预测概率（分类问题）')

    # 元数据
    predicted_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='预测时间')
    created_by = Column(String(128), comment='创建者')

    def to_dict(self):
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "job_id": self.job_id,
            "input_data": self.input_data,
            "prediction": self.prediction,
            "prediction_probability": self.prediction_probability,
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
        }


# 预定义的预测模板
PREDEFINED_TEMPLATES = [
    {
        "name": "销售额预测",
        "category": "sales",
        "description": "基于历史销售数据预测未来销售额",
        "target_variable": "sales_amount",
        "target_type": "regression",
        "prediction_horizon": 30,
        "required_features": [
            "historical_sales",
            "product_id",
            "region",
            "promotion_flag",
            "seasonality",
            "day_of_week",
            "month",
        ],
        "optional_features": [
            "weather",
            "holiday_flag",
            "competitor_price",
        ],
        "default_model": "xgboost_regressor",
        "metrics": {
            "rmse": {"lower_is_better": True},
            "r2": {"lower_is_better": False},
            "mae": {"lower_is_better": True},
        },
        "success_threshold": {
            "r2": 0.7,
            "mape": 0.2,
        },
        "chart_type": "line",
    },
    {
        "name": "客户流失预测",
        "category": "churn",
        "description": "预测客户流失风险",
        "target_variable": "churn_flag",
        "target_type": "binary",
        "prediction_horizon": 30,
        "required_features": [
            "account_age",
            "login_frequency",
            "usage_duration",
            "support_tickets",
            "payment_history",
            "product_usage",
        ],
        "optional_features": [
            "geographic_location",
            "device_type",
            "subscription_plan",
        ],
        "default_model": "random_forest",
        "metrics": {
            "auc_roc": {"lower_is_better": False},
            "precision": {"lower_is_better": False},
            "recall": {"lower_is_better": False},
            "f1": {"lower_is_better": False},
        },
        "success_threshold": {
            "auc_roc": 0.75,
        },
        "chart_type": "bar",
    },
    {
        "name": "转化率预测",
        "category": "conversion",
        "description": "预测用户转化为付费客户的概率",
        "target_variable": "conversion_flag",
        "target_type": "binary",
        "prediction_horizon": 7,
        "required_features": [
            "page_views",
            "time_spent",
            "feature_usage",
            "free_trial_used",
            "email_engagement",
            "device_type",
        ],
        "optional_features": [
            "referral_source",
            "campaign_source",
        ],
        "default_model": "gradient_boosting",
        "metrics": {
            "auc_roc": {"lower_is_better": False},
            "log_loss": {"lower_is_better": True},
        },
        "success_threshold": {
            "auc_roc": 0.8,
        },
        "chart_type": "funnel",
    },
    {
        "name": "需求预测",
        "category": "demand_forecasting",
        "description": "预测产品/服务的需求量",
        "target_variable": "demand_quantity",
        "target_type": "regression",
        "prediction_horizon": 90,
        "required_features": [
            "historical_demand",
            "product_id",
            "seasonality",
            "trend",
            "marketing_spend",
            "price_point",
        ],
        "optional_features": [
            "economic_indicators",
            "competitor_pricing",
        ],
        "default_model": "prophet",
        "metrics": {
            "mape": {"lower_is_better": True},
            "rmse": {"lower_is_better": True},
        },
        "success_threshold": {
            "mape": 0.15,
        },
        "chart_type": "line",
    },
]
