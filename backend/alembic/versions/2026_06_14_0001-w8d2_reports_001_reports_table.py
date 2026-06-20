"""w8d2 reports 001 — reports table (anti report-bombing)

Revision ID: w8d2_reports_001
Revises: w8d1_moderation_001
Create Date: 2026-06-14

NOTE: some dev DBs have a stray legacy `reports` table (enum-based
reason/status, no per-user uniqueness) created out-of-band, never
tracked by Alembic — confirmed empty. upgrade() drops it first so
this migration is safe on both fresh and legacy-tainted databases.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w8d2_reports_001"
down_revision = "w8d1_moderation_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clean up the untracked legacy table/enums if present (no-op otherwise)
    op.execute("DROP TABLE IF EXISTS reports CASCADE")
    op.execute("DROP TYPE IF EXISTS reportreason")
    op.execute("DROP TYPE IF EXISTS reportstatus")

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("artifacts.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("detail", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default=sa.text("'OPEN'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_report_once_per_user", "reports", ["artifact_id", "reporter_id"]
    )
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_artifact_status", "reports",
                    ["artifact_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reports_artifact_status", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_constraint("uq_report_once_per_user", "reports", type_="unique")
    op.drop_table("reports")
