"""
行为收集服务
接收并存储用户行为数据
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from models.user_behavior import UserBehavior, UserSession

logger = logging.getLogger(__name__)


class BehaviorCollector:
    """行为收集器"""

    def __init__(self):
        pass

    def collect(self, behavior_data: Dict, db: Session = None) -> Optional[UserBehavior]:
        """
        收集单条行为数据

        behavior_data: {
            "tenant_id": "租户ID",
            "user_id": "用户ID",
            "session_id": "会话ID",
            "behavior_type": "行为类型",
            "action": "操作名称",
            "target_type": "目标类型",
            "target_id": "目标ID",
            "page_url": "页面URL",
            "page_title": "页面标题",
            "referrer": "来源页面",
            "module": "功能模块",
            "ip_address": "IP地址",
            "user_agent": "用户代理",
            "device_type": "设备类型",
            "browser": "浏览器",
            "os": "操作系统",
            "duration": "停留时长",
            "load_time": "加载时间",
            "metadata": {"额外数据"}
        }
        """
        if not db:
            return None

        try:
            # 解析用户代理获取设备和浏览器信息
            device_info = self._parse_user_agent(
                behavior_data.get("user_agent", "")
            )

            behavior = UserBehavior(
                tenant_id=behavior_data.get("tenant_id", "default"),
                user_id=behavior_data.get("user_id", "anonymous"),
                session_id=behavior_data.get("session_id"),
                behavior_type=behavior_data.get("behavior_type", "unknown"),
                action=behavior_data.get("action"),
                target_type=behavior_data.get("target_type"),
                target_id=behavior_data.get("target_id"),
                page_url=behavior_data.get("page_url"),
                page_title=behavior_data.get("page_title"),
                referrer=behavior_data.get("referrer"),
                module=behavior_data.get("module"),
                ip_address=behavior_data.get("ip_address"),
                user_agent=behavior_data.get("user_agent"),
                device_type=behavior_data.get("device_type") or device_info.get("device_type"),
                browser=behavior_data.get("browser") or device_info.get("browser"),
                os=behavior_data.get("os") or device_info.get("os"),
                duration=behavior_data.get("duration"),
                load_time=behavior_data.get("load_time"),
                metadata=behavior_data.get("metadata"),
                occurred_at=behavior_data.get("occurred_at", datetime.now()),
            )

            db.add(behavior)
            db.commit()

            logger.debug(f"Collected behavior: {behavior.behavior_type} for user {behavior.user_id}")
            return behavior

        except Exception as e:
            logger.error(f"Failed to collect behavior: {e}")
            db.rollback()
            return None

    def collect_batch(self, behaviors_data: List[Dict], db: Session) -> int:
        """
        批量收集行为数据

        返回: 成功收集的数量
        """
        count = 0
        for data in behaviors_data:
            if self.collect(data, db):
                count += 1
        return count

    def collect_api_call(self, api_data: Dict, db: Session = None) -> Optional[UserBehavior]:
        """
        收集API调用行为

        api_data: {
            "user_id": "用户ID",
            "tenant_id": "租户ID",
            "method": "GET/POST等",
            "path": "/api/v1/xxx",
            "status_code": 200,
            "duration": 0.123,
            "user_agent": "用户代理",
            "ip": "IP地址"
        }
        """
        if not db:
            return None

        behavior_data = {
            "tenant_id": api_data.get("tenant_id", "default"),
            "user_id": api_data.get("user_id", "anonymous"),
            "behavior_type": "api_call",
            "action": f"{api_data.get('method', 'UNKNOWN')} {api_data.get('path', '/')}",
            "target_type": "api",
            "target_id": api_data.get("path"),
            "module": self._extract_module_from_path(api_data.get("path", "")),
            "ip_address": api_data.get("ip"),
            "user_agent": api_data.get("user_agent"),
            "duration": api_data.get("duration"),
            "metadata": {
                "method": api_data.get("method"),
                "status_code": api_data.get("status_code"),
            }
        }

        return self.collect(behavior_data, db)

    def collect_page_view(self, page_data: Dict, db: Session = None) -> Optional[UserBehavior]:
        """
        收集页面浏览行为

        page_data: {
            "user_id": "用户ID",
            "tenant_id": "租户ID",
            "session_id": "会话ID",
            "page_url": "/page/xxx",
            "page_title": "页面标题",
            "referrer": "来源页面",
            "load_time": 1.234
        }
        """
        if not db:
            return None

        behavior_data = {
            "tenant_id": page_data.get("tenant_id", "default"),
            "user_id": page_data.get("user_id", "anonymous"),
            "session_id": page_data.get("session_id"),
            "behavior_type": "page_view",
            "action": "view",
            "target_type": "page",
            "page_url": page_data.get("page_url"),
            "page_title": page_data.get("page_title"),
            "referrer": page_data.get("referrer"),
            "module": self._extract_module_from_path(page_data.get("page_url", "")),
            "load_time": page_data.get("load_time"),
        }

        return self.collect(behavior_data, db)

    def collect_click(self, click_data: Dict, db: Session = None) -> Optional[UserBehavior]:
        """
        收集点击行为

        click_data: {
            "user_id": "用户ID",
            "tenant_id": "租户ID",
            "session_id": "会话ID",
            "element_type": "button/link等",
            "element_id": "元素ID",
            "element_text": "元素文本",
            "page_url": "当前页面"
        }
        """
        if not db:
            return None

        behavior_data = {
            "tenant_id": click_data.get("tenant_id", "default"),
            "user_id": click_data.get("user_id", "anonymous"),
            "session_id": click_data.get("session_id"),
            "behavior_type": "click",
            "action": click_data.get("element_text") or click_data.get("element_type"),
            "target_type": click_data.get("element_type"),
            "target_id": click_data.get("element_id"),
            "page_url": click_data.get("page_url"),
            "module": self._extract_module_from_path(click_data.get("page_url", "")),
            "metadata": {
                "element_text": click_data.get("element_text"),
            }
        }

        return self.collect(behavior_data, db)

    def update_session(self, session_data: Dict, db: Session) -> Optional[UserSession]:
        """
        更新或创建会话

        session_data: {
            "session_id": "会话ID",
            "user_id": "用户ID",
            "tenant_id": "租户ID",
            "ip_address": "IP地址",
            "user_agent": "用户代理",
            "page_url": "当前页面",
            "is_entry": 是否是入口页面
        }
        """
        try:
            session = db.query(UserSession).filter(
                UserSession.id == session_data.get("session_id")
            ).first()

            if session:
                # 更新现有会话
                if session_data.get("page_url"):
                    session.exit_page = session_data.get("page_url")
                session.updated_at = datetime.now()
                if session_data.get("is_entry"):
                    session.entry_page = session_data.get("page_url")
            else:
                # 创建新会话
                session = UserSession(
                    id=session_data.get("session_id"),
                    tenant_id=session_data.get("tenant_id", "default"),
                    user_id=session_data.get("user_id", "anonymous"),
                    start_time=datetime.now(),
                    ip_address=session_data.get("ip_address"),
                    user_agent=session_data.get("user_agent"),
                    entry_page=session_data.get("page_url"),
                    exit_page=session_data.get("page_url"),
                    referrer=session_data.get("referrer"),
                    page_views=1,
                )
                db.add(session)

            db.commit()
            return session

        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            db.rollback()
            return None

    def _parse_user_agent(self, user_agent: str) -> Dict:
        """解析用户代理字符串"""
        result = {"device_type": "unknown", "browser": "unknown", "os": "unknown"}

        if not user_agent:
            return result

        ua_lower = user_agent.lower()

        # 设备类型
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            result["device_type"] = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            result["device_type"] = "tablet"
        else:
            result["device_type"] = "pc"

        # 操作系统
        if "windows" in ua_lower:
            result["os"] = "Windows"
        elif "mac os x" in ua_lower or "macos" in ua_lower:
            result["os"] = "macOS"
        elif "linux" in ua_lower:
            result["os"] = "Linux"
        elif "android" in ua_lower:
            result["os"] = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            result["os"] = "iOS"

        # 浏览器
        if "chrome" in ua_lower and "edg" not in ua_lower:
            result["browser"] = "Chrome"
        elif "firefox" in ua_lower:
            result["browser"] = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            result["browser"] = "Safari"
        elif "edg" in ua_lower:
            result["browser"] = "Edge"
        elif "micromessenger" in ua_lower:
            result["browser"] = "WeChat"

        return result

    def _extract_module_from_path(self, path: str) -> Optional[str]:
        """从路径提取功能模块"""
        if not path:
            return None

        # 简单的路径到模块映射
        path_parts = path.strip("/").split("/")
        if len(path_parts) > 0:
            return path_parts[0]

        return None

    def get_user_behaviors(
        self,
        db: Session,
        user_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserBehavior]:
        """获取用户行为列表"""
        return db.query(UserBehavior).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id
        ).order_by(
            UserBehavior.occurred_at.desc()
        ).offset(offset).limit(limit).all()

    def get_behaviors_by_type(
        self,
        db: Session,
        behavior_type: str,
        tenant_id: str,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[UserBehavior]:
        """按类型获取行为"""
        query = db.query(UserBehavior).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.behavior_type == behavior_type
        )

        if start_time:
            query = query.filter(UserBehavior.occurred_at >= start_time)
        if end_time:
            query = query.filter(UserBehavior.occurred_at <= end_time)

        return query.order_by(UserBehavior.occurred_at.desc()).limit(limit).all()
