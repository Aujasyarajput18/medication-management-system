"""
Aujasya — Phase 2 Schema Migration
Adds 6 new tables for AI Intelligence & Clinical Decision Layer:
  - fasting_profiles, fasting_schedule_overrides
  - side_effect_entries
  - drug_interaction_cache, generic_search_cache
  - ai_decision_logs (medico-legal audit trail for all AI decisions)

Also adds columns to: medicines (rxcui, refill tracking), dose_logs (has_journal_entry)

FORWARD-ONLY MIGRATION — downgrade() raises RuntimeError.
Column additions are non-destructive; new tables can be dropped in dev but
data loss is unacceptable in production. Rolling back requires a dedicated
reverse migration with explicit data preservation strategy.

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Phase 2 tables and add columns to existing tables."""

    # ── ALTER TABLE: medicines ───────────────────────────────────────────
    # Add RxNorm concept ID for drug interaction lookups
    op.add_column(
        "medicines",
        sa.Column("rxcui", sa.String(20), nullable=True),
    )
    # Add refill tracking columns
    op.add_column(
        "medicines",
        sa.Column(
            "refill_alert_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "medicines",
        sa.Column(
            "refill_threshold_days",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
    )

    # ── ALTER TABLE: dose_logs ───────────────────────────────────────────
    # Links to expanded side-effect journal
    op.add_column(
        "dose_logs",
        sa.Column(
            "has_journal_entry",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ── fasting_profiles ─────────────────────────────────────────────────
    op.create_table(
        "fasting_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("fasting_type", sa.String(30), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column(
            "disclaimer_accepted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "disclaimer_accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "pharmacist_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("custom_suhoor_time", sa.Time(), nullable=True),
        sa.Column("custom_iftar_time", sa.Time(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "patient_id",
            "fasting_type",
            "start_date",
            name="uq_fasting_patient_type_date",
        ),
    )
    op.create_index(
        "idx_fasting_patient",
        "fasting_profiles",
        ["patient_id", "is_active"],
    )

    # ── fasting_schedule_overrides ────────────────────────────────────────
    op.create_table(
        "fasting_schedule_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "fasting_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "original_meal_anchor", sa.String(30), nullable=False
        ),
        sa.Column(
            "adjusted_meal_anchor", sa.String(30), nullable=False
        ),
        sa.Column("adjustment_reason", sa.Text(), nullable=False),
        sa.Column("physician_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["fasting_profile_id"],
            ["fasting_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"], ["schedules.id"]
        ),
    )

    # ── side_effect_entries ───────────────────────────────────────────────
    op.create_table(
        "side_effect_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "dose_log_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "medicine_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("symptom_text", sa.Text(), nullable=False),
        sa.Column(
            "symptom_normalized",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column("severity", sa.String(10), nullable=True),
        sa.Column(
            "onset_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        sa.Column("input_method", sa.String(10), nullable=False),
        sa.Column("voice_transcript", sa.Text(), nullable=True),
        sa.Column(
            "is_flagged",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("flag_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dose_log_id"], ["dose_logs.id"]
        ),
        sa.ForeignKeyConstraint(
            ["medicine_id"], ["medicines.id"]
        ),
    )
    op.create_index(
        "idx_journal_patient",
        "side_effect_entries",
        ["patient_id", sa.text("onset_date DESC")],
    )
    op.create_index(
        "idx_journal_medicine",
        "side_effect_entries",
        ["medicine_id", sa.text("onset_date DESC")],
    )

    # ── drug_interaction_cache ───────────────────────────────────────────
    op.create_table(
        "drug_interaction_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("rxcui_a", sa.String(20), nullable=False),
        sa.Column("rxcui_b", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(15), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rxcui_a", "rxcui_b", name="uq_interaction_pair"
        ),
    )
    op.create_index(
        "idx_interaction_pair",
        "drug_interaction_cache",
        ["rxcui_a", "rxcui_b", "expires_at"],
    )

    # ── generic_search_cache ─────────────────────────────────────────────
    op.create_table(
        "generic_search_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "brand_name_normalized",
            sa.Text(),
            nullable=False,
            unique=True,
        ),
        sa.Column("active_ingredient", sa.Text(), nullable=False),
        sa.Column("alternatives", postgresql.JSONB(), nullable=False),
        sa.Column(
            "searched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("source", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_generic_cache_brand",
        "generic_search_cache",
        ["brand_name_normalized", "expires_at"],
    )

    # ── ai_decision_logs ─────────────────────────────────────────────────
    # Medico-legal audit trail for every AI-assisted clinical decision.
    # Records model version, confidence, input/output, and user's action.
    op.create_table(
        "ai_decision_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("decision_type", sa.String(30), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column(
            "output_summary", postgresql.JSONB(), nullable=False
        ),
        sa.Column("user_action", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["users.id"]
        ),
    )
    op.create_index(
        "idx_ai_decision_patient",
        "ai_decision_logs",
        ["patient_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_ai_decision_type",
        "ai_decision_logs",
        ["decision_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """
    Phase 2 migration is FORWARD-ONLY.

    Rationale: ALTER TABLE additions (rxcui, refill_threshold_days, etc.)
    are non-destructive, but DROP COLUMN is irreversible for production data.
    New tables can be dropped in dev, but require a dedicated reverse migration
    with data preservation in production.
    """
    raise RuntimeError(
        "Phase 2 migration is forward-only. "
        "Create a dedicated reverse migration if rollback is needed. "
        "See: apps/api/migrations/ROLLBACK_GUIDE.md"
    )
