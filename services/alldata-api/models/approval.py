"""
审批工作流模型
Phase 2: 基础审批流程支持

支持：
- 审批流程模板定义
- 审批工单（发起、审批、驳回、撤销）
- 多级审批节点
- 审批历史记录
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Text, TIMESTAMP, JSON, Index, ForeignKey
from .base import Base


class ApprovalTemplate(Base):
    """审批流程模板"""
    __tablename__ = "approval_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True, comment="模板ID")
    name = Column(String(128), nullable=False, comment="模板名称")
    description = Column(Text, comment="描述")

    # 业务类型
    business_type = Column(String(32), nullable=False, comment="业务类型: data_access, data_masking, etl_publish, asset_change, security_exception")
    category = Column(String(32), default="general", comment="分类: general, security, governance, etl")

    # 审批节点定义（JSON数组）
    nodes = Column(JSON, comment="""
        审批节点配置，例：
        [
            {"node_id": "n1", "name": "部门主管审批", "type": "approve", "approver_type": "role", "approver_value": "data_engineer", "order": 1},
            {"node_id": "n2", "name": "安全管理员审批", "type": "approve", "approver_type": "role", "approver_value": "admin", "order": 2}
        ]
    """)

    # 配置
    auto_approve_timeout_hours = Column(Integer, default=0, comment="自动通过超时(小时), 0=不自动")
    allow_withdraw = Column(Integer, default=1, comment="允许撤回 0=否 1=是")
    notify_on_submit = Column(Integer, default=1, comment="提交时通知审批人")
    notify_on_complete = Column(Integer, default=1, comment="完成时通知申请人")

    # 状态
    status = Column(String(16), default="active", comment="状态: active, disabled")

    # 审计
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(128))

    def to_dict(self):
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "business_type": self.business_type,
            "category": self.category,
            "nodes": self.nodes or [],
            "auto_approve_timeout_hours": self.auto_approve_timeout_hours,
            "allow_withdraw": bool(self.allow_withdraw),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


class ApprovalRequest(Base):
    """审批工单"""
    __tablename__ = "approval_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True, comment="工单ID")
    template_id = Column(String(64), nullable=False, index=True, comment="模板ID")
    title = Column(String(255), nullable=False, comment="工单标题")
    description = Column(Text, comment="申请说明")

    # 业务类型
    business_type = Column(String(32), nullable=False, comment="业务类型")
    business_data = Column(JSON, comment="业务数据（申请内容详情）")

    # 申请人
    applicant_id = Column(String(128), nullable=False, index=True, comment="申请人ID")
    applicant_name = Column(String(128), comment="申请人名称")

    # 审批状态
    status = Column(String(16), default="pending", comment="状态: pending, in_review, approved, rejected, withdrawn, expired")
    current_node_id = Column(String(64), comment="当前审批节点ID")
    current_node_order = Column(Integer, default=1, comment="当前节点序号")
    total_nodes = Column(Integer, default=1, comment="总节点数")

    # 优先级
    priority = Column(String(16), default="normal", comment="优先级: low, normal, high, urgent")

    # 时间
    submitted_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP, comment="完成时间")
    expires_at = Column(TIMESTAMP, comment="过期时间")

    # 结果
    final_comment = Column(Text, comment="最终审批意见")

    __table_args__ = (
        Index("idx_approval_status", "status", "submitted_at"),
        Index("idx_approval_applicant", "applicant_id", "status"),
    )

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "template_id": self.template_id,
            "title": self.title,
            "description": self.description,
            "business_type": self.business_type,
            "business_data": self.business_data,
            "applicant_id": self.applicant_id,
            "applicant_name": self.applicant_name,
            "status": self.status,
            "current_node_id": self.current_node_id,
            "current_node_order": self.current_node_order,
            "total_nodes": self.total_nodes,
            "priority": self.priority,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_comment": self.final_comment,
        }


class ApprovalRecord(Base):
    """审批记录（每个节点的审批动作）"""
    __tablename__ = "approval_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True, comment="记录ID")
    request_id = Column(String(64), nullable=False, index=True, comment="工单ID")
    node_id = Column(String(64), nullable=False, comment="节点ID")
    node_order = Column(Integer, comment="节点序号")

    # 审批人
    approver_id = Column(String(128), nullable=False, comment="审批人ID")
    approver_name = Column(String(128), comment="审批人名称")

    # 审批动作
    action = Column(String(16), nullable=False, comment="动作: approve, reject, delegate, comment")
    comment = Column(Text, comment="审批意见")

    # 委派（转审）
    delegate_to = Column(String(128), comment="委派给")

    # 时间
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "request_id": self.request_id,
            "node_id": self.node_id,
            "node_order": self.node_order,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "action": self.action,
            "comment": self.comment,
            "delegate_to": self.delegate_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
