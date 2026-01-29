"""Initial migration for data-api

Revision ID: 001_initial
Revises:
Create Date: 2026-01-24

ONE-DATA-STUDIO - Data API Initial Schema
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        'datasets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('data_type', sa.String(50), nullable=False, default='structured'),
        sa.Column('storage_type', sa.String(50), nullable=False, default='local'),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('size', sa.BigInteger, nullable=True),
        sa.Column('row_count', sa.Integer, nullable=True),
        sa.Column('schema_info', sa.JSON, nullable=True),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('version', sa.String(50), nullable=True, default='v1.0'),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_datasets_name', 'name'),
        sa.Index('ix_datasets_data_type', 'data_type'),
        sa.Index('ix_datasets_status', 'status'),
        sa.Index('ix_datasets_created_by', 'created_by'),
    )

    # Create table_metadata table
    op.create_table(
        'table_metadata',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('database_name', sa.String(255), nullable=False),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column('table_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('owner', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('row_count', sa.BigInteger, nullable=True),
        sa.Column('size_bytes', sa.BigInteger, nullable=True),
        sa.Column('last_accessed', sa.DateTime, nullable=True),
        sa.Column('last_modified', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('database_name', 'table_name', name='uq_table_metadata_db_table'),
        sa.Index('ix_table_metadata_database', 'database_name'),
        sa.Index('ix_table_metadata_owner', 'owner'),
    )

    # Create column_metadata table
    op.create_table(
        'column_metadata',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('table_id', sa.String(36), sa.ForeignKey('table_metadata.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_nullable', sa.Boolean, default=True),
        sa.Column('is_primary_key', sa.Boolean, default=False),
        sa.Column('is_foreign_key', sa.Boolean, default=False),
        sa.Column('default_value', sa.String(500), nullable=True),
        sa.Column('ordinal_position', sa.Integer, nullable=True),
        sa.Column('sample_values', sa.JSON, nullable=True),
        sa.Column('statistics', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Index('ix_column_metadata_table_id', 'table_id'),
    )

    # Create file_uploads table
    op.create_table(
        'file_uploads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('stored_filename', sa.String(500), nullable=False),
        sa.Column('storage_path', sa.String(1000), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('size', sa.BigInteger, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='uploaded'),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('dataset_id', sa.String(36), sa.ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Index('ix_file_uploads_status', 'status'),
        sa.Index('ix_file_uploads_dataset_id', 'dataset_id'),
        sa.Index('ix_file_uploads_uploaded_by', 'uploaded_by'),
    )


def downgrade() -> None:
    op.drop_table('file_uploads')
    op.drop_table('column_metadata')
    op.drop_table('table_metadata')
    op.drop_table('datasets')
