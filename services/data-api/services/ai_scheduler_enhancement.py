"""
AI 智能调度增强服务
基于机器学习的任务优先级优化、执行时间预测和资源分配
"""

import logging
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class BusinessImpact(str, Enum):
    """业务影响等级"""
    CRITICAL = "critical"      # 关键业务，影响核心收入
    HIGH = "high"              # 高影响，影响重要业务流程
    MEDIUM = "medium"          # 中等影响，影响一般业务
    LOW = "low"                # 低影响，非关键业务


class DataFreshness(str, Enum):
    """数据新鲜度要求"""
    REALTIME = "realtime"      # 实时（分钟级）
    NEAR_REALTIME = "near_realtime"  # 近实时（15分钟级）
    HOURLY = "hourly"          # 小时级
    DAILY = "daily"            # 日级
    WEEKLY = "weekly"          # 周级


@dataclass
class TaskFeatures:
    """任务特征（用于 ML 模型）"""
    task_type: str
    resource_cpu: float
    resource_memory: int
    resource_gpu: int
    estimated_duration_ms: int
    dependency_count: int
    deadline_urgency: float  # 0-1，越接近deadline越接近1
    business_impact: str
    data_freshness: str
    historical_success_rate: float
    avg_execution_time_ms: int
    data_volume_mb: float = 0
    table_count: int = 1
    transformation_complexity: int = 1  # 1-5，转换复杂度


@dataclass
class PriorityScore:
    """优先级评分结果"""
    task_id: str
    base_score: float
    business_impact_score: float
    urgency_score: float
    resource_efficiency_score: float
    historical_performance_score: float
    final_score: float
    recommended_priority: str
    confidence: float  # 0-1，预测置信度
    factors: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "base_score": self.base_score,
            "business_impact_score": self.business_impact_score,
            "urgency_score": self.urgency_score,
            "resource_efficiency_score": self.resource_efficiency_score,
            "historical_performance_score": self.historical_performance_score,
            "final_score": self.final_score,
            "recommended_priority": self.recommended_priority,
            "confidence": self.confidence,
            "factors": self.factors,
        }


@dataclass
class ExecutionTimePrediction:
    """执行时间预测结果"""
    task_id: str
    predicted_duration_ms: int
    confidence_interval_ms: Tuple[int, int]  # (lower, upper)
    prediction_confidence: float
    historical_avg_ms: int
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "predicted_duration_ms": self.predicted_duration_ms,
            "confidence_interval_ms": {
                "lower": self.confidence_interval_ms[0],
                "upper": self.confidence_interval_ms[1],
            },
            "prediction_confidence": self.prediction_confidence,
            "historical_avg_ms": self.historical_avg_ms,
            "factors": self.factors,
        }


@dataclass
class ResourceAllocation:
    """资源分配建议"""
    task_id: str
    recommended_cpu: float
    recommended_memory_mb: int
    recommended_gpu: int
    optimization_reason: str
    expected_improvement: str
    cost_saving_estimate: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "recommended_cpu": self.recommended_cpu,
            "recommended_memory_mb": self.recommended_memory_mb,
            "recommended_gpu": self.recommended_gpu,
            "optimization_reason": self.optimization_reason,
            "expected_improvement": self.expected_improvement,
            "cost_saving_estimate": self.cost_saving_estimate,
        }


class AISchedulerEnhancer:
    """AI 调度增强器"""

    def __init__(self):
        # 业务影响权重
        self._business_impact_weights = {
            BusinessImpact.CRITICAL: 1000,
            BusinessImpact.HIGH: 750,
            BusinessImpact.MEDIUM: 500,
            BusinessImpact.LOW: 250,
        }

        # 新鲜度权重
        self._freshness_weights = {
            DataFreshness.REALTIME: 500,
            DataFreshness.NEAR_REALTIME: 400,
            DataFreshness.HOURLY: 300,
            DataFreshness.DAILY: 200,
            DataFreshness.WEEKLY: 100,
        }

        # 任务类型基础耗时（毫秒）
        self._task_type_base_duration = {
            "etl": 300000,      # 5分钟
            "ml": 3600000,      # 1小时
            "data_quality": 120000,  # 2分钟
            "report": 60000,    # 1分钟
            "notification": 10000,  # 10秒
            "backup": 1800000,  # 30分钟
        }

    def calculate_priority_score(
        self,
        task: Any,
        current_time: datetime = None,
    ) -> PriorityScore:
        """
        计算任务的 AI 优先级分数

        考虑因素：
        1. 业务影响等级
        2. 截止时间紧迫度
        3. 资源效率
        4. 历史表现
        5. 数据新鲜度要求
        """
        if current_time is None:
            current_time = datetime.now()

        features = self._extract_task_features(task)

        # 1. 业务影响分数
        business_impact = BusinessImpact(features.business_impact)
        business_impact_score = self._business_impact_weights.get(business_impact, 500)

        # 2. 新鲜度分数
        freshness = DataFreshness(features.data_freshness)
        freshness_score = self._freshness_weights.get(freshness, 200)

        # 3. 截止时间紧迫度分数
        urgency_score = 0
        if task.deadline:
            time_to_deadline = (task.deadline - current_time).total_seconds()
            if time_to_deadline < 3600:  # 1小时内
                urgency_score = 500
            elif time_to_deadline < 86400:  # 24小时内
                urgency_score = 300
            elif time_to_deadline < 604800:  # 7天内
                urgency_score = 100

        # 4. 等待时长分数
        wait_hours = (current_time - task.created_at).total_seconds() / 3600
        wait_score = min(wait_hours * 10, 100)  # 最多加100分

        # 5. 资源效率分数（资源占用越少越好）
        resource_score = max(0, 200 - features.resource_cpu * 20 - features.resource_memory_mb / 512)

        # 6. 历史表现分数
        performance_score = features.historical_success_rate * 100

        # 7. 依赖复杂度（依赖越少越好）
        dependency_score = max(0, 50 - len(task.dependencies) * 10)

        # 计算总分
        base_score = (
            business_impact_score +
            freshness_score +
            wait_score
        )

        final_score = (
            base_score +
            urgency_score +
            resource_score +
            performance_score +
            dependency_score
        )

        # 确定推荐优先级
        if final_score >= 1500:
            recommended_priority = "critical"
        elif final_score >= 1000:
            recommended_priority = "high"
        elif final_score >= 500:
            recommended_priority = "normal"
        else:
            recommended_priority = "low"

        # 计算置信度（基于历史数据量）
        confidence = min(1.0, features.historical_success_rate * 0.8 + 0.2)

        return PriorityScore(
            task_id=task.task_id,
            base_score=base_score,
            business_impact_score=business_impact_score,
            urgency_score=urgency_score,
            resource_efficiency_score=resource_score,
            historical_performance_score=performance_score,
            final_score=final_score,
            recommended_priority=recommended_priority,
            confidence=confidence,
            factors={
                "business_impact": business_impact.value,
                "freshness": freshness.value,
                "wait_hours": wait_hours,
                "deadline_hours": (task.deadline - current_time).total_seconds() / 3600 if task.deadline else None,
            },
        )

    def predict_execution_time(
        self,
        task: Any,
        historical_runs: List[Dict] = None,
    ) -> ExecutionTimePrediction:
        """
        预测任务执行时间

        基于因素：
        1. 任务类型
        2. 资源配置
        3. 数据量
        4. 历史执行记录
        """
        features = self._extract_task_features(task)

        # 基础预测（基于任务类型）
        base_duration = self._task_type_base_duration.get(
            features.task_type,
            task.estimated_duration_ms,
        )

        # 数据量调整因子
        if features.data_volume_mb > 0:
            # 每100MB增加5%时间
            data_factor = 1 + (features.data_volume_mb / 100) * 0.05
        else:
            data_factor = 1

        # 资源调整因子
        # 更多资源 = 更快执行（但有边际递减）
        if features.resource_cpu > 0:
            cpu_factor = 1 / (features.resource_cpu ** 0.5)  # 平方根缩放
        else:
            cpu_factor = 1

        # GPU 加速
        if features.resource_gpu > 0:
            gpu_factor = 0.5  # GPU 可加速50%
        else:
            gpu_factor = 1

        # 历史平均
        historical_avg = features.avg_execution_time_ms if features.avg_execution_time_ms > 0 else base_duration

        # 组合预测
        predicted_duration = base_duration * data_factor * cpu_factor * gpu_factor

        # 如果有历史数据，进行加权平均
        if historical_runs and len(historical_runs) > 0:
            recent_times = [r.get("duration_ms", base_duration) for r in historical_runs[-10:]]
            historical_avg = statistics.mean(recent_times)

            # 历史数据和模型预测的加权
            predicted_duration = historical_avg * 0.6 + predicted_duration * 0.4

        # 计算置信区间（基于历史方差）
        confidence_margin = predicted_duration * 0.3  # 30% 误差范围
        lower_bound = int(predicted_duration - confidence_margin)
        upper_bound = int(predicted_duration + confidence_margin)

        # 置信度
        if historical_runs and len(historical_runs) >= 5:
            prediction_confidence = 0.8
        elif historical_runs:
            prediction_confidence = 0.6
        else:
            prediction_confidence = 0.4

        return ExecutionTimePrediction(
            task_id=task.task_id,
            predicted_duration_ms=int(predicted_duration),
            confidence_interval_ms=(lower_bound, upper_bound),
            prediction_confidence=prediction_confidence,
            historical_avg_ms=int(historical_avg),
            factors={
                "base_duration_ms": base_duration,
                "data_factor": data_factor,
                "cpu_factor": cpu_factor,
                "gpu_factor": gpu_factor,
            },
        )

    def recommend_resource_allocation(
        self,
        task: Any,
        available_resources: Dict[str, Any],
    ) -> ResourceAllocation:
        """
        推荐最优资源分配

        考虑：
        1. 任务类型
        2. 数据量
        3. 成本效益
        4. 可用资源
        """
        features = self._extract_task_features(task)

        # 基础推荐
        recommended_cpu = features.resource_cpu
        recommended_memory = features.resource_memory_mb
        recommended_gpu = features.resource_gpu

        optimization_reason = "保持当前配置"
        expected_improvement = "无变化"

        # ML 任务优化
        if features.task_type == "ml":
            # ML 任务可以从 GPU 受益
            if available_resources.get("gpu_count", 0) > 0 and recommended_gpu == 0:
                recommended_gpu = 1
                optimization_reason = "启用 GPU 加速可提升 ML 任务性能 2-4 倍"
                expected_improvement = "执行时间减少 50-75%"

            # ML 任务需要更多内存
            recommended_memory = max(recommended_memory, 8192)

        # 大数据量 ETL 优化
        elif features.task_type == "etl" and features.data_volume_mb > 1000:
            # 并行处理
            recommended_cpu = min(recommended_cpu * 2, available_resources.get("cpu_cores", 4))
            optimization_reason = "大数据量任务建议增加 CPU 并行"
            expected_improvement = "执行时间减少 30-50%"

        # 资源节约机会
        elif features.task_type in ["notification", "report"]:
            # 轻量级任务可以降低资源
            if recommended_cpu > 1:
                recommended_cpu = 1
                optimization_reason = "轻量级任务降低资源分配"
                expected_improvement = "资源成本降低 50%+"

        return ResourceAllocation(
            task_id=task.task_id,
            recommended_cpu=recommended_cpu,
            recommended_memory_mb=recommended_memory,
            recommended_gpu=recommended_gpu,
            optimization_reason=optimization_reason,
            expected_improvement=expected_improvement,
        )

    def optimize_schedule_order(
        self,
        tasks: List[Any],
        resource_constraints: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        优化任务调度顺序

        使用拓扑排序 + 优先级队列
        """
        from heapq import heappush, heappop

        if resource_constraints is None:
            resource_constraints = {
                "cpu_cores": 16.0,
                "memory_mb": 32768,
                "gpu_count": 4,
            }

        # 构建依赖图
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for task in tasks:
            for dep in task.dependencies:
                dep_id = dep.task_id if hasattr(dep, 'task_id') else dep.get("task_id")
                if dep_id in {t.task_id for t in tasks}:
                    graph[dep_id].append(task.task_id)
                    in_degree[task.task_id] += 1

        # 计算优先级分数
        priority_scores = {}
        for task in tasks:
            score = self.calculate_priority_score(task)
            priority_scores[task.task_id] = score.final_score

        # 优先队列（负数用于大顶堆）
        queue = []
        for task in tasks:
            if in_degree.get(task.task_id, 0) == 0:
                heappush(queue, (-priority_scores[task.task_id], task.task_id))

        # 拓扑排序
        optimized_order = []
        temp_resources = resource_constraints.copy()
        running_tasks = []

        while queue or running_tasks:
            # 启动新任务
            while queue:
                if not running_tasks:
                    neg_score, task_id = heappop(queue)
                    task = next(t for t in tasks if t.task_id == task_id)

                    # 检查资源
                    if (
                        task.resource_requirement.cpu_cores <= temp_resources.get("cpu_cores", 0) and
                        task.resource_requirement.memory_mb <= temp_resources.get("memory_mb", 0)
                    ):
                        optimized_order.append(task_id)
                        temp_resources["cpu_cores"] -= task.resource_requirement.cpu_cores
                        temp_resources["memory_mb"] -= task.resource_requirement.memory_mb

                        # 更新依赖
                        for dependent_id in graph[task_id]:
                            in_degree[dependent_id] -= 1
                            if in_degree[dependent_id] == 0:
                                heappush(queue, (-priority_scores[dependent_id], dependent_id))
                    else:
                        break
                else:
                    break

            # 模拟任务完成（简化）
            if running_tasks:
                # 移除最早完成的任务
                completed = running_tasks.pop(0)
                temp_resources["cpu_cores"] += completed.resource_requirement.cpu_cores
                temp_resources["memory_mb"] += completed.resource_requirement.memory_mb

        return {
            "optimized_order": optimized_order,
            "priority_scores": priority_scores,
            "total_tasks": len(optimized_order),
        }

    def _extract_task_features(self, task: Any) -> TaskFeatures:
        """提取任务特征"""
        # 计算截止时间紧迫度
        deadline_urgency = 0.0
        if hasattr(task, 'deadline') and task.deadline:
            time_to_deadline = (task.deadline - datetime.now()).total_seconds()
            deadline_urgency = max(0, 1 - time_to_deadline / 86400)  # 1天外为0

        # 获取元数据中的业务影响和新鲜度
        business_impact = "medium"
        data_freshness = "daily"
        if hasattr(task, 'metadata'):
            business_impact = task.metadata.get("business_impact", "medium")
            data_freshness = task.metadata.get("data_freshness", "daily")

        return TaskFeatures(
            task_type=getattr(task, 'task_type', 'etl'),
            resource_cpu=getattr(task, 'resource_requirement', type('', (), {'cpu_cores': 1})).cpu_cores,
            resource_memory_mb=getattr(task, 'resource_requirement', type('', (), {'memory_mb': 512})).memory_mb,
            resource_gpu=getattr(task, 'resource_requirement', type('', (), {'gpu_count': 0})).gpu_count,
            estimated_duration_ms=getattr(task, 'estimated_duration_ms', 60000),
            dependency_count=len(getattr(task, 'dependencies', [])),
            deadline_urgency=deadline_urgency,
            business_impact=business_impact,
            data_freshness=data_freshness,
            historical_success_rate=getattr(task, 'metrics', type('', (), {'success_rate': 1.0})).success_rate,
            avg_execution_time_ms=getattr(task, 'metrics', type('', (), {'avg_execution_time_ms': 0})).avg_execution_time_ms,
        )


# 全局服务实例
_ai_scheduler_enhancer: Optional[AISchedulerEnhancer] = None


def get_ai_scheduler_enhancer() -> AISchedulerEnhancer:
    """获取 AI 调度增强器实例"""
    global _ai_scheduler_enhancer
    if _ai_scheduler_enhancer is None:
        _ai_scheduler_enhancer = AISchedulerEnhancer()
    return _ai_scheduler_enhancer
