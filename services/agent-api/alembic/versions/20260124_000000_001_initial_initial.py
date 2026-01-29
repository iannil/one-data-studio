"""Initial migration for agent-api

Revision ID: 001_initial
Revises:
Create Date: 2026-01-24

ONE-DATA-STUDIO - Agent API Initial Schema
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
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('workflow_id', sa.String(36), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('workflow_type', sa.String(50), nullable=False, default='rag'),
        sa.Column('config', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='draft'),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_workflows_name', 'name'),
        sa.Index('ix_workflows_status', 'status'),
        sa.Index('ix_workflows_created_by', 'created_by'),
    )

    # Create workflow_versions table
    op.create_table(
        'workflow_versions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('version_id', sa.String(36), unique=True, nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.workflow_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON, nullable=True),
        sa.Column('is_current', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_workflow_versions_workflow_id', 'workflow_id'),
    )

    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('execution_id', sa.String(36), unique=True, nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.workflow_id', ondelete='SET NULL'), nullable=True),
        sa.Column('version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('input_data', sa.JSON, nullable=True),
        sa.Column('output_data', sa.JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Index('ix_workflow_executions_workflow_id', 'workflow_id'),
        sa.Index('ix_workflow_executions_status', 'status'),
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), unique=True, nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.workflow_id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('context', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_sessions_workflow_id', 'workflow_id'),
        sa.Index('ix_sessions_created_by', 'created_by'),
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.String(36), unique=True, nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_messages_session_id', 'session_id'),
    )

    # Create agent_templates table
    op.create_table(
        'agent_templates',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('template_id', sa.String(36), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=False, default='assistant'),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('model_config', sa.JSON, nullable=True),
        sa.Column('tools', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_agent_templates_name', 'name'),
        sa.Index('ix_agent_templates_agent_type', 'agent_type'),
    )

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.String(36), unique=True, nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.workflow_id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('size', sa.BigInteger, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='uploaded'),
        sa.Column('chunk_count', sa.Integer, nullable=True, default=0),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_documents_workflow_id', 'workflow_id'),
        sa.Index('ix_documents_status', 'status'),
    )

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('chunk_id', sa.String(36), unique=True, nullable=False),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('embedding_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_document_chunks_document_id', 'document_id'),
    )

    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('schedule_id', sa.String(36), unique=True, nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflows.workflow_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=False),
        sa.Column('input_data', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('next_run', sa.DateTime, nullable=True),
        sa.Column('last_run', sa.DateTime, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_schedules_workflow_id', 'workflow_id'),
        sa.Index('ix_schedules_status', 'status'),
    )

    # Create execution_logs table
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('log_id', sa.String(36), unique=True, nullable=False),
        sa.Column('execution_id', sa.String(36), sa.ForeignKey('workflow_executions.execution_id', ondelete='CASCADE'), nullable=False),
        sa.Column('level', sa.String(20), nullable=False, default='INFO'),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('step_name', sa.String(100), nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('ix_execution_logs_execution_id', 'execution_id'),
        sa.Index('ix_execution_logs_level', 'level'),
    )


def downgrade() -> None:
    op.drop_table('execution_logs')
    op.drop_table('schedules')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('agent_templates')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_versions')
    op.drop_table('workflows')
