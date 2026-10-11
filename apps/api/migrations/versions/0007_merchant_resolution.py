"""Scoped decisions, captured evaluations, and atomic allocation retry records."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "decision_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *(
            sa.Column(name, sa.Uuid(), nullable=False)
            for name in ("case_id", "merchant_id", "invoice_id", "policy_id")
        ),
        sa.Column("verification_id", sa.Uuid(), nullable=True),
        sa.Column("observation_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.UniqueConstraint("id", "case_id", "merchant_id", name="uq_decision_evaluation_owner"),
    )
    for name, target, local, remote in (
        ("case", "cases", ["case_id", "merchant_id"], ["id", "merchant_id"]),
        ("invoice", "invoices", ["invoice_id", "merchant_id"], ["id", "merchant_id"]),
        ("policy", "invoice_policies", ["policy_id", "merchant_id"], ["id", "merchant_id"]),
        (
            "verification",
            "verifications",
            ["verification_id", "case_id", "merchant_id"],
            ["id", "case_id", "merchant_id"],
        ),
        (
            "observation",
            "chain_observations",
            ["observation_id", "verification_id", "case_id", "merchant_id"],
            ["id", "verification_id", "case_id", "merchant_id"],
        ),
    ):
        op.create_foreign_key("fk_decision_" + name, "decision_evaluations", target, local, remote)
    for name in (
        "merchant_id",
        "invoice_id",
        "actor_id",
        "verification_id",
        "evaluation_id",
        "event_id",
    ):
        op.add_column("resolutions", sa.Column(name, sa.Uuid(), nullable=True))
    op.add_column("resolutions", sa.Column("workflow_version", sa.String(16), nullable=True))
    op.add_column(
        "resolutions", sa.Column("outcome_snapshot", sa.JSON(none_as_null=True), nullable=True)
    )
    op.create_unique_constraint(
        "uq_resolution_owner", "resolutions", ["id", "case_id", "merchant_id"]
    )
    op.create_unique_constraint(
        "uq_resolution_allocation_context",
        "resolutions",
        ["id", "invoice_id", "verification_id", "case_id", "merchant_id"],
    )
    op.create_unique_constraint("uq_resolution_evaluation", "resolutions", ["evaluation_id"])
    for name, target, local, remote in (
        ("case", "cases", ["case_id", "merchant_id"], ["id", "merchant_id"]),
        ("invoice", "invoices", ["invoice_id", "merchant_id"], ["id", "merchant_id"]),
        ("actor", "merchant_credentials", ["actor_id", "merchant_id"], ["id", "merchant_id"]),
        (
            "verification",
            "verifications",
            ["verification_id", "case_id", "merchant_id"],
            ["id", "case_id", "merchant_id"],
        ),
        (
            "evaluation",
            "decision_evaluations",
            ["evaluation_id", "case_id", "merchant_id"],
            ["id", "case_id", "merchant_id"],
        ),
    ):
        op.create_foreign_key("fk_resolution_" + name, "resolutions", target, local, remote)
    op.create_foreign_key(
        "fk_resolution_event",
        "resolutions",
        "case_events",
        ["event_id", "case_id"],
        ["id", "case_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    for name in ("case_id", "merchant_id"):
        op.add_column("output_allocations", sa.Column(name, sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_allocation_resolution_context",
        "output_allocations",
        "resolutions",
        ["resolution_id", "invoice_id", "verification_id", "case_id", "merchant_id"],
        ["id", "invoice_id", "verification_id", "case_id", "merchant_id"],
    )
    op.create_table(
        "case_resolution_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *(
            sa.Column(name, sa.Uuid(), nullable=False)
            for name in ("merchant_id", "credential_id", "case_id", "resolution_id")
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_case_resolution_key",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_resolve_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id", "case_id", "merchant_id"],
            ["resolutions.id", "resolutions.case_id", "resolutions.merchant_id"],
            name="fk_resolve_request_owner",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_resolve_request_hash"),
    )
    for table in ("decision_evaluations", "case_resolution_requests"):
        op.execute(
            f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
        )


def downgrade():
    op.execute(
        "LOCK TABLE merchant_credentials, case_resolution_requests, case_verification_requests, "
        "evidence_submission_requests, case_creation_requests, invoice_creation_requests, "
        "cases, invoices, case_events, decision_evaluations, resolutions, output_allocations, "
        "verification_evaluations, chain_observations, verifications IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM resolutions WHERE workflow_version IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM decision_evaluations) "
            "OR EXISTS (SELECT 1 FROM case_resolution_requests) "
            "OR EXISTS (SELECT 1 FROM output_allocations WHERE merchant_id IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM chain_observations "
            "WHERE provenance->>'schema_version' = 'decision-observation-v1')"
        )
    ):
        raise RuntimeError("Cannot discard decision history; use a forward migration")
    op.drop_table("case_resolution_requests")
    op.drop_constraint("fk_allocation_resolution_context", "output_allocations", type_="foreignkey")
    for name in ("case_id", "merchant_id"):
        op.drop_column("output_allocations", name)
    for name in ("case", "invoice", "actor", "verification", "evaluation", "event"):
        op.drop_constraint("fk_resolution_" + name, "resolutions", type_="foreignkey")
    for name in ("owner", "allocation_context", "evaluation"):
        op.drop_constraint("uq_resolution_" + name, "resolutions", type_="unique")
    for name in (
        "merchant_id",
        "invoice_id",
        "actor_id",
        "verification_id",
        "evaluation_id",
        "event_id",
        "workflow_version",
        "outcome_snapshot",
    ):
        op.drop_column("resolutions", name)
    op.drop_table("decision_evaluations")
