"""Immutable invoice policies and creation retry records; preserve legacy snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_credential_merchant", "merchant_credentials", ["id", "merchant_id"]
    )
    op.create_table(
        "invoice_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("merchant_id", sa.Uuid(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.UniqueConstraint("id", "merchant_id", name="uq_policy_merchant"),
    )
    op.add_column("invoices", sa.Column("policy_id", sa.Uuid(), nullable=True))
    op.add_column("invoices", sa.Column("snapshot_version", sa.String(16), nullable=True))
    op.add_column("invoices", sa.Column("expected_memo_text", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_invoice_policy_merchant",
        "invoices",
        "invoice_policies",
        ["policy_id", "merchant_id"],
        ["id", "merchant_id"],
    )
    op.create_table(
        "invoice_creation_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint(
            "merchant_id", "credential_id", "idempotency_key", name="uq_invoice_creation_key"
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_invoice_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id", "merchant_id"],
            ["invoices.id", "invoices.merchant_id"],
            name="fk_invoice_request_owner",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_invoice_request_hash"),
    )
    op.execute("DROP TRIGGER immutable_invoice ON invoices")
    op.execute(
        "CREATE TRIGGER immutable_invoice BEFORE UPDATE OR DELETE ON invoices "
        "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
    )
    for table in ("invoice_policies", "invoice_creation_requests"):
        op.execute(
            f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
        )


def downgrade():
    # Development rollback only; never erase policy evidence on accepted new invoices.
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM invoices WHERE policy_id IS NOT NULL)")
    ):
        raise RuntimeError("Cannot downgrade populated invoice policies; use a forward migration")
    op.drop_table("invoice_creation_requests")
    op.drop_constraint("fk_invoice_policy_merchant", "invoices", type_="foreignkey")
    op.drop_column("invoices", "expected_memo_text")
    op.drop_column("invoices", "snapshot_version")
    op.drop_column("invoices", "policy_id")
    op.drop_table("invoice_policies")
    op.drop_constraint("uq_credential_merchant", "merchant_credentials", type_="unique")
    op.execute("DROP TRIGGER immutable_invoice ON invoices")
    op.execute(
        "CREATE TRIGGER immutable_invoice BEFORE UPDATE ON invoices "
        "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
    )
