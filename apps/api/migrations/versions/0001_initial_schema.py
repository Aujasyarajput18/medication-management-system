"""
Aujasya — Initial Database Schema Migration
Creates all 13 tables: users, otp_sessions, refresh_tokens, user_meal_times,
caregiver_links, medicines, schedules, dose_logs, notification_logs,
push_subscriptions, consent_records, audit_logs + uuid-ossp extension.

Revision ID: 0001
Create Date: 2025-01-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for Aujasya Phase 1."""

    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("phone_number", sa.String(15), nullable=False),
        sa.Column("phone_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("full_name", sa.LargeBinary(), nullable=True),
        sa.Column("date_of_birth", sa.LargeBinary(), nullable=True),
        sa.Column("preferred_language", sa.String(5), server_default="hi", nullable=False),
        sa.Column("role", sa.String(20), server_default="patient", nullable=False),
        sa.Column("abha_id", sa.String(17), nullable=True),
        sa.Column("timezone", sa.String(50), server_default="Asia/Kolkata", nullable=False),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("idx_users_phone", "users", ["phone_number"])
    op.create_index("idx_users_role", "users", ["role"])

    # ── otp_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "otp_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("phone_number", sa.String(15), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_otp_phone_purpose", "otp_sessions", ["phone_number", "purpose", "used"])

    # ── refresh_tokens ───────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("device_info", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_refresh_user", "refresh_tokens", ["user_id", "revoked"])

    # ── user_meal_times ──────────────────────────────────────────────────
    op.create_table(
        "user_meal_times",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_name", sa.String(30), nullable=False),
        sa.Column("typical_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(50), server_default="Asia/Kolkata", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "meal_name", name="uq_user_meal_name"),
    )

    # ── caregiver_links ──────────────────────────────────────────────────
    op.create_table(
        "caregiver_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caregiver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("permissions", postgresql.JSONB(), server_default='{"view_doses": true, "receive_alerts": true}', nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["caregiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("patient_id", "caregiver_id", name="uq_caregiver_link"),
    )

    # ── medicines ────────────────────────────────────────────────────────
    op.create_table(
        "medicines",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_name", sa.Text(), nullable=False),
        sa.Column("generic_name", sa.Text(), nullable=True),
        sa.Column("active_ingredient", sa.Text(), nullable=True),
        sa.Column("dosage_value", sa.Numeric(8, 2), nullable=False),
        sa.Column("dosage_unit", sa.String(20), nullable=False),
        sa.Column("form", sa.String(30), nullable=False),
        sa.Column("color", sa.String(30), nullable=True),
        sa.Column("shape", sa.String(30), nullable=True),
        sa.Column("imprint", sa.String(50), nullable=True),
        sa.Column("total_quantity", sa.Integer(), nullable=True),
        sa.Column("remaining_quantity", sa.Integer(), nullable=True),
        sa.Column("prescribed_by", sa.LargeBinary(), nullable=True),
        sa.Column("instructions", sa.LargeBinary(), nullable=True),
        sa.Column("prescription_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("fhir_medication_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_medicines_patient", "medicines", ["patient_id", "is_active"])

    # ── schedules ────────────────────────────────────────────────────────
    op.create_table(
        "schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_anchor", sa.String(30), nullable=False),
        sa.Column("offset_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dose_quantity", sa.Numeric(8, 2), server_default="1", nullable=False),
        sa.Column("days_of_week", postgresql.ARRAY(sa.Integer()), server_default="{0,1,2,3,4,5,6}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("reminder_level", sa.Integer(), server_default="4", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_schedules_patient", "schedules", ["patient_id", "is_active"])
    op.create_index("idx_schedules_medicine", "schedules", ["medicine_id"])

    # ── dose_logs ────────────────────────────────────────────────────────
    op.create_table(
        "dose_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("meal_anchor", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("logged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("side_effects", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("offline_sync", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("device_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["logged_by"], ["users.id"]),
        sa.UniqueConstraint("schedule_id", "scheduled_date", "meal_anchor", name="uq_dose_schedule_date_anchor"),
    )
    op.create_index("idx_dose_logs_patient_date", "dose_logs", ["patient_id", sa.text("scheduled_date DESC")])
    op.create_index("idx_dose_logs_status", "dose_logs", ["patient_id", "status", "scheduled_date"])

    # ── notification_logs [FIX-11] ───────────────────────────────────────
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dose_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["dose_log_id"], ["dose_logs.id"]),
    )
    op.create_index("idx_notif_patient", "notification_logs", ["patient_id", sa.text("sent_at DESC")])

    # ── push_subscriptions ───────────────────────────────────────────────
    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fcm_token", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ── consent_records ──────────────────────────────────────────────────
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_version", sa.String(10), nullable=False),
        sa.Column("purpose_code", sa.String(50), nullable=False),
        sa.Column("consented", sa.Boolean(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "purpose_code", "consent_version", name="uq_consent_user_purpose_version"),
    )
    op.create_index("idx_consent_user", "consent_records", ["user_id", "purpose_code", "revoked_at"])

    # ── audit_logs [FIX-12] ──────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_path", sa.Text(), nullable=True),
        sa.Column("request_method", sa.String(10), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("metadata_extra", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_audit_user", "audit_logs", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_audit_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("audit_logs")
    op.drop_table("consent_records")
    op.drop_table("push_subscriptions")
    op.drop_table("notification_logs")
    op.drop_table("dose_logs")
    op.drop_table("schedules")
    op.drop_table("medicines")
    op.drop_table("caregiver_links")
    op.drop_table("user_meal_times")
    op.drop_table("refresh_tokens")
    op.drop_table("otp_sessions")
    op.drop_table("users")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
