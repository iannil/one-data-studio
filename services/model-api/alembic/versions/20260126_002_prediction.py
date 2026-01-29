"""Prediction model templates and training jobs tables

Revision ID: 20260126_002
Revises:
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '20260126_002'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ==================== 预测模板表 ====================
    op.create_table(
        'prediction_templates',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('template_id', sa.String(length=64), nullable=False, comment='模板ID'),
        sa.Column('name', sa.String(length=128), nullable=False, comment='模板名称'),
        sa.Column('category', sa.String(length=64), nullable=False, comment='分类: sales, churn, conversion, demand_forecasting'),
        sa.Column('description', sa.Text(), comment='模板描述'),
        sa.Column('target_variable', sa.String(length=128), nullable=False, comment='目标变量名'),
        sa.Column('target_type', sa.String(length=32), nullable=False, comment='目标类型: binary, regression, count'),
        sa.Column('prediction_horizon', sa.Integer(), comment='预测时间窗口（天）'),
        sa.Column('required_features', sa.JSON(), comment='必需特征列表'),
        sa.Column('optional_features', sa.JSON(), comment='可选特征列表'),
        sa.Column('default_model', sa.String(length=64), comment='默认模型类型'),
        sa.Column('allowed_models', sa.JSON(), comment='允许的模型类型'),
        sa.Column('model_params', sa.JSON(), comment='模型参数配置'),
        sa.Column('min_rows', sa.Integer(), default=1000, comment='最少数据行数'),
        sa.Column('feature_importance_threshold', sa.Float(), default=0.1, comment='特征重要性阈值'),
        sa.Column('metrics', sa.JSON(), comment='评估指标配置'),
        sa.Column('success_threshold', sa.JSON(), comment='成功阈值配置'),
        sa.Column('chart_type', sa.String(length=32), comment='推荐图表类型'),
        sa.Column('chart_config', sa.JSON(), comment='图表配置'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('is_system', sa.Boolean(), default=False, comment='是否系统预置'),
        sa.Column('usage_count', sa.Integer(), default=0, comment='使用次数'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.String(length=128), comment='创建者'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_prediction_templates_template_id', 'prediction_templates', ['template_id'], unique=True)
    op.create_index('ix_prediction_templates_category', 'prediction_templates', ['category'])
    op.create_index('ix_prediction_templates_is_active', 'prediction_templates', ['is_active'])

    # ==================== 训练任务表 ====================
    op.create_table(
        'training_jobs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('job_id', sa.String(length=64), nullable=False, comment='任务ID'),
        sa.Column('template_id', sa.String(length=64), comment='模板ID'),
        sa.Column('job_name', sa.String(length=255), comment='任务名称'),
        sa.Column('description', sa.Text(), comment='任务描述'),
        sa.Column('category', sa.String(length=64), comment='分类'),
        sa.Column('dataset_id', sa.String(length=128), comment='数据集ID'),
        sa.Column('table_name', sa.String(length=128), comment='表名'),
        sa.Column('model_type', sa.String(length=64), comment='模型类型'),
        sa.Column('model_params', sa.JSON(), comment='模型参数'),
        sa.Column('feature_config', sa.JSON(), comment='特征工程配置'),
        sa.Column('selected_features', sa.JSON(), comment='选择的特征列表'),
        sa.Column('train_test_split', sa.Float(), default=0.8, comment='训练集比例'),
        sa.Column('random_state', sa.Integer(), comment='随机种子'),
        sa.Column('max_epochs', sa.Integer(), default=100, comment='最大训练轮数'),
        sa.Column('early_stopping', sa.Boolean(), default=True, comment='早停'),
        sa.Column('status', sa.String(length=32), default='pending', comment='状态: pending, running, completed, failed, cancelled'),
        sa.Column('progress', sa.Integer(), default=0, comment='训练进度 0-100'),
        sa.Column('model_path', sa.String(length=512), comment='模型保存路径'),
        sa.Column('model_version', sa.String(length=64), comment='模型版本号'),
        sa.Column('metrics', sa.JSON(), comment='评估指标'),
        sa.Column('feature_importance', sa.JSON(), comment='特征重要性'),
        sa.Column('error_message', sa.Text(), comment='错误信息'),
        sa.Column('created_by', sa.String(length=128), comment='创建者'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('started_at', sa.TIMESTAMP(), comment='开始时间'),
        sa.Column('completed_at', sa.TIMESTAMP(), comment='完成时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_training_jobs_job_id', 'training_jobs', ['job_id'], unique=True)
    op.create_index('ix_training_jobs_template_id', 'training_jobs', ['template_id'])
    op.create_index('ix_training_jobs_status', 'training_jobs', ['status'])
    op.create_index('ix_training_jobs_category', 'training_jobs', ['category'])
    op.create_index('ix_training_jobs_created_at', 'training_jobs', ['created_at'])
    # Note: Foreign key to prediction_templates may not exist if that table is in a different database

    # ==================== 预测记录表 ====================
    op.create_table(
        'prediction_records',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('record_id', sa.String(length=64), nullable=False, comment='记录ID'),
        sa.Column('job_id', sa.String(length=64), comment='任务ID'),
        sa.Column('input_data', sa.JSON(), comment='输入数据'),
        sa.Column('input_hash', sa.String(length=64), comment='输入数据哈希（用于缓存）'),
        sa.Column('prediction', sa.JSON(), comment='预测结果'),
        sa.Column('prediction_probability', sa.Float(), comment='预测概率（分类问题）'),
        sa.Column('predicted_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='预测时间'),
        sa.Column('created_by', sa.String(length=128), comment='创建者'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_prediction_records_record_id', 'prediction_records', ['record_id'], unique=True)
    op.create_index('ix_prediction_records_job_id', 'prediction_records', ['job_id'])
    op.create_index('ix_prediction_records_predicted_at', 'prediction_records', ['predicted_at'])


def downgrade():
    op.drop_table('prediction_records')
    op.drop_table('training_jobs')
    op.drop_table('prediction_templates')
