"""
统一内容管理服务
支持文章、公告、文档等内容管理
"""

import logging
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ==================== 内容类型定义 ====================

class ContentType(str, Enum):
    """内容类型"""
    ARTICLE = "article"         # 文章
    ANNOUNCEMENT = "announcement"  # 公告
    DOCUMENT = "document"       # 文档
    TUTORIAL = "tutorial"       # 教程
    FAQ = "faq"                # 常见问题
    NEWS = "news"              # 新闻


class ContentStatus(str, Enum):
    """内容状态"""
    DRAFT = "draft"            # 草稿
    REVIEWING = "reviewing"    # 审核中
    PUBLISHED = "published"    # 已发布
    ARCHIVED = "archived"      # 已归档


# ==================== 内容实体 ====================

@dataclass
class ContentCategory:
    """内容分类"""
    category_id: str
    name: str
    description: str
    parent_id: Optional[str] = None
    icon: str = ""
    sort_order: int = 0
    enabled: bool = True


@dataclass
class ContentTag:
    """内容标签"""
    tag_id: str
    name: str
    color: str = "#1890ff"
    usage_count: int = 0


@dataclass
class ContentArticle:
    """内容文章"""
    content_id: str
    title: str
    summary: str
    content: str
    content_type: str
    status: str
    category_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    author_id: str = ""
    author_name: str = ""
    cover_image: str = ""
    featured: bool = False
    allow_comment: bool = True
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "content_id": self.content_id,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "content_type": self.content_type,
            "status": self.status,
            "category_id": self.category_id,
            "tags": self.tags,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "cover_image": self.cover_image,
            "featured": self.featured,
            "allow_comment": self.allow_comment,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass
class ContentComment:
    """内容评论"""
    comment_id: str
    content_id: str
    parent_id: Optional[str] = None
    user_id: str = ""
    user_name: str = ""
    user_avatar: str = ""
    content: str = ""
    like_count: int = 0
    status: str = "approved"  # pending, approved, rejected
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "comment_id": self.comment_id,
            "content_id": self.content_id,
            "parent_id": self.parent_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_avatar": self.user_avatar,
            "content": self.content,
            "like_count": self.like_count,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ContentAttachment:
    """内容附件"""
    attachment_id: str
    content_id: str
    name: str
    file_type: str
    file_size: int
    file_url: str
    download_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


# ==================== 内容管理服务 ====================

class ContentService:
    """统一内容管理服务"""

    def __init__(self):
        # 内存存储，实际应使用数据库
        self._articles: Dict[str, ContentArticle] = {}
        self._categories: Dict[str, ContentCategory] = {}
        self._tags: Dict[str, ContentTag] = {}
        self._comments: Dict[str, ContentComment] = {}
        self._attachments: Dict[str, ContentAttachment] = {}

        # 初始化默认数据
        self._init_default_categories()
        self._init_default_tags()
        self._init_default_articles()

    def _init_default_categories(self):
        """初始化默认分类"""
        default_categories = [
            ContentCategory("cat_001", "产品公告", "系统相关公告", icon="📢", sort_order=1),
            ContentCategory("cat_002", "使用指南", "产品使用教程和指南", icon="📖", sort_order=2),
            ContentCategory("cat_003", "常见问题", "用户常见问题解答", icon="❓", sort_order=3),
            ContentCategory("cat_004", "更新日志", "产品更新和版本记录", icon="📝", sort_order=4),
            ContentCategory("cat_005", "技术文档", "开发和技术文档", icon="🔧", sort_order=5),
        ]
        for cat in default_categories:
            self._categories[cat.category_id] = cat

    def _init_default_tags(self):
        """初始化默认标签"""
        default_tags = [
            ContentTag("tag_001", "重要", "#ff4d4f", 5),
            ContentTag("tag_002", "新手", "#52c41a", 8),
            ContentTag("tag_003", "高级", "#1890ff", 3),
            ContentTag("tag_004", "故障", "#faad14", 2),
            ContentTag("tag_005", "新功能", "#722ed1", 4),
        ]
        for tag in default_tags:
            self._tags[tag.tag_id] = tag

    def _init_default_articles(self):
        """初始化默认文章"""
        now = datetime.now()
        default_articles = [
            ContentArticle(
                content_id="art_001",
                title="欢迎使用 ONE-DATA-STUDIO",
                summary="企业级 DataOps + MLOps + LLMOps 融合平台",
                content="<p>欢迎使用 ONE-DATA-STUDIO！</p><p>这是一个将三个 AI 基础设施整合为统一的智能数据平台...</p>",
                content_type=ContentType.ARTICLE.value,
                status=ContentStatus.PUBLISHED.value,
                category_id="cat_001",
                tags=["tag_001", "tag_005"],
                author_id="system",
                author_name="系统管理员",
                featured=True,
                published_at=now,
                created_at=now - timedelta(days=30),
            ),
            ContentArticle(
                content_id="art_002",
                title="如何创建第一个数据管道",
                summary="快速入门指南：创建您的第一个数据处理管道",
                content="<p>本指南将帮助您快速上手 ONE-DATA-STUDIO...</p>",
                content_type=ContentType.TUTORIAL.value,
                status=ContentStatus.PUBLISHED.value,
                category_id="cat_002",
                tags=["tag_002"],
                author_id="system",
                author_name="系统管理员",
                view_count=1250,
                like_count=45,
                published_at=now - timedelta(days=15),
                created_at=now - timedelta(days=15),
            ),
            ContentArticle(
                content_id="art_003",
                title="v2.0.0 版本更新公告",
                summary="新增统一门户、通知管理等多项功能",
                content="<p>v2.0.0 版本带来了以下更新...</p>",
                content_type=ContentType.ANNOUNCEMENT.value,
                status=ContentStatus.PUBLISHED.value,
                category_id="cat_004",
                tags=["tag_001", "tag_005"],
                author_id="system",
                author_name="系统管理员",
                featured=True,
                view_count=3420,
                like_count=128,
                published_at=now - timedelta(days=7),
                created_at=now - timedelta(days=7),
            ),
        ]
        for art in default_articles:
            self._articles[art.content_id] = art

    # ==================== 内容 CRUD ====================

    def create_article(
        self,
        title: str,
        content: str,
        content_type: str,
        author_id: str,
        author_name: str,
        summary: str = "",
        category_id: str = None,
        tags: List[str] = None,
        cover_image: str = "",
        featured: bool = False,
        allow_comment: bool = True,
        status: str = ContentStatus.DRAFT.value,
        metadata: Dict[str, Any] = None,
    ) -> ContentArticle:
        """创建文章"""
        article = ContentArticle(
            content_id=f"art_{secrets.token_hex(8)}",
            title=title,
            summary=summary or (content[:100] + "..." if len(content) > 100 else content),
            content=content,
            content_type=content_type,
            status=status,
            category_id=category_id,
            tags=tags or [],
            author_id=author_id,
            author_name=author_name,
            cover_image=cover_image,
            featured=featured,
            allow_comment=allow_comment,
            metadata=metadata or {},
        )
        self._articles[article.content_id] = article

        # 更新标签使用计数
        for tag_id in tags or []:
            if tag_id in self._tags:
                self._tags[tag_id].usage_count += 1

        return article

    def get_article(self, content_id: str) -> Optional[ContentArticle]:
        """获取文章详情"""
        return self._articles.get(content_id)

    def update_article(
        self,
        content_id: str,
        **updates
    ) -> Optional[ContentArticle]:
        """更新文章"""
        article = self._articles.get(content_id)
        if not article:
            return None

        for key, value in updates.items():
            if hasattr(article, key):
                setattr(article, key, value)

        article.updated_at = datetime.now()
        return article

    def delete_article(self, content_id: str) -> bool:
        """删除文章"""
        if content_id in self._articles:
            # 删除关联评论
            self._comments = {
                k: v for k, v in self._comments.items()
                if v.content_id != content_id
            }
            # 删除关联附件
            self._attachments = {
                k: v for k, v in self._attachments.items()
                if v.content_id != content_id
            }
            del self._articles[content_id]
            return True
        return False

    def list_articles(
        self,
        content_type: str = None,
        status: str = None,
        category_id: str = None,
        tag_id: str = None,
        author_id: str = None,
        featured: bool = None,
        keyword: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ContentArticle], int]:
        """列出文章"""
        articles = list(self._articles.values())

        # 筛选
        if content_type:
            articles = [a for a in articles if a.content_type == content_type]
        if status:
            articles = [a for a in articles if a.status == status]
        if category_id:
            articles = [a for a in articles if a.category_id == category_id]
        if tag_id:
            articles = [a for a in articles if tag_id in a.tags]
        if author_id:
            articles = [a for a in articles if a.author_id == author_id]
        if featured is not None:
            articles = [a for a in articles if a.featured == featured]
        if keyword:
            articles = [
                a for a in articles
                if keyword.lower() in a.title.lower() or keyword.lower() in a.summary.lower()
            ]

        # 排序（最新的在前）
        articles.sort(key=lambda a: a.created_at, reverse=True)

        total = len(articles)
        return articles[offset:offset + limit], total

    def publish_article(self, content_id: str) -> Optional[ContentArticle]:
        """发布文章"""
        article = self._articles.get(content_id)
        if not article:
            return None
        article.status = ContentStatus.PUBLISHED.value
        article.published_at = datetime.now()
        article.updated_at = datetime.now()
        return article

    def archive_article(self, content_id: str) -> Optional[ContentArticle]:
        """归档文章"""
        article = self._articles.get(content_id)
        if not article:
            return None
        article.status = ContentStatus.ARCHIVED.value
        article.updated_at = datetime.now()
        return article

    def increment_view_count(self, content_id: str) -> bool:
        """增加阅读数"""
        article = self._articles.get(content_id)
        if article:
            article.view_count += 1
            return True
        return False

    def toggle_like(self, content_id: str, user_id: str) -> bool:
        """切换点赞状态"""
        # 简化处理，实际需要记录用户点赞状态
        article = self._articles.get(content_id)
        if article:
            article.like_count += 1
            return True
        return False

    # ==================== 分类管理 ====================

    def create_category(
        self,
        name: str,
        description: str = "",
        parent_id: str = None,
        icon: str = "",
        sort_order: int = 0,
    ) -> ContentCategory:
        """创建分类"""
        category = ContentCategory(
            category_id=f"cat_{secrets.token_hex(8)}",
            name=name,
            description=description,
            parent_id=parent_id,
            icon=icon,
            sort_order=sort_order,
        )
        self._categories[category.category_id] = category
        return category

    def get_category(self, category_id: str) -> Optional[ContentCategory]:
        """获取分类"""
        return self._categories.get(category_id)

    def list_categories(self, enabled_only: bool = False) -> List[ContentCategory]:
        """列出分类"""
        categories = list(self._categories.values())
        if enabled_only:
            categories = [c for c in categories if c.enabled]
        categories.sort(key=lambda c: c.sort_order)
        return categories

    def update_category(self, category_id: str, **updates) -> Optional[ContentCategory]:
        """更新分类"""
        category = self._categories.get(category_id)
        if category:
            for key, value in updates.items():
                if hasattr(category, key):
                    setattr(category, key, value)
        return category

    def delete_category(self, category_id: str) -> bool:
        """删除分类"""
        if category_id in self._categories:
            del self._categories[category_id]
            return True
        return False

    # ==================== 标签管理 ====================

    def create_tag(
        self,
        name: str,
        color: str = "#1890ff",
    ) -> ContentTag:
        """创建标签"""
        tag = ContentTag(
            tag_id=f"tag_{secrets.token_hex(8)}",
            name=name,
            color=color,
        )
        self._tags[tag.tag_id] = tag
        return tag

    def get_tag(self, tag_id: str) -> Optional[ContentTag]:
        """获取标签"""
        return self._tags.get(tag_id)

    def list_tags(self) -> List[ContentTag]:
        """列出标签"""
        tags = list(self._tags.values())
        tags.sort(key=lambda t: t.usage_count, reverse=True)
        return tags

    def update_tag(self, tag_id: str, **updates) -> Optional[ContentTag]:
        """更新标签"""
        tag = self._tags.get(tag_id)
        if tag:
            for key, value in updates.items():
                if hasattr(tag, key):
                    setattr(tag, key, value)
        return tag

    def delete_tag(self, tag_id: str) -> bool:
        """删除标签"""
        if tag_id in self._tags:
            del self._tags[tag_id]
            # 从文章中移除该标签
            for article in self._articles.values():
                if tag_id in article.tags:
                    article.tags.remove(tag_id)
            return True
        return False

    # ==================== 评论管理 ====================

    def create_comment(
        self,
        content_id: str,
        user_id: str,
        user_name: str,
        content: str,
        parent_id: str = None,
        user_avatar: str = "",
    ) -> ContentComment:
        """创建评论"""
        comment = ContentComment(
            comment_id=f"cmt_{secrets.token_hex(8)}",
            content_id=content_id,
            parent_id=parent_id,
            user_id=user_id,
            user_name=user_name,
            user_avatar=user_avatar,
            content=content,
        )
        self._comments[comment.comment_id] = comment

        # 更新文章评论数
        article = self._articles.get(content_id)
        if article:
            article.comment_count += 1

        return comment

    def get_comment(self, comment_id: str) -> Optional[ContentComment]:
        """获取评论"""
        return self._comments.get(comment_id)

    def list_comments(
        self,
        content_id: str = None,
        status: str = "approved",
        limit: int = 50,
    ) -> List[ContentComment]:
        """列出评论"""
        comments = list(self._comments.values())

        if content_id:
            comments = [c for c in comments if c.content_id == content_id]
        if status:
            comments = [c for c in comments if c.status == status]

        comments.sort(key=lambda c: c.created_at)
        return comments[:limit]

    def approve_comment(self, comment_id: str) -> bool:
        """审核通过评论"""
        comment = self._comments.get(comment_id)
        if comment:
            comment.status = "approved"
            return True
        return False

    def reject_comment(self, comment_id: str) -> bool:
        """拒绝评论"""
        comment = self._comments.get(comment_id)
        if comment:
            comment.status = "rejected"
            return True
        return False

    def delete_comment(self, comment_id: str) -> bool:
        """删除评论"""
        if comment_id in self._comments:
            comment = self._comments[comment_id]
            # 更新文章评论数
            article = self._articles.get(comment.content_id)
            if article and article.comment_count > 0:
                article.comment_count -= 1
            del self._comments[comment_id]
            return True
        return False

    # ==================== 附件管理 ====================

    def create_attachment(
        self,
        content_id: str,
        name: str,
        file_type: str,
        file_size: int,
        file_url: str,
    ) -> ContentAttachment:
        """创建附件记录"""
        attachment = ContentAttachment(
            attachment_id=f"att_{secrets.token_hex(8)}",
            content_id=content_id,
            name=name,
            file_type=file_type,
            file_size=file_size,
            file_url=file_url,
        )
        self._attachments[attachment.attachment_id] = attachment
        return attachment

    def list_attachments(self, content_id: str) -> List[ContentAttachment]:
        """列出附件"""
        return [a for a in self._attachments.values() if a.content_id == content_id]

    def delete_attachment(self, attachment_id: str) -> bool:
        """删除附件"""
        if attachment_id in self._attachments:
            del self._attachments[attachment_id]
            return True
        return False

    # ==================== 搜索 ====================

    def search(
        self,
        query: str,
        content_type: str = None,
        limit: int = 20,
    ) -> List[ContentArticle]:
        """全文搜索"""
        articles = list(self._articles.values())

        if content_type:
            articles = [a for a in articles if a.content_type == content_type]

        # 简单的关键词匹配
        query_lower = query.lower()
        results = [
            a for a in articles
            if query_lower in a.title.lower() or
               query_lower in a.summary.lower() or
               query_lower in a.content.lower()
        ]

        # 按相关性排序（标题匹配优先）
        results.sort(
            key=lambda a: (
                query_lower not in a.title.lower(),
                query_lower not in a.summary.lower(),
            )
        )

        return results[:limit]

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取内容统计"""
        articles = list(self._articles.values())

        status_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for article in articles:
            status_counts[article.status] = status_counts.get(article.status, 0) + 1
            type_counts[article.content_type] = type_counts.get(article.content_type, 0) + 1

        return {
            "total_articles": len(articles),
            "total_categories": len(self._categories),
            "total_tags": len(self._tags),
            "total_comments": len(self._comments),
            "total_views": sum(a.view_count for a in articles),
            "total_likes": sum(a.like_count for a in articles),
            "status_counts": status_counts,
            "type_counts": type_counts,
            "featured_count": sum(1 for a in articles if a.featured),
        }


# 创建全局服务实例
_content_service = None


def get_content_service() -> ContentService:
    """获取内容管理服务实例"""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service
