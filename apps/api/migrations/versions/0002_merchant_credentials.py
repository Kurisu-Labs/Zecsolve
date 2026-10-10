"""Merchant-bound, expiring, revocable operator-provisioned credentials."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "merchant_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.UniqueConstraint("token_sha256", name="uq_merchant_credential_token"),
        sa.CheckConstraint("token_sha256 ~ '^[0-9a-f]{64}$'", name="ck_credential_digest"),
        sa.CheckConstraint("expires_at > created_at", name="ck_credential_expiry"),
    )
    op.create_index("ix_merchant_credentials_merchant_id", "merchant_credentials", ["merchant_id"])


def downgrade():
    op.drop_index("ix_merchant_credentials_merchant_id", table_name="merchant_credentials")
    op.drop_table("merchant_credentials")
