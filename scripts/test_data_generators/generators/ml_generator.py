"""
机器学习模型生成器

生成：
- ML模型（7个模型）
- 模型版本（15个版本）
- 模型部署（10个部署）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import BaseGenerator, MLModelTypes, generate_id, random_date
from ..config import GeneratorQuantities


# 模型名称模板
MODEL_NAME_TEMPLATES = {
    MLModelTypes.CLASSIFICATION: [
        "用户流失预测模型", "客户分类模型", "欺诈检测模型",
        "违约预测模型", "垃圾邮件分类模型",
    ],
    MLModelTypes.REGRESSION: [
        "销量预测模型", "价格预测模型", "用户价值预测模型",
        "LTV预测模型", "风险评估模型",
    ],
    MLModelTypes.CLUSTERING: [
        "用户分群模型", "商品聚类模型", "行为模式识别模型",
    ],
    MLModelTypes.RECOMMENDATION: [
        "商品推荐模型", "内容推荐模型", "协同过滤推荐模型",
    ],
    MLModelTypes.NLP: [
        "文本分类模型", "命名实体识别模型", "情感分析模型",
    ],
    MLModelTypes.TIME_SERIES: [
        "时序预测模型", "异常检测模型", "趋势预测模型",
    ],
}


class MLGenerator(BaseGenerator):
    """
    机器学习模型生成器

    生成模型、版本和部署信息
    """

    # 框架列表
    FRAMEWORKS = ["tensorflow", "pytorch", "sklearn", "xgboost", "lightgbm", "catboost"]

    # 部署环境
    DEPLOY_ENVS = ["production", "staging", "development"]

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有ML数据

        Returns:
            包含models, versions, deployments的字典
        """
        self.log("Generating ML models...", "info")

        # 生成模型
        models = self._generate_models()
        self.store_data("models", models)

        # 生成模型版本
        versions = self._generate_versions(models)
        self.store_data("versions", versions)

        # 生成模型部署
        deployments = self._generate_deployments(versions)
        self.store_data("deployments", deployments)

        self.log(
            f"Generated {len(models)} models, {len(versions)} versions, "
            f"{len(deployments)} deployments",
            "success"
        )

        return self.get_all_data()

    def _generate_models(self) -> List[Dict[str, Any]]:
        """生成模型"""
        models = []

        # 模型类型分布
        type_distribution = [
            (MLModelTypes.CLASSIFICATION, 2),
            (MLModelTypes.REGRESSION, 2),
            (MLModelTypes.RECOMMENDATION, 1),
            (MLModelTypes.NLP, 1),
            (MLModelTypes.CLUSTERING, 1),
        ]

        model_index = 0

        for model_type, count in type_distribution:
            name_templates = MODEL_NAME_TEMPLATES.get(model_type, [f"模型_{model_index}"])

            for i in range(count):
                # 获取训练数据集
                datasets = self._get_datasets()
                dataset_id = random.choice(datasets)["dataset_id"] if datasets else None

                model = {
                    "model_id": generate_id("model_", 8),
                    "model_name": name_templates[i % len(name_templates)],
                    "model_type": model_type,
                    "framework": random.choice(self.FRAMEWORKS),
                    "description": f"用于{'预测' if model_type in ['classification', 'regression'] else '处理'}{random.choice(['用户行为', '交易数据', '商品特征', '文本内容'])}的{model_type}模型",
                    "dataset_id": dataset_id,
                    "feature_count": random.randint(10, 200),
                    "target_column": random.choice(["label", "target", "class", "value"]),
                    "hyperparameters": self._generate_hyperparameters(model_type),
                    "metrics": self._generate_metrics(model_type),
                    "created_by": random.choice(["ai-dev-01", "ai-dev-02", "ai-dev-03"]),
                    "status": random.choice(["active", "active", "active", "archived", "developing"]),
                    "created_at": random_date(180),
                    "updated_at": random_date(30),
                }
                models.append(model)
                model_index += 1

        return models

    def _get_datasets(self) -> List[Dict[str, Any]]:
        """获取数据集"""
        # 尝试从依赖获取
        datasets = self.get_dependency("datasets")
        if datasets:
            return datasets

        # 生成模拟数据集
        return [
            {"dataset_id": generate_id("ds_", 8), "dataset_name": f"训练数据集_{i}"}
            for i in range(1, 11)
        ]

    def _generate_hyperparameters(self, model_type: str) -> str:
        """生成超参数JSON"""
        import json

        if model_type == MLModelTypes.CLASSIFICATION:
            params = {
                "learning_rate": round(random.uniform(0.001, 0.1), 4),
                "max_depth": random.randint(3, 10),
                "n_estimators": random.randint(50, 500),
            }
        elif model_type == MLModelTypes.REGRESSION:
            params = {
                "learning_rate": round(random.uniform(0.001, 0.1), 4),
                "max_depth": random.randint(3, 8),
                "min_child_weight": random.randint(1, 10),
            }
        else:
            params = {
                "batch_size": random.choice([16, 32, 64, 128]),
                "epochs": random.randint(10, 100),
            }

        return json.dumps(params, ensure_ascii=False)

    def _generate_metrics(self, model_type: str) -> str:
        """生成评估指标JSON"""
        import json

        if model_type == MLModelTypes.CLASSIFICATION:
            metrics = {
                "accuracy": round(random.uniform(0.75, 0.98), 4),
                "precision": round(random.uniform(0.70, 0.95), 4),
                "recall": round(random.uniform(0.70, 0.95), 4),
                "f1_score": round(random.uniform(0.70, 0.95), 4),
                "auc": round(random.uniform(0.75, 0.98), 4),
            }
        elif model_type == MLModelTypes.REGRESSION:
            metrics = {
                "mse": round(random.uniform(0.01, 0.5), 4),
                "rmse": round(random.uniform(0.1, 0.8), 4),
                "mae": round(random.uniform(0.05, 0.5), 4),
                "r2_score": round(random.uniform(0.7, 0.95), 4),
            }
        elif model_type == MLModelTypes.CLUSTERING:
            metrics = {
                "silhouette_score": round(random.uniform(0.3, 0.8), 4),
                "inertia": random.randint(1000, 50000),
            }
        else:
            metrics = {
                "hit_rate": round(random.uniform(0.6, 0.9), 4),
                "ndcg": round(random.uniform(0.7, 0.95), 4),
            }

        return json.dumps(metrics, ensure_ascii=False)

    def _generate_versions(self, models: List[Dict]) -> List[Dict[str, Any]]:
        """生成模型版本"""
        versions = []

        for model in models:
            version_count = random.randint(2, self.quantities.versions_per_model)

            for i in range(version_count):
                version = {
                    "version_id": generate_id("ver_", 8),
                    "model_id": model["model_id"],
                    "version_number": f"v{1 + i}.{random.randint(0, 10)}.{random.randint(0, 20)}",
                    "description": f"{model['model_name']}的第{i+1}个版本",
                    "artifact_path": f"/models/{model['model_id']}/v{1+i}/model.pkl",
                    "framework": model["framework"],
                    "metrics": model["metrics"],
                    "features": model["feature_count"],
                    "is_production_ready": i == version_count - 1,
                    "training_dataset_id": model["dataset_id"],
                    "training_time_seconds": random.randint(300, 7200),
                    "created_by": model["created_by"],
                    "created_at": random_date(180 - i * 30),
                }
                versions.append(version)

        return versions

    def _generate_deployments(self, versions: List[Dict]) -> List[Dict[str, Any]]:
        """生成模型部署"""
        deployments = []

        # 只选择生产就绪的版本
        prod_versions = [v for v in versions if v.get("is_production_ready")]

        # 如果没有生产就绪的版本，随机选择一些
        if not prod_versions:
            prod_versions = versions[:self.quantities.ml_deployment_count]

        for i, version in enumerate(prod_versions[:self.quantities.ml_deployment_count]):
            env = self.DEPLOY_ENVS[i % len(self.DEPLOY_ENVS)]

            deployment = {
                "deployment_id": generate_id("deploy_", 8),
                "version_id": version["version_id"],
                "model_id": version["model_id"],
                "environment": env,
                "endpoint": f"/api/v1/models/{version['model_id']}/predict",
                "instance_count": random.randint(1, 10),
                "cpu_limit": f"{random.choice([1, 2, 4, 8])} cores",
                "memory_limit": f"{random.choice([2, 4, 8, 16])}Gi",
                "gpu_enabled": random.random() > 0.7,
                "status": random.choice(["running", "running", "running", "stopped", "failed"]),
                "last_scaled_at": random_date(7),
                "created_by": version["created_by"],
                "created_at": version["created_at"] + timedelta(days=random.randint(1, 7)),
                "updated_at": random_date(1),
            }
            deployments.append(deployment)

        return deployments

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving ML models to database...", "info")

        # 保存模型
        models = self.get_data("models")
        if models and self.storage.table_exists("ml_models"):
            self.storage.batch_insert(
                "ml_models",
                ["model_id", "model_name", "model_type", "framework", "description",
                 "dataset_id", "feature_count", "target_column", "hyperparameters",
                 "metrics", "created_by", "status", "created_at", "updated_at"],
                models,
                idempotent=True,
                idempotent_columns=["model_id"]
            )
            self.log(f"Saved {len(models)} models", "success")

        # 保存版本
        versions = self.get_data("versions")
        if versions and self.storage.table_exists("model_versions"):
            self.storage.batch_insert(
                "model_versions",
                ["version_id", "model_id", "version_number", "description", "artifact_path",
                 "framework", "metrics", "features", "is_production_ready",
                 "training_dataset_id", "training_time_seconds", "created_by", "created_at"],
                versions,
                idempotent=True,
                idempotent_columns=["version_id"]
            )
            self.log(f"Saved {len(versions)} versions", "success")

        # 保存部署
        deployments = self.get_data("deployments")
        if deployments and self.storage.table_exists("model_deployments"):
            self.storage.batch_insert(
                "model_deployments",
                ["deployment_id", "version_id", "model_id", "environment", "endpoint",
                 "instance_count", "cpu_limit", "memory_limit", "gpu_enabled",
                 "status", "last_scaled_at", "created_by", "created_at", "updated_at"],
                deployments,
                idempotent=True,
                idempotent_columns=["deployment_id"]
            )
            self.log(f"Saved {len(deployments)} deployments", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up ML data...", "info")

        for table, id_col in [
            ("model_deployments", "deployment_id"),
            ("model_versions", "version_id"),
            ("ml_models", "model_id"),
        ]:
            if self.storage.table_exists(table):
                for prefix in ["deploy_", "ver_", "model_"]:
                    self.storage.cleanup_by_prefix(table, id_col, prefix)


def generate_ml_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成ML数据

    Args:
        config: 生成配置

    Returns:
        ML数据字典
    """
    generator = MLGenerator(config)
    return generator.generate()
