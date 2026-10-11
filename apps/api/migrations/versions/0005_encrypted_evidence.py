"""Encrypted evidence bundles and case-scoped retry records; retain legacy evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_event_case", "case_events", ["id", "case_id"])
    for column in (
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
        sa.Column("bundle_version", sa.String(16), nullable=True),
        sa.Column("bundle_metadata", sa.JSON(none_as_null=True), nullable=True),
    ):
        op.add_column("evidence", column)
    op.create_unique_constraint(
        "uq_evidence_case_owner", "evidence", ["id", "case_id", "merchant_id"]
    )
    op.create_foreign_key(
        "fk_evidence_case_owner",
        "evidence",
        "cases",
        ["case_id", "merchant_id"],
        ["id", "merchant_id"],
    )
    op.create_foreign_key(
        "fk_evidence_submitter",
        "evidence",
        "merchant_credentials",
        ["submitted_by", "merchant_id"],
        ["id", "merchant_id"],
    )
    op.create_table(
        "evidence_contents",
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id"), primary_key=True),
        sa.Column("key_id", sa.String(64), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("key_id", "nonce", name="uq_evidence_key_nonce"),
        sa.CheckConstraint("octet_length(nonce) = 12", name="ck_evidence_nonce_length"),
        sa.CheckConstraint(
            "octet_length(ciphertext) BETWEEN 16 AND 4200016", name="ck_evidence_ciphertext_size"
        ),
    )
    op.create_table(
        "evidence_submission_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_evidence_submission_key",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_evidence_request_credential",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id", "case_id", "merchant_id"],
            ["evidence.id", "evidence.case_id", "evidence.merchant_id"],
            name="fk_evidence_request_owner",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "case_id"],
            ["case_events.id", "case_events.case_id"],
            name="fk_evidence_request_event",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_evidence_request_hash"),
    )
    for table in ("evidence", "evidence_submission_requests"):
        op.execute(
            f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
        )
    op.execute(
        "CREATE TRIGGER immutable_content BEFORE UPDATE OR DELETE ON evidence_contents "
        "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
    )


def downgrade():
    op.execute(
        "LOCK TABLE evidence_submission_requests, cases, case_events, evidence, "
        "evidence_contents IN ACCESS EXCLUSIVE MODE"
    )
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM evidence WHERE bundle_version IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM evidence_contents)"
        )
    ):
        raise RuntimeError("Cannot discard encrypted evidence; use a forward migration")
    op.drop_table("evidence_submission_requests")
    op.drop_table("evidence_contents")
    op.execute("DROP TRIGGER immutable_record ON evidence")
    op.drop_constraint("fk_evidence_submitter", "evidence", type_="foreignkey")
    op.drop_constraint("fk_evidence_case_owner", "evidence", type_="foreignkey")
    op.drop_constraint("uq_evidence_case_owner", "evidence", type_="unique")
    for column in ("bundle_metadata", "bundle_version", "submitted_by", "merchant_id"):
        op.drop_column("evidence", column)
    op.drop_constraint("uq_event_case", "case_events", type_="unique")
