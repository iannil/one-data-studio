"""
行为审计API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from models.user_behavior import BehaviorRule
from models.user_profile import BehaviorAnomaly
from services.anomaly_detector import AnomalyDetector
from services.behavior_collector import BehaviorCollector

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
detector = AnomalyDetector()
collector = BehaviorCollector()


# Pydantic模型
class RuleCreate(BaseModel):
    """规则创建"""
    name: str
    tenant_id: str = "default"
    description: Optional[str] = None
    rule_type: str
    conditions: dict
    actions: dict
    priority: int = 0


class RuleUpdate(BaseModel):
    """规则更新"""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    actions: Optional[dict] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


@router.get("/anomalies")
async def list_anomalies(
    tenant_id: str = Query("default"),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取异常列表"""
    query = db.query(BehaviorAnomaly).filter(
        BehaviorAnomaly.tenant_id == tenant_id
    )

    if severity:
        query = query.filter(BehaviorAnomaly.severity == severity)
    if status:
        query = query.filter(BehaviorAnomaly.status == status)
    if user_id:
        query = query.filter(BehaviorAnomaly.user_id == user_id)

    anomalies = query.order_by(
        BehaviorAnomaly.detected_at.desc()
    ).limit(limit).all()

    return {
        "total": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies]
    }


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly_detail(
    anomaly_id: str,
    db: Session = Depends(get_db)
):
    """获取异常详情"""
    anomaly = db.query(BehaviorAnomaly).filter(
        BehaviorAnomaly.id == anomaly_id
    ).first()

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    return anomaly.to_dict()


@router.put("/anomalies/{anomaly_id}/status")
async def update_anomaly_status(
    anomaly_id: str,
    status: str = Body(...),
    investigated_by: str = Body(None),
    notes: str = Body(None),
    db: Session = Depends(get_db)
):
    """更新异常状态"""
    anomaly = detector.update_anomaly_status(
        db, anomaly_id, status, investigated_by, notes
    )

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    return {
        "success": True,
        "anomaly": anomaly.to_dict()
    }


@router.post("/detect")
async def run_detection(
    tenant_id: str = Body("default"),
    detection_type: str = Body("all"),
    db: Session = Depends(get_db)
):
    """运行异常检测"""
    anomalies = []

    if detection_type == "all" or detection_type == "login":
        anomalies.extend(detector.detect_login_anomalies(db, tenant_id))

    if detection_type == "all" or detection_type == "permission":
        anomalies.extend(detector.detect_permission_anomalies(db, tenant_id))

    if detection_type == "all" or detection_type == "behavior":
        anomalies.extend(detector.detect_behavior_anomalies(db, tenant_id))

    if detection_type == "all" or detection_type == "data":
        anomalies.extend(detector.detect_data_anomalies(db, tenant_id))

    return {
        "success": True,
        "detected_count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies[:100]]  # 限制返回数量
    }


@router.get("/audit-log")
async def get_audit_log(
    tenant_id: str = Query("default"),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    behavior_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """获取审计日志（行为记录）"""
    from datetime import datetime
    from models.user_behavior import UserBehavior

    query = db.query(UserBehavior).filter(
        UserBehavior.tenant_id == tenant_id
    )

    if user_id:
        query = query.filter(UserBehavior.user_id == user_id)
    if behavior_type:
        query = query.filter(UserBehavior.behavior_type == behavior_type)
    if start_date:
        query = query.filter(UserBehavior.occurred_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(UserBehavior.occurred_at <= datetime.fromisoformat(end_date))

    total = query.count()
    behaviors = query.order_by(
        UserBehavior.occurred_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "behaviors": [b.to_dict() for b in behaviors]
    }


@router.get("/rules")
async def list_rules(
    tenant_id: str = Query("default"),
    rule_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取规则列表"""
    query = db.query(BehaviorRule).filter(
        BehaviorRule.tenant_id == tenant_id
    )

    if rule_type:
        query = query.filter(BehaviorRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(BehaviorRule.is_active == is_active)

    rules = query.order_by(
        BehaviorRule.priority.desc(),
        BehaviorRule.created_at.desc()
    ).all()

    return {
        "total": len(rules),
        "rules": [r.to_dict() for r in rules]
    }


@router.post("/rules")
async def create_rule(
    rule: RuleCreate,
    db: Session = Depends(get_db)
):
    """创建规则"""
    import uuid
    from datetime import datetime

    new_rule = BehaviorRule(
        id=str(uuid.uuid4()),
        **rule.dict()
    )
    new_rule.created_at = datetime.now()

    db.add(new_rule)
    db.commit()

    return {
        "success": True,
        "rule": new_rule.to_dict()
    }


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """获取规则详情"""
    rule = db.query(BehaviorRule).filter(
        BehaviorRule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule.to_dict()


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    rule_update: RuleUpdate,
    db: Session = Depends(get_db)
):
    """更新规则"""
    rule = db.query(BehaviorRule).filter(
        BehaviorRule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()

    return {
        "success": True,
        "rule": rule.to_dict()
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """删除规则"""
    rule = db.query(BehaviorRule).filter(
        BehaviorRule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()

    return {"success": True}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """启用/禁用规则"""
    rule = db.query(BehaviorRule).filter(
        BehaviorRule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = not rule.is_active
    db.commit()

    return {
        "success": True,
        "rule_id": rule_id,
        "is_active": rule.is_active
    }


@router.get("/statistics/overview")
async def get_statistics_overview(
    tenant_id: str = Query("default"),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """获取统计概览"""
    from datetime import datetime, timedelta
    from models.user_behavior import UserBehavior, UserSession
    from sqlalchemy import func

    since = datetime.now() - timedelta(days=days)

    # 总体统计
    total_behaviors = db.query(func.count(UserBehavior.id)).filter(
        UserBehavior.tenant_id == tenant_id,
        UserBehavior.occurred_at >= since
    ).scalar() or 0

    unique_users = db.query(func.count(func.distinct(UserBehavior.user_id))).filter(
        UserBehavior.tenant_id == tenant_id,
        UserBehavior.occurred_at >= since
    ).scalar() or 0

    total_sessions = db.query(func.count(UserSession.id)).filter(
        UserSession.tenant_id == tenant_id,
        UserSession.start_time >= since
    ).scalar() or 0

    # 按类型统计
    behavior_types = db.query(
        UserBehavior.behavior_type,
        func.count(UserBehavior.id).label("count")
    ).filter(
        UserBehavior.tenant_id == tenant_id,
        UserBehavior.occurred_at >= since
    ).group_by(UserBehavior.behavior_type).all()

    # 异常统计
    open_anomalies = db.query(func.count(BehaviorAnomaly.id)).filter(
        BehaviorAnomaly.tenant_id == tenant_id,
        BehaviorAnomaly.status == "open",
        BehaviorAnomaly.created_at >= since
    ).scalar() or 0

    return {
        "period_days": days,
        "total_behaviors": total_behaviors,
        "unique_users": unique_users,
        "total_sessions": total_sessions,
        "behavior_types": [
            {"type": bt, "count": count}
            for bt, count in behavior_types
        ],
        "open_anomalies": open_anomalies
    }
