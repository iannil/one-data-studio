"""Content management and API management tables

Revision ID: 20260126_002
Revises: 20260126_001
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '20260126_002'
down_revision = '20260126_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== 内容分类表 ====================
    op.create_table(
        'content_categories',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('category_id', sa.String(length=64), nullable=False, comment='分类ID'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='分类名称'),
        sa.Column('slug', sa.String(length=128), nullable=False, comment='URL别名'),
        sa.Column('description', sa.Text(), comment='分类描述'),
        sa.Column('icon', sa.String(length=64), comment='图标'),
        sa.Column('parent_id', sa.String(length=64), comment='父分类ID'),
        sa.Column('level', sa.Integer(), default=0, comment='层级'),
        sa.Column('path', sa.String(length=512), comment='分类路径'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序顺序'),
        sa.Column('is_visible', sa.Boolean(), default=True, comment='是否显示'),
        sa.Column('meta_title', sa.String(length=255), comment='SEO标题'),
        sa.Column('meta_keywords', sa.String(length=512), comment='SEO关键词'),
        sa.Column('meta_description', sa.Text(), comment='SEO描述'),
        sa.Column('content_count', sa.Integer(), default=0, comment='内容数量'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_content_categories_category_id', 'content_categories', ['category_id'], unique=True)
    op.create_index('ix_content_categories_slug', 'content_categories', ['slug'], unique=True)
    op.create_foreign_key('fk_content_categories_parent', 'content_categories', 'content_categories', ['parent_id'], ['category_id'])

    # ==================== 内容标签表 ====================
    op.create_table(
        'content_tags',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('tag_id', sa.String(length=64), nullable=False, comment='标签ID'),
        sa.Column('name', sa.String(length=64), nullable=False, comment='标签名称'),
        sa.Column('slug', sa.String(length=128), nullable=False, comment='URL别名'),
        sa.Column('description', sa.Text(), comment='标签描述'),
        sa.Column('color', sa.String(length=16), comment='标签颜色'),
        sa.Column('usage_count', sa.Integer(), default=0, comment='使用次数'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_content_tags_tag_id', 'content_tags', ['tag_id'], unique=True)
    op.create_index('ix_content_tags_name', 'content_tags', ['name'], unique=True)
    op.create_index('ix_content_tags_slug', 'content_tags', ['slug'], unique=True)

    # ==================== 文章内容表 ====================
    op.create_table(
        'articles',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('article_id', sa.String(length=64), nullable=False, comment='文章ID'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='文章标题'),
        sa.Column('slug', sa.String(length=255), nullable=False, comment='URL别名'),
        sa.Column('summary', sa.Text(), comment='摘要'),
        sa.Column('content', sa.Text(), nullable=False, comment='文章内容（富文本/Markdown）'),
        sa.Column('content_type', sa.String(length=32), default='markdown', comment='内容类型: markdown, html'),
        sa.Column('cover_image', sa.String(length=512), comment='封面图URL'),
        sa.Column('category_id', sa.String(length=64), comment='分类ID'),
        sa.Column('tags', sa.Text(), comment='标签列表 (JSON)'),
        sa.Column('author_id', sa.String(length=128), comment='作者ID'),
        sa.Column('author_name', sa.String(length=128), comment='作者名称'),
        sa.Column('status', sa.String(length=32), default='draft', comment='状态: draft, pending, published, rejected, archived'),
        sa.Column('submitted_at', sa.TIMESTAMP(), comment='提交时间'),
        sa.Column('reviewed_by', sa.String(length=128), comment='审核人ID'),
        sa.Column('reviewed_at', sa.TIMESTAMP(), comment='审核时间'),
        sa.Column('rejection_reason', sa.Text(), comment='拒绝原因'),
        sa.Column('published_at', sa.TIMESTAMP(), comment='发布时间'),
        sa.Column('published_by', sa.String(length=128), comment='发布人ID'),
        sa.Column('meta_title', sa.String(length=255), comment='SEO标题'),
        sa.Column('meta_keywords', sa.String(length=512), comment='SEO关键词'),
        sa.Column('meta_description', sa.Text(), comment='SEO描述'),
        sa.Column('view_count', sa.Integer(), default=0, comment='浏览次数'),
        sa.Column('like_count', sa.Integer(), default=0, comment='点赞次数'),
        sa.Column('comment_count', sa.Integer(), default=0, comment='评论次数'),
        sa.Column('share_count', sa.Integer(), default=0, comment='分享次数'),
        sa.Column('allow_comment', sa.Boolean(), default=True, comment='允许评论'),
        sa.Column('is_featured', sa.Boolean(), default=False, comment='是否精选'),
        sa.Column('is_top', sa.Boolean(), default=False, comment='是否置顶'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_articles_article_id', 'articles', ['article_id'], unique=True)
    op.create_index('ix_articles_slug', 'articles', ['slug'], unique=True)
    op.create_index('ix_articles_category_id', 'articles', ['category_id'])
    op.create_index('ix_articles_status', 'articles', ['status'])
    op.create_index('ix_articles_created_at', 'articles', ['created_at'])
    op.create_foreign_key('fk_articles_category', 'articles', 'content_categories', ['category_id'], ['category_id'])

    # ==================== 文章版本历史表 ====================
    op.create_table(
        'article_versions',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('version_id', sa.String(length=64), nullable=False, comment='版本ID'),
        sa.Column('article_id', sa.String(length=64), nullable=False, comment='文章ID'),
        sa.Column('version_number', sa.Integer(), nullable=False, comment='版本号'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='标题'),
        sa.Column('content', sa.Text(), comment='文章内容'),
        sa.Column('summary', sa.Text(), comment='摘要'),
        sa.Column('change_description', sa.Text(), comment='变更说明'),
        sa.Column('change_type', sa.String(length=32), comment='变更类型: create, update, minor'),
        sa.Column('created_by', sa.String(length=128), comment='操作人ID'),
        sa.Column('created_by_name', sa.String(length=128), comment='操作人名称'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_article_versions_version_id', 'article_versions', ['version_id'], unique=True)
    op.create_index('ix_article_versions_article_id', 'article_versions', ['article_id'])
    op.create_foreign_key('fk_article_versions_article', 'article_versions', 'articles', ['article_id'], ['article_id'], ondelete='CASCADE')

    # ==================== 内容审批记录表 ====================
    op.create_table(
        'content_approvals',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('approval_id', sa.String(length=64), nullable=False, comment='审批ID'),
        sa.Column('content_type', sa.String(length=64), comment='内容类型: article'),
        sa.Column('content_id', sa.String(length=64), comment='内容ID'),
        sa.Column('content_title', sa.String(length=255), comment='内容标题'),
        sa.Column('submitted_by', sa.String(length=128), comment='提交人ID'),
        sa.Column('submitted_by_name', sa.String(length=128), comment='提交人名称'),
        sa.Column('submitted_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='提交时间'),
        sa.Column('workflow_type', sa.String(length=64), comment='工作流类型'),
        sa.Column('current_step', sa.Integer(), default=0, comment='当前步骤'),
        sa.Column('status', sa.String(length=32), default='pending', comment='状态: pending, approved, rejected'),
        sa.Column('reviewer_id', sa.String(length=128), comment='审批人ID'),
        sa.Column('reviewer_name', sa.String(length=128), comment='审批人名称'),
        sa.Column('reviewed_at', sa.TIMESTAMP(), comment='审批时间'),
        sa.Column('comment', sa.Text(), comment='审批意见'),
        sa.Column('rejection_reason', sa.Text(), comment='拒绝原因'),
        sa.Column('completed_at', sa.TIMESTAMP(), comment='完成时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_content_approvals_approval_id', 'content_approvals', ['approval_id'], unique=True)
    op.create_index('ix_content_approvals_status', 'content_approvals', ['status'])
    op.create_index('ix_content_approvals_submitted_at', 'content_approvals', ['submitted_at'])

    # ==================== API端点表 ====================
    op.create_table(
        'api_endpoints',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('endpoint_id', sa.String(length=64), nullable=False, comment='端点ID'),
        sa.Column('path', sa.String(length=512), nullable=False, comment='API路径'),
        sa.Column('method', sa.String(length=16), nullable=False, comment='HTTP方法'),
        sa.Column('service', sa.String(length=64), comment='服务名称'),
        sa.Column('blueprint', sa.String(length=64), comment='蓝图名称'),
        sa.Column('endpoint_name', sa.String(length=255), comment='端点名称'),
        sa.Column('description', sa.Text(), comment='API描述'),
        sa.Column('summary', sa.Text(), comment='简要说明'),
        sa.Column('request_schema', sa.JSON(), comment='请求模式 (OpenAPI)'),
        sa.Column('response_schema', sa.JSON(), comment='响应模式 (OpenAPI)'),
        sa.Column('parameters', sa.JSON(), comment='路径参数定义'),
        sa.Column('query_params', sa.JSON(), comment='查询参数定义'),
        sa.Column('body_params', sa.JSON(), comment='请求体参数定义'),
        sa.Column('tags', sa.JSON(), comment='标签列表'),
        sa.Column('requires_auth', sa.Boolean(), default=True, comment='是否需要认证'),
        sa.Column('required_permissions', sa.JSON(), comment='所需权限列表'),
        sa.Column('call_count', sa.Integer(), default=0, comment='调用次数'),
        sa.Column('error_count', sa.Integer(), default=0, comment='错误次数'),
        sa.Column('avg_duration_ms', sa.Integer(), comment='平均耗时（毫秒）'),
        sa.Column('first_call', sa.TIMESTAMP(), comment='首次调用时间'),
        sa.Column('last_call', sa.TIMESTAMP(), comment='最后调用时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_api_endpoints_endpoint_id', 'api_endpoints', ['endpoint_id'], unique=True)
    op.create_index('ix_api_endpoints_path_method', 'api_endpoints', ['path', 'method'])
    op.create_index('ix_api_endpoints_service', 'api_endpoints', ['service'])

    # ==================== API调用日志表 ====================
    op.create_table(
        'api_call_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('call_id', sa.String(length=64), nullable=False, comment='调用ID'),
        sa.Column('path', sa.String(length=512), nullable=False, comment='请求路径'),
        sa.Column('method', sa.String(length=16), nullable=False, comment='HTTP方法'),
        sa.Column('query_params', sa.Text(), comment='查询参数'),
        sa.Column('request_body', sa.Text(), comment='请求体'),
        sa.Column('request_headers', sa.Text(), comment='请求头'),
        sa.Column('user_id', sa.String(length=128), comment='用户ID'),
        sa.Column('username', sa.String(length=128), comment='用户名'),
        sa.Column('status_code', sa.Integer(), nullable=False, comment='响应状态码'),
        sa.Column('response_body', sa.Text(), comment='响应体'),
        sa.Column('error_message', sa.Text(), comment='错误信息'),
        sa.Column('duration_ms', sa.Integer(), comment='耗时（毫秒）'),
        sa.Column('client_ip', sa.String(length=64), comment='客户端IP'),
        sa.Column('user_agent', sa.String(length=512), comment='User-Agent'),
        sa.Column('extra_data', sa.Text(), comment='额外数据 (JSON)'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_api_call_logs_call_id', 'api_call_logs', ['call_id'], unique=True)
    op.create_index('ix_api_call_logs_path', 'api_call_logs', ['path'])
    op.create_index('ix_api_call_logs_user_id', 'api_call_logs', ['user_id'])
    op.create_index('ix_api_call_logs_status_code', 'api_call_logs', ['status_code'])
    op.create_index('ix_api_call_logs_created_at', 'api_call_logs', ['created_at'])


def downgrade():
    op.drop_table('api_call_logs')
    op.drop_table('api_endpoints')
    op.drop_table('content_approvals')
    op.drop_table('article_versions')
    op.drop_table('articles')
    op.drop_table('content_tags')
    op.drop_table('content_categories')
