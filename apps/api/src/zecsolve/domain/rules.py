"""Pure, conservative rule contracts; no database mutation or automatic credit."""

from dataclasses import dataclass

from zecsolve.domain.statuses import ChainState, ReceiptState
from zecsolve.schemas.verification import MAX_ZAT, RecoveredOutput, VerificationReport

RULES_VERSION = "0.1.0"


@dataclass(frozen=True)
class InvoiceTerms:
    invoice_id: str
    expected_zat: int
    network: str
    pool: str
    receiver_hex: str
    expected_memo_hex: str | None = None
    unique_receiver_binding: bool = False

    def __post_init__(self):
        if type(self.expected_zat) is not int or not 0 < self.expected_zat <= MAX_ZAT:
            raise ValueError("Expected amount must be a positive integer number of zatoshis")


@dataclass(frozen=True)
class ApprovedAllocation:
    output_id: str
    invoice_id: str
    amount_zat: int

    def __post_init__(self):
        if type(self.amount_zat) is not int or not 0 <= self.amount_zat <= MAX_ZAT:
            raise ValueError("Allocation amount must be an integer number of zatoshis")


@dataclass(frozen=True)
class Evaluation:
    rules_version: str
    findings: tuple[str, ...]
    credited_zat: int
    outstanding_zat: int
    excess_zat: int
    candidate_zat: int
    projected_outstanding_zat: int
    eligible_for_credit: bool


def evaluate(
    invoice: InvoiceTerms,
    report: VerificationReport,
    allocations: tuple[ApprovedAllocation, ...] = (),
    chain_state: ChainState = ChainState.UNAVAILABLE,
) -> Evaluation:
    """chain_state must come from a trusted observation adapter, never request input."""
    unique: dict[str, ApprovedAllocation] = {}
    for allocation in allocations:
        if allocation.output_id in unique and unique[allocation.output_id] != allocation:
            raise ValueError("Conflicting allocation records")
        unique[allocation.output_id] = allocation
    credited = sum(a.amount_zat for a in unique.values() if a.invoice_id == invoice.invoice_id)
    findings: list[str] = []
    candidate = 0
    eligible = False
    if report.receipt_state != ReceiptState.VALID:
        findings.append(
            {
                ReceiptState.INVALID: "INVALID_EVIDENCE",
                ReceiptState.UNSUPPORTED: "UNSUPPORTED_EVIDENCE",
            }.get(report.receipt_state, "INSUFFICIENT_EVIDENCE")
        )
    else:
        output: RecoveredOutput = report.output  # type: ignore[assignment]
        match = (
            output.network == invoice.network
            and output.pool == invoice.pool
            and output.receiver_hex == invoice.receiver_hex
        )
        if not match:
            findings.append("RECIPIENT_MISMATCH")
        memo_match = (
            invoice.expected_memo_hex is not None and output.memo_hex == invoice.expected_memo_hex
        )
        reference_bound = memo_match or invoice.unique_receiver_binding
        if invoice.expected_memo_hex is not None and not memo_match:
            findings.append("MEMO_MISMATCH")
        if not reference_bound:
            findings.append("NEEDS_REVIEW")
        allocated = unique.get(output.identity)
        if allocated:
            findings.append(
                "ALREADY_ALLOCATED"
                if allocated.invoice_id == invoice.invoice_id
                else "DUPLICATE_CLAIM"
            )
        if match and reference_bound and allocated is None:
            candidate = output.amount_zat
            eligible = chain_state == ChainState.CONFIRMED
            if credited + candidate > invoice.expected_zat:
                findings.append("OVERPAYMENT_REVIEW")
                eligible = False
    if chain_state != ChainState.CONFIRMED:
        findings.append("CHAIN_UNVERIFIED")
    # Invoice balance uses approved allocations; candidate recovery is a separate projection.
    findings.append(
        "UNDERPAID"
        if credited < invoice.expected_zat
        else ("OVERPAID" if credited > invoice.expected_zat else "MATCH")
    )
    if eligible:
        findings.append("ELIGIBLE_FOR_CREDIT")
    return Evaluation(
        rules_version=RULES_VERSION,
        findings=tuple(findings),
        credited_zat=credited,
        outstanding_zat=max(invoice.expected_zat - credited, 0),
        excess_zat=max(credited - invoice.expected_zat, 0),
        candidate_zat=candidate,
        projected_outstanding_zat=max(invoice.expected_zat - credited - candidate, 0),
        eligible_for_credit=eligible,
    )
