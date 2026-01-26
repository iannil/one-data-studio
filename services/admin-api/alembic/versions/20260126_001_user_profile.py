"""Add user profile and segmentation tables

Revision ID: 001_user_profile
Revises:
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_user_profile'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建用户画像表
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.String(64), nullable=False, comment='画像ID'),
        sa.Column('user_id', sa.String(128), nullable=False, comment='用户ID'),
        sa.Column('username', sa.String(128), comment='用户名'),
        sa.Column('behavior_tags', sa.Text(), comment='行为标签 (JSON)'),
        sa.Column('activity_score', sa.Float(), server_default='0', comment='活跃度分数'),
        sa.Column('segment_id', sa.String(64), comment='所属分群ID'),
        sa.Column('preference_features', sa.JSON(), comment='偏好特征 (JSON)'),
        sa.Column('login_count', sa.Integer(), server_default='0', comment='登录次数'),
        sa.Column('last_login_at', sa.TIMESTAMP(), comment='最后登录时间'),
        sa.Column('login_days', sa.Integer(), server_default='0', comment='活跃天数'),
        sa.Column('module_usage', sa.Text(), comment='模块使用统计 (JSON)'),
        sa.Column('peak_hours', sa.Text(), comment='活跃时段 (JSON)'),
        sa.Column('peak_days', sa.Text(), comment='活跃星期 (JSON)'),
        sa.Column('query_count', sa.Integer(), server_default='0', comment='查询次数'),
        sa.Column('export_count', sa.Integer(), server_default='0', comment='导出次数'),
        sa.Column('create_count', sa.Integer(), server_default='0', comment='创建次数'),
        sa.Column('is_risk_user', sa.Boolean(), server_default='0', comment='是否风险用户'),
        sa.Column('risk_reason', sa.String(255), comment='风险原因'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('last_analyzed_at', sa.TIMESTAMP(), comment='最后分析时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['segment_id'], ['user_segments.segment_id'], ondelete='SET NULL'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_user_profiles_profile_id', 'user_profiles', ['profile_id'], unique=True)
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'])
    op.create_index('ix_user_profiles_segment_id', 'user_profiles', ['segment_id'])
    op.create_index('ix_user_profiles_activity_score', 'user_profiles', ['activity_score'])

    # 创建用户分群表
    op.create_table(
        'user_segments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('segment_id', sa.String(64), nullable=False, comment='分群ID'),
        sa.Column('segment_name', sa.String(128), nullable=False, comment='分群名称'),
        sa.Column('segment_type', sa.String(32), nullable=False, comment='分群类型'),
        sa.Column('description', sa.Text(), comment='分群描述'),
        sa.Column('criteria', sa.JSON(), comment='分群标准 (JSON)'),
        sa.Column('characteristics', sa.JSON(), comment='分群特征 (JSON)'),
        sa.Column('user_count', sa.Integer(), server_default='0', comment='用户数量'),
        sa.Column('strategy', sa.Text(), comment='运营策略建议'),
        sa.Column('is_active', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('is_system', sa.Boolean(), server_default='0', comment='是否系统预置'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('last_rebuilt_at', sa.TIMESTAMP(), comment='最后重建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_user_segments_segment_id', 'user_segments', ['segment_id'], unique=True)
    op.create_index('ix_user_segments_segment_type', 'user_segments', ['segment_type'])

    # 创建用户标签定义表
    op.create_table(
        'user_tags',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tag_id', sa.String(64), nullable=False, comment='标签ID'),
        sa.Column('tag_name', sa.String(64), nullable=False, unique=True, comment='标签名称'),
        sa.Column('tag_category', sa.String(32), comment='标签分类'),
        sa.Column('display_name', sa.String(128), comment='显示名称'),
        sa.Column('description', sa.Text(), comment='标签描述'),
        sa.Column('rules', sa.JSON(), comment='标签规则 (JSON)'),
        sa.Column('color', sa.String(16), comment='标签颜色'),
        sa.Column('icon', sa.String(32), comment='标签图标'),
        sa.Column('priority', sa.Integer(), server_default='0', comment='优先级'),
        sa.Column('is_auto', sa.Boolean(), server_default='0', comment='是否自动打标'),
        sa.Column('update_frequency', sa.String(32), comment='更新频率'),
        sa.Column('user_count', sa.Integer(), server_default='0', comment='拥有此标签的用户数'),
        sa.Column('is_active', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_user_tags_tag_id', 'user_tags', ['tag_id'], unique=True)
    op.create_index('ix_user_tags_tag_name', 'user_tags', ['tag_name'], unique=True)

    # 创建行为异常记录表
    op.create_table(
        'behavior_anomalies',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('anomaly_id', sa.String(64), nullable=False, comment='异常ID'),
        sa.Column('user_id', sa.String(128), nullable=False, comment='用户ID'),
        sa.Column('username', sa.String(128), comment='用户名'),
        sa.Column('anomaly_type', sa.String(32), nullable=False, comment='异常类型'),
        sa.Column('severity', sa.String(16), server_default='medium', comment='严重程度'),
        sa.Column('description', sa.Text(), comment='异常描述'),
        sa.Column('details', sa.JSON(), comment='异常详情'),
        sa.Column('status', sa.String(16), server_default='open', comment='状态'),
        sa.Column('handled_by', sa.String(128), comment='处理人'),
        sa.Column('handled_at', sa.TIMESTAMP(), comment='处理时间'),
        sa.Column('resolution', sa.Text(), comment='处理结果'),
        sa.Column('detected_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='检测时间'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_behavior_anomalies_anomaly_id', 'behavior_anomalies', ['anomaly_id'], unique=True)
    op.create_index('ix_behavior_anomalies_user_id', 'behavior_anomalies', ['user_id'])
    op.create_index('ix_behavior_anomalies_detected_at', 'behavior_anomalies', ['detected_at'])
    op.create_index('ix_behavior_anomalies_status', 'behavior_anomalies', ['status'])


def downgrade() -> None:
    op.drop_table('behavior_anomalies')
    op.drop_table('user_tags')
    op.drop_table('user_segments')
    op.drop_table('user_profiles')
