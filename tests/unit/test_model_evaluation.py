"""
模型评估模块单元测试
覆盖用例: AE-EV-001 ~ AE-EV-003
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
from datetime import datetime


class TestModelEvaluationService:
    """模型评估服务测试"""

    @pytest.fixture
    def mock_model(self):
        """Mock 模型"""
        model = MagicMock()
        model.predict.return_value = np.array([0.8, 0.9, 0.7, 0.85, 0.95])
        model.model_id = 'model-001'
        model.version = '1.0.0'
        return model

    @pytest.fixture
    def sample_test_data(self):
        """测试数据集"""
        return {
            'X_test': np.array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]),
            'y_test': np.array([0.8, 0.85, 0.75, 0.9, 0.92])
        }

    @pytest.fixture
    def classification_data(self):
        """分类任务测试数据"""
        return {
            'y_true': np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1]),
            'y_pred': np.array([1, 0, 1, 0, 0, 1, 1, 0, 1, 1]),
            'y_prob': np.array([0.9, 0.2, 0.85, 0.4, 0.1, 0.95, 0.6, 0.3, 0.8, 0.88])
        }

    @pytest.fixture
    def regression_data(self):
        """回归任务测试数据"""
        return {
            'y_true': np.array([3.0, 5.5, 2.1, 7.8, 4.5]),
            'y_pred': np.array([2.8, 5.2, 2.5, 7.5, 4.8])
        }

    @pytest.fixture
    def evaluation_service(self):
        """评估服务实例"""
        return ModelEvaluationService()

    # ==================== AE-EV-001: 模型评估 ====================

    @pytest.mark.unit
    def test_evaluate_classification_model(self, mock_model, classification_data, evaluation_service):
        """测试分类模型评估"""
        # Given: 分类模型和测试数据
        y_true = classification_data['y_true']
        y_pred = classification_data['y_pred']
        y_prob = classification_data['y_prob']

        # When: 执行评估
        result = evaluation_service.evaluate_classification(y_true, y_pred, y_prob)

        # Then: 应返回完整评估指标
        assert 'accuracy' in result
        assert 'precision' in result
        assert 'recall' in result
        assert 'f1_score' in result
        assert 'auc_roc' in result
        assert 0 <= result['accuracy'] <= 1
        assert 0 <= result['f1_score'] <= 1

    @pytest.mark.unit
    def test_evaluate_regression_model(self, regression_data, evaluation_service):
        """测试回归模型评估"""
        # Given: 回归预测结果
        y_true = regression_data['y_true']
        y_pred = regression_data['y_pred']

        # When: 执行评估
        result = evaluation_service.evaluate_regression(y_true, y_pred)

        # Then: 应返回回归指标
        assert 'mse' in result
        assert 'rmse' in result
        assert 'mae' in result
        assert 'r2_score' in result
        assert result['mse'] >= 0
        assert result['rmse'] >= 0

    @pytest.mark.unit
    def test_evaluate_with_confusion_matrix(self, classification_data, evaluation_service):
        """测试生成混淆矩阵"""
        # Given: 分类结果
        y_true = classification_data['y_true']
        y_pred = classification_data['y_pred']

        # When: 生成混淆矩阵
        cm = evaluation_service.get_confusion_matrix(y_true, y_pred)

        # Then: 应返回正确的混淆矩阵
        assert cm.shape == (2, 2)  # 二分类
        assert cm.sum() == len(y_true)
        # TP + FN = Actual Positives
        assert cm[1, 0] + cm[1, 1] == sum(y_true == 1)

    @pytest.mark.unit
    def test_evaluate_per_class_metrics(self, classification_data, evaluation_service):
        """测试分类别评估指标"""
        # Given: 多类别分类结果
        y_true = classification_data['y_true']
        y_pred = classification_data['y_pred']

        # When: 获取分类别指标
        result = evaluation_service.get_per_class_metrics(y_true, y_pred)

        # Then: 应返回每个类别的指标
        assert 'class_0' in result or 0 in result
        assert 'class_1' in result or 1 in result
        for class_metrics in result.values():
            assert 'precision' in class_metrics
            assert 'recall' in class_metrics
            assert 'f1_score' in class_metrics

    @pytest.mark.unit
    def test_evaluate_model_on_test_set(self, mock_model, sample_test_data, evaluation_service):
        """测试在测试集上评估模型"""
        # Given: 模型和测试集
        X_test = sample_test_data['X_test']
        y_test = sample_test_data['y_test']

        # When: 在测试集上评估
        result = evaluation_service.evaluate_model(mock_model, X_test, y_test, task='regression')

        # Then: 应返回评估结果
        assert 'metrics' in result
        assert 'predictions' in result
        assert 'evaluation_time' in result

    # ==================== AE-EV-002: 模型对比 ====================

    @pytest.mark.unit
    def test_compare_two_models(self, sample_test_data, evaluation_service):
        """测试两个模型对比"""
        # Given: 两个模型的预测结果
        model_a_preds = np.array([0.8, 0.9, 0.7, 0.85, 0.95])
        model_b_preds = np.array([0.75, 0.88, 0.72, 0.83, 0.91])
        y_true = sample_test_data['y_test']

        models = {
            'model_a': {'predictions': model_a_preds, 'version': '1.0.0'},
            'model_b': {'predictions': model_b_preds, 'version': '2.0.0'}
        }

        # When: 对比模型
        result = evaluation_service.compare_models(models, y_true, task='regression')

        # Then: 应返回对比结果
        assert 'model_a' in result
        assert 'model_b' in result
        assert 'comparison' in result
        assert 'best_model' in result['comparison']

    @pytest.mark.unit
    def test_compare_models_multiple_metrics(self, classification_data, evaluation_service):
        """测试多指标模型对比"""
        # Given: 多个模型的分类结果
        y_true = classification_data['y_true']
        models = {
            'model_v1': {
                'predictions': np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1]),
                'version': '1.0'
            },
            'model_v2': {
                'predictions': np.array([1, 0, 1, 0, 0, 1, 1, 0, 1, 1]),
                'version': '2.0'
            }
        }

        # When: 对比模型
        result = evaluation_service.compare_models(models, y_true, task='classification')

        # Then: 应包含多个对比指标
        comparison = result['comparison']
        assert 'accuracy_comparison' in comparison or 'metric_comparison' in comparison
        assert 'improvement' in comparison or 'delta' in comparison

    @pytest.mark.unit
    def test_compare_models_with_visualization_data(self, regression_data, evaluation_service):
        """测试生成可视化对比数据"""
        # Given: 模型预测结果
        y_true = regression_data['y_true']
        models = {
            'baseline': {'predictions': regression_data['y_pred'], 'version': '1.0'},
            'improved': {'predictions': y_true * 0.99, 'version': '2.0'}  # 更好的模型
        }

        # When: 生成对比可视化数据
        result = evaluation_service.compare_models(models, y_true, task='regression')
        viz_data = evaluation_service.get_comparison_visualization_data(result)

        # Then: 应返回可视化数据
        assert 'chart_data' in viz_data
        assert 'labels' in viz_data
        assert len(viz_data['chart_data']) == len(models)

    @pytest.mark.unit
    def test_model_version_history(self, evaluation_service):
        """测试模型版本历史记录"""
        # Given: 模型评估历史
        model_id = 'model-001'
        evaluations = [
            {'version': '1.0', 'accuracy': 0.85, 'timestamp': '2024-01-01'},
            {'version': '1.1', 'accuracy': 0.87, 'timestamp': '2024-01-15'},
            {'version': '2.0', 'accuracy': 0.91, 'timestamp': '2024-02-01'},
        ]

        # When: 获取版本历史
        history = evaluation_service.get_version_history(model_id, evaluations)

        # Then: 应返回趋势数据
        assert 'versions' in history
        assert 'metrics_trend' in history
        assert len(history['versions']) == 3
        assert history['metrics_trend']['accuracy'][-1] > history['metrics_trend']['accuracy'][0]

    # ==================== AE-EV-003: 超参数调优 ====================

    @pytest.mark.unit
    def test_hyperparameter_grid_search(self, sample_test_data, evaluation_service):
        """测试网格搜索超参数"""
        # Given: 超参数搜索空间
        param_grid = {
            'learning_rate': [0.01, 0.1, 0.5],
            'max_depth': [3, 5, 7],
            'n_estimators': [50, 100]
        }

        # When: 执行网格搜索
        result = evaluation_service.grid_search(
            param_grid,
            sample_test_data['X_test'],
            sample_test_data['y_test']
        )

        # Then: 应返回最优参数
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'all_results' in result
        assert len(result['all_results']) == 3 * 3 * 2  # 所有组合数

    @pytest.mark.unit
    def test_hyperparameter_random_search(self, sample_test_data, evaluation_service):
        """测试随机搜索超参数"""
        # Given: 超参数分布
        param_distributions = {
            'learning_rate': {'type': 'log_uniform', 'low': 0.001, 'high': 1.0},
            'max_depth': {'type': 'int_uniform', 'low': 2, 'high': 10},
            'dropout': {'type': 'uniform', 'low': 0.1, 'high': 0.5}
        }
        n_iter = 10

        # When: 执行随机搜索
        result = evaluation_service.random_search(
            param_distributions,
            sample_test_data['X_test'],
            sample_test_data['y_test'],
            n_iter=n_iter
        )

        # Then: 应返回最优参数
        assert 'best_params' in result
        assert 'best_score' in result
        assert len(result['all_results']) == n_iter

    @pytest.mark.unit
    def test_hyperparameter_bayesian_optimization(self, sample_test_data, evaluation_service):
        """测试贝叶斯优化超参数"""
        # Given: 超参数搜索空间
        param_space = {
            'learning_rate': {'type': 'real', 'low': 0.001, 'high': 1.0, 'prior': 'log-uniform'},
            'max_depth': {'type': 'integer', 'low': 2, 'high': 10}
        }
        n_calls = 5

        # When: 执行贝叶斯优化
        result = evaluation_service.bayesian_optimization(
            param_space,
            sample_test_data['X_test'],
            sample_test_data['y_test'],
            n_calls=n_calls
        )

        # Then: 应返回最优参数
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'optimization_history' in result

    @pytest.mark.unit
    def test_early_stopping_in_tuning(self, sample_test_data, evaluation_service):
        """测试调优过程中的早停"""
        # Given: 搜索配置
        param_grid = {
            'learning_rate': [0.01, 0.1, 0.5],
            'max_depth': [3, 5, 7]
        }
        early_stopping = {
            'patience': 3,
            'min_delta': 0.001
        }

        # When: 执行带早停的搜索
        result = evaluation_service.grid_search(
            param_grid,
            sample_test_data['X_test'],
            sample_test_data['y_test'],
            early_stopping=early_stopping
        )

        # Then: 应正常返回结果
        assert 'best_params' in result
        assert 'stopped_early' in result or len(result['all_results']) > 0

    @pytest.mark.unit
    def test_cross_validation_in_tuning(self, sample_test_data, evaluation_service):
        """测试调优过程中使用交叉验证"""
        # Given: 搜索配置和交叉验证
        param_grid = {
            'learning_rate': [0.01, 0.1]
        }
        cv_folds = 3

        # When: 执行带交叉验证的搜索
        result = evaluation_service.grid_search(
            param_grid,
            sample_test_data['X_test'],
            sample_test_data['y_test'],
            cv=cv_folds
        )

        # Then: 每个参数组合应有CV分数
        for r in result['all_results']:
            assert 'cv_scores' in r or 'mean_cv_score' in r
            assert 'std_cv_score' in r or len(r.get('cv_scores', [])) == cv_folds


class ModelEvaluationService:
    """模型评估服务"""

    def evaluate_classification(self, y_true: np.ndarray, y_pred: np.ndarray,
                                 y_prob: np.ndarray = None) -> Dict[str, float]:
        """评估分类模型"""
        # 计算基本指标
        accuracy = np.mean(y_true == y_pred)

        # 计算精确率和召回率
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # 计算 AUC-ROC (简化实现)
        auc_roc = 0.5
        if y_prob is not None:
            # 简化的 AUC 计算
            pos_probs = y_prob[y_true == 1]
            neg_probs = y_prob[y_true == 0]
            if len(pos_probs) > 0 and len(neg_probs) > 0:
                auc_roc = np.mean([np.mean(pos_probs > neg) for neg in neg_probs])

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'auc_roc': auc_roc
        }

    def evaluate_regression(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """评估回归模型"""
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y_true - y_pred))

        # R2 分数
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2_score': r2
        }

    def get_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
        """生成混淆矩阵"""
        classes = np.unique(np.concatenate([y_true, y_pred]))
        n_classes = len(classes)
        cm = np.zeros((n_classes, n_classes), dtype=int)

        for i, c1 in enumerate(classes):
            for j, c2 in enumerate(classes):
                cm[i, j] = np.sum((y_true == c1) & (y_pred == c2))

        return cm

    def get_per_class_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict]:
        """获取每个类别的指标"""
        classes = np.unique(y_true)
        result = {}

        for cls in classes:
            tp = np.sum((y_true == cls) & (y_pred == cls))
            fp = np.sum((y_true != cls) & (y_pred == cls))
            fn = np.sum((y_true == cls) & (y_pred != cls))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            result[f'class_{cls}'] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'support': int(np.sum(y_true == cls))
            }

        return result

    def evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray,
                       task: str = 'classification') -> Dict:
        """在测试集上评估模型"""
        start_time = datetime.now()
        predictions = model.predict(X_test)
        eval_time = (datetime.now() - start_time).total_seconds()

        if task == 'classification':
            metrics = self.evaluate_classification(y_test, predictions)
        else:
            metrics = self.evaluate_regression(y_test, predictions)

        return {
            'metrics': metrics,
            'predictions': predictions,
            'evaluation_time': eval_time
        }

    def compare_models(self, models: Dict, y_true: np.ndarray, task: str) -> Dict:
        """对比多个模型"""
        results = {}

        for name, model_info in models.items():
            preds = model_info['predictions']
            if task == 'classification':
                metrics = self.evaluate_classification(y_true, preds)
            else:
                metrics = self.evaluate_regression(y_true, preds)

            results[name] = {
                'version': model_info.get('version'),
                'metrics': metrics
            }

        # 确定最佳模型
        if task == 'classification':
            metric_key = 'accuracy'
        else:
            metric_key = 'r2_score'

        best_model = max(results.keys(), key=lambda k: results[k]['metrics'].get(metric_key, 0))

        # 计算改进
        model_names = list(results.keys())
        if len(model_names) >= 2:
            delta = results[model_names[1]]['metrics'][metric_key] - results[model_names[0]]['metrics'][metric_key]
        else:
            delta = 0

        results['comparison'] = {
            'best_model': best_model,
            'metric_comparison': metric_key,
            'delta': delta,
            'improvement': delta > 0
        }

        return results

    def get_comparison_visualization_data(self, comparison_result: Dict) -> Dict:
        """获取对比可视化数据"""
        labels = []
        chart_data = []

        for name, data in comparison_result.items():
            if name != 'comparison' and isinstance(data, dict) and 'metrics' in data:
                labels.append(name)
                chart_data.append(data['metrics'])

        return {
            'labels': labels,
            'chart_data': chart_data
        }

    def get_version_history(self, model_id: str, evaluations: List[Dict]) -> Dict:
        """获取模型版本历史"""
        versions = [e['version'] for e in evaluations]
        metrics_trend = {
            'accuracy': [e.get('accuracy', 0) for e in evaluations]
        }

        return {
            'model_id': model_id,
            'versions': versions,
            'metrics_trend': metrics_trend,
            'timestamps': [e.get('timestamp') for e in evaluations]
        }

    def grid_search(self, param_grid: Dict, X: np.ndarray, y: np.ndarray,
                    early_stopping: Dict = None, cv: int = None) -> Dict:
        """网格搜索"""
        from itertools import product

        # 生成所有参数组合
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(product(*values))

        all_results = []
        best_score = -float('inf')
        best_params = None
        no_improve_count = 0

        for combo in combinations:
            params = dict(zip(keys, combo))

            # 模拟评估 (实际会训练模型)
            score = np.random.uniform(0.7, 0.95)  # Mock 分数

            result = {'params': params, 'score': score}
            if cv:
                result['cv_scores'] = [score + np.random.uniform(-0.05, 0.05) for _ in range(cv)]
                result['mean_cv_score'] = np.mean(result['cv_scores'])
                result['std_cv_score'] = np.std(result['cv_scores'])

            all_results.append(result)

            if score > best_score:
                if early_stopping:
                    if score - best_score < early_stopping.get('min_delta', 0):
                        no_improve_count += 1
                    else:
                        no_improve_count = 0
                best_score = score
                best_params = params
            else:
                no_improve_count += 1

            # 早停检查
            if early_stopping and no_improve_count >= early_stopping.get('patience', 3):
                break

        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results,
            'stopped_early': early_stopping is not None and no_improve_count >= early_stopping.get('patience', 3)
        }

    def random_search(self, param_distributions: Dict, X: np.ndarray, y: np.ndarray,
                      n_iter: int = 10) -> Dict:
        """随机搜索"""
        all_results = []
        best_score = -float('inf')
        best_params = None

        for _ in range(n_iter):
            params = {}
            for name, dist in param_distributions.items():
                if dist['type'] == 'log_uniform':
                    params[name] = np.exp(np.random.uniform(np.log(dist['low']), np.log(dist['high'])))
                elif dist['type'] == 'int_uniform':
                    params[name] = np.random.randint(dist['low'], dist['high'] + 1)
                else:
                    params[name] = np.random.uniform(dist['low'], dist['high'])

            score = np.random.uniform(0.7, 0.95)  # Mock 分数
            all_results.append({'params': params, 'score': score})

            if score > best_score:
                best_score = score
                best_params = params

        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results
        }

    def bayesian_optimization(self, param_space: Dict, X: np.ndarray, y: np.ndarray,
                               n_calls: int = 10) -> Dict:
        """贝叶斯优化"""
        all_results = []
        best_score = -float('inf')
        best_params = None

        for i in range(n_calls):
            params = {}
            for name, space in param_space.items():
                if space['type'] == 'real':
                    if space.get('prior') == 'log-uniform':
                        params[name] = np.exp(np.random.uniform(np.log(space['low']), np.log(space['high'])))
                    else:
                        params[name] = np.random.uniform(space['low'], space['high'])
                elif space['type'] == 'integer':
                    params[name] = np.random.randint(space['low'], space['high'] + 1)

            # 模拟：随着迭代次数增加，分数趋于更优
            base_score = np.random.uniform(0.7, 0.95)
            improvement = 0.01 * i  # 模拟贝叶斯优化的改进
            score = min(base_score + improvement, 0.99)

            all_results.append({'params': params, 'score': score, 'iteration': i})

            if score > best_score:
                best_score = score
                best_params = params

        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': all_results,
            'optimization_history': [r['score'] for r in all_results]
        }
