"""Opt-in live RPC validation with public fixtures and a disposable PostgreSQL schema.

Uses the application's real authenticated ASGI routes, verifier and configured
ZebraObserver. Never substitutes an observer, authority check or RPC transport.
Not part of offline CI: the operator must explicitly configure RPC and a test DB.
"""

import argparse
import base64
import hashlib
import json
import logging
import os
import platform
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant
from zecsolve.config import Settings
from zecsolve.main import create_app

ROOT = Path(__file__).resolve().parents[1]


class ValidationFailure(Exception):
    """Only fixed, secret-free diagnostic messages belong in this exception."""


def require(condition, message):
    if not condition:
        raise ValidationFailure(message)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_workflow(settings, engine):
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
    file_hashes = {}
    for item in manifest["files"]:
        actual = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        require(actual == item["sha256"], "Fixture differs from the pinned public manifest")
        file_hashes[item["path"]] = actual
    fixture = manifest["expected"]
    with Session(engine) as session, session.begin():
        merchant = provision_merchant(session, "M3.1 disposable public-fixture validation")
    headers = {"Authorization": "Bearer " + merchant.token}
    steps = []
    app = create_app(settings)
    with TestClient(app) as api:

        def request(method, path, expected_status, *, payload=None, key=None, authenticated=True):
            sent_headers = dict(headers) if authenticated else {}
            if key:
                sent_headers["Idempotency-Key"] = key
            start = monotonic()
            response = api.request(method, path, headers=sent_headers, json=payload)
            steps.append(
                dict(
                    method=method,
                    path=path,
                    status=response.status_code,
                    idempotency_replayed=response.headers.get("Idempotency-Replayed"),
                    elapsed_ms=round((monotonic() - start) * 1000),
                )
            )
            require(
                response.status_code == expected_status,
                f"{method} {path}: expected {expected_status}, got {response.status_code}",
            )
            return response.json()

        readiness = request("GET", "/health/ready", 200, authenticated=False)
        identity = request("GET", "/api/auth/me", 200)
        invoice = request(
            "POST",
            "/api/invoices",
            201,
            key="m3-invoice",
            payload=dict(
                expected_zat=200_000,
                network="mainnet",
                pool="orchard",
                receiver_address=fixture["receiver_address"],
                expected_memo=fixture["memo_text"],
            ),
        )
        case = request(
            "POST",
            "/api/cases",
            201,
            key="m3-case",
            payload={"invoice_id": invoice["invoice_id"]},
        )
        path = f"/api/cases/{case['case_id']}"
        evidence = request(
            "POST",
            path + "/evidence",
            201,
            key="m3-evidence",
            payload=dict(
                receipt_json=(ROOT / "fixtures/mainnet/receipt.json").read_text(),
                raw_tx_hex=(ROOT / "fixtures/mainnet/transaction.hex").read_text(),
                source="Public Glasspane historical mainnet fixture",
                source_kind="public_fixture",
                processing_authorized=True,
            ),
        )
        attempt = request(
            "POST",
            path + "/verify",
            201,
            key="m3-verify",
            payload={"evidence_id": evidence["evidence_id"]},
        )
        result = attempt["result"]
        require(result["receipt_state"] == "VALID", "Public receipt did not verify")
        require(result["output"]["amount_zat"] == 100_000, "Unexpected recovered amount")
        require(result["output"]["txid"] == fixture["txid"], "Unexpected transaction binding")
        require(attempt["observation"]["state"] == "UNAVAILABLE", "Offline state changed")
        before = request("GET", path + "/report", 200)
        require(before["balances"]["credited_zat"] == 0, "Credit exists before approval")
        refresh_body = {"verification_id": attempt["verification_id"]}
        request(
            "POST",
            path + "/chain-observations",
            401,
            payload=refresh_body,
            key="m3-anonymous",
            authenticated=False,
        )
        refresh = request(
            "POST", path + "/chain-observations", 201, payload=refresh_body, key="m3-refresh"
        )
        require(refresh["state"] == "CONFIRMED", "Live refresh did not confirm; rerun separately")
        replay = request(
            "POST", path + "/chain-observations", 200, payload=refresh_body, key="m3-refresh"
        )
        require(replay == refresh, "Refresh retry changed the observation")
        require(steps[-1]["idempotency_replayed"] == "true", "Refresh retry was not replayed")
        resolve_body = dict(
            action="APPROVE_OUTPUT",
            verification_id=attempt["verification_id"],
            expected_case_version=attempt["case_version"],
            reason="M3.1 public fixture: reviewed live operator-selected RPC observation",
        )
        decision = request("POST", path + "/resolve", 201, payload=resolve_body, key="m3-approve")
        evaluation = decision["evaluation"]
        observation = evaluation["observation"]
        policy = invoice["policy"]
        age = (
            datetime.fromisoformat(evaluation["evaluated_at"])
            - datetime.fromisoformat(observation["observed_at"])
        ).total_seconds()
        for observed in (refresh, observation):
            require(observed["state"] == "CONFIRMED", "Observation was not confirmed")
            require(observed["source_kind"] == "RPC", "Observation was not live RPC")
            require(observed["source"] == settings.rpc_source_id, "Unexpected RPC source")
            require(observed["txid"] == fixture["txid"], "RPC transaction binding differs")
            require(
                observed["raw_tx_sha256"] == result["raw_tx_sha256"], "RPC byte binding differs"
            )
            require(
                observed["confirmations"] >= policy["minimum_confirmations"],
                "Insufficient confirmations",
            )
        require(
            observation["observation_id"] != refresh["observation_id"],
            "Approval reused the manual refresh",
        )
        require(0 <= age <= policy["max_observation_age_seconds"], "Decision observation is stale")
        require(evaluation["source_authorized"] is True, "RPC source was not authorized")
        require(evaluation["result"]["eligible_for_credit"] is True, "Decision was ineligible")
        require(decision["allocated_zat"] == 100_000, "Unexpected allocation amount")
        repeated = request("POST", path + "/resolve", 200, payload=resolve_body, key="m3-approve")
        require(repeated == decision, "Approval retry changed the decision")
        require(steps[-1]["idempotency_replayed"] == "true", "Approval retry was not replayed")
        after = request("GET", path + "/report", 200)
        require(after["report_scope"] == "MERCHANT_DECISIONS", "Unexpected report scope")
        require(after["balances"]["credited_zat"] == 100_000, "Credit was duplicated or missing")
        require(after["balances"]["outstanding_zat"] == 100_000, "Unexpected outstanding balance")
        require(len(after["decisions"]) == 1, "Expected exactly one merchant decision")
        require(not after["chain_review"], "Report has an unresolved chain review")
    return dict(
        fixture_manifest="fixtures/manifest.json",
        fixture_file_sha256=file_hashes,
        readiness=readiness,
        merchant_identity=identity,
        invoice=invoice,
        references={
            "case_id": case["case_id"],
            "evidence_id": evidence["evidence_id"],
            "verification_id": attempt["verification_id"],
        },
        verification=result,
        initial_observation=attempt["observation"],
        manual_refresh=refresh,
        approval=decision,
        decision_observation_age_seconds=age,
        before_balances=before["balances"],
        after_balances=after["balances"],
        report_scope=after["report_scope"],
        http_steps=steps,
        checks=dict(
            refresh_retry_identical=True,
            approval_retry_identical=True,
            approval_observation_is_new=True,
            decision_count=1,
            anonymous_refresh_denied=True,
            unresolved_chain_review=False,
        ),
    )


def validate():
    url = os.environ.get("ZECSOLVE_TEST_DATABASE_URL")
    require(bool(url), "Set ZECSOLVE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    configured = Settings()
    require(bool(configured.rpc_url.get_secret_value()), "Configure ZECSOLVE_RPC_URL explicitly")
    require(
        not git("status", "--porcelain", "--untracked-files=no"),
        "Commit tracked changes before recording a reproducible live run",
    )
    schema = "zecsolve_live_" + uuid.uuid4().hex
    scoped = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    settings = Settings(
        _env_file=None,
        database_url=scoped.render_as_string(hide_password=False),
        verifier_path=ROOT / "target/debug/zecsolve-verifier",
        migrations_path=ROOT / "apps/api/migrations",
        evidence_key_id="ephemeral-m3-live",
        evidence_key=base64.b64encode(os.urandom(32)).decode(),
        rpc_url=configured.rpc_url,
        rpc_source_id=configured.rpc_source_id,
        rpc_username=configured.rpc_username,
        rpc_password=configured.rpc_password,
        rpc_allow_private_http=configured.rpc_allow_private_http,
        rpc_timeout_seconds=configured.rpc_timeout_seconds,
        rpc_tip_max_age_seconds=configured.rpc_tip_max_age_seconds,
        poc_token="",
        browser_origins=[],
    )
    started = datetime.now(UTC).isoformat()
    admin = create_engine(url, connect_args={"connect_timeout": 3})
    engine = create_engine(scoped, connect_args={"connect_timeout": 3})
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        try:
            config = Config(str(ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(settings.migrations_path))
            with engine.begin() as connection:
                require(
                    connection.scalar(text("SELECT current_schema()")) == schema,
                    "Database schema isolation failed",
                )
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                migration = connection.scalar(text("SELECT version_num FROM alembic_version"))
                postgres = connection.scalar(text("SHOW server_version"))
            trace = run_workflow(settings, engine)
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                require(
                    not connection.scalar(
                        text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:schema)"),
                        {"schema": schema},
                    ),
                    "Disposable schema was not removed",
                )
    finally:
        admin.dispose()
    return dict(
        schema_version="m3-live-validation-v1",
        started_at=started,
        completed_at=datetime.now(UTC).isoformat(),
        app_revision=git("rev-parse", "HEAD"),
        tracked_worktree_clean=True,
        migration=migration,
        environment=dict(
            os=platform.system(),
            os_release=platform.release(),
            architecture=platform.machine(),
            python=platform.python_version(),
            postgres=postgres,
        ),
        verifier_binary_sha256=hashlib.sha256(settings.verifier_path.read_bytes()).hexdigest(),
        input_classification="public historical mainnet fixture; synthetic invoice; live RPC",
        api_transport="FastAPI TestClient (in-process ASGI); RPC uses actual HTTPS",
        source_id=settings.rpc_source_id,
        methods_exercised=[
            "getnetworkinfo",
            "getblockchaininfo",
            "getblockheader",
            "getrawtransaction",
        ],
        rpc_timeout_seconds=settings.rpc_timeout_seconds,
        rpc_tip_max_age_seconds=settings.rpc_tip_max_age_seconds,
        live_confirmation=True,
        new_payment_sent=False,
        schema_removed=True,
        full_release_complete=False,
        **trace,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New JSON evidence file; existing records are never overwritten",
    )
    args = parser.parse_args()
    # Avoid request logging of provider URLs; exceptions never echo configuration.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        require(not args.output.exists(), "Choose a new evidence file; output already exists")
        trace = validate()
        with args.output.open("x") as output:
            output.write(json.dumps(trace, indent=2) + "\n")
    except ValidationFailure as error:
        raise SystemExit(
            f"Live validation failed: {error}. No successful evidence recorded."
        ) from None
    except Exception:
        raise SystemExit(
            "Live validation failed; no successful evidence was recorded. Check configuration, "
            "database access and RPC availability. Never publish raw exceptions or secrets."
        ) from None
    print("Live validation passed; recorded public-fixture evidence and removed disposable schema.")


if __name__ == "__main__":
    main()
