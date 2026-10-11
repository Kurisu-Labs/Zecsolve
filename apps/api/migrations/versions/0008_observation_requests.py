"""Idempotent merchant chain refreshes; preserve all prior observation formats."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "observation_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("verification_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_observation_request_key",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_observation_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id", "verification_id", "case_id", "merchant_id"],
            [
                "chain_observations.id",
                "chain_observations.verification_id",
                "chain_observations.case_id",
                "chain_observations.merchant_id",
            ],
            name="fk_observation_request_owner",
        ),
    )
    op.execute(
        "CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON observation_requests "
        "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
    )


def downgrade():
    op.execute(
        "LOCK TABLE merchant_credentials, observation_requests, cases, chain_observations "
        "IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM observation_requests) OR EXISTS "
            "(SELECT 1 FROM chain_observations "
            "WHERE provenance->>'schema_version' = 'decision-observation-v2')"
        )
    ):
        raise RuntimeError("Cannot discard RPC observation history; use a forward migration")
    op.drop_table("observation_requests")
