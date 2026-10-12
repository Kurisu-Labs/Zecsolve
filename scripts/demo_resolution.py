"""Public fixture + explicitly simulated confirmation, in a disposable schema only."""

import base64
import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.adapters.evidence_crypto import EvidenceCipher
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.evidence import EvidenceSubmitRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.schemas.resolution import ResolveRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.cases import CaseService
from zecsolve.services.evidence import EvidenceService
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService
from zecsolve.services.verifications import VerificationService
from zecsolve.services.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class SimulatedDemoObserver:
    def observe(self, network, txid, raw_hash):
        # This fixture is an accounting test, never evidence of real chain inclusion.
        return dict(
            state="CONFIRMED",
            source_kind="SIMULATED",
            source="isolated-demo",
            reason_code="SIMULATED_CONFIRMATION",
            observed_at=datetime.now(UTC),
            network=network,
            txid=txid,
            raw_tx_sha256=raw_hash,
            confirmations=10,
            block_hash="ab" * 32,
            block_height=100,
        )


def simulated_demo_authority(observation):
    return observation.source_kind == "SIMULATED" and observation.source == "isolated-demo"


def run_demo(engine):
    slots = threading.BoundedSemaphore(2)
    cipher = EvidenceCipher("ephemeral-demo", SecretStr(base64.b64encode(os.urandom(32)).decode()))
    binary = ROOT / "target/debug/zecsolve-verifier"
    invoices = InvoiceService(engine, AddressNormalizer(binary), slots)
    cases = CaseService(engine)
    evidence = EvidenceService(engine, cipher, slots)
    verifications = VerificationService(engine, cipher, VerifierAdapter(binary), slots)
    decisions = ResolutionService(engine, SimulatedDemoObserver(), simulated_demo_authority)
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())["expected"]
    receipt = (ROOT / "fixtures/mainnet/receipt.json").read_text()
    raw = (ROOT / "fixtures/mainnet/transaction.hex").read_text()
    with Session(engine) as session, session.begin():
        issued = provision_merchant(session, "Isolated public-fixture demo")
    principal = MerchantPrincipal(issued.merchant_id, issued.credential_id)

    def create_case(key):
        invoice, _ = invoices.create(
            principal,
            InvoiceCreateRequest(
                expected_zat=200_000,
                network="mainnet",
                pool="orchard",
                receiver_address=manifest["receiver_address"],
                expected_memo=manifest["memo_text"],
            ),
            key,
        )
        return cases.create(principal, CaseCreateRequest(invoice_id=invoice.invoice_id), key)[0]

    def verify(case, content, key):
        bundle, _ = evidence.submit(
            principal,
            case.case_id,
            EvidenceSubmitRequest(
                receipt_json=content,
                raw_tx_hex=raw,
                source="public historical fixture",
                source_kind="public_fixture",
                processing_authorized=True,
            ),
            key,
        )
        return verifications.verify(
            principal, case.case_id, CaseVerifyRequest(evidence_id=bundle.evidence_id), key
        )[0]

    def request(attempt):
        return ResolveRequest(
            action="APPROVE_OUTPUT",
            verification_id=attempt.verification_id,
            expected_case_version=attempt.case_version,
            reason="Isolated SIMULATED confirmation demo",
        )

    def rejected(service, case, attempt, key):
        try:
            service.resolve(principal, case.case_id, request(attempt), key)
        except WorkflowError as error:
            return error.code
        raise AssertionError("Unsafe approval unexpectedly succeeded")

    case = create_case("first")
    attempt = verify(case, receipt, "first")
    offline = rejected(ResolutionService(engine), case, attempt, "offline")
    decision, _ = decisions.resolve(principal, case.case_id, request(attempt), "approve")
    replay, reused = decisions.resolve(principal, case.case_id, request(attempt), "approve")
    second = create_case("second")
    duplicate = verify(second, receipt, "second")
    conflict = rejected(decisions, second, duplicate, "duplicate")
    tampered = verify(
        second, (ROOT / "fixtures/negative/tampered-ock.json").read_text(), "tampered"
    )
    invalid = rejected(decisions, second, tampered, "invalid")
    report = CaseReportService(engine).get(principal, case.case_id)
    rejected_report = CaseReportService(engine).get(principal, second.case_id)
    return dict(
        source_kind="SIMULATED",
        live_confirmation=False,
        receipt_state=attempt.result.receipt_state,
        recovered_zat=attempt.result.output.amount_zat,
        offline_approval=offline,
        balances={
            name: getattr(report.balances, name)
            for name in ("credited_zat", "outstanding_zat", "candidate_zat")
        },
        retry_same_resolution=reused and replay == decision,
        second_invoice=conflict,
        tampered_receipt=tampered.result.receipt_state,
        tampered_reason=tampered.result.reason_code,
        tampered_approval=invalid,
        rejected_invoice_credited_zat=rejected_report.balances.credited_zat,
        report_scope=report.report_scope,
        references={
            "invoice_id": str(case.invoice_id),
            "case_id": str(case.case_id),
            "verification_id": str(attempt.verification_id),
            "observation_id": str(decision.evaluation.observation.observation_id),
            "evaluation_id": str(decision.evaluation.evaluation_id),
            "resolution_id": str(decision.resolution_id),
            "output_id": decision.output_id,
        },
    )


def main():
    url = os.getenv("ZECSOLVE_TEST_DATABASE_URL")
    if not url:
        raise SystemExit("Set ZECSOLVE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    schema = "zecsolve_demo_" + uuid.uuid4().hex
    admin = create_engine(url, connect_args={"connect_timeout": 3})
    engine = create_engine(
        url, connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 3}
    )
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "apps/api/migrations"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        trace = run_demo(engine)
        with engine.connect() as connection:
            trace["postgres_version"] = connection.execute(text("SHOW server_version")).scalar_one()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
    print(json.dumps(trace | {"schema_removed": True}, indent=2))


if __name__ == "__main__":
    main()
