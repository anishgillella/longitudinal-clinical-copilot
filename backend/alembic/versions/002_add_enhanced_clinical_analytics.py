"""Add enhanced clinical analytics fields

Adds confidence intervals, reasoning chains, evidence quality tiers,
DSM-5 criteria tracking, and session delta tracking to support
clinical-grade analytics with proper uncertainty quantification.

Revision ID: 002_enhanced_analytics
Revises: 001_add_interview_mode_and_deep_analytics
Create Date: 2025-01-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_enhanced_analytics'
down_revision = '001_interview_mode_analytics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === ClinicalSignal enhancements ===
    # Evidence quality tier (1-4, per clinical research standards)
    op.add_column('clinical_signals', sa.Column(
        'evidence_quality_tier', sa.Integer(), nullable=True, server_default='3'
    ))

    # Cross-session consistency tracking
    op.add_column('clinical_signals', sa.Column(
        'consistency_score', sa.Float(), nullable=True
    ))
    op.add_column('clinical_signals', sa.Column(
        'occurrence_count', sa.Integer(), nullable=True, server_default='1'
    ))

    # Informant tracking (critical for pediatric assessments)
    op.add_column('clinical_signals', sa.Column(
        'informant_source', sa.String(50), nullable=True
    ))
    op.add_column('clinical_signals', sa.Column(
        'informant_agreement', sa.String(20), nullable=True
    ))

    # Temporal pattern
    op.add_column('clinical_signals', sa.Column(
        'temporal_pattern', sa.String(30), nullable=True
    ))

    # Functional impact
    op.add_column('clinical_signals', sa.Column(
        'functional_impact_description', sa.Text(), nullable=True
    ))
    op.add_column('clinical_signals', sa.Column(
        'functional_impact_severity', sa.String(20), nullable=True
    ))

    # === DiagnosticHypothesis enhancements ===
    # Confidence interval (95% CI per clinical standards)
    op.add_column('diagnostic_hypotheses', sa.Column(
        'confidence_interval_lower', sa.Float(), nullable=True, server_default='0.0'
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'confidence_interval_upper', sa.Float(), nullable=True, server_default='1.0'
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'interval_method', sa.String(30), nullable=True, server_default="'evidence_weighted'"
    ))

    # Reasoning chain (audit trail for clinical transparency)
    op.add_column('diagnostic_hypotheses', sa.Column(
        'reasoning_chain', postgresql.JSONB(), nullable=True
    ))

    # Evidence quality summary
    op.add_column('diagnostic_hypotheses', sa.Column(
        'evidence_quality_score', sa.Float(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'gold_standard_evidence_count', sa.Integer(), nullable=True, server_default='0'
    ))

    # DSM-5 criteria status
    op.add_column('diagnostic_hypotheses', sa.Column(
        'criterion_a_met', sa.Boolean(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'criterion_a_count', sa.Integer(), nullable=True, server_default='0'
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'criterion_b_met', sa.Boolean(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'criterion_b_count', sa.Integer(), nullable=True, server_default='0'
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'functional_impairment_documented', sa.Boolean(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'developmental_period_documented', sa.Boolean(), nullable=True
    ))

    # Session delta tracking
    op.add_column('diagnostic_hypotheses', sa.Column(
        'last_session_delta', sa.Float(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'sessions_since_stable', sa.Integer(), nullable=True, server_default='0'
    ))

    # Differential diagnosis context
    op.add_column('diagnostic_hypotheses', sa.Column(
        'differential_considerations', postgresql.JSONB(), nullable=True
    ))
    op.add_column('diagnostic_hypotheses', sa.Column(
        'rule_outs_addressed', postgresql.JSONB(), nullable=True
    ))


def downgrade() -> None:
    # === DiagnosticHypothesis ===
    op.drop_column('diagnostic_hypotheses', 'rule_outs_addressed')
    op.drop_column('diagnostic_hypotheses', 'differential_considerations')
    op.drop_column('diagnostic_hypotheses', 'sessions_since_stable')
    op.drop_column('diagnostic_hypotheses', 'last_session_delta')
    op.drop_column('diagnostic_hypotheses', 'developmental_period_documented')
    op.drop_column('diagnostic_hypotheses', 'functional_impairment_documented')
    op.drop_column('diagnostic_hypotheses', 'criterion_b_count')
    op.drop_column('diagnostic_hypotheses', 'criterion_b_met')
    op.drop_column('diagnostic_hypotheses', 'criterion_a_count')
    op.drop_column('diagnostic_hypotheses', 'criterion_a_met')
    op.drop_column('diagnostic_hypotheses', 'gold_standard_evidence_count')
    op.drop_column('diagnostic_hypotheses', 'evidence_quality_score')
    op.drop_column('diagnostic_hypotheses', 'reasoning_chain')
    op.drop_column('diagnostic_hypotheses', 'interval_method')
    op.drop_column('diagnostic_hypotheses', 'confidence_interval_upper')
    op.drop_column('diagnostic_hypotheses', 'confidence_interval_lower')

    # === ClinicalSignal ===
    op.drop_column('clinical_signals', 'functional_impact_severity')
    op.drop_column('clinical_signals', 'functional_impact_description')
    op.drop_column('clinical_signals', 'temporal_pattern')
    op.drop_column('clinical_signals', 'informant_agreement')
    op.drop_column('clinical_signals', 'informant_source')
    op.drop_column('clinical_signals', 'occurrence_count')
    op.drop_column('clinical_signals', 'consistency_score')
    op.drop_column('clinical_signals', 'evidence_quality_tier')
