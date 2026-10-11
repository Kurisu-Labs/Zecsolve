import uuid
from datetime import UTC, datetime, timedelta

import pytest
from test_offline_evaluation import invoice_snapshot  # noqa: F401
from zecsolve.schemas.resolution import DecisionObservationV1
from zecsolve.schemas.workflow_verification import OwnedAllocationV1


def observation(report, now, **changes):
    return DecisionObservationV1.model_validate(
        dict(
            observation_id=uuid.uuid4(),
            verification_id=uuid.uuid4(),
            state="CONFIRMED",
            source_kind="SIMULATED",
            source="isolated-test",
            reason_code="SIMULATED_CONFIRMATION",
            observed_at=now,
            txid=report.output.txid,
            raw_tx_sha256=report.raw_tx_sha256,
            confirmations=10,
            block_hash="ab" * 32,
            block_height=100,
        )
        | changes
    )


@pytest.mark.parametrize(
    "changes,authorized,finding",
    [
        ({}, False, "UNTRUSTED_OBSERVATION"),
        ({"confirmations": 9}, True, "INSUFFICIENT_CONFIRMATIONS"),
        ({"txid": "00" * 32}, True, "OBSERVATION_BINDING_MISMATCH"),
        ({"raw_tx_sha256": "00" * 32}, True, "OBSERVATION_BINDING_MISMATCH"),
        ({"state": "UNAVAILABLE"}, True, "CHAIN_UNVERIFIED"),
    ],
)
def test_unsafe_observation_cannot_authorize_credit(
    invoice_snapshot, report, changes, authorized, finding
):
    from zecsolve.domain.decision_rules import evaluate_decision

    now = datetime.now(UTC)
    result = evaluate_decision(
        invoice_snapshot, report, [], observation(report, now, **changes), now, authorized
    )
    assert not result.eligible_for_credit and finding in result.findings
    assert result.candidate_zat == 100_000 and result.credited_zat == 0


def test_freshness_boundaries_and_explicit_version(invoice_snapshot, report):
    from zecsolve.domain.decision_rules import evaluate_decision

    now = datetime.now(UTC)
    for age, eligible in [(60, True), (60.001, False), (-0.001, False)]:
        obs = observation(report, now - timedelta(seconds=age))
        result = evaluate_decision(invoice_snapshot, report, [], obs, now, True)
        assert result.eligible_for_credit == eligible
        assert result.rules_version == "0.2.0"
        if not eligible:
            assert "STALE_OBSERVATION" in result.findings
    assert invoice_snapshot.policy.rules_version == "0.1.0"


def test_approval_gates_preserve_memo_overpayment_and_allocation_rules(invoice_snapshot, report):
    from zecsolve.domain.decision_rules import evaluate_decision

    now = datetime.now(UTC)
    obs = observation(report, now)
    own = OwnedAllocationV1(
        output_id="synthetic-other-output",
        invoice_id=invoice_snapshot.invoice_id,
        amount_zat=150_000,
    )
    over = evaluate_decision(invoice_snapshot, report, [own], obs, now, True)
    assert not over.eligible_for_credit and "OVERPAYMENT_REVIEW" in over.findings
    missing = invoice_snapshot.model_copy(
        update={"terms": invoice_snapshot.terms.model_copy(update={"memo_hex": None})}
    )
    assert not evaluate_decision(missing, report, [], obs, now, True).eligible_for_credit
    zero = report.model_copy(update={"output": report.output.model_copy(update={"amount_zat": 0})})
    assert not evaluate_decision(invoice_snapshot, zero, [], obs, now, True).eligible_for_credit
    conflict = evaluate_decision(
        invoice_snapshot, report, [], obs, now, True, foreign_conflict=True
    )
    assert not conflict.eligible_for_credit and "DUPLICATE_CLAIM" in conflict.findings
