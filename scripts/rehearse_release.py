"""Assert the three public-fixture demo scenarios and offline replay limits.

Requires a disposable PostgreSQL database. No RPC is used. Raw child output is
never printed or retained; only exact expected results and tool versions enter
the report. This rehearsal does not decide overall release readiness.
"""

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from zecsolve.domain.snapshots import digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".cache/release-rehearsal.json"
PUBLIC_PACKET = ROOT / ".cache/release-demo-packet.json"
VERIFIER = ROOT / "target/debug/zecsolve-verifier"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run_json(command, expected_exit=0):
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        require(result.returncode == expected_exit, "Unexpected demo/replay exit code")
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise RuntimeError("Demo/replay execution failed; raw diagnostics withheld") from None


def check_scenarios(poc, demo):
    """Validate actual outcomes, then return only static, allowlisted facts."""
    expected_projection = dict(
        credited_zat=0,
        outstanding_zat=200_000,
        candidate_zat=100_000,
        projected_outstanding_zat=100_000,
        eligible_for_credit=False,
    )
    require(
        poc["valid_receipt"] == {"state": "VALID", "amount_zat": 100_000}
        and poc["tampered_receipt"] == {"state": "INVALID", "reason": "OUTPUT_RECOVERY_FAILED"}
        and poc["chain_state"] == "UNAVAILABLE"
        and all(poc["evaluation"][key] == value for key, value in expected_projection.items()),
        "Candidate projection or offline evidence did not match",
    )
    expected_demo = dict(
        source_kind="SIMULATED",
        live_confirmation=False,
        receipt_state="VALID",
        recovered_zat=100_000,
        offline_approval="CREDIT_INELIGIBLE",
        balances=dict(credited_zat=100_000, outstanding_zat=100_000, candidate_zat=0),
        retry_same_resolution=True,
        second_invoice="OUTPUT_ALLOCATION_CONFLICT",
        tampered_receipt="INVALID",
        tampered_reason="OUTPUT_RECOVERY_FAILED",
        tampered_approval="CREDIT_INELIGIBLE",
        rejected_invoice_credited_zat=0,
        schema_removed=True,
    )
    require(
        all(demo[key] == value for key, value in expected_demo.items()),
        "Simulated decision, retry, conflict, rejection or cleanup did not match",
    )
    return [
        dict(
            scenario="1-candidate-projection",
            acceptance=["A-01", "A-03", "A-10"],
            status="passed",
            inputs="public historical Orchard receipt; synthetic invoice; offline observer",
            outcome=expected_projection,
        ),
        dict(
            scenario="2-retry-and-conflict",
            acceptance=["A-05", "A-06"],
            status="passed",
            inputs="public receipt; synthetic invoices; explicitly SIMULATED confirmation",
            outcome={
                key: expected_demo[key]
                for key in ("balances", "retry_same_resolution", "second_invoice", "source_kind")
            },
        ),
        dict(
            scenario="3-invalid-evidence",
            acceptance=["A-02"],
            status="passed",
            inputs="public tampered OCK fixture; synthetic invoice",
            outcome={
                key: expected_demo[key]
                for key in (
                    "tampered_receipt",
                    "tampered_reason",
                    "tampered_approval",
                    "rejected_invoice_credited_zat",
                )
            },
        ),
    ]


def replay_examples():
    original = (ROOT / "fixtures/packets/complete-v1.json").read_bytes()
    variants = {
        "complete-v1": (original, 0, "REPRODUCED"),
        "complete-v2": ((ROOT / "fixtures/packets/complete-v2.json").read_bytes(), 0, "REPRODUCED"),
        "tampered": (
            original.replace(b"Synthetic demonstration only", b"Synthetic demonstration onl!"),
            1,
            "FAILED",
        ),
        "scoped": ((ROOT / "fixtures/packets/scoped.json").read_bytes(), 2, "LIMITED"),
    }
    require(variants["tampered"][0] != original, "Tamper fixture was not changed")
    for name, version, code, status in [
        ("missing-version", None, 2, "LIMITED"),
        ("unsupported-version", "999.0.0", 3, "UNSUPPORTED"),
    ]:
        packet = json.loads(original)
        packet["payload"]["implementations"]["verifiers"][0]["version"] = version
        packet["integrity"]["payload_sha256"] = digest(packet["payload"])
        variants[name] = (json.dumps(packet).encode(), code, status)
    results = {}
    with tempfile.TemporaryDirectory(prefix="zecsolve-release-replay-") as directory:
        for name, (data, code, status) in variants.items():
            source = Path(directory) / f"{name}.json"
            source.write_bytes(data)
            result = run_json(
                [sys.executable, "-m", "zecsolve.replay", str(source), "--verifier", str(VERIFIER)],
                expected_exit=code,
            )
            file_hash = hashlib.sha256(data).hexdigest()
            require(
                result["status"] == status
                and result["full_replay"] == (code == 0)
                and result["packet_file_sha256"] == file_hash,
                "Replay outcome did not match",
            )
            results[name] = dict(exit_code=code, status=status, packet_file_sha256=file_hash)
    return results


def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    PUBLIC_PACKET.unlink(missing_ok=True)
    started = datetime.now(UTC).isoformat()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip())
    poc = run_json([sys.executable, "scripts/poc.py"])
    with tempfile.TemporaryDirectory(prefix="zecsolve-release-export-") as directory:
        packet = Path(directory) / "public-demo.json"
        demo = run_json(
            [sys.executable, "scripts/demo_resolution.py", "--export-public-packet", str(packet)]
        )
        exported = packet.read_bytes()
        replayed = run_json(
            [sys.executable, "-m", "zecsolve.replay", str(packet), "--verifier", str(VERIFIER)]
        )
        exported_hash = hashlib.sha256(exported).hexdigest()
        require(
            replayed["status"] == "REPRODUCED"
            and replayed["full_replay"] is True
            and replayed["packet_file_sha256"] == exported_hash,
            "Authorized public demo export did not reproduce",
        )
    scenarios = check_scenarios(poc, demo)
    replay = replay_examples()
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
    for entry in manifest["files"]:
        require(
            hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"],
            "Public fixture or license hash did not match",
        )
    report = dict(
        schema_version="release-rehearsal-v1",
        revision=revision,
        working_tree_changes=dirty,
        started_at=started,
        finished_at=datetime.now(UTC).isoformat(),
        environment=dict(
            host=platform.platform(),
            python=platform.python_version(),
            rust=subprocess.check_output(["rustc", "--version"], text=True).strip(),
            postgres=demo["postgres_version"],
        ),
        command="uv run --locked python scripts/rehearse_release.py",
        status="passed",
        scenarios=scenarios,
        replay=replay,
        authorized_public_export=dict(
            packet_file="release-demo-packet.json",
            sha256=exported_hash,
            exit_code=0,
            status="REPRODUCED",
            boundary="authorized merchant export service",
            inputs="exact public fixture; synthetic invoice; SIMULATED approval history",
        ),
        fixture_manifest_sha256=hashlib.sha256(
            (ROOT / "fixtures/manifest.json").read_bytes()
        ).hexdigest(),
        schema_removed=True,
        live_confirmation=False,
        release_complete=False,
        limitations=[
            "Service/CLI rehearsal, not a browser recording or public deployment",
            "SIMULATED credit is test-only; no new payment or live RPC used",
            "Packet samples mix public evidence with synthetic business history",
            "Authorized HTTP export, live and browser results are separately indexed",
            "Hashes identify bytes, not authors or fresh chain inclusion",
        ],
    )
    PUBLIC_PACKET.write_bytes(exported)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "PASS: three demo scenarios, authorized public export, "
        "six replay outcomes and fixture/license hashes"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit(
            "Release rehearsal failed; no success report retained; diagnostics withheld"
        ) from None
