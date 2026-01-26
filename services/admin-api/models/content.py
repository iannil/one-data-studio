"""
内容管理数据模型
Phase 2.1: 内容分类、标签、版本管理、审批流程
"""

import json
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


def generate_content_id() -> str:
    """生成内容ID"""
    return f"content_{uuid.uuid4().hex[:12]}"


def generate_category_id() -> str:
    """生成分类ID"""
    return f"cat_{uuid.uuid4().hex[:8]}"


def generate_tag_id() -> str:
    """生成标签ID"""
    return f"tag_{uuid.uuid4().hex[:8]}"


class ContentCategory(Base):
    """内容分类表"""
    __tablename__ = "content_categories"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True, comment='分类ID')

    # 基本信息
    name = Column(String(128), nullable=False, comment='分类名称')
    slug = Column(String(128), unique=True, nullable=False, comment='URL别名')
    description = Column(Text, comment='分类描述')
    icon = Column(String(64), comment='图标')

    # 层级结构
    parent_id = Column(String(64), ForeignKey('content_categories.category_id'), comment='父分类ID')
    level = Column(Integer, default=0, comment='层级')
    path = Column(String(512), comment='分类路径')

    # 排序和显示
    sort_order = Column(Integer, default=0, comment='排序顺序')
    is_visible = Column(Boolean, default=True, comment='是否显示')

    # SEO
    meta_title = Column(String(255), comment='SEO标题')
    meta_keywords = Column(String(512), comment='SEO关键词')
    meta_description = Column(Text, comment='SEO描述')

    # 统计
    content_count = Column(Integer, default=0, comment='内容数量')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    parent = relationship("ContentCategory", remote_side=[category_id], backref="children")

    def to_dict(self, include_children=False):
        """转换为字典"""
        result = {
            "category_id": self.category_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "level": self.level,
            "path": self.path,
            "sort_order": self.sort_order,
            "is_visible": self.is_visible,
            "content_count": self.content_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_children:
            result["children"] = [c.to_dict() for c in getattr(self, 'children', [])]

        return result


class ContentTag(Base):
    """内容标签表"""
    __tablename__ = "content_tags"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_id = Column(String(64), unique=True, nullable=False, index=True, comment='标签ID')

    # 基本信息
    name = Column(String(64), unique=True, nullable=False, comment='标签名称')
    slug = Column(String(128), unique=True, nullable=False, comment='URL别名')
    description = Column(Text, comment='标签描述')
    color = Column(String(16), comment='标签颜色')

    # 统计
    usage_count = Column(Integer, default=0, comment='使用次数')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "tag_id": self.tag_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "color": self.color,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Article(Base):
    """文章内容表"""
    __tablename__ = "articles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    article_id = Column(String(64), unique=True, nullable=False, index=True, comment='文章ID')

    # 基本信息
    title = Column(String(255), nullable=False, comment='文章标题')
    slug = Column(String(255), unique=True, nullable=False, comment='URL别名')
    summary = Column(Text, comment='摘要')
    content = Column(Text, nullable=False, comment='文章内容（富文本/Markdown）')
    content_type = Column(String(32), default='markdown', comment='内容类型: markdown, html')

    # 封面图
    cover_image = Column(String(512), comment='封面图URL')

    # 分类和标签
    category_id = Column(String(64), ForeignKey('content_categories.category_id'), comment='分类ID')
    tags = Column(Text, comment='标签列表 (JSON)')

    # 作者
    author_id = Column(String(128), comment='作者ID')
    author_name = Column(String(128), comment='作者名称')

    # 状态
    status = Column(String(32), default='draft', comment='状态: draft, pending, published, rejected, archived')

    # 审批流程
    submitted_at = Column(TIMESTAMP, comment='提交时间')
    reviewed_by = Column(String(128), comment='审核人ID')
    reviewed_at = Column(TIMESTAMP, comment='审核时间')
    rejection_reason = Column(Text, comment='拒绝原因')

    # 发布
    published_at = Column(TIMESTAMP, comment='发布时间')
    published_by = Column(String(128), comment='发布人ID')

    # SEO
    meta_title = Column(String(255), comment='SEO标题')
    meta_keywords = Column(String(512), comment='SEO关键词')
    meta_description = Column(Text, comment='SEO描述')

    # 统计
    view_count = Column(Integer, default=0, comment='浏览次数')
    like_count = Column(Integer, default=0, comment='点赞次数')
    comment_count = Column(Integer, default=0, comment='评论次数')
    share_count = Column(Integer, default=0, comment='分享次数')

    # 设置
    allow_comment = Column(Boolean, default=True, comment='允许评论')
    is_featured = Column(Boolean, default=False, comment='是否精选')
    is_top = Column(Boolean, default=False, comment='是否置顶')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True, comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')

    # 关系
    category = relationship("ContentCategory", backref="articles")
    versions = relationship("ArticleVersion", back_populates="article", cascade="all, delete-orphan")

    def get_tags(self) -> list:
        """获取标签列表"""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list):
        """设置标签列表"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def to_dict(self, include_content=False):
        """转换为字典"""
        result = {
            "article_id": self.article_id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "cover_image": self.cover_image,
            "category_id": self.category_id,
            "tags": self.get_tags(),
            "author_id": self.author_id,
            "author_name": self.author_name,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "allow_comment": self.allow_comment,
            "is_featured": self.is_featured,
            "is_top": self.is_top,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_content:
            result["content"] = self.content

        return result


class ArticleVersion(Base):
    """文章版本历史表"""
    __tablename__ = "article_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_id = Column(String(64), unique=True, nullable=False, comment='版本ID')

    # 关联文章
    article_id = Column(String(64), ForeignKey('articles.article_id', ondelete='CASCADE'), nullable=False, index=True, comment='文章ID')

    # 版本信息
    version_number = Column(Integer, nullable=False, comment='版本号')
    title = Column(String(255), nullable=False, comment='标题')
    content = Column(Text, comment='文章内容')
    summary = Column(Text, comment='摘要')

    # 变更说明
    change_description = Column(Text, comment='变更说明')
    change_type = Column(String(32), comment='变更类型: create, update, minor')

    # 操作人
    created_by = Column(String(128), comment='操作人ID')
    created_by_name = Column(String(128), comment='操作人名称')

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='创建时间')

    # 关系
    article = relationship("Article", back_populates="versions")

    def to_dict(self):
        """转换为字典"""
        return {
            "version_id": self.version_id,
            "article_id": self.article_id,
            "version_number": self.version_number,
            "title": self.title,
            "summary": self.summary,
            "change_description": self.change_description,
            "change_type": self.change_type,
            "created_by": self.created_by,
            "created_by_name": self.created_by_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ContentApproval(Base):
    """内容审批记录表"""
    __tablename__ = "content_approvals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    approval_id = Column(String(64), unique=True, nullable=False, index=True, comment='审批ID')

    # 关联内容
    content_type = Column(String(64), comment='内容类型: article')
    content_id = Column(String(64), comment='内容ID')
    content_title = Column(String(255), comment='内容标题')

    # 提交信息
    submitted_by = Column(String(128), comment='提交人ID')
    submitted_by_name = Column(String(128), comment='提交人名称')
    submitted_at = Column(TIMESTAMP, server_default=func.current_timestamp(), comment='提交时间')

    # 审批流程
    workflow_type = Column(String(64), comment='工作流类型')
    current_step = Column(Integer, default=0, comment='当前步骤')

    # 审批状态
    status = Column(String(32), default='pending', comment='状态: pending, approved, rejected')

    # 审批人
    reviewer_id = Column(String(128), comment='审批人ID')
    reviewer_name = Column(String(128), comment='审批人名称')
    reviewed_at = Column(TIMESTAMP, comment='审批时间')

    # 审批意见
    comment = Column(Text, comment='审批意见')
    rejection_reason = Column(Text, comment='拒绝原因')

    # 时间戳
    completed_at = Column(TIMESTAMP, comment='完成时间')

    def to_dict(self):
        """转换为字典"""
        return {
            "approval_id": self.approval_id,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "content_title": self.content_title,
            "submitted_by": self.submitted_by,
            "submitted_by_name": self.submitted_by_name,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "workflow_type": self.workflow_type,
            "current_step": self.current_step,
            "status": self.status,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "comment": self.comment,
            "rejection_reason": self.rejection_reason,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
