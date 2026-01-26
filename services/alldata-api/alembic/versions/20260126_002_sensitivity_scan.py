"""Add sensitivity scan tables

Revision ID: 002_sensitivity_scan
Revises: 001_initial
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_sensitivity_scan'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建敏感数据扫描任务表
    op.create_table(
        'sensitivity_scan_tasks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.String(64), nullable=False, comment='扫描任务ID'),
        sa.Column('target_type', sa.String(32), nullable=False, comment='扫描目标类型'),
        sa.Column('target_id', sa.String(128), comment='目标ID'),
        sa.Column('target_name', sa.String(255), comment='目标名称'),
        sa.Column('scan_mode', sa.String(32), server_default='full', comment='扫描模式'),
        sa.Column('sample_rate', sa.Integer(), server_default='100', comment='采样率'),
        sa.Column('confidence_threshold', sa.Integer(), server_default='70', comment='置信度阈值'),
        sa.Column('databases', sa.Text(), comment='扫描的数据库列表 (JSON)'),
        sa.Column('tables', sa.Text(), comment='扫描的表列表 (JSON)'),
        sa.Column('exclude_patterns', sa.Text(), comment='排除的表/列模式 (JSON)'),
        sa.Column('status', sa.String(32), server_default='pending', comment='状态'),
        sa.Column('progress', sa.Integer(), server_default='0', comment='进度百分比'),
        sa.Column('total_columns', sa.Integer(), server_default='0', comment='总列数'),
        sa.Column('scanned_columns', sa.Integer(), server_default='0', comment='已扫描列数'),
        sa.Column('sensitive_found', sa.Integer(), server_default='0', comment='发现敏感字段数'),
        sa.Column('pii_count', sa.Integer(), server_default='0', comment='PII类型数量'),
        sa.Column('financial_count', sa.Integer(), server_default='0', comment='财务类型数量'),
        sa.Column('health_count', sa.Integer(), server_default='0', comment='健康类型数量'),
        sa.Column('credential_count', sa.Integer(), server_default='0', comment='凭证类型数量'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('started_at', sa.TIMESTAMP(), comment='开始时间'),
        sa.Column('completed_at', sa.TIMESTAMP(), comment='完成时间'),
        sa.Column('estimated_duration', sa.Integer(), comment='预估耗时（秒）'),
        sa.Column('created_by', sa.String(128), comment='创建者'),
        sa.Column('error_message', sa.Text(), comment='错误信息'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_sensitivity_scan_tasks_task_id', 'sensitivity_scan_tasks', ['task_id'], unique=True)
    op.create_index('ix_sensitivity_scan_tasks_status', 'sensitivity_scan_tasks', ['status'])

    # 创建敏感数据扫描结果表
    op.create_table(
        'sensitivity_scan_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('result_id', sa.String(64), nullable=False, comment='结果ID'),
        sa.Column('task_id', sa.String(64), nullable=False, comment='任务ID'),
        sa.Column('database_name', sa.String(128), comment='数据库名'),
        sa.Column('table_name', sa.String(128), comment='表名'),
        sa.Column('column_name', sa.String(128), nullable=False, comment='列名'),
        sa.Column('sensitivity_type', sa.String(64), comment='敏感类型'),
        sa.Column('sensitivity_sub_type', sa.String(64), comment='敏感子类型'),
        sa.Column('sensitivity_level', sa.String(32), comment='敏感级别'),
        sa.Column('confidence', sa.Integer(), comment='置信度'),
        sa.Column('matched_pattern', sa.String(255), comment='匹配的模式'),
        sa.Column('sample_values', sa.Text(), comment='样本值 (JSON)'),
        sa.Column('verified', sa.Boolean(), server_default='0', comment='是否已人工校验'),
        sa.Column('verified_by', sa.String(128), comment='校验人'),
        sa.Column('verified_at', sa.TIMESTAMP(), comment='校验时间'),
        sa.Column('verified_result', sa.String(16), comment='校验结果'),
        sa.Column('original_type', sa.String(64), comment='原始识别类型'),
        sa.Column('original_level', sa.String(32), comment='原始敏感级别'),
        sa.Column('original_confidence', sa.Integer(), comment='原始置信度'),
        sa.Column('masking_strategy', sa.String(64), comment='推荐脱敏策略'),
        sa.Column('is_masked', sa.Boolean(), server_default='0', comment='是否已应用脱敏'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['sensitivity_scan_tasks.task_id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_sensitivity_scan_results_result_id', 'sensitivity_scan_results', ['result_id'], unique=True)
    op.create_index('ix_sensitivity_scan_results_task_id', 'sensitivity_scan_results', ['task_id'])

    # 创建敏感数据模式库表
    op.create_table(
        'sensitivity_patterns',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('pattern_id', sa.String(64), nullable=False, comment='模式ID'),
        sa.Column('category', sa.String(64), nullable=False, comment='分类'),
        sa.Column('sub_type', sa.String(64), nullable=False, comment='子类型'),
        sa.Column('name', sa.String(128), nullable=False, comment='模式名称'),
        sa.Column('pattern_type', sa.String(32), server_default='regex', comment='模式类型'),
        sa.Column('pattern', sa.String(512), comment='正则表达式模式'),
        sa.Column('keywords', sa.Text(), comment='关键词列表 (JSON)'),
        sa.Column('description', sa.Text(), comment='模式描述'),
        sa.Column('confidence_weight', sa.Integer(), server_default='80', comment='置信度权重'),
        sa.Column('sensitivity_level', sa.String(32), server_default='confidential', comment='默认敏感级别'),
        sa.Column('masking_strategy', sa.String(64), server_default='mask', comment='推荐脱敏策略'),
        sa.Column('examples', sa.Text(), comment='匹配示例 (JSON)'),
        sa.Column('counter_examples', sa.Text(), comment='不匹配示例 (JSON)'),
        sa.Column('is_active', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('is_system', sa.Boolean(), server_default='0', comment='是否系统预置'),
        sa.Column('match_count', sa.Integer(), server_default='0', comment='匹配次数'),
        sa.Column('false_positive_count', sa.Integer(), server_default='0', comment='误报次数'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.String(128), comment='创建者'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_sensitivity_patterns_pattern_id', 'sensitivity_patterns', ['pattern_id'], unique=True)


def downgrade() -> None:
    op.drop_table('sensitivity_patterns')
    op.drop_table('sensitivity_scan_results')
    op.drop_table('sensitivity_scan_tasks')
