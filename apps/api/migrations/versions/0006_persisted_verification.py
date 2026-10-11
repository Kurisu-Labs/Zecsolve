"""Scoped verification attempts, append-only observations, and initial evaluations."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    for column in (
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_version", sa.String(16), nullable=True),
        sa.Column("case_version", sa.Integer(), nullable=True),
        sa.Column("case_state", sa.String(32), nullable=True),
    ):
        op.add_column("verifications", column)
    op.create_unique_constraint(
        "uq_verification_case_owner", "verifications", ["id", "case_id", "merchant_id"]
    )
    op.create_foreign_key(
        "fk_verification_evidence_owner",
        "verifications",
        "evidence",
        ["evidence_id", "case_id", "merchant_id"],
        ["id", "case_id", "merchant_id"],
    )
    op.create_foreign_key(
        "fk_verification_actor",
        "verifications",
        "merchant_credentials",
        ["actor_id", "merchant_id"],
        ["id", "merchant_id"],
    )
    op.create_foreign_key(
        "fk_verification_event",
        "verifications",
        "case_events",
        ["event_id", "case_id"],
        ["id", "case_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.add_column("chain_observations", sa.Column("case_id", sa.Uuid(), nullable=True))
    op.add_column("chain_observations", sa.Column("merchant_id", sa.Uuid(), nullable=True))
    op.add_column(
        "chain_observations", sa.Column("provenance", sa.JSON(none_as_null=True), nullable=True)
    )
    op.create_unique_constraint(
        "uq_observation_verification_owner",
        "chain_observations",
        ["id", "verification_id", "case_id", "merchant_id"],
    )
    op.create_foreign_key(
        "fk_observation_verification_owner",
        "chain_observations",
        "verifications",
        ["verification_id", "case_id", "merchant_id"],
        ["id", "case_id", "merchant_id"],
    )
    op.create_table(
        "verification_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *(
            sa.Column(name, sa.Uuid(), nullable=False)
            for name in (
                "case_id",
                "merchant_id",
                "invoice_id",
                "policy_id",
                "verification_id",
                "observation_id",
            )
        ),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.UniqueConstraint("verification_id", name="uq_evaluation_verification"),
        sa.ForeignKeyConstraint(
            ["verification_id", "case_id", "merchant_id"],
            ["verifications.id", "verifications.case_id", "verifications.merchant_id"],
            name="fk_evaluation_verification_owner",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id", "verification_id", "case_id", "merchant_id"],
            [
                "chain_observations.id",
                "chain_observations.verification_id",
                "chain_observations.case_id",
                "chain_observations.merchant_id",
            ],
            name="fk_evaluation_observation",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id", "merchant_id"],
            ["invoices.id", "invoices.merchant_id"],
            name="fk_evaluation_invoice",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "merchant_id"],
            ["invoice_policies.id", "invoice_policies.merchant_id"],
            name="fk_evaluation_policy",
        ),
    )
    op.create_table(
        "case_verification_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *(
            sa.Column(name, sa.Uuid(), nullable=False)
            for name in ("merchant_id", "credential_id", "case_id", "verification_id")
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_case_verification_key",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_verify_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["verification_id", "case_id", "merchant_id"],
            ["verifications.id", "verifications.case_id", "verifications.merchant_id"],
            name="fk_verify_request_owner",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_verify_request_hash"),
    )
    for table in ("chain_observations", "verification_evaluations", "case_verification_requests"):
        op.execute(
            f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
        )


def downgrade():
    # Authorizers precede all writer tables, including earlier-revision creators.
    op.execute(
        "LOCK TABLE merchant_credentials, case_verification_requests, "
        "evidence_submission_requests, case_creation_requests, invoice_creation_requests, "
        "cases, invoices, case_events, "
        "verification_evaluations, chain_observations, verifications IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM verifications WHERE workflow_version IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM verification_evaluations) OR "
            "EXISTS (SELECT 1 FROM chain_observations WHERE provenance IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot discard verification history; use a forward migration")
    op.drop_table("case_verification_requests")
    op.drop_table("verification_evaluations")
    op.execute("DROP TRIGGER immutable_record ON chain_observations")
    op.drop_constraint(
        "fk_observation_verification_owner", "chain_observations", type_="foreignkey"
    )
    op.drop_constraint("uq_observation_verification_owner", "chain_observations", type_="unique")
    for name in ("provenance", "merchant_id", "case_id"):
        op.drop_column("chain_observations", name)
    for name in (
        "fk_verification_event",
        "fk_verification_actor",
        "fk_verification_evidence_owner",
    ):
        op.drop_constraint(name, "verifications", type_="foreignkey")
    op.drop_constraint("uq_verification_case_owner", "verifications", type_="unique")
    for name in (
        "case_state",
        "case_version",
        "workflow_version",
        "event_id",
        "actor_id",
        "merchant_id",
        "case_id",
    ):
        op.drop_column("verifications", name)
