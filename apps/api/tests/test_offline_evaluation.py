import uuid
from datetime import UTC, datetime

import pytest
from zecsolve.schemas.invoice import InvoicePolicyV1, InvoiceSnapshotV1, InvoiceTermsV1
from zecsolve.schemas.workflow_verification import OwnedAllocationV1


@pytest.fixture
def invoice_snapshot(report):
    return InvoiceSnapshotV1(
        invoice_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        terms=InvoiceTermsV1(
            expected_zat=200_000,
            network="mainnet",
            pool="orchard",
            receiver_address=report.output.receiver_address,
            receiver_hex=report.output.receiver_hex,
            expected_memo="glasspane first receipt",
            memo_hex=report.output.memo_hex,
        ),
        policy=InvoicePolicyV1(),
        snapshot_hash="ab" * 32,
    )


def test_offline_candidate_is_not_credit(invoice_snapshot, report):
    from zecsolve.domain.offline_evaluation import evaluate_offline

    result = evaluate_offline(invoice_snapshot, report, [])
    assert (
        result.credited_zat,
        result.outstanding_zat,
        result.candidate_zat,
        result.projected_outstanding_zat,
    ) == (0, 200_000, 100_000, 100_000)
    assert result.eligible_for_credit is False and "CHAIN_UNVERIFIED" in result.findings


def test_owned_allocations_and_foreign_conflict_are_separate(invoice_snapshot, report):
    from zecsolve.domain.offline_evaluation import evaluate_offline

    own = OwnedAllocationV1(
        output_id=report.output.identity, invoice_id=invoice_snapshot.invoice_id, amount_zat=100_000
    )
    result = evaluate_offline(invoice_snapshot, report, [own])
    assert result.credited_zat == 100_000 and result.candidate_zat == 0
    assert "ALREADY_ALLOCATED" in result.findings
    foreign = evaluate_offline(invoice_snapshot, report, [], foreign_conflict=True)
    assert foreign.credited_zat == 0 and foreign.candidate_zat == 0
    assert "DUPLICATE_CLAIM" in foreign.findings
    with pytest.raises(ValueError):
        evaluate_offline(
            invoice_snapshot, report, [own.model_copy(update={"invoice_id": uuid.uuid4()})]
        )


def test_no_attempt_has_no_recovered_candidate_and_unsupported_rules_fail(invoice_snapshot):
    from zecsolve.domain.offline_evaluation import evaluate_offline

    result = evaluate_offline(invoice_snapshot, None, [])
    assert result.candidate_zat == 0 and result.outstanding_zat == 200_000
    unsupported = invoice_snapshot.model_copy(
        update={"policy": InvoicePolicyV1(rules_version="future")}
    )
    with pytest.raises(ValueError):
        evaluate_offline(unsupported, None, [])
