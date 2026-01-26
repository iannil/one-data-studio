"""
行为采集API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import get_db
from models.user_behavior import UserBehavior, UserSession
from services.behavior_collector import BehaviorCollector

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化收集器
collector = BehaviorCollector()


# Pydantic模型
class PageViewEvent(BaseModel):
    """页面浏览事件"""
    user_id: str
    tenant_id: str = "default"
    session_id: Optional[str] = None
    page_url: str
    page_title: Optional[str] = None
    referrer: Optional[str] = None
    load_time: Optional[float] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class ClickEvent(BaseModel):
    """点击事件"""
    user_id: str
    tenant_id: str = "default"
    session_id: Optional[str] = None
    element_type: str
    element_id: Optional[str] = None
    element_text: Optional[str] = None
    page_url: str
    user_agent: Optional[str] = None


class BehaviorEvent(BaseModel):
    """通用行为事件"""
    user_id: str
    tenant_id: str = "default"
    session_id: Optional[str] = None
    behavior_type: str
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    module: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[dict] = None


class BatchEvents(BaseModel):
    """批量事件"""
    events: List[BehaviorEvent]
    tenant_id: str = "default"


@router.post("/page-view")
async def track_page_view(
    event: PageViewEvent,
    db: Session = Depends(get_db)
):
    """记录页面浏览"""
    result = collector.collect_page_view(event.dict(), db)
    if result:
        # 更新会话
        if event.session_id:
            collector.update_session({
                "session_id": event.session_id,
                "user_id": event.user_id,
                "tenant_id": event.tenant_id,
                "page_url": event.page_url,
                "referrer": event.referrer,
                "is_entry": True
            }, db)
        return {"success": True, "message": "Page view tracked"}
    return {"success": False, "message": "Failed to track page view"}


@router.post("/click")
async def track_click(
    event: ClickEvent,
    db: Session = Depends(get_db)
):
    """记录点击事件"""
    result = collector.collect_click(event.dict(), db)
    if result:
        return {"success": True, "message": "Click tracked"}
    return {"success": False, "message": "Failed to track click"}


@router.post("/track")
async def track_behavior(
    event: BehaviorEvent,
    db: Session = Depends(get_db)
):
    """记录通用行为事件"""
    result = collector.collect(event.dict(), db)
    if result:
        return {"success": True, "message": "Behavior tracked"}
    return {"success": False, "message": "Failed to track behavior"}


@router.post("/batch")
async def track_behaviors_batch(
    batch: BatchEvents,
    db: Session = Depends(get_db)
):
    """批量记录行为事件"""
    count = collector.collect_batch(
        [e.dict() for e in batch.events],
        db
    )
    return {"success": True, "tracked_count": count}


@router.get("/user/{user_id}")
async def get_user_behaviors(
    user_id: str,
    tenant_id: str = Query("default"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取用户行为列表"""
    behaviors = collector.get_user_behaviors(
        db, user_id, tenant_id, limit, offset
    )
    return {
        "total": len(behaviors),
        "behaviors": [b.to_dict() for b in behaviors]
    }


@router.get("/type/{behavior_type}")
async def get_behaviors_by_type(
    behavior_type: str,
    tenant_id: str = Query("default"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """按类型获取行为"""
    from datetime import datetime

    start_time = datetime.fromisoformat(start_date) if start_date else None
    end_time = datetime.fromisoformat(end_date) if end_date else None

    behaviors = collector.get_behaviors_by_type(
        db, behavior_type, tenant_id, start_time, end_time, limit
    )
    return {
        "total": len(behaviors),
        "behaviors": [b.to_dict() for b in behaviors]
    }


@router.post("/session/start")
async def start_session(
    user_id: str,
    tenant_id: str = Body("default"),
    page_url: str = Body(...),
    user_agent: str = Body(None),
    ip_address: str = Body(None),
    referrer: str = Body(None),
    db: Session = Depends(get_db)
):
    """开始会话"""
    import uuid
    session_id = str(uuid.uuid4())

    session = collector.update_session({
        "session_id": session_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "page_url": page_url,
        "referrer": referrer,
        "user_agent": user_agent,
        "ip_address": ip_address,
    }, db)

    return {
        "success": True,
        "session_id": session_id,
        "session": session.to_dict() if session else None
    }


@router.post("/session/end")
async def end_session(
    session_id: str,
    tenant_id: str = Body("default"),
    db: Session = Depends(get_db)
):
    """结束会话"""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.tenant_id == tenant_id
    ).first()

    if session:
        session.is_active = False
        session.end_time = datetime.now()
        if session.start_time:
            duration = (session.end_time - session.start_time).total_seconds()
            session.duration = duration
        db.commit()

        return {"success": True, "session": session.to_dict()}

    raise HTTPException(status_code=404, detail="Session not found")
