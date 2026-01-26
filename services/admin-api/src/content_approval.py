"""
内容审批流程服务
Phase 2.1: 内容审批工作流、状态机管理
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database import db_manager
from models.content import Article, ContentApproval, generate_content_id
from models.base import SessionLocal

logger = logging.getLogger(__name__)


# 审批工作流定义
WORKFLOWS = {
    "simple": {
        "name": "简单审批",
        "steps": [
            {"role": "editor", "name": "编辑", "action": "submit"},
            {"role": "reviewer", "name": "审核", "action": "review"},
            {"role": "publisher", "name": "发布", "action": "publish"},
        ]
    },
    "expert": {
        "name": "专家审批",
        "steps": [
            {"role": "editor", "name": "编辑", "action": "submit"},
            {"role": "technical_reviewer", "name": "技术审核", "action": "review"},
            {"role": "content_reviewer", "name": "内容审核", "action": "review"},
            {"role": "publisher", "name": "发布", "action": "publish"},
        ]
    }
}


class ContentApprovalService:
    """内容审批服务"""

    def __init__(self):
        self.workflows = WORKFLOWS

    def submit_for_approval(
        self,
        content_type: str,
        content_id: str,
        content_title: str,
        submitted_by: str,
        submitted_by_name: str,
        workflow_type: str = "simple",
    ) -> ContentApproval:
        """
        提交内容审批

        Args:
            content_type: 内容类型
            content_id: 内容ID
            content_title: 内容标题
            submitted_by: 提交人ID
            submitted_by_name: 提交人名称
            workflow_type: 工作流类型

        Returns:
            审批记录
        """
        approval = ContentApproval(
            approval_id=f"appr_{uuid.uuid4().hex[:12]}",
            content_type=content_type,
            content_id=content_id,
            content_title=content_title,
            submitted_by=submitted_by,
            submitted_by_name=submitted_by_name,
            workflow_type=workflow_type,
            current_step=0,
            status="pending",
        )

        with db_manager.get_session() as session:
            # 更新内容状态
            if content_type == "article":
                article = session.query(Article).filter(
                    Article.article_id == content_id
                ).first()
                if article:
                    article.status = "pending"
                    article.submitted_at = datetime.utcnow()

            session.add(approval)
            session.commit()
            session.refresh(approval)

        return approval

    def approve(
        self,
        approval_id: str,
        reviewer_id: str,
        reviewer_name: str,
        comment: Optional[str] = None,
    ) -> bool:
        """
        审批通过

        Args:
            approval_id: 审批ID
            reviewer_id: 审批人ID
            reviewer_name: 审批人名称
            comment: 审批意见

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            approval = session.query(ContentApproval).filter(
                ContentApproval.approval_id == approval_id
            ).first()

            if not approval or approval.status != "pending":
                return False

            workflow = self.workflows.get(approval.workflow_type, {})
            steps = workflow.get("steps", [])
            total_steps = len(steps)
            current_step = approval.current_step

            # 检查是否是最后一步
            if current_step >= total_steps - 1:
                # 审批完成，发布内容
                approval.status = "approved"
                approval.completed_at = datetime.utcnow()
                self._publish_content(approval.content_type, approval.content_id, session)
            else:
                # 进入下一步
                approval.current_step = current_step + 1

            approval.reviewer_id = reviewer_id
            approval.reviewer_name = reviewer_name
            approval.reviewed_at = datetime.utcnow()
            approval.comment = comment

            session.commit()

        return True

    def reject(
        self,
        approval_id: str,
        reviewer_id: str,
        reviewer_name: str,
        rejection_reason: str,
    ) -> bool:
        """
        审批拒绝

        Args:
            approval_id: 审批ID
            reviewer_id: 审批人ID
            reviewer_name: 审批人名称
            rejection_reason: 拒绝原因

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            approval = session.query(ContentApproval).filter(
                ContentApproval.approval_id == approval_id
            ).first()

            if not approval or approval.status != "pending":
                return False

            approval.status = "rejected"
            approval.reviewer_id = reviewer_id
            approval.reviewer_name = reviewer_name
            approval.reviewed_at = datetime.utcnow()
            approval.rejection_reason = rejection_reason
            approval.completed_at = datetime.utcnow()

            # 更新内容状态
            if approval.content_type == "article":
                article = session.query(Article).filter(
                    Article.article_id == approval.content_id
                ).first()
                if article:
                    article.status = "rejected"
                    article.rejection_reason = rejection_reason

            session.commit()

        return True

    def _publish_content(
        self,
        content_type: str,
        content_id: str,
        session: Session,
    ):
        """
        发布内容

        Args:
            content_type: 内容类型
            content_id: 内容ID
            session: 数据库会话
        """
        if content_type == "article":
            article = session.query(Article).filter(
                Article.article_id == content_id
            ).first()
            if article:
                article.status = "published"
                article.published_at = datetime.utcnow()

                # 创建新版本记录
                self._create_version(article, session)

    def _create_version(self, article: Article, session: Session):
        """
        创建文章版本记录

        Args:
            article: 文章对象
            session: 数据库会话
        """
        # 获取当前版本号
        last_version = session.query(ArticleVersion).filter(
            ArticleVersion.article_id == article.article_id
        ).order_by(ArticleVersion.version_number.desc()).first()

        new_version_number = (last_version.version_number + 1) if last_version else 1

        from models.content import ArticleVersion

        version = ArticleVersion(
            version_id=f"ver_{uuid.uuid4().hex[:12]}",
            article_id=article.article_id,
            version_number=new_version_number,
            title=article.title,
            content=article.content,
            summary=article.summary,
            change_type="update",
            created_by=article.author_id,
            created_by_name=article.author_name,
        )

        session.add(version)

    def get_pending_approvals(
        self,
        reviewer_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取待审批列表

        Args:
            reviewer_id: 审批人ID（可选）
            content_type: 内容类型过滤
            limit: 返回数量

        Returns:
            待审批列表
        """
        with db_manager.get_session() as session:
            query = session.query(ContentApproval).filter(
                ContentApproval.status == "pending"
            )

            if content_type:
                query = query.filter(ContentApproval.content_type == content_type)

            query = query.order_by(ContentApproval.submitted_at.desc())

            approvals = query.limit(limit).all()

            return [a.to_dict() for a in approvals]

    def get_approval_history(
        self,
        content_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取审批历史

        Args:
            content_id: 内容ID
            content_type: 内容类型
            limit: 返回数量

        Returns:
            审批历史列表
        """
        with db_manager.get_session() as session:
            query = session.query(ContentApproval)

            if content_id:
                query = query.filter(ContentApproval.content_id == content_id)
            if content_type:
                query = query.filter(ContentApproval.content_type == content_type)

            query = query.order_by(ContentApproval.submitted_at.desc())

            approvals = query.limit(limit).all()

            return [a.to_dict() for a in approvals]


# 全局实例
_approval_service: Optional[ContentApprovalService] = None


def get_content_approval_service() -> ContentApprovalService:
    """获取内容审批服务单例"""
    global _approval_service
    if _approval_service is None:
        _approval_service = ContentApprovalService()
    return _approval_service
