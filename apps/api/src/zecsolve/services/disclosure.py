"""Shared disclosure primitives for report, evidence reads, and later scoped exports."""

from zecsolve.auth.access import authorize_case_access
from zecsolve.schemas.disclosure import ReviewerEvidenceV1, ReviewerObservationV1


def selected_evidence(session, principal, case_id, context):
    for evidence_id in context.evidence_ids:
        authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
    return set(context.evidence_ids)


def project_evidence(metadata):
    return ReviewerEvidenceV1(
        evidence_id=metadata.evidence_id,
        submitted_at=metadata.submitted_at,
        source=metadata.source,
        source_kind=metadata.source_kind,
        receipt_sha256=metadata.receipt_sha256,
        raw_tx_hex_sha256=metadata.raw_tx_hex_sha256,
    )


def shared_claim_event(claim, events):
    # Historical merchant assertions and evidence links cannot fabricate claim consent.
    return next(
        (
            event
            for event in events
            if event.action == "CLAIM_SUBMITTED"
            and event.payload.get("claim_id") == str(claim.id)
            and event.payload.get("processing_authorized") is True
            and event.payload.get("share_with_reviewers") is True
        ),
        None,
    )


def project_observation(item):
    # Provenance dictionaries are not a reviewer disclosure contract. Keep only
    # these typed observation fields; never pass arbitrary nested RPC metadata.
    return ReviewerObservationV1(
        observation_id=item.observation_id,
        verification_id=item.verification_id,
        state=item.state,
        source_kind=getattr(item, "source_kind", "OFFLINE"),
        source=item.source,
        reason_code=item.reason_code,
        observed_at=item.observed_at,
        network=item.network,
        txid=item.txid,
        raw_tx_sha256=item.raw_tx_sha256,
        confirmations=item.confirmations,
        block_hash=item.block_hash,
        block_height=item.block_height,
    )
