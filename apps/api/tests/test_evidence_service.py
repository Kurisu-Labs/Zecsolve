import base64
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.adapters.evidence_crypto import EvidenceCipher
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import Case, CaseEvent, Evidence, EvidenceContent, EvidenceSubmissionRequest
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.evidence import EvidenceSubmitRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.services.cases import CaseService
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


@pytest.fixture
def evidence_setup(database, root, receipt, raw_tx):
    from zecsolve.services.evidence import EvidenceService

    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Evidence merchant")
    principal = MerchantPrincipal(issued.merchant_id, issued.credential_id)
    address = json.loads((root / "fixtures/manifest.json").read_text())["expected"][
        "receiver_address"
    ]
    invoices = InvoiceService(
        database,
        AddressNormalizer(root / "target/debug/zecsolve-verifier"),
        threading.BoundedSemaphore(2),
    )
    invoice, _ = invoices.create(
        principal,
        InvoiceCreateRequest(
            expected_zat=200_000, network="mainnet", pool="orchard", receiver_address=address
        ),
        "invoice",
    )
    case, _ = CaseService(database).create(
        principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "case"
    )
    cipher = EvidenceCipher("test", SecretStr(base64.b64encode(os.urandom(32)).decode()))
    service = EvidenceService(database, cipher, threading.BoundedSemaphore(2))
    request = EvidenceSubmitRequest(
        receipt_json=receipt,
        raw_tx_hex=raw_tx,
        source="historical fixture",
        source_kind="public_fixture",
        processing_authorized=True,
    )
    return service, principal, case, request


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(model))
            for model in (Evidence, EvidenceContent, EvidenceSubmissionRequest, CaseEvent)
        ]


def test_submission_encrypts_original_bytes_and_commits_metadata_and_event(
    database, evidence_setup
):
    service, principal, case, request = evidence_setup
    stored, replayed = service.submit(principal, case.case_id, request, "upload")
    assert not replayed and stored.case_version == 2 and stored.case_state == "OPEN"
    assert service.read_content(principal, case.case_id, stored.evidence_id) == request
    assert service.get(principal, case.case_id, stored.evidence_id) == stored
    with Session(database) as session:
        row = session.get(Evidence, stored.evidence_id)
        encrypted = session.get(EvidenceContent, stored.evidence_id)
        assert request.receipt_json not in json.dumps(row.bundle_metadata)
        assert request.receipt_json.encode() not in encrypted.ciphertext
        assert encrypted.key_id == "test" and len(encrypted.nonce) == 12
        assert session.get(Case, case.case_id).version == 2
    assert counts(database) == [1, 1, 1, 2]
    assert service.submit(principal, case.case_id, request, "upload") == (stored, True)
    with pytest.raises(WorkflowError) as error:
        service.submit(
            principal, case.case_id, request.model_copy(update={"source": "changed"}), "upload"
        )
    assert error.value.status == 409


def test_missing_components_are_stored_without_fabricating_evidence(database, evidence_setup):
    service, principal, case, _ = evidence_setup
    empty = EvidenceSubmitRequest(source="reported missing receipt", processing_authorized=True)
    stored, _ = service.submit(principal, case.case_id, empty, "missing")
    assert stored.receipt_sha256 is None and stored.raw_tx_hex_sha256 is None
    assert stored.case_state == "AWAITING_EVIDENCE"
    assert service.read_content(principal, case.case_id, stored.evidence_id) == empty
    assert counts(database) == [1, 1, 1, 2]


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_submissions_serialize_case_version_and_event_chain(
    database, evidence_setup, same_key
):
    service, principal, case, request = evidence_setup
    barrier = threading.Barrier(2)

    def submit(index):
        barrier.wait(timeout=5)
        return service.submit(
            principal, case.case_id, request, "shared" if same_key else str(index)
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, [0, 1]))
    if same_key:
        assert results[0][0] == results[1][0]
        assert sorted(replay for _, replay in results) == [False, True]
    else:
        assert sorted(item.case_version for item, _ in results) == [2, 3]
    count = 1 if same_key else 2
    assert counts(database) == [count, count, count, count + 1]
    with Session(database) as session:
        from zecsolve.services.audit import load_event_chain

        load_event_chain(session, session.get(Case, case.case_id))


def test_access_is_scoped_before_decryption_and_revoked_replay_is_denied(database, evidence_setup):
    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "upload")
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = MerchantPrincipal(other.merchant_id, other.credential_id)
    for operation in [
        lambda: service.read_content(foreign, case.case_id, stored.evidence_id),
        lambda: service.get(foreign, case.case_id, stored.evidence_id),
        lambda: service.read_content(principal, uuid.uuid4(), stored.evidence_id),
    ]:
        with pytest.raises(WorkflowError) as error:
            operation()
        assert error.value.status == 404
    with Session(database) as session, session.begin():
        revoke_credential(session, principal.credential_id)
    with pytest.raises(WorkflowError) as error:
        service.submit(principal, case.case_id, request, "upload")
    assert error.value.status == 401


def test_terminal_case_allows_only_completed_retry(database, evidence_setup):
    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "upload")
    with database.begin() as connection:
        connection.execute(update(Case).where(Case.id == case.case_id).values(state="RESOLVED"))
    assert service.submit(principal, case.case_id, request, "upload") == (stored, True)
    with pytest.raises(WorkflowError) as error:
        service.submit(principal, case.case_id, request, "new")
    assert error.value.status == 409


def test_failed_commit_rolls_back_ciphertext_metadata_version_and_event(database, evidence_setup):
    from sqlalchemy.exc import SQLAlchemyError

    service, principal, case, request = evidence_setup
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_evidence_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'test evidence failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_evidence_commit AFTER INSERT ON "
                "evidence_submission_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                "EXECUTE FUNCTION fail_evidence_commit()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        service.submit(principal, case.case_id, request, "rollback")
    assert counts(database) == [0, 0, 0, 1]
    with Session(database) as session:
        assert session.get(Case, case.case_id).version == 1


def test_ciphertext_and_nonce_reservation_cannot_be_deleted(database, evidence_setup):
    from sqlalchemy.exc import DBAPIError

    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "upload")
    for operation in [
        EvidenceContent.__table__.delete().where(EvidenceContent.evidence_id == stored.evidence_id),
        Evidence.__table__.delete().where(Evidence.id == stored.evidence_id),
    ]:
        with pytest.raises(DBAPIError, match="immutable record"):
            with database.begin() as connection:
                connection.execute(operation)


def test_nonce_collision_rolls_back_all_submission_side_effects(
    database, evidence_setup, monkeypatch
):
    service, principal, case, request = evidence_setup
    real_random = os.urandom
    monkeypatch.setattr(
        "zecsolve.adapters.evidence_crypto.os.urandom",
        lambda size: bytes(12) if size == 12 else real_random(size),
    )
    service.submit(principal, case.case_id, request, "first")
    with pytest.raises(WorkflowError) as error:
        service.submit(principal, case.case_id, request, "second")
    assert error.value.status == 409
    assert counts(database) == [1, 1, 1, 2]
    with Session(database) as session:
        assert session.get(Case, case.case_id).version == 2


def test_tampered_ciphertext_is_rejected_without_returning_content(database, evidence_setup):
    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "upload")
    # Simulate corrupted storage through the test database administrator, not an API mutation.
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE evidence_contents DISABLE TRIGGER immutable_content"))
        raw = connection.scalar(
            select(EvidenceContent.ciphertext).where(
                EvidenceContent.evidence_id == stored.evidence_id
            )
        )
        connection.execute(
            update(EvidenceContent)
            .where(EvidenceContent.evidence_id == stored.evidence_id)
            .values(ciphertext=bytes([raw[0] ^ 1]) + raw[1:])
        )
        connection.execute(text("ALTER TABLE evidence_contents ENABLE TRIGGER immutable_content"))
    with pytest.raises(WorkflowError) as error:
        service.read_content(principal, case.case_id, stored.evidence_id)
    assert (error.value.status, error.value.code) == (409, "EVIDENCE_INTEGRITY_ERROR")


def test_revocation_during_decryption_prevents_plaintext_return(database, evidence_setup):
    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "upload")
    decrypt = service.cipher.decrypt

    def revoke_then_decrypt(*args, **kwargs):
        with Session(database) as session, session.begin():
            revoke_credential(session, principal.credential_id)
        return decrypt(*args, **kwargs)

    service.cipher.decrypt = revoke_then_decrypt
    with pytest.raises(WorkflowError) as error:
        service.read_content(principal, case.case_id, stored.evidence_id)
    assert error.value.status == 401


def test_corrupted_audit_reference_blocks_submission_without_side_effects(database, evidence_setup):
    service, principal, case, request = evidence_setup
    stored, _ = service.submit(principal, case.case_id, request, "first")
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE case_events DISABLE TRIGGER immutable_record"))
        payload = connection.scalar(
            select(CaseEvent.payload).where(CaseEvent.id == stored.event_id)
        )
        connection.execute(
            update(CaseEvent)
            .where(CaseEvent.id == stored.event_id)
            .values(payload={**payload, "evidence_id": None})
        )
        connection.execute(text("ALTER TABLE case_events ENABLE TRIGGER immutable_record"))
    with pytest.raises(WorkflowError) as error:
        service.submit(principal, case.case_id, request, "second")
    assert (error.value.status, error.value.code) == (409, "CASE_HISTORY_UNAVAILABLE")
    assert counts(database) == [1, 1, 1, 2]


def test_downgrade_waits_for_inflight_encrypted_submission(database, root, evidence_setup):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import event

    service, principal, case, request = evidence_setup
    paused, release = threading.Event(), threading.Event()
    role = threading.local()

    def coordinate(connection, cursor, statement, parameters, context, executemany):
        statement = statement.lstrip()
        if (
            getattr(role, "name", None) == "writer"
            and "FROM invoices" in statement
            and "FOR UPDATE" in statement
        ):
            paused.set()
            assert release.wait(timeout=5)
        if getattr(role, "name", None) == "migration" and statement.startswith(
            "LOCK TABLE evidence_submission_requests"
        ):
            release.set()

    def submit():
        role.name = "writer"
        return service.submit(principal, case.case_id, request, "inflight")

    def downgrade():
        role.name = "migration"
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        try:
            with database.begin() as connection:
                config.attributes["connection"] = connection
                command.downgrade(config, "0004")
            return "downgraded"
        except RuntimeError as error:
            return str(error)

    event.listen(database, "before_cursor_execute", coordinate)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            writer = executor.submit(submit)
            assert paused.wait(timeout=5)
            migration = executor.submit(downgrade)
            stored, _ = writer.result(timeout=10)
            assert "forward migration" in migration.result(timeout=10)
    finally:
        release.set()
        event.remove(database, "before_cursor_execute", coordinate)
    assert service.read_content(principal, case.case_id, stored.evidence_id) == request
    assert counts(database) == [1, 1, 1, 2]
