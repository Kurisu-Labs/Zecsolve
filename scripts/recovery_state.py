"""Private worker injected into disposable containers by check_deployment --recovery.

The production app never imports this simulated accounting composition.
"""

import base64
import hashlib
import json
import os
import sys
import threading
import uuid
from datetime import UTC, datetime

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.adapters.evidence_crypto import EvidenceCipher
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant
from zecsolve.db.models import Base, Claim, Invoice, OutputAllocation
from zecsolve.db.session import make_engine
from zecsolve.deployment.settings import DeploymentSettings, application_settings
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.evidence import EvidenceSubmitRequest, EvidenceSubmitRequestV2
from zecsolve.schemas.grant import GrantCreateRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.schemas.resolution import ResolveRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.cases import CaseService
from zecsolve.services.evidence import EvidenceService
from zecsolve.services.grants import GrantService
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService
from zecsolve.services.verifications import VerificationService
from zecsolve.services.workflow import WorkflowError


class SimulatedRecoveryObserver:
    def observe(self, network, txid, raw_hash):
        return dict(
            state="CONFIRMED",
            source_kind="SIMULATED",
            source="isolated-recovery-rehearsal",
            reason_code="SIMULATED_CONFIRMATION",
            observed_at=datetime.now(UTC),
            network=network,
            txid=txid,
            raw_tx_sha256=raw_hash,
            confirmations=10,
            block_hash="ab" * 32,
            block_height=100,
        )


def fingerprint(engine):
    records, counts = {}, {}
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            for name, table in sorted(Base.metadata.tables.items()):
                rows = [
                    json.dumps(dict(row), sort_keys=True, default=str)
                    for row in connection.execute(select(table)).mappings()
                ]
                records[name] = sorted(rows)
                counts[name] = len(rows)
    return {
        "rows_sha256": hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
        "counts": counts,
    }


def execute(engine, settings, data):
    slots = threading.BoundedSemaphore(2)
    cipher = EvidenceCipher(settings.evidence_key_id, settings.evidence_key)
    evidence = EvidenceService(engine, cipher, slots)
    if data["phase"] == "seed":
        with Session(engine) as session, session.begin():
            issued = provision_merchant(session, "Public-fixture recovery rehearsal")
        merchant = MerchantPrincipal(issued.merchant_id, issued.credential_id)
        invoice, _ = InvoiceService(
            engine, AddressNormalizer(settings.verifier_path), slots
        ).create(
            merchant,
            InvoiceCreateRequest(
                expected_zat=200_000,
                network="mainnet",
                pool="orchard",
                receiver_address=data["fixture"]["receiver_address"],
                expected_memo=data["fixture"]["memo_text"],
            ),
            "recovery-invoice",
        )
        case, _ = CaseService(engine).create(
            merchant, CaseCreateRequest(invoice_id=invoice.invoice_id), "recovery-case"
        )
        legacy, _ = evidence.submit(
            merchant,
            case.case_id,
            EvidenceSubmitRequest.model_validate(data["legacy_request"]),
            "recovery-legacy",
        )
        granted, _ = GrantService(engine).create(
            merchant, case.case_id, GrantCreateRequest(scope={"role": "customer"}), "recovery-grant"
        )
        return dict(
            merchant_id=str(issued.merchant_id),
            credential_id=str(issued.credential_id),
            token=issued.token,
            case_id=str(case.case_id),
            access_code=granted.access_code,
            grant_id=str(granted.grant.grant_id),
            legacy_id=str(legacy.evidence_id),
        )
    merchant = MerchantPrincipal(uuid.UUID(data["merchant_id"]), uuid.UUID(data["credential_id"]))
    case = uuid.UUID(data["case_id"])
    if data["phase"] in {"verify", "approve"}:
        attempt, _ = VerificationService(
            engine, cipher, VerifierAdapter(settings.verifier_path), slots
        ).verify(
            merchant,
            case,
            CaseVerifyRequest(evidence_id=uuid.UUID(data["evidence_id"])),
            "recovery-verify",
        )
        assert attempt.result.receipt_state == "VALID"
        request = ResolveRequest(
            action="APPROVE_OUTPUT",
            verification_id=attempt.verification_id,
            expected_case_version=attempt.case_version,
            reason="SIMULATED recovery accounting fixture",
        )
        if data["phase"] == "verify":
            return request.model_dump(mode="json")
        service = ResolutionService(
            engine,
            SimulatedRecoveryObserver(),
            lambda observation: (
                observation.source_kind == "SIMULATED"
                and observation.source == "isolated-recovery-rehearsal"
            ),
        )
        outcome, replayed = service.resolve(merchant, case, request, "recovery-approve")
        assert not replayed and outcome.allocated_zat == 100_000
        return {
            "request": request.model_dump(mode="json"),
            "outcome": outcome.model_dump(mode="json"),
        }
    if data["phase"] == "check":
        report = CaseReportService(engine).get(merchant, case)
        assert (
            report.balances.credited_zat == 100_000 and report.balances.outstanding_zat == 100_000
        )
        assert report.report_scope == "SIMULATED_DECISIONS"
        for field, request, model in (
            ("legacy_id", "legacy_request", EvidenceSubmitRequest),
            ("evidence_id", "evidence_request", EvidenceSubmitRequestV2),
        ):
            assert evidence.read_content(
                merchant, case, uuid.UUID(data[field])
            ) == model.model_validate(data[request])
        for key_id, key in (
            (settings.evidence_key_id, SecretStr(base64.b64encode(bytes(32)).decode())),
            ("missing-recovery-key", settings.evidence_key),
        ):
            wrong = EvidenceService(engine, EvidenceCipher(key_id, key), slots)
            try:
                wrong.read_content(merchant, case, uuid.UUID(data["evidence_id"]))
            except WorkflowError as error:
                assert error.code in {"EVIDENCE_INTEGRITY_ERROR", "EVIDENCE_KEY_UNAVAILABLE"}
            else:
                raise AssertionError("Incorrect evidence key accepted")
        # Constraint/trigger probes each roll back; successful restore includes schema protections.
        with engine.connect() as connection:
            allocation = dict(
                connection.execute(select(OutputAllocation.__table__)).mappings().one()
            )
        for statement, code in (
            (OutputAllocation.__table__.insert().values(**allocation), "23505"),
            (Invoice.__table__.update().values(expected_zat=1), "P0001"),
            (
                Claim.__table__.insert().values(case_id=uuid.uuid4(), claimant_role="customer"),
                "23503",
            ),
        ):
            try:
                with engine.begin() as connection:
                    connection.execute(statement)
                    raise AssertionError("Restored database protection missing")
            except DBAPIError as error:
                assert error.orig.sqlstate == code
        return fingerprint(engine)
    raise ValueError("Unknown recovery phase")


if __name__ == "__main__":
    if os.environ.get("ZECSOLVE_REHEARSAL_ONLY") != "disposable":
        raise SystemExit("Only the disposable rehearsal harness may invoke this worker")
    settings = application_settings(DeploymentSettings())
    engine = make_engine(settings)
    try:
        print(json.dumps(execute(engine, settings, json.load(sys.stdin))))
    finally:
        engine.dispose()
