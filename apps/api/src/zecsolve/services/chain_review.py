"""Later loss of inclusion flags review without reversing an immutable approval."""

from sqlalchemy import select

from zecsolve.db.models import ChainObservation, Resolution
from zecsolve.schemas.resolution import ChainReviewV1
from zecsolve.services.observations import read_decision_observation
from zecsolve.services.resolution_records import read_resolution


def chain_review(decisions, observations):
    findings = []
    for decision in decisions:
        original = decision.evaluation.observation
        if decision.action != "APPROVE_OUTPUT" or original is None or original.source_kind != "RPC":
            continue
        later = sorted(
            (
                item
                for item in observations
                if item.source_kind == "RPC"
                and item.source == original.source
                and (item.network, item.txid, item.raw_tx_sha256)
                == (original.network, original.txid, original.raw_tx_sha256)
                and item.observed_at > original.observed_at
            ),
            key=lambda item: (item.observed_at, str(item.observation_id)),
        )
        # An unavailable refresh cannot erase a previously observed loss of inclusion.
        relevant = [item for item in later if item.state != "UNAVAILABLE"]
        if relevant and relevant[-1].state == "UNCONFIRMED":
            findings.append(
                ChainReviewV1(
                    resolution_id=decision.resolution_id, observation_id=relevant[-1].observation_id
                )
            )
    return findings


def read_chain_review(session, principal, case_id):
    decisions = [
        read_resolution(session, principal, case_id, row.id)
        for row in session.scalars(
            select(Resolution).where(
                Resolution.case_id == case_id,
                Resolution.merchant_id == principal.merchant_id,
                Resolution.workflow_version == "1",
            )
        )
    ]
    observations = [
        read_decision_observation(session, principal, case_id, row.id)
        for row in session.scalars(
            select(ChainObservation).where(
                ChainObservation.case_id == case_id,
                ChainObservation.merchant_id == principal.merchant_id,
            )
        )
        if row.provenance
        and row.provenance.get("schema_version")
        in ("decision-observation-v1", "decision-observation-v2")
    ]
    return chain_review(decisions, observations)
