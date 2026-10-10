from dataclasses import replace

import pytest
from zecsolve.domain.rules import ApprovedAllocation, InvoiceTerms, evaluate
from zecsolve.domain.statuses import ChainState, ReceiptState
from zecsolve.schemas.verification import VerificationReport


def terms(report, amount=200_000):
    return InvoiceTerms(
        "invoice-a",
        amount,
        "mainnet",
        "orchard",
        report.output.receiver_hex,
        expected_memo_hex=report.output.memo_hex,
    )


def test_unapproved_recovery_is_only_a_projection(report):
    result = evaluate(terms(report), report)
    assert result.credited_zat == 0
    assert result.outstanding_zat == 200_000
    assert result.candidate_zat == 100_000
    assert result.projected_outstanding_zat == 100_000
    assert not result.eligible_for_credit
    assert "CHAIN_UNVERIFIED" in result.findings


def test_total_approved_payments_satisfy_invoice(report):
    allocations = (
        ApprovedAllocation("mainnet:orchard:tx:0", "invoice-a", 600_000),
        ApprovedAllocation("mainnet:orchard:tx:1", "invoice-a", 400_000),
    )
    result = evaluate(terms(report, 1_000_000), report, allocations)
    assert result.credited_zat == 1_000_000
    assert result.outstanding_zat == 0
    assert "MATCH" in result.findings


def test_same_invoice_retry_does_not_add_credit(report):
    allocation = ApprovedAllocation(report.output.identity, "invoice-a", 100_000)
    result = evaluate(terms(report), report, (allocation, allocation))
    assert result.credited_zat == 100_000
    assert result.candidate_zat == 0
    assert "ALREADY_ALLOCATED" in result.findings
    assert "DUPLICATE_CLAIM" not in result.findings


def test_cross_invoice_conflict_is_not_eligible_even_if_confirmed(report):
    allocation = ApprovedAllocation(report.output.identity, "invoice-b", 100_000)
    result = evaluate(terms(report), report, (allocation,), ChainState.CONFIRMED)
    assert "DUPLICATE_CLAIM" in result.findings
    assert not result.eligible_for_credit
    assert result.credited_zat == result.candidate_zat == 0


def test_recipient_and_memo_mismatch_block_matching(report):
    wrong = replace(terms(report), receiver_hex="00" * 43, expected_memo_hex="00" * 512)
    result = evaluate(wrong, report, chain_state=ChainState.CONFIRMED)
    assert "RECIPIENT_MISMATCH" in result.findings
    assert "MEMO_MISMATCH" in result.findings
    assert not result.eligible_for_credit


def test_missing_reference_requires_review_without_unique_receiver(report):
    result = evaluate(
        replace(terms(report), expected_memo_hex=None),
        report,
        chain_state=ChainState.CONFIRMED,
    )
    assert "NEEDS_REVIEW" in result.findings
    assert not result.eligible_for_credit


def test_confirmed_matched_partial_payment_can_be_proposed_for_approval(report):
    result = evaluate(terms(report), report, chain_state=ChainState.CONFIRMED)
    assert result.eligible_for_credit
    assert result.credited_zat == 0


def test_overpayment_requires_review(report):
    result = evaluate(terms(report, 50_000), report, chain_state=ChainState.CONFIRMED)
    assert "OVERPAYMENT_REVIEW" in result.findings
    assert not result.eligible_for_credit


@pytest.mark.parametrize("state", [ReceiptState.NONE, ReceiptState.UNAVAILABLE, ReceiptState.ERROR])
def test_missing_or_unavailable_is_insufficient_evidence(report, state):
    result = evaluate(terms(report), VerificationReport(receipt_state=state, reason_code="TEST"))
    assert "INSUFFICIENT_EVIDENCE" in result.findings
    assert "INVALID_EVIDENCE" not in result.findings


@pytest.mark.parametrize("amount", [0, -1, 1.5, True, 2_100_000_000_000_001])
def test_invalid_money_rejected(report, amount):
    with pytest.raises(ValueError):
        terms(report, amount)
