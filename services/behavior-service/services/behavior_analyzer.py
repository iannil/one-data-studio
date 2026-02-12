"""
行为统计指标分析服务

原名: BehaviorAnalyzer

职责: 分析用户行为模式，生成统计指标（活跃度、留存率、漏斗分析等）
区别于 admin-api 的 UserProfileAnalyzer（用户画像特征提取）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models.user_behavior import UserBehavior, UserSession
from models.user_profile import BehaviorMetric

logger = logging.getLogger(__name__)


class BehaviorMetricsAnalyzer:
    """
    行为统计指标分析器

    原名: BehaviorAnalyzer

    职责: 分析用户行为模式，生成统计指标
    提供功能: 活跃度分析、模块使用分析、漏斗分析、留存分析
    """

    def __init__(self):
        pass

    def analyze_user_activity(
        self, db: Session, user_id: str, tenant_id: str, days: int = 30
    ) -> Dict:
        """
        分析用户活跃度

        返回: {
            "total_sessions": 总会话数,
            "total_page_views": 总页面浏览,
            "total_actions": 总操作数,
            "avg_daily_sessions": 平均日会话数,
            "avg_daily_duration": 平均日使用时长(分钟),
            "most_active_hour": 最活跃时段,
            "most_visited_pages": 最常访问页面,
            "activity_trend": 活跃趋势(7天/30天)
        }
        """
        since = datetime.now() - timedelta(days=days)

        # 基础统计
        behaviors = (
            db.query(UserBehavior)
            .filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.user_id == user_id,
                UserBehavior.occurred_at >= since,
            )
            .all()
        )

        sessions = (
            db.query(UserSession)
            .filter(
                UserSession.tenant_id == tenant_id,
                UserSession.user_id == user_id,
                UserSession.start_time >= since,
            )
            .all()
        )

        page_views = [b for b in behaviors if b.behavior_type == "page_view"]
        actions = [
            b
            for b in behaviors
            if b.behavior_type in ["click", "submit", "form_submit"]
        ]

        # 计算统计指标
        total_duration = sum([s.duration or 0 for s in sessions])
        avg_daily_duration = total_duration / days if days > 0 else 0

        # 最活跃时段
        hour_counts = {}
        for b in behaviors:
            hour = b.occurred_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        most_active_hour = (
            max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        )

        # 最常访问页面
        page_counts = {}
        for pv in page_views:
            url = pv.page_url or "unknown"
            page_counts[url] = page_counts.get(url, 0) + 1
        most_visited_pages = sorted(
            page_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # 活跃趋势（按天统计）
        daily_counts = {}
        for b in behaviors:
            date = b.occurred_at.date()
            daily_counts[date] = daily_counts.get(date, 0) + 1

        activity_trend = [
            {"date": str(date), "count": count}
            for date, count in sorted(daily_counts.items())
        ]

        return {
            "total_sessions": len(sessions),
            "total_page_views": len(page_views),
            "total_actions": len(actions),
            "avg_daily_sessions": len(sessions) / days if days > 0 else 0,
            "avg_daily_duration": round(avg_daily_duration / 60, 2),  # 转换为分钟
            "most_active_hour": most_active_hour,
            "most_visited_pages": [
                {"url": url, "count": count} for url, count in most_visited_pages
            ],
            "activity_trend": activity_trend,
        }

    def analyze_module_usage(
        self, db: Session, tenant_id: str, days: int = 30
    ) -> List[Dict]:
        """
        分析功能模块使用情况

        返回: [
            {
                "module": "模块名",
                "page_views": 浏览量,
                "unique_users": 唯一用户数,
                "avg_duration": 平均停留时长,
                "total_actions": 操作数
            }
        ]
        """
        since = datetime.now() - timedelta(days=days)

        behaviors = (
            db.query(UserBehavior)
            .filter(
                UserBehavior.tenant_id == tenant_id, UserBehavior.occurred_at >= since
            )
            .all()
        )

        # 按模块分组统计
        module_stats = {}
        for b in behaviors:
            module = b.module or "unknown"
            if module not in module_stats:
                module_stats[module] = {
                    "module": module,
                    "page_views": 0,
                    "users": set(),
                    "durations": [],
                    "actions": 0,
                }

            if b.behavior_type == "page_view":
                module_stats[module]["page_views"] += 1
                module_stats[module]["users"].add(b.user_id)
            if b.duration:
                module_stats[module]["durations"].append(b.duration)
            if b.behavior_type in ["click", "submit", "form_submit"]:
                module_stats[module]["actions"] += 1

        # 转换为结果格式
        result = []
        for stats in module_stats.values():
            avg_duration = (
                sum(stats["durations"]) / len(stats["durations"])
                if stats["durations"]
                else 0
            )

            result.append(
                {
                    "module": stats["module"],
                    "page_views": stats["page_views"],
                    "unique_users": len(stats["users"]),
                    "avg_duration": round(avg_duration, 2),
                    "total_actions": stats["actions"],
                }
            )

        return sorted(result, key=lambda x: x["page_views"], reverse=True)

    def get_active_users(
        self, db: Session, tenant_id: str, days: int = 7
    ) -> List[Dict]:
        """
        获取活跃用户列表

        返回: [
            {
                "user_id": "用户ID",
                "session_count": 会话数,
                "page_views": 页面浏览数,
                "last_active": 最后活跃时间
            }
        ]
        """
        since = datetime.now() - timedelta(days=days)

        # 查询活跃用户
        active_users = (
            db.query(
                UserBehavior.user_id,
                func.count(func.distinct(UserBehavior.session_id)).label("sessions"),
                func.count(func.distinct(UserBehavior.page_url)).label("pages"),
                func.max(UserBehavior.occurred_at).label("last_active"),
            )
            .filter(
                UserBehavior.tenant_id == tenant_id, UserBehavior.occurred_at >= since
            )
            .group_by(UserBehavior.user_id)
            .all()
        )

        return [
            {
                "user_id": row.user_id,
                "session_count": row.sessions,
                "page_views": row.pages,
                "last_active": row.last_active.isoformat() if row.last_active else None,
            }
            for row in active_users
        ]

    def get_hourly_activity(
        self, db: Session, tenant_id: str, days: int = 7
    ) -> List[Dict]:
        """
        获取按小时统计的活动量

        返回: [
            {"hour": 0, "count": 100, "users": 50},
            {"hour": 1, "count": 80, "users": 40},
            ...
        ]
        """
        since = datetime.now() - timedelta(days=days)

        hourly_data = (
            db.query(
                func.hour(UserBehavior.occurred_at).label("hour"),
                func.count(UserBehavior.id).label("count"),
                func.count(func.distinct(UserBehavior.user_id)).label("users"),
            )
            .filter(
                UserBehavior.tenant_id == tenant_id, UserBehavior.occurred_at >= since
            )
            .group_by(func.hour(UserBehavior.occurred_at))
            .all()
        )

        return [
            {
                "hour": row.hour,
                "count": row.count,
                "users": row.users,
            }
            for row in hourly_data
        ]

    def get_behavior_funnel(
        self, db: Session, tenant_id: str, steps: List[str], days: int = 30
    ) -> Dict:
        """
        分析行为漏斗

        steps: ["page_view", "click", "submit"] 等

        返回: {
            "steps": ["步骤1", "步骤2", ...],
            "counts": [1000, 500, 200],
            "conversion_rates": [100%, 50%, 20%]
        }
        """
        since = datetime.now() - timedelta(days=days)

        counts = []
        for step in steps:
            count = (
                db.query(func.count(func.distinct(UserBehavior.user_id)))
                .filter(
                    UserBehavior.tenant_id == tenant_id,
                    UserBehavior.behavior_type == step,
                    UserBehavior.occurred_at >= since,
                )
                .scalar()
            )
            counts.append(count or 0)

        # 计算转化率
        conversion_rates = []
        if counts and counts[0] > 0:
            base = counts[0]
            for count in counts:
                rate = (count / base) * 100 if base > 0 else 0
                conversion_rates.append(round(rate, 2))

        return {
            "steps": steps,
            "counts": counts,
            "conversion_rates": conversion_rates,
        }

    def calculate_retention(
        self, db: Session, tenant_id: str, cohort_days: int = 7
    ) -> List[Dict]:
        """
        计算用户留存率

        返回: [
            {"day": 0, "retention_rate": 100%},
            {"day": 1, "retention_rate": 60%},
            ...
        ]
        """
        # 获取cohort用户（在cohort_days天内首次活跃的用户）
        cohort_start = datetime.now() - timedelta(days=cohort_days * 2)
        cohort_end = datetime.now() - timedelta(days=cohort_days)

        # 找到cohort用户
        cohort_users = (
            db.query(
                UserBehavior.user_id,
                func.min(UserBehavior.occurred_at).label("first_active"),
            )
            .filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.occurred_at >= cohort_start,
                UserBehavior.occurred_at < cohort_end,
            )
            .group_by(UserBehavior.user_id)
            .all()
        )

        if not cohort_users:
            return []

        cohort_user_ids = [row.user_id for row in cohort_users]

        # 计算每天的留存率
        retention_data = []
        cohort_size = len(cohort_user_ids)

        for day in range(min(cohort_days, 30)):
            day_start = cohort_end + timedelta(days=day)
            day_end = day_start + timedelta(days=1)

            retained = (
                db.query(func.count(func.distinct(UserBehavior.user_id)))
                .filter(
                    UserBehavior.tenant_id == tenant_id,
                    UserBehavior.user_id.in_(cohort_user_ids),
                    UserBehavior.occurred_at >= day_start,
                    UserBehavior.occurred_at < day_end,
                )
                .scalar()
            )

            retention_rate = (retained / cohort_size * 100) if cohort_size > 0 else 0

            retention_data.append(
                {
                    "day": day,
                    "retained_users": retained or 0,
                    "retention_rate": round(retention_rate, 2),
                }
            )

        return retention_data

    def generate_daily_metrics(
        self, db: Session, tenant_id: str, date: datetime = None
    ) -> List[BehaviorMetric]:
        """
        生成每日指标

        返回: 创建的指标列表
        """
        if date is None:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        next_day = date + timedelta(days=1)

        created_metrics = []

        # 总体活跃度指标
        total_behaviors = (
            db.query(func.count(UserBehavior.id))
            .filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.occurred_at >= date,
                UserBehavior.occurred_at < next_day,
            )
            .scalar()
        )

        unique_users = (
            db.query(func.count(func.distinct(UserBehavior.user_id)))
            .filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.occurred_at >= date,
                UserBehavior.occurred_at < next_day,
            )
            .scalar()
        )

        # 总会话数
        total_sessions = (
            db.query(func.count(UserSession.id))
            .filter(
                UserSession.tenant_id == tenant_id,
                UserSession.start_time >= date,
                UserSession.start_time < next_day,
            )
            .scalar()
        )

        # 创建总体指标
        overall_metric = BehaviorMetric(
            id=f"overall_{tenant_id}_{date.strftime('%Y%m%d')}",
            tenant_id=tenant_id,
            metric_type="overall",
            metric_name="daily_activity",
            date=date,
            period="daily",
            count=total_behaviors or 0,
            unique_users=unique_users or 0,
        )
        db.add(overall_metric)
        created_metrics.append(overall_metric)

        # 按模块统计
        module_stats = (
            db.query(
                UserBehavior.module,
                func.count(UserBehavior.id).label("count"),
                func.count(func.distinct(UserBehavior.user_id)).label("users"),
            )
            .filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.occurred_at >= date,
                UserBehavior.occurred_at < next_day,
            )
            .group_by(UserBehavior.module)
            .all()
        )

        for stat in module_stats:
            module_metric = BehaviorMetric(
                id=f"module_{tenant_id}_{stat.module or 'unknown'}_{date.strftime('%Y%m%d')}",
                tenant_id=tenant_id,
                metric_type="module",
                metric_name=stat.module or "unknown",
                dimension="module",
                date=date,
                period="daily",
                count=stat.count,
                unique_users=stat.users,
            )
            db.add(module_metric)
            created_metrics.append(module_metric)

        db.commit()
        return created_metrics


# 向后兼容别名
BehaviorAnalyzer = BehaviorMetricsAnalyzer
