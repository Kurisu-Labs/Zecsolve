"""One database snapshot, outside-transaction decryption, then fresh authorization."""

from sqlalchemy import text

from zecsolve.adapters.evidence_crypto import EncryptedEvidence
from zecsolve.auth.access import authorize_case_access
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import EvidenceContent
from zecsolve.domain.packets import (
    ASSERTIONS,
    component,
    decoded_transaction_hash,
    implementations,
    seal_packet,
)
from zecsolve.domain.snapshots import canonical_bytes
from zecsolve.schemas.packet import (
    MAX_PACKET_BYTES,
    PacketBalanceContextV1,
    PacketEvidenceV1,
    PacketPayloadV1,
    PacketProvenanceV1,
)
from zecsolve.services.evidence import EvidenceService, read_evidence_metadata
from zecsolve.services.reports import CaseReportService
from zecsolve.services.reviewer_reports import ReviewerReportService
from zecsolve.services.verification_records import allocation_context
from zecsolve.services.workflow import WorkflowError, transaction


class CaseExportService:
    def __init__(self, engine, cipher, slots):
        self.engine = engine
        self.evidence = EvidenceService(engine, cipher, slots)

    def export(self, principal, case_id):
        merchant = isinstance(principal, MerchantPrincipal)
        with transaction(self.engine) as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            context = authorize_case_access(session, principal, case_id, "case:export")
            balance = None
            if merchant:
                report = CaseReportService(self.engine).assemble(session, principal, case_id)
                metadata = report.evidence
                selected = next(
                    (
                        item.result
                        for item in report.verifications
                        if item.verification_id == report.selected_verification_id
                    ),
                    None,
                )
                allocations, foreign = allocation_context(
                    session, report.invoice.invoice_id, selected
                )
                balance = PacketBalanceContextV1(
                    selected_verification_id=report.selected_verification_id,
                    approved_allocations=allocations,
                    foreign_conflict=foreign,
                )
            else:
                report = ReviewerReportService(self.engine).assemble(
                    session, principal, case_id, context
                )
                metadata = [
                    read_evidence_metadata(session, principal, case_id, identity)
                    for identity in sorted(context.evidence_ids)
                ]
            captured = []
            # Original components and merchant submission payload both need base64;
            # budget conservatively before loading/decrypting the whole case.
            size = len(report.model_dump_json().encode("utf-8"))
            for item in metadata:
                row = session.get(EvidenceContent, item.evidence_id)
                if row is None:
                    raise WorkflowError(409, "EVIDENCE_CONTENT_UNAVAILABLE")
                size += len(row.ciphertext) * (3 if merchant else 2)
                if size > MAX_PACKET_BYTES:
                    raise WorkflowError(413, "EXPORT_TOO_LARGE")
                captured.append((item, EncryptedEvidence(row.key_id, row.nonce, row.ciphertext)))
            authorize_case_access(session, principal, case_id, "case:export")
        # These ciphertexts, metadata, report and allocations belong to the same
        # MVCC snapshot. Never reread report state after decryption and mix versions.
        inputs = []
        for item, sealed in captured:
            request = self.evidence.decrypt_snapshot(
                principal, case_id, item.evidence_id, item, sealed
            )
            inputs.append(
                PacketEvidenceV1(
                    evidence_id=item.evidence_id,
                    provenance=PacketProvenanceV1(
                        source=item.source,
                        source_kind=item.source_kind,
                        submitted_at=item.submitted_at,
                    ),
                    receipt=component(request.receipt_json),
                    raw_transaction_hex=component(request.raw_tx_hex),
                    submission_payload=component(
                        canonical_bytes(request.model_dump(mode="json")).decode("utf-8")
                        if merchant
                        else None,
                        omitted=not merchant,
                    ),
                    decoded_transaction_sha256=decoded_transaction_hash(request.raw_tx_hex),
                )
            )
        omissions = (
            []
            if merchant
            else [
                "UNSELECTED_SECTIONS_AND_EVIDENCE",
                "HISTORICAL_ALLOCATION_CONTEXT",
                "FULL_SUBMISSION_AND_AUDIT_HISTORY",
            ]
        )
        if merchant and len(report.resolutions) != len(report.decisions):
            omissions.append("LEGACY_DECISION_CONTEXT_UNAVAILABLE")
        packet = seal_packet(
            PacketPayloadV1(
                disclosure_scope="MERCHANT" if merchant else "REVIEWER_SCOPED",
                replay_scope="LIMITED" if omissions else "FULL_HISTORY",
                omissions=omissions,
                assertions=ASSERTIONS,
                report=report,
                evidence=inputs,
                balance_context=balance,
                implementations=implementations(report),
            )
        )
        if len(packet.model_dump_json().encode("utf-8")) > MAX_PACKET_BYTES:
            raise WorkflowError(413, "EXPORT_TOO_LARGE")
        with transaction(self.engine) as session:
            # case:export revalidates the entire persisted selection and every consent.
            authorize_case_access(session, principal, case_id, "case:export")
        return packet
