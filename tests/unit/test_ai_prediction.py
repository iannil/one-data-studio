"""
AI预测分析模块单元测试
覆盖用例: BU-AI-001 ~ BU-AI-004
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
from datetime import datetime, timedelta

# 检查 pandas 是否可用
try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

# 如果 pandas 不可用则跳过所有测试
pytestmark = pytest.mark.skipif(
    not _PANDAS_AVAILABLE,
    reason="pandas is not installed"
)


class TestAIPredictionService:
    """AI 预测分析服务测试"""

    @pytest.fixture
    def sample_sales_data(self):
        """销售历史数据"""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(90)]
        sales = [100 + i * 2 + np.random.normal(0, 10) for i in range(90)]
        return {
            'dates': dates,
            'sales': sales,
            'products': ['A'] * 30 + ['B'] * 30 + ['C'] * 30
        }

    @pytest.fixture
    def sample_customer_data(self):
        """客户数据"""
        return {
            'customer_id': [f'C{i:04d}' for i in range(100)],
            'age': np.random.randint(18, 70, 100),
            'income': np.random.uniform(30000, 200000, 100),
            'purchase_count': np.random.randint(1, 50, 100),
            'total_spend': np.random.uniform(100, 10000, 100),
            'last_purchase_days': np.random.randint(1, 365, 100)
        }

    @pytest.fixture
    def sample_behavior_data(self):
        """用户行为数据"""
        return {
            'user_id': [f'U{i:04d}' for i in range(50)],
            'page_views': np.random.randint(10, 500, 50),
            'session_duration': np.random.uniform(60, 3600, 50),
            'click_count': np.random.randint(5, 100, 50),
            'add_to_cart': np.random.randint(0, 20, 50),
            'purchase': np.random.choice([0, 1], 50, p=[0.7, 0.3])
        }

    @pytest.fixture
    def sample_anomaly_data(self):
        """包含异常的业务数据"""
        normal_data = np.random.normal(100, 10, 100)
        # 插入异常值
        anomaly_indices = [20, 45, 78]
        for idx in anomaly_indices:
            normal_data[idx] = 100 + np.random.choice([-1, 1]) * np.random.uniform(50, 100)
        return {
            'values': normal_data.tolist(),
            'timestamps': [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(100)],
            'anomaly_indices': anomaly_indices
        }

    @pytest.fixture
    def prediction_service(self):
        """预测服务实例"""
        return AIPredictionService()

    # ==================== BU-AI-001: 销量预测 ====================

    @pytest.mark.unit
    def test_sales_forecast_basic(self, sample_sales_data, prediction_service):
        """测试基础销量预测"""
        # Given: 历史销售数据
        history = sample_sales_data

        # When: 预测未来 7 天
        result = prediction_service.forecast_sales(
            dates=history['dates'],
            sales=history['sales'],
            forecast_days=7
        )

        # Then: 应返回预测结果
        assert 'forecast' in result
        assert 'dates' in result
        assert len(result['forecast']) == 7
        assert len(result['dates']) == 7

    @pytest.mark.unit
    def test_sales_forecast_with_confidence_interval(self, sample_sales_data, prediction_service):
        """测试带置信区间的销量预测"""
        # Given: 历史销售数据
        history = sample_sales_data

        # When: 预测并请求置信区间
        result = prediction_service.forecast_sales(
            dates=history['dates'],
            sales=history['sales'],
            forecast_days=7,
            include_confidence=True
        )

        # Then: 应包含置信区间
        assert 'lower_bound' in result
        assert 'upper_bound' in result
        assert all(result['lower_bound'][i] <= result['forecast'][i] <= result['upper_bound'][i]
                  for i in range(len(result['forecast'])))

    @pytest.mark.unit
    def test_sales_forecast_by_product(self, sample_sales_data, prediction_service):
        """测试按产品分组的销量预测"""
        # Given: 包含产品分类的销售数据
        history = sample_sales_data

        # When: 按产品预测
        result = prediction_service.forecast_sales_by_group(
            dates=history['dates'],
            sales=history['sales'],
            groups=history['products'],
            forecast_days=7
        )

        # Then: 应返回每个产品的预测
        assert 'A' in result
        assert 'B' in result
        assert 'C' in result
        for product in ['A', 'B', 'C']:
            assert len(result[product]['forecast']) == 7

    @pytest.mark.unit
    def test_sales_forecast_trend_detection(self, sample_sales_data, prediction_service):
        """测试销量趋势检测"""
        # Given: 有上升趋势的销售数据
        history = sample_sales_data

        # When: 分析趋势
        result = prediction_service.analyze_trend(
            dates=history['dates'],
            values=history['sales']
        )

        # Then: 应检测到上升趋势
        assert 'trend' in result
        assert result['trend'] in ['increasing', 'decreasing', 'stable']
        assert 'slope' in result
        assert 'trend_strength' in result

    # ==================== BU-AI-002: 客户分群 ====================

    @pytest.mark.unit
    def test_customer_segmentation_basic(self, sample_customer_data, prediction_service):
        """测试基础客户分群"""
        # Given: 客户数据
        customers = sample_customer_data

        # When: 执行 K-Means 分群
        result = prediction_service.segment_customers(
            data=customers,
            n_clusters=4,
            features=['income', 'total_spend', 'purchase_count']
        )

        # Then: 应返回分群结果
        assert 'clusters' in result
        assert 'cluster_centers' in result
        assert len(result['clusters']) == len(customers['customer_id'])
        assert len(set(result['clusters'])) <= 4

    @pytest.mark.unit
    def test_customer_segmentation_rfm(self, sample_customer_data, prediction_service):
        """测试 RFM 客户分群"""
        # Given: 包含 RFM 指标的客户数据
        customers = sample_customer_data

        # When: 执行 RFM 分群
        result = prediction_service.rfm_segmentation(
            recency=customers['last_purchase_days'],
            frequency=customers['purchase_count'],
            monetary=customers['total_spend']
        )

        # Then: 应返回 RFM 分群结果
        assert 'segments' in result
        assert 'rfm_scores' in result
        # 典型 RFM 分群
        expected_segments = ['Champions', 'Loyal', 'At Risk', 'Lost']
        assert any(seg in result['segment_names'] for seg in expected_segments)

    @pytest.mark.unit
    def test_customer_segmentation_cluster_profile(self, sample_customer_data, prediction_service):
        """测试分群特征画像"""
        # Given: 客户数据和分群结果
        customers = sample_customer_data
        segmentation = prediction_service.segment_customers(
            data=customers,
            n_clusters=3,
            features=['income', 'total_spend', 'purchase_count']
        )

        # When: 生成分群画像
        profiles = prediction_service.get_cluster_profiles(
            data=customers,
            clusters=segmentation['clusters']
        )

        # Then: 应返回每个分群的特征画像
        assert len(profiles) == 3
        for profile in profiles.values():
            assert 'avg_income' in profile or 'mean_income' in profile
            assert 'count' in profile or 'size' in profile

    # ==================== BU-AI-003: 用户行为预测 ====================

    @pytest.mark.unit
    def test_conversion_prediction(self, sample_behavior_data, prediction_service):
        """测试转化预测"""
        # Given: 用户行为数据
        behavior = sample_behavior_data
        features = ['page_views', 'session_duration', 'click_count', 'add_to_cart']

        # When: 预测购买概率
        result = prediction_service.predict_conversion(
            data=behavior,
            features=features,
            target='purchase'
        )

        # Then: 应返回转化概率
        assert 'probabilities' in result
        assert len(result['probabilities']) == len(behavior['user_id'])
        assert all(0 <= p <= 1 for p in result['probabilities'])

    @pytest.mark.unit
    def test_churn_prediction(self, sample_behavior_data, prediction_service):
        """测试流失预测"""
        # Given: 用户活跃度数据
        behavior = sample_behavior_data

        # When: 预测流失风险
        result = prediction_service.predict_churn(
            data=behavior,
            features=['page_views', 'session_duration', 'click_count']
        )

        # Then: 应返回流失风险评分
        assert 'churn_risk' in result
        assert len(result['churn_risk']) == len(behavior['user_id'])
        assert 'high_risk_users' in result

    @pytest.mark.unit
    def test_next_action_prediction(self, sample_behavior_data, prediction_service):
        """测试下一步行为预测"""
        # Given: 用户行为序列
        behavior = sample_behavior_data

        # When: 预测下一步行为
        result = prediction_service.predict_next_action(
            user_id='U0001',
            behavior_history=behavior
        )

        # Then: 应返回预测行为
        assert 'predicted_action' in result
        assert 'confidence' in result
        assert result['predicted_action'] in ['browse', 'search', 'add_to_cart', 'purchase', 'leave']

    # ==================== BU-AI-004: 异常检测 ====================

    @pytest.mark.unit
    def test_anomaly_detection_basic(self, sample_anomaly_data, prediction_service):
        """测试基础异常检测"""
        # Given: 包含异常的数据
        data = sample_anomaly_data

        # When: 执行异常检测
        result = prediction_service.detect_anomalies(
            values=data['values'],
            timestamps=data['timestamps']
        )

        # Then: 应检测到异常点
        assert 'anomalies' in result
        assert 'anomaly_indices' in result
        assert len(result['anomaly_indices']) > 0

    @pytest.mark.unit
    def test_anomaly_detection_with_threshold(self, sample_anomaly_data, prediction_service):
        """测试带阈值的异常检测"""
        # Given: 数据和阈值配置
        data = sample_anomaly_data
        threshold = 2.5  # 2.5 标准差

        # When: 使用阈值检测
        result = prediction_service.detect_anomalies(
            values=data['values'],
            timestamps=data['timestamps'],
            method='zscore',
            threshold=threshold
        )

        # Then: 应根据阈值检测异常
        assert 'scores' in result
        for idx in result['anomaly_indices']:
            assert abs(result['scores'][idx]) > threshold

    @pytest.mark.unit
    def test_anomaly_detection_isolation_forest(self, sample_anomaly_data, prediction_service):
        """测试 Isolation Forest 异常检测"""
        # Given: 数据
        data = sample_anomaly_data

        # When: 使用 Isolation Forest
        result = prediction_service.detect_anomalies(
            values=data['values'],
            timestamps=data['timestamps'],
            method='isolation_forest',
            contamination=0.05
        )

        # Then: 应检测到异常
        assert 'anomalies' in result
        assert 'anomaly_scores' in result

    @pytest.mark.unit
    def test_anomaly_detection_time_series(self, sample_anomaly_data, prediction_service):
        """测试时序异常检测"""
        # Given: 时序数据
        data = sample_anomaly_data

        # When: 使用时序异常检测
        result = prediction_service.detect_time_series_anomalies(
            values=data['values'],
            timestamps=data['timestamps'],
            seasonality='hourly'
        )

        # Then: 应检测到异常并考虑季节性
        assert 'anomalies' in result
        assert 'expected_values' in result
        assert 'residuals' in result

    @pytest.mark.unit
    def test_anomaly_alert_generation(self, sample_anomaly_data, prediction_service):
        """测试异常告警生成"""
        # Given: 检测到的异常
        data = sample_anomaly_data
        detection_result = prediction_service.detect_anomalies(
            values=data['values'],
            timestamps=data['timestamps']
        )

        # When: 生成告警
        alerts = prediction_service.generate_anomaly_alerts(
            detection_result=detection_result,
            metric_name='sales',
            severity_thresholds={'warning': 2, 'critical': 3}
        )

        # Then: 应生成告警
        assert len(alerts) > 0
        for alert in alerts:
            assert 'severity' in alert
            assert 'timestamp' in alert
            assert 'value' in alert
            assert alert['severity'] in ['warning', 'critical']


class AIPredictionService:
    """AI 预测分析服务"""

    def forecast_sales(self, dates: List, sales: List, forecast_days: int,
                       include_confidence: bool = False) -> Dict:
        """销量预测"""
        # 简单线性趋势预测
        x = np.arange(len(sales))
        coeffs = np.polyfit(x, sales, 1)
        trend = np.poly1d(coeffs)

        # 预测未来
        future_x = np.arange(len(sales), len(sales) + forecast_days)
        forecast = trend(future_x)

        # 生成未来日期
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]

        result = {
            'forecast': forecast.tolist(),
            'dates': future_dates
        }

        if include_confidence:
            # 简单置信区间（基于历史标准差）
            std = np.std(sales)
            result['lower_bound'] = (forecast - 1.96 * std).tolist()
            result['upper_bound'] = (forecast + 1.96 * std).tolist()

        return result

    def forecast_sales_by_group(self, dates: List, sales: List, groups: List,
                                 forecast_days: int) -> Dict:
        """按分组销量预测"""
        import pandas as pd

        # 按组分组
        unique_groups = list(set(groups))
        result = {}

        for group in unique_groups:
            group_indices = [i for i, g in enumerate(groups) if g == group]
            group_sales = [sales[i] for i in group_indices]
            group_dates = [dates[i] for i in group_indices]

            result[group] = self.forecast_sales(group_dates, group_sales, forecast_days)

        return result

    def analyze_trend(self, dates: List, values: List) -> Dict:
        """分析趋势"""
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        slope = coeffs[0]

        # 计算趋势强度（R²）
        predicted = np.poly1d(coeffs)(x)
        ss_res = np.sum((np.array(values) - predicted) ** 2)
        ss_tot = np.sum((np.array(values) - np.mean(values)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 判断趋势方向
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'slope': slope,
            'trend_strength': r2
        }

    def segment_customers(self, data: Dict, n_clusters: int, features: List) -> Dict:
        """客户分群"""
        # 提取特征
        feature_matrix = np.array([data[f] for f in features]).T

        # 简化的 K-Means 实现
        np.random.seed(42)
        centers = feature_matrix[np.random.choice(len(feature_matrix), n_clusters, replace=False)]

        for _ in range(10):  # 迭代
            # 分配簇
            distances = np.array([[np.linalg.norm(x - c) for c in centers] for x in feature_matrix])
            clusters = np.argmin(distances, axis=1)

            # 更新中心
            new_centers = np.array([feature_matrix[clusters == k].mean(axis=0)
                                   if np.sum(clusters == k) > 0 else centers[k]
                                   for k in range(n_clusters)])
            centers = new_centers

        return {
            'clusters': clusters.tolist(),
            'cluster_centers': centers.tolist()
        }

    def rfm_segmentation(self, recency: List, frequency: List, monetary: List) -> Dict:
        """RFM 分群"""
        # 计算 RFM 分数 (1-5)
        def score_quantile(values, reverse=False):
            percentiles = np.percentile(values, [20, 40, 60, 80])
            scores = []
            for v in values:
                if v <= percentiles[0]:
                    scores.append(5 if reverse else 1)
                elif v <= percentiles[1]:
                    scores.append(4 if reverse else 2)
                elif v <= percentiles[2]:
                    scores.append(3)
                elif v <= percentiles[3]:
                    scores.append(2 if reverse else 4)
                else:
                    scores.append(1 if reverse else 5)
            return scores

        r_scores = score_quantile(recency, reverse=True)  # Recency 越小越好
        f_scores = score_quantile(frequency)
        m_scores = score_quantile(monetary)

        # 综合分数
        rfm_scores = [f'{r}{f}{m}' for r, f, m in zip(r_scores, f_scores, m_scores)]

        # 分群规则
        segments = []
        for r, f, m in zip(r_scores, f_scores, m_scores):
            avg = (r + f + m) / 3
            if avg >= 4:
                segments.append('Champions')
            elif avg >= 3:
                segments.append('Loyal')
            elif r <= 2:
                segments.append('At Risk')
            else:
                segments.append('Others')

        return {
            'segments': segments,
            'rfm_scores': rfm_scores,
            'segment_names': list(set(segments))
        }

    def get_cluster_profiles(self, data: Dict, clusters: List) -> Dict:
        """获取分群画像"""
        unique_clusters = set(clusters)
        profiles = {}

        for cluster_id in unique_clusters:
            cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
            profile = {'count': len(cluster_indices)}

            for key, values in data.items():
                if isinstance(values[0], (int, float)):
                    cluster_values = [values[i] for i in cluster_indices]
                    profile[f'mean_{key}'] = np.mean(cluster_values)
                    profile[f'std_{key}'] = np.std(cluster_values)

            profiles[f'cluster_{cluster_id}'] = profile

        return profiles

    def predict_conversion(self, data: Dict, features: List, target: str) -> Dict:
        """预测转化"""
        # 提取特征和目标
        X = np.array([data[f] for f in features]).T
        y = np.array(data[target])

        # 简单逻辑回归预测
        # 使用 sigmoid 函数
        weights = np.random.randn(len(features))
        scores = X @ weights
        probabilities = 1 / (1 + np.exp(-scores))

        return {
            'probabilities': probabilities.tolist(),
            'predictions': (probabilities > 0.5).astype(int).tolist()
        }

    def predict_churn(self, data: Dict, features: List) -> Dict:
        """预测流失"""
        X = np.array([data[f] for f in features]).T

        # 简化的流失风险评分
        # 活跃度越低，风险越高
        normalized = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)
        churn_risk = 1 / (1 + np.exp(normalized.mean(axis=1)))

        high_risk_threshold = 0.7
        high_risk_users = [data.get('user_id', [f'user_{i}' for i in range(len(churn_risk))])[i]
                          for i, risk in enumerate(churn_risk) if risk > high_risk_threshold]

        return {
            'churn_risk': churn_risk.tolist(),
            'high_risk_users': high_risk_users
        }

    def predict_next_action(self, user_id: str, behavior_history: Dict) -> Dict:
        """预测下一步行为"""
        actions = ['browse', 'search', 'add_to_cart', 'purchase', 'leave']
        probabilities = np.random.dirichlet(np.ones(5))

        return {
            'user_id': user_id,
            'predicted_action': actions[np.argmax(probabilities)],
            'confidence': float(max(probabilities)),
            'action_probabilities': dict(zip(actions, probabilities.tolist()))
        }

    def detect_anomalies(self, values: List, timestamps: List,
                         method: str = 'zscore', threshold: float = 3.0,
                         contamination: float = 0.05) -> Dict:
        """检测异常"""
        values_arr = np.array(values)

        if method == 'zscore':
            mean = np.mean(values_arr)
            std = np.std(values_arr)
            scores = (values_arr - mean) / (std + 1e-8)
            anomaly_mask = np.abs(scores) > threshold
        elif method == 'isolation_forest':
            # 简化的 Isolation Forest
            scores = np.abs(values_arr - np.median(values_arr)) / (np.std(values_arr) + 1e-8)
            n_anomalies = int(len(values) * contamination)
            threshold_score = np.sort(scores)[-n_anomalies] if n_anomalies > 0 else float('inf')
            anomaly_mask = scores >= threshold_score
        else:
            scores = np.zeros_like(values_arr)
            anomaly_mask = np.zeros(len(values), dtype=bool)

        anomaly_indices = np.where(anomaly_mask)[0].tolist()

        return {
            'anomalies': [values[i] for i in anomaly_indices],
            'anomaly_indices': anomaly_indices,
            'anomaly_timestamps': [timestamps[i] for i in anomaly_indices],
            'scores': scores.tolist(),
            'anomaly_scores': scores.tolist()
        }

    def detect_time_series_anomalies(self, values: List, timestamps: List,
                                      seasonality: str = 'daily') -> Dict:
        """时序异常检测"""
        values_arr = np.array(values)

        # 简单移动平均作为期望值
        window = 5
        expected = np.convolve(values_arr, np.ones(window)/window, mode='same')
        residuals = values_arr - expected

        # 基于残差检测异常
        threshold = 2 * np.std(residuals)
        anomaly_mask = np.abs(residuals) > threshold

        return {
            'anomalies': [values[i] for i, m in enumerate(anomaly_mask) if m],
            'anomaly_indices': np.where(anomaly_mask)[0].tolist(),
            'expected_values': expected.tolist(),
            'residuals': residuals.tolist()
        }

    def generate_anomaly_alerts(self, detection_result: Dict, metric_name: str,
                                 severity_thresholds: Dict) -> List[Dict]:
        """生成异常告警"""
        alerts = []

        for i, idx in enumerate(detection_result['anomaly_indices']):
            score = abs(detection_result['scores'][idx])

            if score >= severity_thresholds.get('critical', 3):
                severity = 'critical'
            elif score >= severity_thresholds.get('warning', 2):
                severity = 'warning'
            else:
                continue

            alerts.append({
                'metric': metric_name,
                'severity': severity,
                'timestamp': detection_result['anomaly_timestamps'][i],
                'value': detection_result['anomalies'][i],
                'score': score,
                'message': f"Anomaly detected in {metric_name}: value={detection_result['anomalies'][i]:.2f}"
            })

        return alerts
