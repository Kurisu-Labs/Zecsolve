import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from test_resolutions import (
    SimulatedObserver,
    approve,
    counts,
    simulated_authority,
)
from test_resolutions import (
    resolution_setup as resolution_setup,
)
from test_resolutions import (
    verification_setup as verification_setup,
)
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import (
    Case,
    CaseEvent,
    CaseResolutionRequest,
    ChainObservation,
    DecisionEvaluation,
    OutputAllocation,
    Resolution,
)
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.evidence import EvidenceSubmitRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.schemas.resolution import ResolveRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.cases import CaseService
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def second_case(database, root, verifier, principal, original, receipt, raw_tx, expected=200_000):
    invoice, _ = InvoiceService(
        database, AddressNormalizer(root / "target/debug/zecsolve-verifier"), verifier.slots
    ).create(
        principal,
        InvoiceCreateRequest(
            expected_zat=expected,
            network="mainnet",
            pool="orchard",
            receiver_address=original.result.output.receiver_address,
            expected_memo="glasspane first receipt",
        ),
        "second-invoice",
    )
    case, _ = CaseService(database).create(
        principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "second-case"
    )
    evidence, _ = verifier.evidence.submit(
        principal,
        case.case_id,
        EvidenceSubmitRequest(
            receipt_json=receipt,
            raw_tx_hex=raw_tx,
            source="public fixture",
            processing_authorized=True,
        ),
        "second-evidence",
    )
    attempt, _ = verifier.verify(
        principal,
        case.case_id,
        CaseVerifyRequest(evidence_id=evidence.evidence_id),
        "second-verify",
    )
    return case, attempt


def capture(call):
    try:
        return call()
    except WorkflowError as error:
        return error


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_same_output_same_invoice_commits_once(database, resolution_setup, same_key):
    principal, case, attempt = resolution_setup
    barrier = threading.Barrier(2)

    class ConcurrentObserver(SimulatedObserver):
        def observe(self, *args):
            barrier.wait(timeout=5)
            return super().observe(*args)

    service = ResolutionService(database, ConcurrentObserver(), simulated_authority)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                service.resolve,
                principal,
                case.case_id,
                approve(attempt),
                "same" if same_key else str(i),
            )
            for i in range(2)
        ]
        outcomes = [f.result(timeout=10) for f in futures]
    assert outcomes[0][0] == outcomes[1][0]
    assert sorted(replay for _, replay in outcomes) == [False, True]
    assert counts(database) == [1, 1, 4]


def test_concurrent_two_invoices_one_output_has_one_winner_and_opaque_conflict(
    database, root, resolution_setup, verification_setup, receipt, raw_tx
):
    principal, case, attempt = resolution_setup
    verifier = verification_setup[0]
    other_case, other_attempt = second_case(
        database, root, verifier, principal, attempt, receipt, raw_tx
    )
    barrier = threading.Barrier(2)

    class ConcurrentObserver(SimulatedObserver):
        def observe(self, *args):
            barrier.wait(timeout=5)
            return super().observe(*args)

    service = ResolutionService(database, ConcurrentObserver(), simulated_authority)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                capture, lambda c=c, a=a: service.resolve(principal, c.case_id, approve(a), "race")
            )
            for c, a in ((case, attempt), (other_case, other_attempt))
        ]
        outcomes = [f.result(timeout=10) for f in futures]
    errors = [x for x in outcomes if isinstance(x, WorkflowError)]
    assert len(errors) == 1 and errors[0].code == "OUTPUT_ALLOCATION_CONFLICT"
    assert counts(database) == [1, 1, 7]
    loser = other_case if isinstance(outcomes[1], WorkflowError) else case
    winner = case if loser == other_case else other_case
    report = CaseReportService(database).get(principal, loser.case_id)
    assert str(winner.invoice_id) not in report.model_dump_json()
    assert report.balances.credited_zat == 0


def test_different_outputs_serialize_and_require_fresh_review_before_overpayment(
    database, resolution_setup, verification_setup
):
    principal, case, first = resolution_setup
    verifier = verification_setup[0]
    # Synthetic second output tests accounting; this is not another cryptographic fixture.
    synthetic = first.result.model_copy(
        update={
            "output": first.result.output.model_copy(
                update={"output_index": first.result.output.output_index + 1, "amount_zat": 150_000}
            )
        }
    )
    verifier.verifier.verify = lambda *args: synthetic
    second, _ = verifier.verify(
        principal,
        case.case_id,
        CaseVerifyRequest(evidence_id=first.evidence_id),
        "synthetic-second",
    )
    barrier = threading.Barrier(2)

    class ConcurrentObserver(SimulatedObserver):
        def observe(self, *args):
            barrier.wait(timeout=5)
            return super().observe(*args)

    service = ResolutionService(database, ConcurrentObserver(), simulated_authority)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                capture,
                lambda a=a: service.resolve(
                    principal,
                    case.case_id,
                    approve(a, expected_case_version=4),
                    str(a.verification_id),
                ),
            )
            for a in (first, second)
        ]
        outcomes = [f.result(timeout=10) for f in futures]
    errors = [x for x in outcomes if isinstance(x, WorkflowError)]
    assert len(errors) == 1 and errors[0].code == "STALE_CASE_VERSION"
    loser = second if isinstance(outcomes[1], WorkflowError) else first
    with pytest.raises(WorkflowError) as error:
        ResolutionService(database, SimulatedObserver(), simulated_authority).resolve(
            principal, case.case_id, approve(loser, expected_case_version=5), "fresh-review"
        )
    assert error.value.code == "CREDIT_INELIGIBLE"
    assert "OVERPAYMENT_REVIEW" in error.value.details["findings"]
    assert counts(database) == [1, 1, 5]


@pytest.mark.parametrize("failure", ["event", "commit"])
def test_failed_decision_rolls_back_all_business_records_but_keeps_refresh(
    database, resolution_setup, failure
):
    principal, case, attempt = resolution_setup
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_decision() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'injected rollback'; END; $$"
            )
        )
        if failure == "commit":
            connection.execute(
                text(
                    "CREATE CONSTRAINT TRIGGER fail_decision AFTER INSERT ON "
                    "case_resolution_requests DEFERRABLE INITIALLY DEFERRED "
                    "FOR EACH ROW EXECUTE FUNCTION fail_decision()"
                )
            )
        else:
            connection.execute(
                text(
                    "CREATE TRIGGER fail_decision BEFORE INSERT ON case_events FOR EACH ROW "
                    "WHEN (NEW.action = 'RESOLUTION_RECORDED') "
                    "EXECUTE FUNCTION fail_decision()"
                )
            )
    with pytest.raises(SQLAlchemyError):
        ResolutionService(database, SimulatedObserver(), simulated_authority).resolve(
            principal, case.case_id, approve(attempt), "failure"
        )
    assert counts(database) == [0, 0, 3]
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(DecisionEvaluation)) == 0
        assert session.scalar(select(func.count()).select_from(CaseResolutionRequest)) == 0
        assert session.scalar(select(func.count()).select_from(ChainObservation)) == 2
        assert session.get(Case, case.case_id).version == 3


def test_revocation_during_refresh_prevents_decision_and_refresh_persistence(
    database, resolution_setup
):
    principal, case, attempt = resolution_setup

    class RevokingObserver(SimulatedObserver):
        def observe(self, *args):
            with Session(database) as session, session.begin():
                revoke_credential(session, principal.credential_id)
            return super().observe(*args)

    with pytest.raises(WorkflowError) as error:
        ResolutionService(database, RevokingObserver(), simulated_authority).resolve(
            principal, case.case_id, approve(attempt), "revoked"
        )
    assert error.value.status == 401 and counts(database) == [0, 0, 3]


def test_foreign_merchant_and_wrong_case_cannot_decide(
    database, root, resolution_setup, verification_setup, receipt, raw_tx
):
    principal, case, attempt = resolution_setup
    with Session(database) as session, session.begin():
        foreign = provision_merchant(session, "Foreign")
    other = MerchantPrincipal(foreign.merchant_id, foreign.credential_id)
    second, _ = second_case(
        database, root, verification_setup[0], principal, attempt, receipt, raw_tx
    )
    for actor, case_id in ((other, case.case_id), (principal, second.case_id)):
        with pytest.raises(WorkflowError) as error:
            ResolutionService(database).resolve(actor, case_id, approve(attempt), "foreign")
        assert error.value.status == 404
    assert counts(database) == [0, 0, 6]


def test_terminal_cases_reject_new_actions_and_replay_original_approval(
    database, root, resolution_setup, verification_setup, receipt, raw_tx
):
    principal, _, attempt = resolution_setup
    case, full = second_case(
        database, root, verification_setup[0], principal, attempt, receipt, raw_tx, expected=100_000
    )
    service = ResolutionService(database, SimulatedObserver(), simulated_authority)
    decision, _ = service.resolve(principal, case.case_id, approve(full), "full")
    assert decision.case_state == "RESOLVED" and decision.balances.outstanding_zat == 0
    assert service.resolve(principal, case.case_id, approve(full), "new") == (decision, True)
    with pytest.raises(WorkflowError) as error:
        service.resolve(
            principal,
            case.case_id,
            ResolveRequest(action="REQUEST_EVIDENCE", reason="New", expected_case_version=4),
            "terminal",
        )
    assert error.value.code == "CASE_TERMINAL"


def test_decision_history_is_immutable_and_corrupted_replay_fails(database, resolution_setup):
    principal, case, attempt = resolution_setup
    service = ResolutionService(database, SimulatedObserver(), simulated_authority)
    decision, _ = service.resolve(principal, case.case_id, approve(attempt), "done")
    for model in (Resolution, DecisionEvaluation, OutputAllocation, CaseResolutionRequest):
        with pytest.raises(DBAPIError, match="immutable record"):
            with database.begin() as connection:
                connection.execute(model.__table__.delete())
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE case_events DISABLE TRIGGER immutable_record"))
        connection.execute(
            update(CaseEvent).where(CaseEvent.id == decision.event_id).values(event_hash="00" * 32)
        )
        connection.execute(text("ALTER TABLE case_events ENABLE TRIGGER immutable_record"))
    with pytest.raises(WorkflowError) as error:
        service.resolve(principal, case.case_id, approve(attempt), "done")
    assert error.value.status == 409


def test_default_authority_rejects_simulated_confirmation_even_when_persisted(
    database, resolution_setup
):
    principal, case, attempt = resolution_setup
    with pytest.raises(WorkflowError) as error:
        ResolutionService(database, SimulatedObserver()).resolve(
            principal, case.case_id, approve(attempt), "untrusted"
        )
    assert "UNTRUSTED_OBSERVATION" in error.value.details["findings"]
    with pytest.raises(WorkflowError) as offline:
        ResolutionService(database).resolve(principal, case.case_id, approve(attempt), "refresh")
    assert "CHAIN_UNVERIFIED" in offline.value.details["findings"]
    assert counts(database) == [0, 0, 3]


def test_confirmation_expiry_during_invoice_lock_blocks_credit(database, resolution_setup):
    principal, case, attempt = resolution_setup
    refreshed = threading.Event()

    class NearExpiryObserver(SimulatedObserver):
        def observe(self, *args):
            data = super().observe(*args)
            data["observed_at"] -= timedelta(seconds=59.8)
            refreshed.set()
            return data

    service = ResolutionService(database, NearExpiryObserver(), simulated_authority)
    with database.begin() as connection:
        connection.execute(
            text("SELECT id FROM invoices WHERE id=:id FOR UPDATE"), {"id": case.invoice_id}
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                capture, lambda: service.resolve(principal, case.case_id, approve(attempt), "stale")
            )
            assert refreshed.wait(timeout=5)
            # Wait using the database clock, not a mocked evaluator time.
            connection.execute(text("SELECT pg_sleep(0.3)"))
            connection.commit()
            result = future.result(timeout=10)
    assert isinstance(result, WorkflowError) and "STALE_OBSERVATION" in result.details["findings"]
    assert counts(database) == [0, 0, 3]
