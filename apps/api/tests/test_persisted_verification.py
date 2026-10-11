import base64
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.adapters.evidence_crypto import EvidenceCipher
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import (
    Case,
    CaseEvent,
    CaseVerificationRequest,
    ChainObservation,
    OutputAllocation,
    Verification,
    VerificationEvaluation,
)
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.evidence import EvidenceSubmitRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.cases import CaseService
from zecsolve.services.evidence import EvidenceService
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


@pytest.fixture
def verification_setup(database, root, receipt, raw_tx):
    from zecsolve.services.verifications import VerificationService

    slots = threading.BoundedSemaphore(2)
    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Verification merchant")
    principal = MerchantPrincipal(issued.merchant_id, issued.credential_id)
    cipher = EvidenceCipher("test", SecretStr(base64.b64encode(os.urandom(32)).decode()))
    address = json.loads((root / "fixtures/manifest.json").read_text())["expected"][
        "receiver_address"
    ]
    invoice, _ = InvoiceService(
        database, AddressNormalizer(root / "target/debug/zecsolve-verifier"), slots
    ).create(
        principal,
        InvoiceCreateRequest(
            expected_zat=200_000,
            network="mainnet",
            pool="orchard",
            receiver_address=address,
            expected_memo="glasspane first receipt",
        ),
        "invoice",
    )
    case, _ = CaseService(database).create(
        principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "case"
    )
    evidence = EvidenceService(database, cipher, slots)
    submitted, _ = evidence.submit(
        principal,
        case.case_id,
        EvidenceSubmitRequest(
            receipt_json=receipt,
            raw_tx_hex=raw_tx,
            source="fixture",
            source_kind="public_fixture",
            processing_authorized=True,
        ),
        "evidence",
    )
    service = VerificationService(
        database, cipher, VerifierAdapter(root / "target/debug/zecsolve-verifier"), slots
    )
    return service, principal, case, submitted, evidence


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(model))
            for model in (
                Verification,
                ChainObservation,
                VerificationEvaluation,
                CaseVerificationRequest,
                OutputAllocation,
            )
        ]


def test_real_verifier_persists_offline_attempt_and_replay_skips_subprocess(
    database, verification_setup
):
    service, principal, case, evidence, _ = verification_setup
    request = CaseVerifyRequest(evidence_id=evidence.evidence_id)
    attempt, replayed = service.verify(principal, case.case_id, request, "verify")
    assert not replayed and attempt.result.receipt_state == "VALID"
    assert attempt.result.output.amount_zat == 100_000
    assert attempt.observation.state == "UNAVAILABLE" and attempt.observation.confirmations is None
    result = attempt.evaluation.result
    assert (
        result.credited_zat,
        result.outstanding_zat,
        result.candidate_zat,
        result.projected_outstanding_zat,
    ) == (0, 200_000, 100_000, 100_000)
    assert result.eligible_for_credit is False
    service.verifier.verify = lambda *args: pytest.fail("Replay must not execute Rust")
    assert service.verify(principal, case.case_id, request, "verify") == (attempt, True)
    assert counts(database) == [1, 1, 1, 1, 0]
    with Session(database) as session:
        assert session.get(Case, case.case_id).version == 3
        assert session.scalar(select(func.count()).select_from(CaseEvent)) == 3


@pytest.mark.parametrize(
    "kind,state",
    [
        ("tampered", "INVALID"),
        ("missing", "NONE"),
        ("malformed", "ERROR"),
        ("unsupported", "UNSUPPORTED"),
    ],
)
def test_unsuccessful_attempts_are_persisted_honestly(
    database, root, raw_tx, verification_setup, kind, state
):
    service, principal, case, _, evidence = verification_setup
    receipt = (root / "fixtures/negative/tampered-ock.json").read_text()
    if kind == "missing":
        receipt = None
    if kind == "unsupported":
        receipt = '{"version":"999"}'
    submitted, _ = evidence.submit(
        principal,
        case.case_id,
        EvidenceSubmitRequest(
            receipt_json=receipt,
            raw_tx_hex="not hex" if kind == "malformed" else raw_tx,
            source="test",
            processing_authorized=True,
        ),
        kind,
    )
    result, _ = service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=submitted.evidence_id), kind
    )
    assert result.result.receipt_state == state
    assert result.result.output is None and result.evaluation.result.candidate_zat == 0
    assert counts(database) == [1, 1, 1, 1, 0]


def test_concurrent_same_key_persists_one_attempt(database, verification_setup):
    service, principal, case, evidence, _ = verification_setup
    original = service.verifier.verify
    barrier = threading.Barrier(2)

    def synchronize(*args):
        result = original(*args)
        barrier.wait(timeout=5)
        return result

    service.verifier.verify = synchronize
    request = CaseVerifyRequest(evidence_id=evidence.evidence_id)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=10)
            for future in [
                executor.submit(service.verify, principal, case.case_id, request, "race")
                for _ in range(2)
            ]
        ]
    assert results[0][0] == results[1][0]
    assert sorted(replay for _, replay in results) == [False, True]
    assert counts(database) == [1, 1, 1, 1, 0]


def test_revocation_during_verifier_prevents_all_persistence(database, verification_setup):
    service, principal, case, evidence, _ = verification_setup
    original = service.verifier.verify

    def revoke_then_verify(*args):
        with Session(database) as session, session.begin():
            revoke_credential(session, principal.credential_id)
        return original(*args)

    service.verifier.verify = revoke_then_verify
    with pytest.raises(WorkflowError) as error:
        service.verify(
            principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "revoked"
        )
    assert error.value.status == 401 and counts(database) == [0, 0, 0, 0, 0]


def test_failed_commit_rolls_back_every_verification_record(database, verification_setup):
    from sqlalchemy.exc import SQLAlchemyError

    service, principal, case, evidence, _ = verification_setup
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_verify_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'verification rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_verify_commit AFTER INSERT ON "
                "case_verification_requests "
                "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fail_verify_commit()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        service.verify(
            principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "rollback"
        )
    assert counts(database) == [0, 0, 0, 0, 0]
    with Session(database) as session:
        assert session.get(Case, case.case_id).version == 2


@pytest.mark.parametrize(
    "failure,state,reason",
    [("missing", "UNAVAILABLE", "VERIFIER_UNAVAILABLE"), ("timeout", "ERROR", "VERIFIER_TIMEOUT")],
)
def test_technical_failures_are_recorded_and_new_key_can_retry(
    database, root, tmp_path, verification_setup, failure, state, reason
):
    service, principal, case, evidence, _ = verification_setup
    binary = tmp_path / "verifier"
    if failure == "timeout":
        binary.write_text("#!/usr/bin/python3\nimport time; time.sleep(2)\n")
        binary.chmod(0o700)
    service.verifier = VerifierAdapter(binary, timeout=0.05)
    request = CaseVerifyRequest(evidence_id=evidence.evidence_id)
    failed, _ = service.verify(principal, case.case_id, request, "first")
    assert (failed.result.receipt_state, failed.result.reason_code) == (state, reason)
    service.verifier = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    assert service.verify(principal, case.case_id, request, "first") == (failed, True)
    recovered, replayed = service.verify(principal, case.case_id, request, "retry")
    assert not replayed and recovered.result.receipt_state == "VALID"
    assert counts(database) == [2, 2, 2, 2, 0]


def test_replay_rejects_corrupted_verification_event(database, verification_setup):
    from sqlalchemy import update

    service, principal, case, evidence, _ = verification_setup
    request = CaseVerifyRequest(evidence_id=evidence.evidence_id)
    attempt, _ = service.verify(principal, case.case_id, request, "verify")
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE case_events DISABLE TRIGGER immutable_record"))
        connection.execute(
            update(CaseEvent).where(CaseEvent.id == attempt.event_id).values(event_hash="00" * 32)
        )
        connection.execute(text("ALTER TABLE case_events ENABLE TRIGGER immutable_record"))
    with pytest.raises(WorkflowError) as error:
        service.verify(principal, case.case_id, request, "verify")
    assert error.value.status == 409


def test_verification_records_reject_updates_and_deletes(database, verification_setup):
    from sqlalchemy.exc import DBAPIError

    service, principal, case, evidence, _ = verification_setup
    service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "verify"
    )
    for model in (Verification, ChainObservation, VerificationEvaluation, CaseVerificationRequest):
        for statement in (
            model.__table__.delete(),
            model.__table__.update().values(id=uuid.uuid4()),
        ):
            with pytest.raises(DBAPIError, match="immutable record"):
                with database.begin() as connection:
                    connection.execute(statement)


def test_storage_failure_is_persisted_as_error(database, verification_setup, monkeypatch):
    service, principal, case, evidence, _ = verification_setup

    def fail(*args, **kwargs):
        raise OSError(28, "synthetic ENOSPC")

    monkeypatch.setattr("zecsolve.adapters.verifier.tempfile.TemporaryDirectory", fail)
    attempt, _ = service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "storage"
    )
    assert (attempt.result.receipt_state, attempt.result.reason_code) == (
        "ERROR",
        "VERIFIER_PROCESS_ERROR",
    )
    assert counts(database) == [1, 1, 1, 1, 0]
