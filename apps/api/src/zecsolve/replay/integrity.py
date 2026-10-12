"""Historical hashes and relationships; no trust in a self-consistent author."""

import hashlib
import json

from zecsolve.domain.events import validate_event_chain
from zecsolve.domain.packets import decoded_transaction_hash, unique_object
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.evidence import EvidenceSubmitRequest, EvidenceSubmitRequestV2
from zecsolve.schemas.resolution import MerchantCaseReportV1


def require(condition):
    if not condition:
        raise ValueError("Historical integrity or linkage mismatch")


def validate_history(payload):
    report = payload.report
    evidence = {item.evidence_id: item for item in payload.evidence}
    for item in payload.evidence:
        for component in (item.receipt, item.raw_transaction_hex, item.submission_payload):
            if component.availability == "PRESENT":
                require(
                    hashlib.sha256(component.text().encode("utf-8")).hexdigest() == component.sha256
                )
        require(
            decoded_transaction_hash(item.raw_transaction_hex.text())
            == item.decoded_transaction_sha256
        )
    for metadata in report.evidence or []:
        item = evidence.get(metadata.evidence_id)
        if item is None:
            require(payload.replay_scope == "LIMITED")
            continue
        for original, expected in (
            (item.receipt, metadata.receipt_sha256),
            (item.raw_transaction_hex, metadata.raw_tx_hex_sha256),
        ):
            if original.availability != "OMITTED":
                require(original.sha256 == expected)
        require(
            (item.provenance.source, item.provenance.source_kind, item.provenance.submitted_at)
            == (metadata.source, metadata.source_kind, metadata.submitted_at)
        )
    if not isinstance(report, MerchantCaseReportV1):
        return
    invoice = report.invoice
    case = report.case
    require((invoice.invoice_id, invoice.merchant_id) == (case.invoice_id, case.merchant_id))
    require(report.policy == invoice.policy)
    require(
        invoice.snapshot_hash
        == digest(invoice.model_dump(mode="json", exclude={"created_at", "snapshot_hash"}))
    )
    validate_event_chain(report.events, case.case_id, case.version)
    events = {item.event_id: item for item in report.events}
    require(len(events) == len(report.events))
    require(
        report.events[0].payload
        == {
            "invoice_id": str(invoice.invoice_id),
            "invoice_snapshot_hash": invoice.snapshot_hash,
            "policy_id": str(invoice.policy_id),
        }
    )
    metadata = {item.evidence_id: item for item in report.evidence}
    require(len(metadata) == len(report.evidence))
    for item in report.evidence:
        require((item.case_id, item.merchant_id) == (case.case_id, case.merchant_id))
        event = events[item.event_id]
        require(
            event.action == "EVIDENCE_SUBMITTED"
            and event.payload["evidence_id"] == str(item.evidence_id)
        )
        require(
            event.payload["payload_sha256"] == item.payload_sha256
            and event.sequence == item.case_version
        )
        stored = evidence[item.evidence_id].submission_payload
        if stored.availability != "PRESENT":
            require(payload.replay_scope == "LIMITED")
            continue
        require(stored.sha256 == item.payload_sha256)
        model = EvidenceSubmitRequestV2 if item.schema_version == "2" else EvidenceSubmitRequest
        submitted = model.model_validate(json.loads(stored.text(), object_pairs_hook=unique_object))
        require(digest(submitted.model_dump(mode="json")) == item.payload_sha256)
        require(submitted.receipt_json == evidence[item.evidence_id].receipt.text())
        require(submitted.raw_tx_hex == evidence[item.evidence_id].raw_transaction_hex.text())
        for key in (
            "source",
            "source_kind",
            "processing_authorized",
            "share_with_reviewers",
            "disclosure_version",
        ):
            require(getattr(submitted, key) == getattr(item, key))
        require(getattr(submitted, "claim_id", None) == getattr(item, "claim_id", None))
        if item.schema_version == "2":
            require(event.payload["consent_id"] == str(item.consent_id))
            require(event.payload["claim_id"] == (str(item.claim_id) if item.claim_id else None))
        actor = (
            "credential:" + str(item.submitted_by)
            if item.submitted_by
            else "grant:" + str(item.actor_grant_id)
        )
        require(event.actor == actor)
    attempts = {item.verification_id: item for item in report.verifications}
    require(len(attempts) == len(report.verifications))
    require(report.evaluations == [item.evaluation for item in report.verifications])
    require(report.chain_observations == [item.observation for item in report.verifications])
    for item in report.verifications:
        snapshot, observation = item.evaluation, item.observation
        require(item.evidence_id in metadata)
        require((item.case_id, item.merchant_id) == (case.case_id, case.merchant_id))
        require(snapshot.inputs.invoice == invoice and snapshot.inputs.verification == item.result)
        require(
            (
                snapshot.case_id,
                snapshot.merchant_id,
                snapshot.verification_id,
                snapshot.observation_id,
            )
            == (case.case_id, case.merchant_id, item.verification_id, observation.observation_id)
        )
        require(observation.verification_id == item.verification_id)
        require(observation.txid == (item.result.output.txid if item.result.output else None))
        require(observation.raw_tx_sha256 == item.result.raw_tx_sha256)
        require(
            snapshot.snapshot_hash
            == digest(snapshot.model_dump(mode="json", exclude={"snapshot_hash"}))
        )
        event = events[item.event_id]
        require(event.action == "VERIFICATION_RECORDED" and event.sequence == item.case_version)
        require(event.actor == "credential:" + str(item.actor_id))
        require(
            event.payload
            == {
                "verification_id": str(item.verification_id),
                "evidence_id": str(item.evidence_id),
                "observation_id": str(observation.observation_id),
                "evaluation_id": str(snapshot.evaluation_id),
                "result_sha256": digest(item.result.model_dump(mode="json")),
                "evaluation_sha256": snapshot.snapshot_hash,
                "case_version": item.case_version,
                "case_state": item.case_state,
            }
        )
        require(
            all(
                owned.invoice_id == invoice.invoice_id
                for owned in snapshot.inputs.approved_allocations
            )
        )
    require(report.decision_evaluations == [item.evaluation for item in report.decisions])
    decisions = {item.resolution_id: item for item in report.decisions}
    require(len(decisions) == len(report.decisions))
    observations = {item.observation_id: item for item in report.decision_observations}
    require(len(observations) == len(report.decision_observations))
    for obs in report.decision_observations:
        require(obs.verification_id in attempts)
    for item in report.decisions:
        snapshot = item.evaluation
        require(
            (item.case_id, item.merchant_id, item.invoice_id)
            == (case.case_id, case.merchant_id, invoice.invoice_id)
        )
        require(snapshot.invoice == invoice)
        require(
            (
                snapshot.case_id,
                snapshot.merchant_id,
                snapshot.verification_id,
                snapshot.evaluated_at,
            )
            == (case.case_id, case.merchant_id, item.verification_id, item.decided_at)
        )
        require(
            snapshot.verification
            == (attempts[item.verification_id].result if item.verification_id else None)
        )
        if snapshot.observation:
            require(snapshot.observation == observations[snapshot.observation.observation_id])
        require(
            snapshot.snapshot_hash
            == digest(snapshot.model_dump(mode="json", exclude={"snapshot_hash"}))
        )
        require(
            all(owned.invoice_id == invoice.invoice_id for owned in snapshot.approved_allocations)
        )
        event = events[item.event_id]
        require(
            event.action == "RESOLUTION_RECORDED"
            and event.actor == "credential:" + str(item.actor_id)
        )
        require(event.sequence == item.case_version)
        require(
            event.payload
            == {
                "resolution_id": str(item.resolution_id),
                "evaluation_id": str(snapshot.evaluation_id),
                "outcome_sha256": digest(item.model_dump(mode="json")),
                "case_version": item.case_version,
                "case_state": item.case_state,
            }
        )
    for item in report.resolutions:
        if item.resolution_id not in decisions:
            require(payload.replay_scope == "LIMITED")
            continue
        decision = decisions[item.resolution_id]
        require(
            (item.outcome, item.reason, item.approved_by, item.approved_at)
            == (
                decision.action,
                decision.reason,
                "credential:" + str(decision.actor_id),
                decision.decided_at,
            )
        )
    if payload.balance_context:
        require(payload.balance_context.selected_verification_id == report.selected_verification_id)
        require(
            report.selected_verification_id is None or report.selected_verification_id in attempts
        )
        require(
            all(
                item.invoice_id == invoice.invoice_id
                for item in payload.balance_context.approved_allocations
            )
        )
    # Each recorded v2 claim binds its content/consent to its original request hash.
    claims = {item.claim_id: item for item in report.claims}
    require(len(claims) == len(report.claims))
    for event in report.events:
        if event.action == "CLAIM_SUBMITTED":
            import uuid

            claim = claims[uuid.UUID(event.payload["claim_id"])]
            require(
                event.payload["request_sha256"]
                == digest(
                    {
                        "note": claim.note,
                        "reported_txid": claim.reported_txid,
                        "disclosure_version": event.payload["disclosure_version"],
                        "processing_authorized": event.payload["processing_authorized"],
                        "share_with_reviewers": event.payload["share_with_reviewers"],
                    }
                )
            )

    if payload.replay_scope == "FULL_HISTORY":
        require(
            {
                event.payload["evidence_id"]
                for event in report.events
                if event.action == "EVIDENCE_SUBMITTED"
            }
            == {str(key) for key in metadata}
        )
        require(
            {
                event.payload["verification_id"]
                for event in report.events
                if event.action == "VERIFICATION_RECORDED"
            }
            == {str(key) for key in attempts}
        )
        require(
            {
                event.payload["resolution_id"]
                for event in report.events
                if event.action == "RESOLUTION_RECORDED"
            }
            == {str(key) for key in decisions}
        )
        require(case.created_at == report.events[0].at)
        require(
            case.state == (report.events[-1].payload["case_state"] if case.version > 1 else "OPEN")
        )
