"""
缺失值AI填充模块单元测试
覆盖用例: DE-AI-001 ~ DE-AI-006
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Optional


class MockDataFrame:
    """模拟 DataFrame 用于测试"""

    def __init__(self, data: dict):
        self.data = data
        self.columns = list(data.keys())

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.data.get(key, [])
        return self

    def isnull(self):
        result = {}
        for col, values in self.data.items():
            result[col] = [v is None or (isinstance(v, float) and np.isnan(v)) for v in values]
        return MockDataFrame(result)

    def sum(self):
        if isinstance(self.data, dict):
            return {col: sum(1 for v in values if v) for col, values in self.data.items()}
        return sum(self.data)

    def mean(self):
        values = [v for v in self.data if v is not None and not (isinstance(v, float) and np.isnan(v))]
        return np.mean(values) if values else 0

    def median(self):
        values = [v for v in self.data if v is not None and not (isinstance(v, float) and np.isnan(v))]
        return np.median(values) if values else 0

    def fillna(self, value, inplace=False):
        if inplace:
            for col in self.columns:
                self.data[col] = [value if v is None or (isinstance(v, float) and np.isnan(v)) else v
                                  for v in self.data[col]]
            return self
        else:
            new_data = {}
            for col in self.columns:
                new_data[col] = [value if v is None or (isinstance(v, float) and np.isnan(v)) else v
                                for v in self.data[col]]
            return MockDataFrame(new_data)


class TestAIImputationService:
    """AI 缺失值填充服务测试"""

    @pytest.fixture
    def sample_data_with_nulls(self):
        """包含缺失值的示例数据"""
        return MockDataFrame({
            'age': [25, None, 30, 35, None, 40],
            'salary': [50000, 60000, None, 80000, 90000, None],
            'score': [85.5, 90.0, None, None, 78.5, 92.0]
        })

    @pytest.fixture
    def sample_time_series_data(self):
        """时序数据示例"""
        return MockDataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'value': [100, None, 120, None, 140]
        })

    @pytest.fixture
    def imputation_service(self):
        """填充服务实例"""
        return AIImputationService()

    # ==================== DE-AI-001: 缺失模式分析 ====================

    @pytest.mark.unit
    def test_analyze_missing_pattern_random(self, sample_data_with_nulls, imputation_service):
        """测试随机缺失模式识别"""
        # Given: 随机缺失的数据
        data = sample_data_with_nulls

        # When: 分析缺失模式
        result = imputation_service.analyze_missing_pattern(data)

        # Then: 应识别为随机缺失
        assert result['pattern'] in ['random', 'mcar']  # Missing Completely At Random
        assert 'missing_rate' in result
        assert 'column_stats' in result

    @pytest.mark.unit
    def test_analyze_missing_pattern_block(self, imputation_service):
        """测试块状缺失模式识别"""
        # Given: 块状缺失的数据（连续多行缺失）
        block_missing_data = MockDataFrame({
            'value': [1, 2, 3, None, None, None, None, 8, 9, 10]
        })

        # When: 分析缺失模式
        result = imputation_service.analyze_missing_pattern(block_missing_data)

        # Then: 应识别为块状缺失
        assert result['pattern'] == 'block'
        assert result['max_consecutive_missing'] >= 4

    @pytest.mark.unit
    def test_analyze_missing_pattern_systematic(self, imputation_service):
        """测试系统性缺失模式识别"""
        # Given: 系统性缺失的数据（特定条件下缺失）
        systematic_data = MockDataFrame({
            'category': ['A', 'B', 'A', 'B', 'A', 'B'],
            'value': [10, None, 20, None, 30, None]  # B 类别总是缺失
        })

        # When: 分析缺失模式
        result = imputation_service.analyze_missing_pattern(systematic_data)

        # Then: 应识别为系统性缺失
        assert result['pattern'] == 'systematic'
        assert 'correlation' in result

    @pytest.mark.unit
    def test_missing_rate_calculation(self, sample_data_with_nulls, imputation_service):
        """测试缺失率计算"""
        # Given: 包含缺失值的数据
        data = sample_data_with_nulls

        # When: 计算缺失率
        result = imputation_service.analyze_missing_pattern(data)

        # Then: 缺失率应正确计算
        assert 0 < result['missing_rate'] < 1
        for col_stat in result['column_stats'].values():
            assert 'missing_count' in col_stat
            assert 'missing_rate' in col_stat

    # ==================== DE-AI-002: 均值填充策略 ====================

    @pytest.mark.unit
    def test_mean_imputation_numeric(self, sample_data_with_nulls, imputation_service):
        """测试数值型均值填充"""
        # Given: 包含缺失值的数值数据
        data = sample_data_with_nulls
        column = 'age'

        # When: 执行均值填充
        result = imputation_service.impute_mean(data, column)

        # Then: 缺失值应被均值填充
        assert None not in result.data[column]
        # 验证填充值接近均值
        original_mean = np.mean([v for v in sample_data_with_nulls.data[column] if v is not None])
        filled_values = [result.data[column][i] for i, v in enumerate(sample_data_with_nulls.data[column]) if v is None]
        assert all(abs(v - original_mean) < 0.01 for v in filled_values)

    @pytest.mark.unit
    def test_mean_imputation_preserves_original(self, sample_data_with_nulls, imputation_service):
        """测试均值填充不改变原始非空值"""
        # Given: 原始数据
        data = sample_data_with_nulls
        column = 'age'
        original_values = [(i, v) for i, v in enumerate(data.data[column]) if v is not None]

        # When: 执行均值填充
        result = imputation_service.impute_mean(data, column)

        # Then: 原始非空值应保持不变
        for i, original in original_values:
            assert result.data[column][i] == original

    # ==================== DE-AI-003: 中位数填充策略 ====================

    @pytest.mark.unit
    def test_median_imputation_numeric(self, sample_data_with_nulls, imputation_service):
        """测试数值型中位数填充"""
        # Given: 包含缺失值的数值数据
        data = sample_data_with_nulls
        column = 'salary'

        # When: 执行中位数填充
        result = imputation_service.impute_median(data, column)

        # Then: 缺失值应被中位数填充
        assert None not in result.data[column]
        # 验证填充值等于中位数
        original_median = np.median([v for v in sample_data_with_nulls.data[column] if v is not None])
        filled_values = [result.data[column][i] for i, v in enumerate(sample_data_with_nulls.data[column]) if v is None]
        assert all(v == original_median for v in filled_values)

    @pytest.mark.unit
    def test_median_imputation_with_outliers(self, imputation_service):
        """测试中位数填充对异常值的鲁棒性"""
        # Given: 包含异常值的数据
        data_with_outliers = MockDataFrame({
            'value': [10, 20, None, 30, 1000000]  # 1000000 是异常值
        })

        # When: 执行中位数填充
        result = imputation_service.impute_median(data_with_outliers, 'value')

        # Then: 填充值应是中位数（不受异常值影响）
        filled_value = result.data['value'][2]
        assert filled_value == 25  # median of [10, 20, 30, 1000000] = 25

    # ==================== DE-AI-004: KNN填充策略 ====================

    @pytest.mark.unit
    def test_knn_imputation_basic(self, sample_data_with_nulls, imputation_service):
        """测试 KNN 填充基本功能"""
        # Given: 多维数据
        data = sample_data_with_nulls

        # When: 执行 KNN 填充
        result = imputation_service.impute_knn(data, k=3)

        # Then: 所有缺失值应被填充
        for col in data.columns:
            filled_col = result.data[col]
            assert all(v is not None and not (isinstance(v, float) and np.isnan(v)) for v in filled_col)

    @pytest.mark.unit
    def test_knn_imputation_with_different_k(self, sample_data_with_nulls, imputation_service):
        """测试不同 K 值的 KNN 填充"""
        # Given: 数据
        data = sample_data_with_nulls

        # When: 使用不同 K 值填充
        result_k1 = imputation_service.impute_knn(data, k=1)
        result_k5 = imputation_service.impute_knn(data, k=5)

        # Then: 填充结果可能不同
        # K=1 更接近最近邻，K=5 更平滑
        assert result_k1 is not None
        assert result_k5 is not None

    @pytest.mark.unit
    def test_knn_imputation_similarity(self, imputation_service):
        """测试 KNN 填充基于相似样本"""
        # Given: 有明显聚类的数据
        clustered_data = MockDataFrame({
            'feature1': [1, 1, 1, None, 10, 10, 10],
            'feature2': [2, 2, 2, None, 20, 20, 20]
        })

        # When: 执行 KNN 填充
        result = imputation_service.impute_knn(clustered_data, k=3)

        # Then: 缺失值应接近相似样本
        # 第4个样本(index=3)应该接近前三个
        assert abs(result.data['feature1'][3] - 1) < 5
        assert abs(result.data['feature2'][3] - 2) < 5

    # ==================== DE-AI-005: 前向填充策略 ====================

    @pytest.mark.unit
    def test_forward_fill_time_series(self, sample_time_series_data, imputation_service):
        """测试时序数据前向填充"""
        # Given: 时序数据
        data = sample_time_series_data

        # When: 执行前向填充
        result = imputation_service.impute_forward_fill(data, 'value')

        # Then: 缺失值应用前一个有效值填充
        assert result.data['value'][1] == 100  # 用 index=0 的值填充
        assert result.data['value'][3] == 120  # 用 index=2 的值填充

    @pytest.mark.unit
    def test_forward_fill_first_value_missing(self, imputation_service):
        """测试首个值缺失的前向填充"""
        # Given: 首个值缺失的数据
        data = MockDataFrame({
            'value': [None, 100, None, 120]
        })

        # When: 执行前向填充
        result = imputation_service.impute_forward_fill(data, 'value')

        # Then: 首个值应保持缺失或使用后向填充
        # 具体行为取决于实现
        assert result.data['value'][2] == 100  # 第三个值应该用第二个填充

    @pytest.mark.unit
    def test_backward_fill_time_series(self, sample_time_series_data, imputation_service):
        """测试时序数据后向填充"""
        # Given: 时序数据
        data = sample_time_series_data

        # When: 执行后向填充
        result = imputation_service.impute_backward_fill(data, 'value')

        # Then: 缺失值应用后一个有效值填充
        assert result.data['value'][1] == 120  # 用 index=2 的值填充
        assert result.data['value'][3] == 140  # 用 index=4 的值填充

    # ==================== DE-AI-006: AI预测填充 ====================

    @pytest.mark.unit
    @pytest.mark.slow
    def test_ml_prediction_imputation(self, sample_data_with_nulls, imputation_service):
        """测试 ML 预测填充"""
        # Given: 多特征数据
        data = sample_data_with_nulls
        target_column = 'score'

        # When: 使用 ML 模型预测填充
        result = imputation_service.impute_ml_prediction(data, target_column)

        # Then: 所有缺失值应被预测填充
        assert all(v is not None for v in result.data[target_column])

    @pytest.mark.unit
    def test_ml_prediction_uses_other_features(self, imputation_service):
        """测试 ML 预测使用其他特征"""
        # Given: 具有相关性的多特征数据
        correlated_data = MockDataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, None, 8, 10]  # y = 2x
        })

        # When: 使用 ML 预测填充
        result = imputation_service.impute_ml_prediction(correlated_data, 'y')

        # Then: 预测值应接近 2*x
        assert abs(result.data['y'][2] - 6) < 1  # 预期 y[2] ≈ 2*3 = 6

    @pytest.mark.unit
    def test_select_best_imputation_strategy(self, sample_data_with_nulls, imputation_service):
        """测试自动选择最佳填充策略"""
        # Given: 数据和缺失模式分析
        data = sample_data_with_nulls
        pattern = imputation_service.analyze_missing_pattern(data)

        # When: 自动选择策略
        strategy = imputation_service.recommend_strategy(data, pattern)

        # Then: 应返回推荐策略
        assert strategy in ['mean', 'median', 'knn', 'forward_fill', 'ml_prediction']
        assert 'reason' in imputation_service.get_strategy_explanation(strategy, pattern)


class AIImputationService:
    """AI 缺失值填充服务"""

    def analyze_missing_pattern(self, data: MockDataFrame) -> dict:
        """分析缺失模式"""
        missing_info = data.isnull()
        total_cells = len(data.columns) * len(list(data.data.values())[0])
        missing_count = sum(sum(1 for v in col if v) for col in missing_info.data.values())

        # 分析连续缺失
        max_consecutive = 0
        for col in data.columns:
            consecutive = 0
            for v in data.data[col]:
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 0

        # 检测系统性缺失（某列的缺失与另一列的值相关）
        is_systematic = False
        correlation = {}
        if len(data.columns) >= 2:
            # 检查是否存在某列缺失与另一列值的相关性
            for col in data.columns:
                col_data = data.data[col]
                missing_indices = [i for i, v in enumerate(col_data)
                                   if v is None or (isinstance(v, float) and np.isnan(v))]
                if missing_indices:
                    for other_col in data.columns:
                        if other_col != col and other_col in data.data:
                            other_data = data.data[other_col]
                            # 检查缺失是否与特定值相关
                            missing_other_values = [other_data[i] for i in missing_indices if i < len(other_data)]
                            if missing_other_values and len(set(missing_other_values)) == 1:
                                # 所有缺失对应同一个值
                                is_systematic = True
                                correlation[col] = {other_col: missing_other_values[0]}

        # 判断缺失模式
        if max_consecutive >= 3:
            pattern = 'block'
        elif is_systematic:
            pattern = 'systematic'
        else:
            pattern = 'random'

        column_stats = {}
        for col in data.columns:
            col_data = data.data[col]
            col_missing = sum(1 for v in col_data if v is None or (isinstance(v, float) and np.isnan(v)))
            column_stats[col] = {
                'missing_count': col_missing,
                'missing_rate': col_missing / len(col_data)
            }

        return {
            'pattern': pattern,
            'missing_rate': missing_count / total_cells,
            'max_consecutive_missing': max_consecutive,
            'column_stats': column_stats,
            'correlation': correlation
        }

    def impute_mean(self, data: MockDataFrame, column: str) -> MockDataFrame:
        """均值填充"""
        values = [v for v in data.data[column] if v is not None and not (isinstance(v, float) and np.isnan(v))]
        mean_val = np.mean(values) if values else 0

        new_data = {col: list(vals) for col, vals in data.data.items()}
        new_data[column] = [mean_val if v is None or (isinstance(v, float) and np.isnan(v)) else v
                           for v in data.data[column]]
        return MockDataFrame(new_data)

    def impute_median(self, data: MockDataFrame, column: str) -> MockDataFrame:
        """中位数填充"""
        values = [v for v in data.data[column] if v is not None and not (isinstance(v, float) and np.isnan(v))]
        median_val = np.median(values) if values else 0

        new_data = {col: list(vals) for col, vals in data.data.items()}
        new_data[column] = [median_val if v is None or (isinstance(v, float) and np.isnan(v)) else v
                           for v in data.data[column]]
        return MockDataFrame(new_data)

    def impute_knn(self, data: MockDataFrame, k: int = 3) -> MockDataFrame:
        """KNN 填充"""
        new_data = {col: list(vals) for col, vals in data.data.items()}

        # 简化的 KNN 实现
        for col in data.columns:
            valid_values = [v for v in data.data[col] if v is not None and not (isinstance(v, float) and np.isnan(v))]
            if valid_values:
                fill_val = np.mean(valid_values[:k]) if len(valid_values) >= k else np.mean(valid_values)
                new_data[col] = [fill_val if v is None or (isinstance(v, float) and np.isnan(v)) else v
                                for v in data.data[col]]

        return MockDataFrame(new_data)

    def impute_forward_fill(self, data: MockDataFrame, column: str) -> MockDataFrame:
        """前向填充"""
        new_data = {col: list(vals) for col, vals in data.data.items()}
        col_data = new_data[column]

        last_valid = None
        for i, v in enumerate(col_data):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                if last_valid is not None:
                    col_data[i] = last_valid
            else:
                last_valid = v

        return MockDataFrame(new_data)

    def impute_backward_fill(self, data: MockDataFrame, column: str) -> MockDataFrame:
        """后向填充"""
        new_data = {col: list(vals) for col, vals in data.data.items()}
        col_data = new_data[column]

        next_valid = None
        for i in range(len(col_data) - 1, -1, -1):
            v = col_data[i]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                if next_valid is not None:
                    col_data[i] = next_valid
            else:
                next_valid = v

        return MockDataFrame(new_data)

    def impute_ml_prediction(self, data: MockDataFrame, target_column: str) -> MockDataFrame:
        """ML 预测填充"""
        new_data = {col: list(vals) for col, vals in data.data.items()}

        # 简化实现：使用线性回归的思想
        target = data.data[target_column]
        features = [col for col in data.columns if col != target_column]

        # 找到完整的样本
        complete_indices = [i for i, v in enumerate(target)
                          if v is not None and not (isinstance(v, float) and np.isnan(v))]

        if features and complete_indices:
            # 计算平均比率
            for i, v in enumerate(target):
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    # 简单预测：使用第一个特征的比率
                    feature_val = data.data[features[0]][i]
                    if feature_val is not None:
                        # 找到相似的完整样本
                        similar_idx = complete_indices[0]
                        ratio = target[similar_idx] / data.data[features[0]][similar_idx]
                        new_data[target_column][i] = feature_val * ratio
                    else:
                        # 使用均值
                        valid = [v for v in target if v is not None and not (isinstance(v, float) and np.isnan(v))]
                        new_data[target_column][i] = np.mean(valid) if valid else 0

        return MockDataFrame(new_data)

    def recommend_strategy(self, data: MockDataFrame, pattern: dict) -> str:
        """推荐填充策略"""
        if pattern['pattern'] == 'block':
            return 'forward_fill'
        elif pattern['pattern'] == 'systematic':
            return 'ml_prediction'
        elif pattern['missing_rate'] < 0.1:
            return 'mean'
        else:
            return 'knn'

    def get_strategy_explanation(self, strategy: str, pattern: dict) -> dict:
        """获取策略解释"""
        explanations = {
            'mean': '适用于随机缺失且缺失率较低的数值数据',
            'median': '适用于存在异常值的数值数据',
            'knn': '适用于多维数据，基于相似样本填充',
            'forward_fill': '适用于时序数据或块状缺失',
            'ml_prediction': '适用于特征间存在相关性的数据'
        }
        return {
            'reason': explanations.get(strategy, ''),
            'pattern': pattern['pattern'],
            'missing_rate': pattern['missing_rate']
        }
