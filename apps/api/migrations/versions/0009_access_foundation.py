"""Shared scoped access persistence; preserve historical merchant evidence and hashes."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE case_grants (
        merchant_id UUID NOT NULL,
        case_id UUID NOT NULL,
        issued_by UUID NOT NULL,
        role VARCHAR(16) NOT NULL,
        token_sha256 VARCHAR(64) NOT NULL,
        scope JSON NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_grant_owner UNIQUE (id, case_id, merchant_id),
        CONSTRAINT uq_grant_token UNIQUE (token_sha256),
        CONSTRAINT fk_grant_case FOREIGN KEY(case_id, merchant_id) REFERENCES cases (id,
        merchant_id),
        CONSTRAINT fk_grant_issuer FOREIGN KEY(issued_by, merchant_id) REFERENCES
        merchant_credentials (id, merchant_id),
        CONSTRAINT ck_grant_role CHECK (role IN ('customer','reviewer')),
        CONSTRAINT ck_grant_digest CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),
        CONSTRAINT ck_grant_expiry CHECK (expires_at > created_at)
        )
    """)
    op.add_column("claims", sa.Column("merchant_id", sa.Uuid(), nullable=True))
    op.add_column("claims", sa.Column("actor_credential_id", sa.Uuid(), nullable=True))
    op.add_column("claims", sa.Column("actor_grant_id", sa.Uuid(), nullable=True))
    op.execute("""
        ALTER TABLE claims ADD CONSTRAINT ck_claim_actor CHECK (actor_grant_id IS NULL OR
        actor_credential_id IS NULL)
    """)
    op.execute("""
        ALTER TABLE claims ADD CONSTRAINT fk_claim_credential FOREIGN KEY(actor_credential_id,
        merchant_id) REFERENCES merchant_credentials (id, merchant_id)
    """)
    op.execute("""
        ALTER TABLE claims ADD CONSTRAINT fk_claim_grant FOREIGN KEY(actor_grant_id, case_id,
        merchant_id) REFERENCES case_grants (id, case_id, merchant_id)
    """)
    op.execute("""
        ALTER TABLE claims ADD CONSTRAINT fk_claim_owner FOREIGN KEY(case_id, merchant_id)
        REFERENCES cases (id, merchant_id)
    """)
    op.execute("""
        ALTER TABLE claims ADD CONSTRAINT uq_claim_owner UNIQUE (id, case_id, merchant_id)
    """)
    op.add_column("evidence", sa.Column("actor_grant_id", sa.Uuid(), nullable=True))
    op.execute("""
        ALTER TABLE evidence ADD CONSTRAINT ck_evidence_actor CHECK (actor_grant_id IS NULL OR
        submitted_by IS NULL)
    """)
    op.execute("""
        ALTER TABLE evidence ADD CONSTRAINT fk_evidence_grant FOREIGN KEY(actor_grant_id,
        case_id, merchant_id) REFERENCES case_grants (id, case_id, merchant_id)
    """)
    op.execute("""
        CREATE TABLE grant_evidence (
        grant_id UUID NOT NULL,
        evidence_id UUID NOT NULL,
        merchant_id UUID NOT NULL,
        case_id UUID NOT NULL,
        PRIMARY KEY (grant_id, evidence_id),
        CONSTRAINT fk_selection_grant FOREIGN KEY(grant_id, case_id, merchant_id) REFERENCES
        case_grants (id, case_id, merchant_id),
        CONSTRAINT fk_selection_evidence FOREIGN KEY(evidence_id, case_id, merchant_id)
        REFERENCES evidence (id, case_id, merchant_id)
        )
    """)
    op.execute("""
        CREATE TABLE grant_creation_requests (
        merchant_id UUID NOT NULL,
        credential_id UUID NOT NULL,
        case_id UUID NOT NULL,
        grant_id UUID NOT NULL,
        idempotency_key VARCHAR(128) NOT NULL,
        request_hash VARCHAR(64) NOT NULL,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_grant_creation_key UNIQUE (merchant_id, credential_id, case_id,
        idempotency_key),
        CONSTRAINT fk_grant_request_credential FOREIGN KEY(credential_id, merchant_id)
        REFERENCES merchant_credentials (id, merchant_id),
        CONSTRAINT fk_grant_request_owner FOREIGN KEY(grant_id, case_id, merchant_id) REFERENCES
        case_grants (id, case_id, merchant_id),
        CONSTRAINT ck_grant_request_hash CHECK (request_hash ~ '^[0-9a-f]{64}$')
        )
    """)
    op.execute("""
        CREATE TABLE browser_sessions (
        merchant_id UUID NOT NULL,
        credential_id UUID,
        grant_id UUID,
        case_id UUID,
        token_sha256 VARCHAR(64) NOT NULL,
        csrf_sha256 VARCHAR(64) NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_session_token UNIQUE (token_sha256),
        CONSTRAINT fk_session_credential FOREIGN KEY(credential_id, merchant_id) REFERENCES
        merchant_credentials (id, merchant_id),
        CONSTRAINT fk_session_grant FOREIGN KEY(grant_id, case_id, merchant_id) REFERENCES
        case_grants (id, case_id, merchant_id),
        CONSTRAINT ck_session_actor CHECK ((credential_id IS NOT NULL AND grant_id IS NULL AND
        case_id IS NULL) OR (credential_id IS NULL AND grant_id IS NOT NULL AND case_id IS NOT
        NULL)),
        CONSTRAINT ck_session_digest CHECK (token_sha256 ~ '^[0-9a-f]{64}$' AND csrf_sha256 ~
        '^[0-9a-f]{64}$'),
        CONSTRAINT ck_session_expiry CHECK (expires_at > created_at AND expires_at <= created_at
        + interval '8 hours')
        )
    """)
    op.execute("""
        CREATE TABLE evidence_consents (
        merchant_id UUID NOT NULL,
        case_id UUID NOT NULL,
        evidence_id UUID NOT NULL,
        credential_id UUID,
        grant_id UUID,
        disclosure_version VARCHAR(80) NOT NULL,
        processing_authorized BOOLEAN NOT NULL,
        share_with_reviewers BOOLEAN NOT NULL,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_evidence_consent UNIQUE (evidence_id),
        CONSTRAINT fk_consent_evidence FOREIGN KEY(evidence_id, case_id, merchant_id) REFERENCES
        evidence (id, case_id, merchant_id),
        CONSTRAINT fk_consent_credential FOREIGN KEY(credential_id, merchant_id) REFERENCES
        merchant_credentials (id, merchant_id),
        CONSTRAINT fk_consent_grant FOREIGN KEY(grant_id, case_id, merchant_id) REFERENCES
        case_grants (id, case_id, merchant_id),
        CONSTRAINT ck_consent_actor CHECK ((credential_id IS NOT NULL) <> (grant_id IS NOT
        NULL)),
        CONSTRAINT ck_consent_processing CHECK (processing_authorized)
        )
    """)
    op.execute("""
        CREATE TABLE access_submission_requests (
        merchant_id UUID NOT NULL,
        case_id UUID NOT NULL,
        credential_id UUID,
        grant_id UUID,
        operation VARCHAR(16) NOT NULL,
        claim_id UUID,
        evidence_id UUID,
        event_id UUID NOT NULL,
        idempotency_key VARCHAR(128) NOT NULL,
        request_hash VARCHAR(64) NOT NULL,
        id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_access_credential_retry UNIQUE (credential_id, case_id, operation,
        idempotency_key),
        CONSTRAINT uq_access_grant_retry UNIQUE (grant_id, case_id, operation, idempotency_key),
        CONSTRAINT fk_access_retry_credential FOREIGN KEY(credential_id, merchant_id) REFERENCES
        merchant_credentials (id, merchant_id),
        CONSTRAINT fk_access_retry_grant FOREIGN KEY(grant_id, case_id, merchant_id) REFERENCES
        case_grants (id, case_id, merchant_id),
        CONSTRAINT fk_access_retry_evidence FOREIGN KEY(evidence_id, case_id, merchant_id)
        REFERENCES evidence (id, case_id, merchant_id),
        CONSTRAINT fk_access_retry_claim FOREIGN KEY(claim_id, case_id, merchant_id) REFERENCES
        claims (id, case_id, merchant_id),
        CONSTRAINT fk_access_retry_event FOREIGN KEY(event_id, case_id) REFERENCES case_events
        (id, case_id),
        CONSTRAINT ck_access_retry_actor CHECK ((credential_id IS NOT NULL) <> (grant_id IS NOT
        NULL)),
        CONSTRAINT ck_access_retry_resource CHECK ((operation = 'claim' AND claim_id IS NOT NULL
        AND evidence_id IS NULL) OR (operation = 'evidence' AND evidence_id IS NOT NULL AND
        claim_id IS NULL)),
        CONSTRAINT ck_access_retry_hash CHECK (request_hash ~ '^[0-9a-f]{64}$')
        )
    """)
    op.create_check_constraint(
        "ck_claim_actor_owner",
        "claims",
        "merchant_id IS NOT NULL OR (actor_grant_id IS NULL AND actor_credential_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_evidence_actor_owner", "evidence", "actor_grant_id IS NULL OR merchant_id IS NOT NULL"
    )
    op.execute("""
        CREATE FUNCTION zecsolve_revoke_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
        IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'immutable access record'; END IF;
        IF (to_jsonb(NEW) - 'revoked_at') IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at')
        OR NEW.revoked_at IS NULL
        OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
        THEN RAISE EXCEPTION 'immutable access record'; END IF;
        RETURN NEW;
        END; $$
    """)
    for table in ("case_grants", "browser_sessions"):
        op.execute(
            f"CREATE TRIGGER revoke_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_revoke_only()"
        )
    for table in (
        "grant_evidence",
        "grant_creation_requests",
        "evidence_consents",
        "access_submission_requests",
    ):
        op.execute(
            f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION zecsolve_reject_mutation()"
        )


def downgrade():
    op.execute(
        "LOCK TABLE merchant_credentials, case_grants, browser_sessions, grant_evidence, "
        "grant_creation_requests, evidence_consents, access_submission_requests, cases, claims, "
        "evidence IN ACCESS EXCLUSIVE MODE"
    )
    for table in (
        "case_grants",
        "browser_sessions",
        "grant_evidence",
        "grant_creation_requests",
        "evidence_consents",
        "access_submission_requests",
    ):
        if op.get_bind().scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")):
            raise RuntimeError("Cannot discard access history; use a forward migration")
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM claims WHERE merchant_id IS NOT NULL "
            "OR actor_credential_id IS NOT NULL OR actor_grant_id IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM evidence WHERE actor_grant_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot discard attribution history; use a forward migration")
    for table in (
        "access_submission_requests",
        "evidence_consents",
        "browser_sessions",
        "grant_creation_requests",
        "grant_evidence",
    ):
        op.drop_table(table)
    op.drop_constraint("ck_claim_actor_owner", "claims")
    op.drop_constraint("ck_evidence_actor_owner", "evidence")
    for table, constraints in (
        (
            "claims",
            (
                "fk_claim_owner",
                "fk_claim_credential",
                "fk_claim_grant",
                "ck_claim_actor",
                "uq_claim_owner",
            ),
        ),
        ("evidence", ("fk_evidence_grant", "ck_evidence_actor")),
    ):
        for constraint in constraints:
            op.drop_constraint(constraint, table)
    for col in ("merchant_id", "actor_credential_id", "actor_grant_id"):
        op.drop_column("claims", col)
    op.drop_column("evidence", "actor_grant_id")
    op.drop_table("case_grants")
    op.execute("""
        DROP FUNCTION zecsolve_revoke_only()
    """)
