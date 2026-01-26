"""
自动特征工程服务
Phase 2.3: 特征选择、特征工程模板
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class FeatureInfo:
    """特征信息"""
    name: str
    data_type: str
    missing_ratio: float
    unique_ratio: float
    cardinality: int
    correlation_with_target: float = 0.0
    importance_score: float = 0.0
    is_selected: bool = False


class FeatureAutoEngine:
    """自动特征工程引擎"""

    def __init__(self):
        self.feature_templates = {
            "sales": {
                "time_features": ["day_of_week", "month", "quarter", "is_holiday", "is_weekend"],
                "lag_features": [1, 7, 30],  # 1天、7天、30天滞后
                "rolling_features": {
                    "mean": [7, 30],  # 7天、30天滚动平均
                    "std": [7, 30],
                    "min": [7, 30],
                    "max": [7, 30],
                },
            },
            "churn": {
                "behavior_features": [
                    "login_frequency",
                    "avg_session_duration",
                    "pages_per_session",
                    "days_since_last_login",
                    "total_actions",
                ],
                "engagement_features": [
                    "feature_usage_diversity",
                    "support_ticket_count",
                    "payment_success_rate",
                ],
                "demographic_features": [
                    "age_group",
                    "subscription_tier",
                    "geo_location",
                ],
            },
            "conversion": {
                "behavior_features": [
                    "time_spent_on_site",
                    "page_depth",
                    "return_visit_count",
                    "product_view_count",
                ],
                "engagement_features": [
                    "free_trial_usage_rate",
                    "email_open_rate",
                    "video_watch_progress",
                ],
            },
        }

    def auto_feature_engineering(
        self,
        df: pd.DataFrame,
        category: str,
        target_column: str,
        feature_config: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        自动特征工程

        Args:
            df: 原始数据框
            category: 业务类别 (sales, churn, conversion, demand_forecasting)
            target_column: 目标列名
            feature_config: 特征配置

        Returns:
            增强后的数据框
        """
        if category not in self.feature_templates:
            logger.warning(f"No feature template found for category: {category}")
            return df

        template = self.feature_templates[category]
        df_enhanced = df.copy()

        try:
            # 时间特征
            if "time_features" in template:
                df_enhanced = self._add_time_features(
                    df_enhanced, template["time_features"], df[target_column]
                )

            # 滞后特征
            if "lag_features" in template:
                df_enhanced = self._add_lag_features(
                    df_enhanced, template["lag_features"], df[target_column]
                )

            # 滚动窗口特征
            if "rolling_features" in template:
                df_enhanced = self._add_rolling_features(
                    df_enhanced, template["rolling_features"]
                )

            # 行为特征
            if "behavior_features" in template:
                df_enhanced = self._add_behavior_features(
                    df_enhanced, template["behavior_features"]
                )

        except Exception as e:
            logger.error(f"Error in auto feature engineering: {e}")

        return df_enhanced

    def _add_time_features(
        self,
        df: pd.DataFrame,
        features: List[str],
        date_column: str,
    ) -> pd.DataFrame:
        """添加时间特征"""
        df = df.copy()

        # 假设有一个日期列（需要从配置中获取或自动检测）
        date_col = self._detect_date_column(df)
        if not date_col:
            return df

        df[date_col] = pd.to_datetime(df[date_col])

        for feature in features:
            if feature == "day_of_week":
                df[f"feat_{feature}"] = df[date_col].dt.dayofweek
            elif feature == "month":
                df[f"feat_{feature}"] = df[date_col].dt.month
            elif feature == "quarter":
                df[f"feat_{feature}"] = df[date_col].dt.quarter
            elif feature == "is_holiday":
                df[f"feat_{feature}"] = 0  # 需要节假日API
            elif feature == "is_weekend":
                df[f"feat_{feature}"] = df[date_col].dt.dayofweek >= 5

        return df

    def _add_lag_features(
        self,
        df: pd.DataFrame,
        lags: List[int],
        value_column: str,
    ) -> pd.DataFrame:
        """添加滞后特征"""
        df = df.copy()

        for lag in lags:
            if value_column in df.columns:
                df[f"feat_lag_{lag}"] = df[value_column].shift(lag)

        return df

    def _add_rolling_features(
        self,
        df: pd.DataFrame,
        rolling_config: Dict[str, List[int]],
    ) -> pd.DataFrame:
        """添加滚动窗口特征"""
        df = df.copy()

        # 需要找到数值型列来计算滚动特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in numeric_cols:
            for agg, windows in rolling_config.items():
                for window in windows:
                    if agg == "mean":
                        df[f"feat_rolling_{agg}_{window}"] = df[col].rolling(window=window, min_periods=1).mean()
                    elif agg == "std":
                        df[f"feat_rolling_{agg}_{window}"] = df[col].rolling(window=window, min_periods=1).std()
                    elif agg == "min":
                        df[f"feat_rolling_{agg}_{window}"] = df[col].rolling(window=window, min_periods=1).min()
                    elif agg == "max":
                        df[f"feat_rolling_{agg}_{window}"] = df[col].rolling(window=window, min_periods=1).max()

        return df

    def _add_behavior_features(
        self,
        df: pd.DataFrame,
        features: List[str],
    ) -> pd.DataFrame:
        """添加行为特征"""
        df = df.copy()

        # 这里需要根据实际数据结构来实现
        for feature in features:
            if feature == "login_frequency" and "user_id" in df.columns:
                df[f"feat_{feature}"] = df.groupby("user_id")["action"].transform("count")

        return df

    def _detect_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """检测日期列"""
        for col in df.columns:
            if df[col].dtype in ['object', 'datetime64[ns]']:
                try:
                    pd.to_datetime(df[col].head(1))
                    return col
                except:
                    continue
        return None

    def select_features(
        self,
        df: pd.DataFrame,
        target_column: str,
        method: str = "importance",
        max_features: int = 50,
        threshold: float = 0.1,
    ) -> List[FeatureInfo]:
        """
        特征选择

        Args:
            df: 数据框
            target_column: 目标列
            method: 选择方法 (importance, correlation, mutual_info)
            max_features: 最大特征数
            threshold: 重要性阈值

        Returns:
            选择的特征信息列表
        """
        feature_infos = []

        # 计算每个特征的基本信息
        for col in df.columns:
            if col == target_column:
                continue

            missing_ratio = df[col].isnull().sum() / len(df)
            unique_ratio = df[col].nunique() / len(df)

            # 计算与目标的相关性
            correlation = 0
            if df[col].dtype in [np.int64, np.float64] and df[target_column].dtype in [np.int64, np.float64]:
                correlation = abs(df[col].corr(df[target_column]))

            feature_infos.append(FeatureInfo(
                name=col,
                data_type=str(df[col].dtype),
                missing_ratio=missing_ratio,
                unique_ratio=unique_ratio,
                cardinality=df[col].nunique(),
                correlation_with_target=correlation,
                is_selected=False,
            ))

        # 根据方法排序
        if method == "importance":
            feature_infos.sort(key=lambda f: f.correlation_with_target, reverse=True)
        elif method == "correlation":
            feature_infos.sort(key=lambda f: abs(f.correlation_with_target), reverse=True)

        # 应用阈值和数量限制
        selected = []
        for info in feature_infos:
            if len(selected) >= max_features:
                break
            if info.correlation_with_target >= threshold:
                info.is_selected = True
                selected.append(info)

        return selected


class AutoMLService:
    """AutoML服务 - 自动化模型训练"""

    def __init__(self):
        self.algorithms = {
            "binary": ["random_forest", "gradient_boosting", "logistic_regression"],
            "regression": ["xgboost_regressor", "random_forest", "linear_regression"],
        }

    def auto_train(
        self,
        df: pd.DataFrame,
        target_column: str,
        task_type: str,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        自动训练模型

        Args:
            df: 数据框
            target_column: 目标列
            task_type: 任务类型 (binary, regression, multiclass)
            test_size: 测试集比例
            random_state: 随机种子

        Returns:
            训练结果
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            mean_squared_error, r2_score, mean_absolute_error,
            roc_auc_score,
        )
        import warnings
        warnings.filterwarnings('ignore')

        # 准备数据
        X = df.drop(columns=[target_column])
        y = df[target_column]

        # 处理分类变量
        X = pd.get_dummies(X, drop_first=True)

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        # 选择算法
        algorithms = self.algorithms.get(task_type, self.algorithms["binary"])

        results = []

        for algo in algorithms:
            try:
                if algo == "logistic_regression" and task_type == "binary":
                    from sklearn.linear_model import LogisticRegression
                    model = LogisticRegression(random_state=random_state, max_iter=1000)
                elif algo == "linear_regression":
                    from sklearn.linear_model import LinearRegression
                    model = LinearRegression()
                elif algo == "random_forest":
                    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
                    if task_type == "binary":
                        model = RandomForestClassifier(
                            n_estimators=100, random_state=random_state, n_jobs=-1
                        )
                    else:
                        model = RandomForestRegressor(
                            n_estimators=100, random_state=random_state, n_jobs=-1
                        )
                elif algo in ["gradient_boosting", "xgboost_regressor"]:
                    # 使用 sklearn 的 GradientBoosting 替代
                    if task_type == "binary":
                        from sklearn.ensemble import GradientBoostingClassifier
                        model = GradientBoostingClassifier(
                            n_estimators=100, random_state=random_state
                        )
                    else:
                        from sklearn.ensemble import GradientBoostingRegressor
                        model = GradientBoostingRegressor(
                            n_estimators=100, random_state=random_state
                        )
                else:
                    continue

                # 训练
                model.fit(X_train, y_train)

                # 预测
                y_pred = model.predict(X_test)

                # 评估
                if task_type == "binary":
                    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
                    metrics = {
                        "accuracy": accuracy_score(y_test, y_pred),
                        "precision": precision_score(y_test, y_pred, zero_division=0),
                        "recall": recall_score(y_test, y_pred, zero_division=0),
                        "f1": f1_score(y_test, y_pred, zero_division=0),
                    }
                    if y_prob is not None:
                        metrics["auc_roc"] = roc_auc_score(y_test, y_prob)
                else:
                    metrics = {
                        "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
                        "r2": r2_score(y_test, y_pred),
                        "mae": mean_absolute_error(y_test, y_pred),
                        "mape": np.mean(np.abs((y_test - y_pred) / (y_test + 1e-8))) * 100,
                    }

                # 特征重要性
                feature_importance = []
                if hasattr(model, "feature_importances_"):
                    for name, importance in zip(X.columns, model.feature_importances_):
                        feature_importance.append({"feature": name, "importance": importance})

                results.append({
                    "algorithm": algo,
                    "metrics": metrics,
                    "feature_importance": feature_importance,
                })

            except Exception as e:
                logger.warning(f"Error training {algo}: {e}")

        if not results:
            return {"error": "No model could be trained"}

        # 选择最佳模型
        if task_type == "binary":
            best_result = max(results, key=lambda r: r["metrics"].get("auc_roc", 0))
        else:
            best_result = min(results, key=lambda r: r["metrics"].get("rmse", float('inf')))

        return {
            "best_algorithm": best_result["algorithm"],
            "metrics": best_result["metrics"],
            "feature_importance": best_result["feature_importance"],
            "all_results": results,
        }


# 全局实例
_feature_engine: Optional[FeatureAutoEngine] = None
_auto_ml_service: Optional[AutoMLService] = None


def get_feature_engine() -> FeatureAutoEngine:
    """获取特征工程引擎单例"""
    global _feature_engine
    if _feature_engine is None:
        _feature_engine = FeatureAutoEngine()
    return _feature_engine


def get_auto_ml_service() -> AutoMLService:
    """获取AutoML服务单例"""
    global _auto_ml_service
    if _auto_ml_service is None:
        _auto_ml_service = AutoMLService()
    return _auto_ml_service
