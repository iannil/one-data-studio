"""
审批工作流引擎
Phase 2: 基础审批流程支持

功能：
- 审批模板管理（创建、查询、启用/禁用）
- 审批工单发起与流转
- 多级节点审批（顺序审批）
- 审批/驳回/撤回/委派操作
- 待办任务查询
- 审批历史查询
- 到期自动处理
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 预置审批模板
DEFAULT_TEMPLATES = [
    {
        "template_id": "tpl_data_access",
        "name": "数据访问权限申请",
        "description": "申请访问受限数据资产的权限",
        "business_type": "data_access",
        "category": "security",
        "nodes": [
            {"node_id": "n1", "name": "数据负责人审批", "type": "approve", "approver_type": "role", "approver_value": "data_engineer", "order": 1},
            {"node_id": "n2", "name": "安全管理员审批", "type": "approve", "approver_type": "role", "approver_value": "admin", "order": 2},
        ],
    },
    {
        "template_id": "tpl_data_masking",
        "name": "数据脱敏规则变更",
        "description": "变更或豁免数据脱敏规则",
        "business_type": "data_masking",
        "category": "security",
        "nodes": [
            {"node_id": "n1", "name": "安全管理员审批", "type": "approve", "approver_type": "role", "approver_value": "admin", "order": 1},
        ],
    },
    {
        "template_id": "tpl_etl_publish",
        "name": "ETL任务上线审批",
        "description": "ETL任务发布到生产环境的审批",
        "business_type": "etl_publish",
        "category": "etl",
        "nodes": [
            {"node_id": "n1", "name": "技术负责人审批", "type": "approve", "approver_type": "role", "approver_value": "data_engineer", "order": 1},
        ],
    },
    {
        "template_id": "tpl_asset_change",
        "name": "数据资产变更申请",
        "description": "数据资产结构或分类变更审批",
        "business_type": "asset_change",
        "category": "governance",
        "nodes": [
            {"node_id": "n1", "name": "数据治理专员审批", "type": "approve", "approver_type": "role", "approver_value": "data_engineer", "order": 1},
        ],
    },
    {
        "template_id": "tpl_security_exception",
        "name": "安全策略例外申请",
        "description": "申请安全策略临时例外",
        "business_type": "security_exception",
        "category": "security",
        "nodes": [
            {"node_id": "n1", "name": "安全管理员审批", "type": "approve", "approver_type": "role", "approver_value": "admin", "order": 1},
            {"node_id": "n2", "name": "系统管理员确认", "type": "approve", "approver_type": "role", "approver_value": "admin", "order": 2},
        ],
    },
]


class ApprovalWorkflowEngine:
    """
    审批工作流引擎

    提供基础的多级审批流程，支持数据治理场景中的
    权限申请、脱敏变更、ETL上线等审批需求。
    """

    def __init__(self):
        self._initialized = False

    # ==================== 模板管理 ====================

    def initialize_default_templates(self, db_session=None) -> int:
        """初始化预置审批模板"""
        if db_session is None or self._initialized:
            return 0

        created = 0
        try:
            from models.approval import ApprovalTemplate

            for tpl_data in DEFAULT_TEMPLATES:
                existing = db_session.query(ApprovalTemplate).filter(
                    ApprovalTemplate.template_id == tpl_data["template_id"]
                ).first()

                if not existing:
                    tpl = ApprovalTemplate(
                        template_id=tpl_data["template_id"],
                        name=tpl_data["name"],
                        description=tpl_data["description"],
                        business_type=tpl_data["business_type"],
                        category=tpl_data.get("category", "general"),
                        nodes=tpl_data["nodes"],
                        created_by="system",
                    )
                    db_session.add(tpl)
                    created += 1

            if created:
                db_session.commit()
                logger.info(f"初始化 {created} 个默认审批模板")

            self._initialized = True

        except Exception as e:
            logger.error(f"初始化审批模板失败: {e}")

        return created

    def create_template(
        self,
        name: str,
        business_type: str,
        nodes: List[Dict[str, Any]],
        description: str = "",
        category: str = "general",
        created_by: str = "",
        db_session=None,
    ) -> Dict[str, Any]:
        """创建审批模板"""
        result = {"success": False, "template_id": None, "message": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        if not nodes:
            result["message"] = "审批节点不能为空"
            return result

        try:
            from models.approval import ApprovalTemplate

            template_id = f"tpl_{uuid.uuid4().hex[:12]}"

            # 确保节点有序号
            for i, node in enumerate(nodes):
                if "order" not in node:
                    node["order"] = i + 1
                if "node_id" not in node:
                    node["node_id"] = f"n{i + 1}"

            tpl = ApprovalTemplate(
                template_id=template_id,
                name=name,
                description=description,
                business_type=business_type,
                category=category,
                nodes=nodes,
                created_by=created_by,
            )

            db_session.add(tpl)
            db_session.commit()

            result["success"] = True
            result["template_id"] = template_id
            result["message"] = f"模板 {name} 创建成功"

            logger.info(f"审批模板创建: {template_id} ({name})")

        except Exception as e:
            logger.error(f"创建审批模板失败: {e}")
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def list_templates(
        self,
        business_type: str = None,
        category: str = None,
        status: str = "active",
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """列出审批模板"""
        if db_session is None:
            return []

        try:
            from models.approval import ApprovalTemplate

            query = db_session.query(ApprovalTemplate)
            if business_type:
                query = query.filter(ApprovalTemplate.business_type == business_type)
            if category:
                query = query.filter(ApprovalTemplate.category == category)
            if status:
                query = query.filter(ApprovalTemplate.status == status)

            templates = query.order_by(ApprovalTemplate.created_at.desc()).all()
            return [t.to_dict() for t in templates]

        except Exception as e:
            logger.error(f"查询模板失败: {e}")
            return []

    # ==================== 工单管理 ====================

    def submit_request(
        self,
        template_id: str,
        title: str,
        business_data: Dict[str, Any],
        applicant_id: str,
        applicant_name: str = "",
        description: str = "",
        priority: str = "normal",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        提交审批工单

        Args:
            template_id: 模板ID
            title: 工单标题
            business_data: 业务数据
            applicant_id: 申请人ID
            applicant_name: 申请人名称
            description: 申请说明
            priority: 优先级
            db_session: 数据库会话

        Returns:
            提交结果
        """
        result = {"success": False, "request_id": None, "message": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        try:
            from models.approval import ApprovalTemplate, ApprovalRequest

            # 查找模板
            template = db_session.query(ApprovalTemplate).filter(
                ApprovalTemplate.template_id == template_id,
                ApprovalTemplate.status == "active",
            ).first()

            if not template:
                result["message"] = f"审批模板 {template_id} 不存在或已禁用"
                return result

            nodes = template.nodes or []
            if not nodes:
                result["message"] = "审批模板无审批节点"
                return result

            # 按 order 排序
            sorted_nodes = sorted(nodes, key=lambda n: n.get("order", 0))
            first_node = sorted_nodes[0]

            request_id = f"req_{uuid.uuid4().hex[:12]}"

            # 计算过期时间
            expires_at = None
            if template.auto_approve_timeout_hours and template.auto_approve_timeout_hours > 0:
                expires_at = datetime.utcnow() + timedelta(hours=template.auto_approve_timeout_hours)

            approval_request = ApprovalRequest(
                request_id=request_id,
                template_id=template_id,
                title=title,
                description=description,
                business_type=template.business_type,
                business_data=business_data,
                applicant_id=applicant_id,
                applicant_name=applicant_name,
                status="in_review",
                current_node_id=first_node["node_id"],
                current_node_order=1,
                total_nodes=len(sorted_nodes),
                priority=priority,
                expires_at=expires_at,
            )

            db_session.add(approval_request)
            db_session.commit()

            result["success"] = True
            result["request_id"] = request_id
            result["message"] = f"工单 {title} 已提交，等待审批"
            result["current_node"] = first_node.get("name", "")
            result["total_nodes"] = len(sorted_nodes)

            logger.info(f"审批工单提交: {request_id} ({title}) by {applicant_id}")

        except Exception as e:
            logger.error(f"提交审批工单失败: {e}", exc_info=True)
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def process_approval(
        self,
        request_id: str,
        approver_id: str,
        approver_name: str,
        action: str,
        comment: str = "",
        delegate_to: str = None,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        处理审批（审批/驳回/委派）

        Args:
            request_id: 工单ID
            approver_id: 审批人ID
            approver_name: 审批人名称
            action: 动作 approve/reject/delegate
            comment: 审批意见
            delegate_to: 委派目标（当action=delegate时）
            db_session: 数据库会话

        Returns:
            处理结果
        """
        result = {"success": False, "message": "", "new_status": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        if action not in ("approve", "reject", "delegate"):
            result["message"] = f"不支持的操作: {action}"
            return result

        try:
            from models.approval import ApprovalTemplate, ApprovalRequest, ApprovalRecord

            req = db_session.query(ApprovalRequest).filter(
                ApprovalRequest.request_id == request_id,
            ).first()

            if not req:
                result["message"] = "工单不存在"
                return result

            if req.status not in ("pending", "in_review"):
                result["message"] = f"工单状态 {req.status} 不允许审批"
                return result

            # 记录审批
            record = ApprovalRecord(
                record_id=f"rec_{uuid.uuid4().hex[:12]}",
                request_id=request_id,
                node_id=req.current_node_id or "",
                node_order=req.current_node_order,
                approver_id=approver_id,
                approver_name=approver_name,
                action=action,
                comment=comment,
                delegate_to=delegate_to,
            )
            db_session.add(record)

            if action == "approve":
                # 查找模板节点
                template = db_session.query(ApprovalTemplate).filter(
                    ApprovalTemplate.template_id == req.template_id,
                ).first()

                nodes = sorted(template.nodes or [], key=lambda n: n.get("order", 0)) if template else []
                current_order = req.current_node_order or 1

                if current_order >= len(nodes):
                    # 最后一个节点，审批通过
                    req.status = "approved"
                    req.completed_at = datetime.utcnow()
                    req.final_comment = comment
                    result["new_status"] = "approved"
                    result["message"] = "审批通过"
                else:
                    # 流转到下一个节点
                    next_node = nodes[current_order]
                    req.current_node_id = next_node["node_id"]
                    req.current_node_order = current_order + 1
                    result["new_status"] = "in_review"
                    result["message"] = f"已审批，流转到: {next_node.get('name', '')}"

            elif action == "reject":
                req.status = "rejected"
                req.completed_at = datetime.utcnow()
                req.final_comment = comment
                result["new_status"] = "rejected"
                result["message"] = "已驳回"

            elif action == "delegate":
                if not delegate_to:
                    result["message"] = "委派目标不能为空"
                    return result
                result["new_status"] = "in_review"
                result["message"] = f"已委派给 {delegate_to}"

            db_session.commit()
            result["success"] = True

            logger.info(
                f"审批处理: {request_id} action={action} by={approver_id} -> {result['new_status']}"
            )

        except Exception as e:
            logger.error(f"审批处理失败: {e}", exc_info=True)
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def withdraw_request(
        self,
        request_id: str,
        applicant_id: str,
        db_session=None,
    ) -> Dict[str, Any]:
        """撤回审批工单"""
        result = {"success": False, "message": ""}

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        try:
            from models.approval import ApprovalTemplate, ApprovalRequest

            req = db_session.query(ApprovalRequest).filter(
                ApprovalRequest.request_id == request_id,
                ApprovalRequest.applicant_id == applicant_id,
            ).first()

            if not req:
                result["message"] = "工单不存在或无权限"
                return result

            if req.status not in ("pending", "in_review"):
                result["message"] = f"状态 {req.status} 不允许撤回"
                return result

            # 检查模板是否允许撤回
            template = db_session.query(ApprovalTemplate).filter(
                ApprovalTemplate.template_id == req.template_id,
            ).first()

            if template and not template.allow_withdraw:
                result["message"] = "此流程不允许撤回"
                return result

            req.status = "withdrawn"
            req.completed_at = datetime.utcnow()
            db_session.commit()

            result["success"] = True
            result["message"] = "工单已撤回"

            logger.info(f"审批撤回: {request_id} by {applicant_id}")

        except Exception as e:
            logger.error(f"撤回失败: {e}")
            result["message"] = str(e)

        return result

    # ==================== 查询 ====================

    def get_request_detail(
        self,
        request_id: str,
        db_session=None,
    ) -> Optional[Dict[str, Any]]:
        """获取工单详情（含审批记录）"""
        if db_session is None:
            return None

        try:
            from models.approval import ApprovalRequest, ApprovalRecord

            req = db_session.query(ApprovalRequest).filter(
                ApprovalRequest.request_id == request_id,
            ).first()

            if not req:
                return None

            detail = req.to_dict()

            # 附加审批记录
            records = db_session.query(ApprovalRecord).filter(
                ApprovalRecord.request_id == request_id,
            ).order_by(ApprovalRecord.created_at.asc()).all()

            detail["records"] = [r.to_dict() for r in records]

            return detail

        except Exception as e:
            logger.error(f"获取工单详情失败: {e}")
            return None

    def get_pending_approvals(
        self,
        approver_role: str = None,
        approver_id: str = None,
        page: int = 1,
        page_size: int = 20,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        获取待审批列表

        根据审批人的角色匹配当前节点需要的审批角色
        """
        if db_session is None:
            return {"total": 0, "items": []}

        try:
            from models.approval import ApprovalRequest, ApprovalTemplate

            # 查所有 in_review 工单
            query = db_session.query(ApprovalRequest).filter(
                ApprovalRequest.status == "in_review",
            )

            all_requests = query.order_by(
                ApprovalRequest.submitted_at.desc()
            ).all()

            # 根据角色过滤
            filtered = []
            for req in all_requests:
                if approver_role:
                    template = db_session.query(ApprovalTemplate).filter(
                        ApprovalTemplate.template_id == req.template_id,
                    ).first()

                    if template and template.nodes:
                        current_node = None
                        for node in template.nodes:
                            if node.get("node_id") == req.current_node_id:
                                current_node = node
                                break

                        if current_node:
                            node_approver = current_node.get("approver_value", "")
                            if node_approver == approver_role or node_approver == "*":
                                filtered.append(req)
                        else:
                            filtered.append(req)
                    else:
                        filtered.append(req)
                else:
                    filtered.append(req)

            total = len(filtered)
            start = (page - 1) * page_size
            paged = filtered[start:start + page_size]

            return {
                "total": total,
                "items": [r.to_dict() for r in paged],
            }

        except Exception as e:
            logger.error(f"获取待审批列表失败: {e}")
            return {"total": 0, "items": []}

    def get_my_requests(
        self,
        applicant_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 20,
        db_session=None,
    ) -> Dict[str, Any]:
        """获取我的申请列表"""
        if db_session is None:
            return {"total": 0, "items": []}

        try:
            from models.approval import ApprovalRequest

            query = db_session.query(ApprovalRequest).filter(
                ApprovalRequest.applicant_id == applicant_id,
            )

            if status:
                query = query.filter(ApprovalRequest.status == status)

            total = query.count()
            requests = query.order_by(
                ApprovalRequest.submitted_at.desc()
            ).offset((page - 1) * page_size).limit(page_size).all()

            return {
                "total": total,
                "items": [r.to_dict() for r in requests],
            }

        except Exception as e:
            logger.error(f"获取申请列表失败: {e}")
            return {"total": 0, "items": []}

    def get_approval_statistics(
        self,
        db_session=None,
    ) -> Dict[str, Any]:
        """获取审批统计信息"""
        stats = {
            "total_requests": 0,
            "pending_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "withdrawn_count": 0,
            "by_business_type": {},
        }

        if db_session is None:
            return stats

        try:
            from models.approval import ApprovalRequest
            from sqlalchemy import func

            stats["total_requests"] = db_session.query(
                func.count(ApprovalRequest.id)
            ).scalar() or 0

            stats["pending_count"] = db_session.query(
                func.count(ApprovalRequest.id)
            ).filter(ApprovalRequest.status == "in_review").scalar() or 0

            stats["approved_count"] = db_session.query(
                func.count(ApprovalRequest.id)
            ).filter(ApprovalRequest.status == "approved").scalar() or 0

            stats["rejected_count"] = db_session.query(
                func.count(ApprovalRequest.id)
            ).filter(ApprovalRequest.status == "rejected").scalar() or 0

            stats["withdrawn_count"] = db_session.query(
                func.count(ApprovalRequest.id)
            ).filter(ApprovalRequest.status == "withdrawn").scalar() or 0

            # 按业务类型统计
            type_counts = db_session.query(
                ApprovalRequest.business_type,
                func.count(ApprovalRequest.id),
            ).group_by(ApprovalRequest.business_type).all()

            stats["by_business_type"] = {
                t: c for t, c in type_counts
            }

        except Exception as e:
            logger.error(f"获取审批统计失败: {e}")

        return stats


# 全局实例
_workflow_engine: Optional[ApprovalWorkflowEngine] = None


def get_approval_workflow_engine() -> ApprovalWorkflowEngine:
    """获取审批工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = ApprovalWorkflowEngine()
    return _workflow_engine
