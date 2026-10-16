"""Esquema inicial de fase 1, congelado sin generación audiovisual."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "imports",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("file_hash", sa.String, nullable=False),
        sa.Column("profile", sa.String, nullable=False),
        sa.Column("suffix", sa.String, nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("issues", sa.JSON, nullable=False),
        sa.UniqueConstraint("file_hash", "profile"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "import_id", sa.String, sa.ForeignKey("imports.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("logical_key", sa.String, nullable=False),
        sa.Column("content_hash", sa.String, nullable=False),
        sa.Column("current", sa.Boolean, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("total_cents", sa.BigInteger),
        sa.Column("calculated_cents", sa.BigInteger, nullable=False),
        sa.Column("snapshot", sa.JSON, nullable=False),
        sa.Column("issues", sa.JSON, nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
    )
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "invoice_id",
            sa.String,
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_key", sa.String, nullable=False),
        sa.Column("amount_cents", sa.BigInteger, nullable=False),
        sa.Column("source", sa.JSON, nullable=False),
    )
    op.create_table(
        "scripts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "invoice_id",
            sa.String,
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signature", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
        sa.UniqueConstraint("invoice_id", "signature"),
    )
    op.create_table(
        "reviews",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "script_id", sa.String, sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("decision", sa.String, nullable=False),
        sa.Column("reason", sa.String, nullable=False),
        sa.Column("operator", sa.String, nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
    )
    for table, columns in {
        "imports": ["file_hash"],
        "invoices": ["import_id", "logical_key", "content_hash"],
        "invoice_lines": ["invoice_id"],
        "scripts": ["invoice_id"],
        "reviews": ["script_id"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in ("reviews", "scripts", "invoice_lines", "invoices", "imports"):
        op.drop_table(table)
