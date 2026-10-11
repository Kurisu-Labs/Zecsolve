"""One case per invoice, replayable opening events, and scoped creation retries."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    # Keep the preflight report and uniqueness change on the same stable table.
    op.execute("LOCK TABLE cases IN ACCESS EXCLUSIVE MODE")
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT invoice_id, count(*) FROM cases GROUP BY invoice_id HAVING count(*) > 1 "
                "ORDER BY invoice_id LIMIT 10"
            )
        )
        .all()
    )
    if duplicates:
        report = ", ".join(f"{invoice}: {count} cases" for invoice, count in duplicates)
        raise RuntimeError(
            "Resolve duplicate invoice cases before migration; no rows changed: " + report
        )
    op.create_unique_constraint("uq_case_invoice", "cases", ["invoice_id"])
    op.create_unique_constraint("uq_case_merchant", "cases", ["id", "merchant_id"])
    op.create_check_constraint("ck_case_version", "cases", "version >= 1")
    op.add_column("cases", sa.Column("workflow_version", sa.String(16), nullable=True))
    op.add_column("case_events", sa.Column("schema_version", sa.String(16), nullable=True))
    op.add_column("case_events", sa.Column("payload", sa.JSON(none_as_null=True), nullable=True))
    op.create_table(
        "case_creation_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint(
            "merchant_id", "credential_id", "idempotency_key", name="uq_case_creation_key"
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_case_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "merchant_id"],
            ["cases.id", "cases.merchant_id"],
            name="fk_case_request_owner",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_case_request_hash"),
    )
    op.execute(
        "CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_creation_requests "
        "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
    )


def downgrade():
    # Creators read retry records first. Wait for them before inspecting evidence,
    # then keep all affected tables stable until rollback either finishes or aborts.
    op.execute("LOCK TABLE case_creation_requests, cases, case_events IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM cases WHERE workflow_version IS NOT NULL) OR "
            "EXISTS (SELECT 1 FROM case_events "
            "WHERE schema_version IS NOT NULL OR payload IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot remove case workflow evidence; use a forward migration")
    op.drop_table("case_creation_requests")
    op.drop_column("case_events", "payload")
    op.drop_column("case_events", "schema_version")
    op.drop_column("cases", "workflow_version")
    op.drop_constraint("ck_case_version", "cases", type_="check")
    op.drop_constraint("uq_case_merchant", "cases", type_="unique")
    op.drop_constraint("uq_case_invoice", "cases", type_="unique")
