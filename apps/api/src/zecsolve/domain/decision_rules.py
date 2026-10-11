"""Policy-aware decisions; retain the 0.1.0 offline evaluator for historical replay."""

from zecsolve.domain.offline_evaluation import evaluate_offline
from zecsolve.schemas.resolution import DecisionEvaluationV1

RULES_VERSION = "0.2.0"


def evaluate_decision(
    invoice, report, allocations, observation, now, source_authorized, foreign_conflict=False
):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Evaluation time must be timezone aware")
    base = evaluate_offline(invoice, report, allocations, foreign_conflict)
    findings = list(base.findings)
    blockers = []
    if observation is None or observation.state != "CONFIRMED":
        blockers.append("CHAIN_UNVERIFIED")
    else:
        findings.remove("CHAIN_UNVERIFIED")
        if not source_authorized:
            blockers.append("UNTRUSTED_OBSERVATION")
        output = report.output if report else None
        if (
            output is None
            or observation.network != output.network
            or observation.txid != output.txid
            or observation.raw_tx_sha256 != report.raw_tx_sha256
        ):
            blockers.append("OBSERVATION_BINDING_MISMATCH")
        age = (now - observation.observed_at).total_seconds()
        if age < 0 or age > invoice.policy.max_observation_age_seconds:
            blockers.append("STALE_OBSERVATION")
        if observation.confirmations < invoice.policy.minimum_confirmations:
            blockers.append("INSUFFICIENT_CONFIRMATIONS")
    eligible = not blockers and base.candidate_zat > 0 and "OVERPAYMENT_REVIEW" not in findings
    if report and report.output and report.output.amount_zat == 0:
        blockers.append("ZERO_VALUE_OUTPUT")
    findings.extend(item for item in blockers if item not in findings)
    if eligible:
        findings.append("ELIGIBLE_FOR_CREDIT")
    return DecisionEvaluationV1(
        **(
            base.model_dump()
            | {
                "rules_version": RULES_VERSION,
                "findings": findings,
                "eligible_for_credit": eligible,
            }
        )
    )
