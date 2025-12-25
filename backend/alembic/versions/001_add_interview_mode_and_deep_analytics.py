"""Add interview_mode and deep analytics fields

Revision ID: 001_interview_mode_analytics
Revises:
Create Date: 2024-12-23

This migration adds:
1. interview_mode column to voice_sessions table
2. DSM-5 criteria mapping and quote-level evidence fields to clinical_signals
3. Clinician verification fields to clinical_signals
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_interview_mode_analytics'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add interview_mode to voice_sessions
    op.add_column(
        'voice_sessions',
        sa.Column('interview_mode', sa.String(20), nullable=False, server_default='parent')
    )

    # Add evidence_type column to clinical_signals (required for signal extraction)
    op.add_column(
        'clinical_signals',
        sa.Column('evidence_type', sa.String(20), nullable=False, server_default='inferred')
    )

    # Add reasoning column to clinical_signals
    op.add_column(
        'clinical_signals',
        sa.Column('reasoning', sa.Text(), nullable=True)
    )

    # Add transcript position columns for deep-linking
    op.add_column(
        'clinical_signals',
        sa.Column('transcript_offset_start', sa.Integer(), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('transcript_offset_end', sa.Integer(), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('transcript_line', sa.Integer(), nullable=True)
    )

    # Add clinical_significance column
    op.add_column(
        'clinical_signals',
        sa.Column('clinical_significance', sa.String(20), nullable=False, server_default='moderate')
    )

    # Add metadata columns
    op.add_column(
        'clinical_signals',
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('model_version', sa.String(50), nullable=True)
    )

    # Add DSM-5 criteria mapping to clinical_signals
    op.add_column(
        'clinical_signals',
        sa.Column('dsm5_criteria', sa.String(20), nullable=True)
    )

    # Add quote-level evidence fields to clinical_signals
    op.add_column(
        'clinical_signals',
        sa.Column('verbatim_quote', sa.Text(), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('quote_context', sa.Text(), nullable=True)
    )

    # Add clinician verification fields to clinical_signals
    op.add_column(
        'clinical_signals',
        sa.Column('clinician_verified', sa.Boolean(), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('clinician_notes', sa.Text(), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'clinical_signals',
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add foreign key constraint for verified_by
    op.create_foreign_key(
        'fk_clinical_signals_verified_by_clinicians',
        'clinical_signals',
        'clinicians',
        ['verified_by'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index on dsm5_criteria for faster lookups
    op.create_index(
        'ix_clinical_signals_dsm5_criteria',
        'clinical_signals',
        ['dsm5_criteria']
    )

    # Create index on interview_mode for filtering
    op.create_index(
        'ix_voice_sessions_interview_mode',
        'voice_sessions',
        ['interview_mode']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_voice_sessions_interview_mode', table_name='voice_sessions')
    op.drop_index('ix_clinical_signals_dsm5_criteria', table_name='clinical_signals')

    # Drop foreign key constraint
    op.drop_constraint(
        'fk_clinical_signals_verified_by_clinicians',
        'clinical_signals',
        type_='foreignkey'
    )

    # Drop clinician verification columns from clinical_signals
    op.drop_column('clinical_signals', 'verified_at')
    op.drop_column('clinical_signals', 'verified_by')
    op.drop_column('clinical_signals', 'clinician_notes')
    op.drop_column('clinical_signals', 'clinician_verified')

    # Drop quote-level evidence columns from clinical_signals
    op.drop_column('clinical_signals', 'quote_context')
    op.drop_column('clinical_signals', 'verbatim_quote')

    # Drop DSM-5 criteria column from clinical_signals
    op.drop_column('clinical_signals', 'dsm5_criteria')

    # Drop metadata columns
    op.drop_column('clinical_signals', 'model_version')
    op.drop_column('clinical_signals', 'extracted_at')

    # Drop clinical_significance column
    op.drop_column('clinical_signals', 'clinical_significance')

    # Drop transcript position columns
    op.drop_column('clinical_signals', 'transcript_line')
    op.drop_column('clinical_signals', 'transcript_offset_end')
    op.drop_column('clinical_signals', 'transcript_offset_start')

    # Drop reasoning column
    op.drop_column('clinical_signals', 'reasoning')

    # Drop evidence_type column
    op.drop_column('clinical_signals', 'evidence_type')

    # Drop interview_mode from voice_sessions
    op.drop_column('voice_sessions', 'interview_mode')
