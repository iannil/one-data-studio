"""
统一门户服务
聚合各系统数据，提供统一的工作台入口
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DashboardWidget:
    """仪表盘小组件"""

    def __init__(
        self,
        widget_id: str,
        widget_type: str,
        title: str,
        icon: str,
        size: str,  # small, medium, large, full
        position: Dict = None,
        config: Dict = None,
        data_source: str = None,
    ):
        self.widget_id = widget_id
        self.widget_type = widget_type  # statistic, chart, list, alert, task
        self.title = title
        self.icon = icon
        self.size = size
        self.position = position or {"x": 0, "y": 0, "w": 1, "h": 1}
        self.config = config or {}
        self.data_source = data_source
        self.enabled = True

    def to_dict(self) -> Dict:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "icon": self.icon,
            "size": self.size,
            "position": self.position,
            "config": self.config,
            "data_source": self.data_source,
            "enabled": self.enabled,
        }


class PortalNotification:
    """门户通知"""

    def __init__(
        self,
        notification_id: str,
        type: str,  # info, warning, error, success
        title: str,
        content: str,
        source: str,
        action_url: Optional[str] = None,
        priority: str = "normal",  # low, normal, high, urgent
        expires_at: Optional[datetime] = None,
        created_at: datetime = None,
    ):
        self.notification_id = notification_id
        self.type = type
        self.title = title
        self.content = content
        self.source = source
        self.action_url = action_url
        self.priority = priority
        self.expires_at = expires_at
        self.created_at = created_at or datetime.now()
        self.read = False

    def to_dict(self) -> Dict:
        return {
            "notification_id": self.notification_id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "action_url": self.action_url,
            "priority": self.priority,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
        }


class QuickLink:
    """快捷入口"""

    def __init__(
        self,
        link_id: str,
        title: str,
        description: str,
        url: str,
        icon: str,
        category: str,
        badge_count: int = 0,
        new_window: bool = False,
    ):
        self.link_id = link_id
        self.title = title
        self.description = description
        self.url = url
        self.icon = icon
        self.category = category
        self.badge_count = badge_count
        self.new_window = new_window

    def to_dict(self) -> Dict:
        return {
            "link_id": self.link_id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "icon": self.icon,
            "category": self.category,
            "badge_count": self.badge_count,
            "new_window": self.new_window,
        }


class TodoItem:
    """待办事项"""

    def __init__(
        self,
        todo_id: str,
        title: str,
        description: str,
        source: str,
        priority: str,
        due_date: Optional[datetime] = None,
        action_url: Optional[str] = None,
        created_at: datetime = None,
    ):
        self.todo_id = todo_id
        self.title = title
        self.description = description
        self.source = source
        self.priority = priority
        self.due_date = due_date
        self.action_url = action_url
        self.created_at = created_at or datetime.now()
        self.completed = False
        self.completed_at = None

    def to_dict(self) -> Dict:
        return {
            "todo_id": self.todo_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "action_url": self.action_url,
            "created_at": self.created_at.isoformat(),
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class PortalService:
    """统一门户服务"""

    def __init__(self):
        # 默认仪表盘配置
        self._default_widgets = self._init_default_widgets()
        self._default_links = self._init_default_links()

    def _init_default_widgets(self) -> List[DashboardWidget]:
        """初始化默认仪表盘小组件"""
        return [
            DashboardWidget(
                widget_id="stat_total_assets",
                widget_type="statistic",
                title="数据资产总数",
                icon="📊",
                size="small",
                position={"x": 0, "y": 0, "w": 1, "h": 1},
                config={"prefix": "共", "suffix": "个"},
                data_source="data.assets",
            ),
            DashboardWidget(
                widget_id="stat_quality_score",
                widget_type="statistic",
                title="数据质量评分",
                icon="✅",
                size="small",
                position={"x": 1, "y": 0, "w": 1, "h": 1},
                config={"suffix": "分"},
                data_source="quality.score",
            ),
            DashboardWidget(
                widget_id="stat_today_tasks",
                widget_type="statistic",
                title="今日任务",
                icon="📋",
                size="small",
                position={"x": 2, "y": 0, "w": 1, "h": 1},
                config={"prefix": "完成", "suffix": "/ 12"},
                data_source="tasks.today",
            ),
            DashboardWidget(
                widget_id="stat_alerts",
                widget_type="statistic",
                title="待处理告警",
                icon="🔔",
                size="small",
                position={"x": 3, "y": 0, "w": 1, "h": 1},
                config={},
                data_source="alerts.pending",
            ),
            DashboardWidget(
                widget_id="chart_data_trend",
                widget_type="chart",
                title="数据访问趋势",
                icon="📈",
                size="large",
                position={"x": 0, "y": 1, "w": 2, "h": 2},
                config={"chart_type": "line", "period": "7d"},
                data_source="metrics.access_trend",
            ),
            DashboardWidget(
                widget_id="chart_data_distribution",
                widget_type="chart",
                title="数据分布",
                icon="🥧",
                size="medium",
                position={"x": 2, "y": 1, "w": 2, "h": 1},
                config={"chart_type": "pie"},
                data_source="metrics.data_distribution",
            ),
            DashboardWidget(
                widget_id="list_recent_activities",
                widget_type="list",
                title="最近活动",
                icon="🕐",
                size="medium",
                position={"x": 2, "y": 2, "w": 2, "h": 1},
                config={"limit": 10},
                data_source="activities.recent",
            ),
            DashboardWidget(
                widget_id="list_quality_issues",
                widget_type="list",
                title="数据质量问题",
                icon="⚠️",
                size="medium",
                position={"x": 0, "y": 3, "w": 2, "h": 1},
                config={"limit": 5},
                data_source="quality.issues",
            ),
            DashboardWidget(
                widget_id="list_pending_approvals",
                widget_type="list",
                title="待审批",
                icon="📝",
                size="medium",
                position={"x": 2, "y": 3, "w": 2, "h": 1},
                config={"limit": 5},
                data_source="approvals.pending",
            ),
        ]

    def _init_default_links(self) -> List[QuickLink]:
        """初始化默认快捷入口"""
        return [
            QuickLink(
                link_id="link_assets",
                title="数据资产",
                description="查看和管理数据资产",
                url="/data/assets",
                icon="📊",
                category="data",
            ),
            QuickLink(
                link_id="link_metadata",
                title="元数据管理",
                description="查看元数据图谱",
                url="/metadata/graph",
                icon="🔗",
                category="metadata",
            ),
            QuickLink(
                link_id="link_quality",
                title="数据质量",
                description="数据质量规则配置",
                url="/quality/rules",
                icon="✅",
                category="quality",
            ),
            QuickLink(
                link_id="link_workflows",
                title="工作流编排",
                description="Bisheng 应用编排",
                url="/agent/workflows",
                icon="⚙️",
                category="agent",
            ),
            QuickLink(
                link_id="link_models",
                title="模型服务",
                description="Cube Studio 模型管理",
                url="/cube/models",
                icon="🤖",
                category="cube",
            ),
            QuickLink(
                link_id="link_notebooks",
                title="在线开发",
                description="JupyterLab 笔记本",
                url="/cube/notebooks",
                icon="📓",
                category="cube",
            ),
            QuickLink(
                link_id="link_chatbi",
                title="智能分析",
                description="ChatBI 自然语言查询",
                url="/chatbi",
                icon="💬",
                category="chatbi",
            ),
            QuickLink(
                link_id="link_settings",
                title="系统设置",
                description="系统配置管理",
                url="/admin/settings",
                icon="⚙️",
                category="admin",
            ),
        ]

    # ==================== 仪表盘数据 ====================

    def get_dashboard_data(
        self,
        db: Session,
        user_id: str,
        tenant_id: str = "default",
    ) -> Dict:
        """
        获取仪表盘数据

        汇总来自各系统的数据：
        - Alldata: 数据资产、元数据、质量规则
        - Bisheng: 工作流、应用
        - Cube: 模型、任务、Notebook
        - 通用: 告警、通知
        """
        # 这里简化处理，实际应该调用各系统的 API

        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "widgets": self._get_widgets_data(db, tenant_id),
            "widgets_data": self._get_widgets_data_values(db, tenant_id),
            "last_updated": datetime.now().isoformat(),
        }

    def _get_widgets_data(
        self,
        db: Session,
        tenant_id: str,
    ) -> List[Dict]:
        """获取小组件配置"""
        return [w.to_dict() for w in self._default_widgets if w.enabled]

    def _get_widgets_data_values(
        self,
        db: Session,
        tenant_id: str,
    ) -> Dict:
        """获取小组件数据值"""
        # 模拟数据
        return {
            "stat_total_assets": {
                "value": 1247,
                "trend": 5.2,  # 同比增长
                "trend_direction": "up",
            },
            "stat_quality_score": {
                "value": 87.5,
                "trend": 2.1,
                "trend_direction": "up",
            },
            "stat_today_tasks": {
                "value": 8,
                "total": 12,
                "trend": "up",
            },
            "stat_alerts": {
                "value": 3,
                "critical": 1,
                "warning": 2,
            },
            "chart_data_trend": {
                "labels": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                "series": [
                    {
                        "name": "API 调用",
                        "data": [1200, 1800, 1500, 2100, 1900, 2400, 2200],
                    },
                    {
                        "name": "数据查询",
                        "data": [800, 1200, 1100, 1500, 1300, 900, 700],
                    },
                ],
            },
            "chart_data_distribution": {
                "labels": ["结构化数据", "非结构化数据", "API 数据", "文件数据"],
                "series": [
                    { "name": "数据量", "data": [45, 25, 20, 10] },
                ],
            },
            "list_recent_activities": [
                {
                    "id": "act_001",
                    "title": "数据服务「用户画像」已发布",
                    "time": "5 分钟前",
                    "source": "data",
                    "type": "success",
                    "icon": "✅",
                },
                {
                    "id": "act_002",
                    "title": "数据质量检测发现 3 个问题",
                    "time": "15 分钟前",
                    "source": "quality",
                    "type": "warning",
                    "icon": "⚠️",
                },
                {
                    "id": "act_003",
                    "title": "模型训练任务完成",
                    "time": "1 小时前",
                    "source": "cube",
                    "type": "info",
                    "icon": "🤖",
                },
                {
                    "id": "act_004",
                    "title": "工作流「数据清洗」执行成功",
                    "time": "2 小时前",
                    "source": "agent",
                    "type": "success",
                    "icon": "⚙️",
                },
            ],
            "list_quality_issues": [
                {
                    "id": "qi_001",
                    "table": "users",
                    "column": "email",
                    "issue": "格式无效",
                    "severity": "warning",
                    "count": 234,
                },
                {
                    "id": "qi_002",
                    "table": "orders",
                    "column": "customer_id",
                    "issue": "存在空值",
                    "severity": "error",
                    "count": 56,
                },
            ],
            "list_pending_approvals": [
                {
                    "id": "appr_001",
                    "title": "数据导出申请",
                    "applicant": "张三",
                    "time": "2024-01-26 10:30",
                    "type": "data_export",
                },
                {
                    "id": "appr_002",
                    "title": "质量规则发布",
                    "applicant": "李四",
                    "time": "2024-01-26 09:15",
                    "type": "rule_publish",
                },
            ],
        }

    # ==================== 快捷入口 ====================

    def get_quick_links(
        self,
        db: Session,
        user_id: str,
        categories: Optional[List[str]] = None,
    ) -> Dict:
        """获取快捷入口列表"""
        links = self._default_links

        if categories:
            links = [l for l in links if l.category in categories]

        return {
            "links": [l.to_dict() for l in links],
            "categories": list(set(l.category for l in links)),
        }

    # ==================== 通知 ====================

    def get_notifications(
        self,
        db: Session,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
    ) -> Dict:
        """获取通知列表"""
        # 模拟通知数据
        notifications = [
            PortalNotification(
                notification_id="notif_001",
                type="info",
                title="系统维护通知",
                content="系统将于今晚 22:00-23:00 进行维护升级",
                source="system",
                priority="normal",
            ),
            PortalNotification(
                notification_id="notif_002",
                type="warning",
                title="数据质量告警",
                content="表 users 的 email 字段发现 234 个格式无效值",
                source="quality",
                priority="high",
                action_url="/quality/issues?table=users&column=email",
            ),
            PortalNotification(
                notification_id="notif_003",
                type="success",
                title="模型训练完成",
                content="您的时间序列预测模型训练已完成",
                source="cube",
                priority="normal",
                action_url="/cube/models/model_123",
            ),
            PortalNotification(
                notification_id="notif_004",
                type="info",
                title="新版本发布",
                content="Bisheng v2.5.0 已发布，包含多项新功能",
                source="agent",
                priority="low",
            ),
        ]

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        return {
            "notifications": [n.to_dict() for n in notifications[:limit]],
            "total": len(notifications),
            "unread_count": sum(1 for n in notifications if not n.read),
        }

    def mark_notification_read(
        self,
        db: Session,
        notification_id: str,
        user_id: str,
    ) -> bool:
        """标记通知为已读"""
        # 简化处理
        return True

    def mark_all_notifications_read(
        self,
        db: Session,
        user_id: str,
    ) -> int:
        """标记所有通知为已读"""
        # 简化处理，返回已读数量
        return 4

    def delete_notification(
        self,
        db: Session,
        notification_id: str,
        user_id: str,
    ) -> bool:
        """删除通知"""
        return True

    # ==================== 待办事项 ====================

    def get_todos(
        self,
        db: Session,
        user_id: str,
        status: str = "pending",  # pending, completed, all
        source: Optional[str] = None,
        limit: int = 20,
    ) -> Dict:
        """获取待办事项列表"""
        # 模拟待办数据
        todos = [
            TodoItem(
                todo_id="todo_001",
                title="审批数据导出申请",
                description="张三申请导出 users 表数据（100万行）",
                source="data",
                priority="high",
                due_date=datetime.now() + timedelta(hours=24),
                action_url="/data/approvals/001",
            ),
            TodoItem(
                todo_id="todo_002",
                title="处理数据质量告警",
                description="表 orders 存在大量空值需要处理",
                source="quality",
                priority="medium",
                due_date=datetime.now() + timedelta(hours=48),
                action_url="/quality/issues?table=orders",
            ),
            TodoItem(
                todo_id="todo_003",
                title="更新API文档",
                description="用户画像 API 文档需要更新",
                source="api",
                priority="low",
                due_date=datetime.now() + timedelta(days=7),
                action_url="/api/docs/users",
            ),
            TodoItem(
                todo_id="todo_004",
                title="审批模型发布申请",
                description="李四申请将模型「销量预测」发布到生产",
                source="cube",
                priority="high",
                due_date=datetime.now() + timedelta(hours=12),
                action_url="/cube/approvals/002",
            ),
        ]

        if status == "pending":
            todos = [t for t in todos if not t.completed]
        elif status == "completed":
            todos = [t for t in todos if t.completed]

        if source:
            todos = [t for t in todos if t.source == source]

        # 按优先级和到期时间排序
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        todos.sort(key=lambda t: (priority_order.get(t.priority, 999), t.due_date or datetime.max))

        return {
            "todos": [t.to_dict() for t in todos[:limit]],
            "total": len(todos),
            "pending_count": sum(1 for t in todos if not t.completed),
        }

    def complete_todo(
        self,
        db: Session,
        todo_id: str,
        user_id: str,
    ) -> bool:
        """完成待办事项"""
        # 简化处理
        return True

    # ==================== 用户配置 ====================

    def get_user_layout(
        self,
        db: Session,
        user_id: str,
    ) -> Dict:
        """获取用户自定义门户布局"""
        # 简化处理，返回默认布局
        return {
            "user_id": user_id,
            "layout_version": "1.0",
            "theme": "light",
            "widgets": [w.to_dict() for w in self._default_widgets],
            "custom_links": [],
            "hide_defaults": False,
        }

    def update_user_layout(
        self,
        db: Session,
        user_id: str,
        layout: Dict,
    ) -> Dict:
        """更新用户门户布局"""
        # 简化处理
        return {
            "user_id": user_id,
            "updated": True,
        }

    # ==================== 搜索 ====================

    def global_search(
        self,
        db: Session,
        user_id: str,
        query: str,
        categories: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict:
        """
        全局搜索

        跨系统搜索：资产、元数据、工作流、模型、文档等
        """
        # 简化处理，返回模拟搜索结果
        results = [
            {
                "id": "search_001",
                "type": "asset",
                "title": "用户画像数据表",
                "description": "包含用户基本信息的结构化数据表",
                "category": "data",
                "url": "/data/assets/users_profile",
                "icon": "📊",
                "highlight": "用户<b>画像</b>",
            },
            {
                "id": "search_002",
                "type": "workflow",
                "title": "数据清洗工作流",
                "description": "Bisheng 数据清洗 ETL 流程",
                "category": "agent",
                "url": "/agent/workflows/data_cleaning",
                "icon": "⚙️",
                "highlight": "数据<b>清洗</b>",
            },
            {
                "id": "search_003",
                "type": "model",
                "title": "销量预测模型",
                "description": "基于 XGBoost 的商品销量预测模型",
                "category": "cube",
                "url": "/cube/models/sales_forecast",
                "icon": "🤖",
                "highlight": "<b>销量</b>预测",
            },
        ]

        # 简单的搜索匹配
        if query:
            results = [r for r in results if query.lower() in r["title"].lower() or query.lower() in r["description"].lower()]

        if categories:
            results = [r for r in results if r.get("category") in categories]

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results),
        }

    # ==================== 系统状态 ====================

    def get_system_status(
        self,
        db: Session,
        tenant_id: str = "default",
    ) -> Dict:
        """获取各系统状态"""
        # 模拟系统状态
        return {
            "systems": [
                {
                    "id": "data",
                    "name": "Alldata 数据治理",
                    "status": "healthy",
                    "uptime_percent": 99.95,
                    "last_check": datetime.now().isoformat(),
                },
                {
                    "id": "agent",
                    "name": "Bisheng 应用编排",
                    "status": "healthy",
                    "uptime_percent": 99.8,
                    "last_check": datetime.now().isoformat(),
                },
                {
                    "id": "cube",
                    "name": "Cube Studio",
                    "status": "healthy",
                    "uptime_percent": 99.9,
                    "last_check": datetime.now().isoformat(),
                },
                {
                    "id": "chatbi",
                    "name": "ChatBI 智能分析",
                    "status": "healthy",
                    "uptime_percent": 99.7,
                    "last_check": datetime.now().isoformat(),
                },
            ],
            "overall_status": "healthy",
        }


# 创建全局服务实例
_portal_service = None


def get_portal_service() -> PortalService:
    """获取统一门户服务实例"""
    global _portal_service
    if _portal_service is None:
        _portal_service = PortalService()
    return _portal_service
