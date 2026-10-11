import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from test_resolutions import approve
from test_resolutions import resolution_setup as resolution_setup
from test_rpc_observer import BLOCK, Node
from test_verification_api import verification_api as verification_api
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import ChainObservation, ObservationRequest
from zecsolve.schemas.resolution import DecisionObservationV1
from zecsolve.services.observations import ObservationService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def make_observer(attempt, raw_tx):
    node = Node(attempt.result.output.txid, raw_tx.strip())
    return node, node.observer()


def test_rpc_approval_roundtrips_and_later_loss_of_inclusion_keeps_history(
    database, resolution_setup, raw_tx
):
    principal, case, attempt = resolution_setup
    node, observer = make_observer(attempt, raw_tx)
    service = ResolutionService(database, observer, observer.authorizes)
    approved, _ = service.resolve(principal, case.case_id, approve(attempt), "approve")
    report = CaseReportService(database).get(principal, case.case_id)
    assert report.decisions == [approved] and not report.chain_review
    assert report.decisions[0].evaluation.observation.rpc["block"]["hash"] == BLOCK
    node.tx.update(height=-1, confirmations=0, in_active_chain=False)
    node.block["confirmations"] = -1
    refresh = ObservationService(database, observer)
    lost, _ = refresh.refresh_request(principal, case.case_id, attempt.verification_id, "reorg")
    assert lost.state == "UNCONFIRMED"
    report = CaseReportService(database).get(principal, case.case_id)
    assert report.chain_review[0].observation_id == lost.observation_id
    assert report.decisions == [approved] and report.balances.credited_zat == 100_000
    # An outage cannot clear the review flag or reverse the credit.
    node.failure = lambda *_: httpx.Response(503)
    failed, _ = refresh.refresh_request(principal, case.case_id, attempt.verification_id, "outage")
    assert failed.state == "UNAVAILABLE"
    assert CaseReportService(database).get(principal, case.case_id).chain_review
    # Completed business retries still return the original decision.
    assert service.resolve(principal, case.case_id, approve(attempt), "approve") == (approved, True)


def test_refresh_idempotency_ownership_revocation_and_concurrency(
    database, resolution_setup, raw_tx
):
    principal, case, attempt = resolution_setup
    node, observer = make_observer(attempt, raw_tx)
    service = ObservationService(database, observer)

    def refresh(_):
        return service.refresh_request(principal, case.case_id, attempt.verification_id, "refresh")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(refresh, range(2)))
    assert results[0][0] == results[1][0]
    assert sorted(r[1] for r in results) == [False, True]
    node.failure = lambda *_: pytest.fail("Completed refresh must replay without network access")
    assert refresh(None)[1]
    with pytest.raises(WorkflowError, match="IDEMPOTENCY_CONFLICT"):
        service.refresh_request(principal, case.case_id, uuid.uuid4(), "refresh")
    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Other merchant")
    other = MerchantPrincipal(issued.merchant_id, issued.credential_id)
    with pytest.raises(WorkflowError) as denied:
        service.refresh_request(other, case.case_id, attempt.verification_id, "refresh")
    assert denied.value.status == 404
    with Session(database) as session, session.begin():
        assert session.scalar(select(func.count()).select_from(ObservationRequest)) == 1
        revoke_credential(session, principal.credential_id)
    with pytest.raises(WorkflowError) as revoked:
        refresh(None)
    assert revoked.value.status == 401


@pytest.mark.parametrize("count", [1, 9])
def test_rpc_confirmation_count_remains_confirmed_but_policy_blocks(
    database, resolution_setup, raw_tx, count
):
    principal, case, attempt = resolution_setup
    node, observer = make_observer(attempt, raw_tx)
    node.tx.update(height=110 - count, confirmations=count)
    node.block.update(height=110 - count, confirmations=count)
    with pytest.raises(WorkflowError) as blocked:
        ResolutionService(database, observer, observer.authorizes).resolve(
            principal, case.case_id, approve(attempt), "approve"
        )
    assert "INSUFFICIENT_CONFIRMATIONS" in blocked.value.details["findings"]
    report = CaseReportService(database).get(principal, case.case_id)
    assert report.decision_observations[0].state == "CONFIRMED"
    assert report.balances.credited_zat == 0


def test_http_refresh_authority_spoofing_and_historical_v1_compatibility(verification_api, raw_tx):
    api, headers, case, evidence = verification_api
    attempt = api.post(
        f"/api/cases/{case}/verify", headers=headers, json={"evidence_id": evidence}
    ).json()
    node = Node(attempt["result"]["output"]["txid"], raw_tx.strip())
    observer = node.observer()
    api.app.state.chain_observer = observer
    api.app.state.chain_authority = observer.authorizes
    path = f"/api/cases/{case}/chain-observations"
    payload = {"verification_id": attempt["verification_id"]}
    assert api.post(path, json=payload).status_code == 401
    assert api.post(path, headers=headers, json=payload | {"confirmations": 100}).status_code == 422
    response = api.post(path, headers=headers, json=payload)
    assert response.status_code == 201 and response.json()["source_kind"] == "RPC"
    replay = api.post(path, headers=headers, json=payload)
    assert replay.status_code == 200 and replay.json() == response.json()
    approved = api.post(
        f"/api/cases/{case}/resolve",
        headers=headers,
        json={
            "action": "APPROVE_OUTPUT",
            "verification_id": attempt["verification_id"],
            "expected_case_version": 3,
            "reason": "Reviewed",
        },
    )
    assert approved.status_code == 201
    report = api.get(f"/api/cases/{case}/report", headers=headers)
    assert report.status_code == 200 and report.json()["balances"]["credited_zat"] == 100_000
    old = DecisionObservationV1(
        observation_id=uuid.uuid4(),
        verification_id=uuid.uuid4(),
        state="CONFIRMED",
        source_kind="RPC",
        source=observer.source,
        reason_code="OLD",
        observed_at=datetime.now(UTC) - timedelta(days=1),
        network="mainnet",
        txid=node.tx["txid"],
        raw_tx_sha256=attempt["result"]["raw_tx_sha256"],
        confirmations=10,
        block_hash=BLOCK,
        block_height=100,
    )
    assert not observer.authorizes(old)
    assert "rpc" not in old.model_dump(mode="json")


def test_new_observation_history_blocks_destructive_downgrade(
    database, resolution_setup, raw_tx, root
):
    principal, case, attempt = resolution_setup
    _, observer = make_observer(attempt, raw_tx)
    ObservationService(database, observer).refresh_request(
        principal, case.case_id, attempt.verification_id, "refresh"
    )
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with pytest.raises(RuntimeError, match="Cannot discard RPC"):
        with database.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0007")
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(ChainObservation)) == 2


def test_refresh_revocation_during_rpc_discards_result(database, resolution_setup, raw_tx):
    principal, case, attempt = resolution_setup
    _, observer = make_observer(attempt, raw_tx)
    original = observer.observe

    def revoke(*args):
        result = original(*args)
        with Session(database) as session, session.begin():
            revoke_credential(session, principal.credential_id)
        return result

    observer.observe = revoke
    with pytest.raises(WorkflowError) as denied:
        ObservationService(database, observer).refresh_request(
            principal, case.case_id, attempt.verification_id, "refresh"
        )
    assert denied.value.status == 401
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(ChainObservation)) == 1


def test_reorg_blocks_another_output_until_prior_inclusion_is_restored(
    database, resolution_setup, verification_setup, raw_tx
):
    from zecsolve.schemas.workflow_verification import CaseVerifyRequest

    principal, case, first = resolution_setup
    node, observer = make_observer(first, raw_tx)
    resolver = ResolutionService(database, observer, observer.authorizes)
    resolver.resolve(principal, case.case_id, approve(first), "approve-first")
    node.tx.update(height=-1, confirmations=0, in_active_chain=False)
    node.block["confirmations"] = -1
    ObservationService(database, observer).refresh_request(
        principal, case.case_id, first.verification_id, "reorg"
    )
    # A synthetic second transaction isolates the accounting guard, not cryptography.
    verifier = verification_setup[0]
    synthetic = first.result.model_copy(
        update={"output": first.result.output.model_copy(update={"txid": "12" * 32})}
    )
    verifier.verifier.verify = lambda *args: synthetic
    second, _ = verifier.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=first.evidence_id), "second"
    )
    second_node, second_observer = make_observer(second, raw_tx)
    resolver = ResolutionService(database, second_observer, second_observer.authorizes)
    with pytest.raises(WorkflowError, match="APPROVED_OUTPUT_CHAIN_REVIEW"):
        resolver.resolve(principal, case.case_id, approve(second), "approve-second")
    assert CaseReportService(database).get(principal, case.case_id).balances.credited_zat == 100_000
    node.tx.update(height=109, confirmations=1, in_active_chain=True)
    node.block.update(height=109, confirmations=1)
    ObservationService(database, observer).refresh_request(
        principal, case.case_id, first.verification_id, "reincluded-below-policy"
    )
    assert CaseReportService(database).get(principal, case.case_id).chain_review
    node.tx.update(height=100, confirmations=10, in_active_chain=True)
    node.block.update(height=100, confirmations=10)
    ObservationService(database, observer).refresh_request(
        principal, case.case_id, first.verification_id, "restored"
    )
    restored = CaseReportService(database).get(principal, case.case_id)
    assert not restored.chain_review
    decision, _ = resolver.resolve(principal, case.case_id, approve(second), "approve-second")
    assert decision.balances.credited_zat == 200_000


def test_refresh_history_is_immutable_and_failed_retry_write_rolls_back(
    database, resolution_setup, raw_tx
):
    from sqlalchemy import event, text
    from sqlalchemy.exc import DBAPIError

    principal, case, attempt = resolution_setup
    _, observer = make_observer(attempt, raw_tx)
    service = ObservationService(database, observer)

    def fail_request(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO observation_requests"):
            raise RuntimeError("injected retry persistence failure")

    event.listen(database, "before_cursor_execute", fail_request)
    try:
        with pytest.raises(RuntimeError, match="injected"):
            service.refresh_request(principal, case.case_id, attempt.verification_id, "first")
    finally:
        event.remove(database, "before_cursor_execute", fail_request)
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(ChainObservation)) == 1
        assert session.scalar(select(func.count()).select_from(ObservationRequest)) == 0
    service.refresh_request(principal, case.case_id, attempt.verification_id, "first")
    for statement in (
        "DELETE FROM observation_requests",
        "UPDATE observation_requests SET idempotency_key='changed'",
        "DELETE FROM chain_observations",
    ):
        with pytest.raises(DBAPIError):
            with database.begin() as connection:
                connection.execute(text(statement))


def test_unknown_observation_format_cannot_hide_chain_review(database, resolution_setup, raw_tx):
    from sqlalchemy import text, update
    from zecsolve.services.chain_review import read_chain_review

    principal, case, attempt = resolution_setup
    node, observer = make_observer(attempt, raw_tx)
    ResolutionService(database, observer, observer.authorizes).resolve(
        principal, case.case_id, approve(attempt), "approve"
    )
    node.tx.update(height=-1, confirmations=0, in_active_chain=False)
    node.block["confirmations"] = -1
    lost = ObservationService(database, observer).refresh(
        principal, case.case_id, attempt.verification_id
    )
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE chain_observations DISABLE TRIGGER immutable_record"))
        connection.execute(
            update(ChainObservation)
            .where(ChainObservation.id == lost.observation_id)
            .values(provenance={"schema_version": "unknown"})
        )
        connection.execute(text("ALTER TABLE chain_observations ENABLE TRIGGER immutable_record"))
    with (
        Session(database) as session,
        pytest.raises(WorkflowError, match="OBSERVATION_HISTORY_UNAVAILABLE"),
    ):
        read_chain_review(session, principal, case.case_id)
