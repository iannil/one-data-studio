"""Initial migration for model-api

Revision ID: 001_initial
Revises:
Create Date: 2026-01-24

ONE-DATA-STUDIO - Model API Initial Schema
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ml_models table
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('model_id', sa.String(36), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('model_type', sa.String(100), nullable=False),
        sa.Column('framework', sa.String(100), nullable=True),
        sa.Column('source', sa.String(100), nullable=True, default='custom'),
        sa.Column('huggingface_id', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_ml_models_model_id', 'model_id'),
        sa.Index('ix_ml_models_name', 'name'),
        sa.Index('ix_ml_models_model_type', 'model_type'),
        sa.Index('ix_ml_models_status', 'status'),
    )

    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('version_id', sa.String(36), unique=True, nullable=False),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('ml_models.model_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('metrics', sa.JSON, nullable=True),
        sa.Column('parameters', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='registered'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_model_versions_model_id', 'model_id'),
        sa.Index('ix_model_versions_version', 'version'),
    )

    # Create model_deployments table
    op.create_table(
        'model_deployments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('deployment_id', sa.String(36), unique=True, nullable=False),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('ml_models.model_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_id', sa.String(36), sa.ForeignKey('model_versions.version_id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('endpoint_url', sa.String(500), nullable=True),
        sa.Column('replicas', sa.Integer, nullable=False, default=1),
        sa.Column('resources', sa.JSON, nullable=True),
        sa.Column('environment', sa.String(50), nullable=True, default='staging'),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('stopped_at', sa.DateTime, nullable=True),
        sa.Index('ix_model_deployments_model_id', 'model_id'),
        sa.Index('ix_model_deployments_status', 'status'),
    )

    # Create training_jobs table
    op.create_table(
        'training_jobs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.String(36), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('ml_models.model_id', ondelete='SET NULL'), nullable=True),
        sa.Column('algorithm', sa.String(100), nullable=True),
        sa.Column('hyperparameters', sa.JSON, nullable=True),
        sa.Column('dataset_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('progress', sa.Float, nullable=True, default=0),
        sa.Column('metrics', sa.JSON, nullable=True),
        sa.Column('logs', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Index('ix_training_jobs_model_id', 'model_id'),
        sa.Index('ix_training_jobs_status', 'status'),
    )

    # Create batch_prediction_jobs table
    op.create_table(
        'batch_prediction_jobs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.String(36), unique=True, nullable=False),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('ml_models.model_id', ondelete='SET NULL'), nullable=True),
        sa.Column('deployment_id', sa.String(36), sa.ForeignKey('model_deployments.deployment_id', ondelete='SET NULL'), nullable=True),
        sa.Column('input_path', sa.String(500), nullable=True),
        sa.Column('output_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('progress', sa.Float, nullable=True, default=0),
        sa.Column('total_records', sa.Integer, nullable=True),
        sa.Column('processed_records', sa.Integer, nullable=True, default=0),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Index('ix_batch_prediction_jobs_model_id', 'model_id'),
        sa.Index('ix_batch_prediction_jobs_status', 'status'),
    )


def downgrade() -> None:
    op.drop_table('batch_prediction_jobs')
    op.drop_table('training_jobs')
    op.drop_table('model_deployments')
    op.drop_table('model_versions')
    op.drop_table('ml_models')
