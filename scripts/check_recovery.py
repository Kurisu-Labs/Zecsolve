"""M7.2 backend recovery checks; called only inside the disposable deployment harness."""

import base64
import hashlib
import json
import os
import time
from http.cookies import SimpleCookie

from recovery_exports import ExportRecovery


def rehearse(root, directory, compose, run, request, origin, passed):
    worker = (root / "scripts/recovery_state.py").read_text()
    crypto = (root / "scripts/recovery_backup.py").read_text()
    worker_command = compose + [
        "exec",
        "-T",
        "-e",
        "ZECSOLVE_REHEARSAL_ONLY=disposable",
        "api",
        "python",
        "-c",
        worker,
    ]

    def state(phase, **data):
        return json.loads(run(worker_command, input=json.dumps({"phase": phase, **data})))

    def http(path, *, method="GET", body=None, headers=None):
        time.sleep(0.3)
        return request(
            path,
            method=method,
            body=json.dumps(body) if body is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})},
        )

    migration = json.loads(
        run(
            compose
            + [
                "exec",
                "-T",
                "api",
                "python",
                "-c",
                (root / "scripts/rehearse_migration.py").read_text(),
            ]
        )
    )
    passed("populated 0008 to packaged-head forward migration preserves legacy rows and allocation")
    legacy = dict(
        receipt_json=(root / "fixtures/mainnet/receipt.json").read_text(),
        raw_tx_hex=(root / "fixtures/mainnet/transaction.hex").read_text(),
        source="public historical recovery fixture",
        source_kind="public_fixture",
        processing_authorized=True,
    )
    identity = state(
        "seed",
        fixture=json.loads((root / "fixtures/manifest.json").read_text())["expected"],
        legacy_request=legacy,
    )
    merchant = {"Authorization": "Bearer " + identity["token"]}
    status, headers, body = http(
        "/api/session",
        method="POST",
        body={"code": identity["access_code"]},
        headers={"Origin": origin},
    )
    assert status == 201
    cookies = SimpleCookie()
    for value in headers.get_all("Set-Cookie", []):
        cookies.load(value)
    customer = {
        "Cookie": "; ".join(f"{name}={cookie.value}" for name, cookie in cookies.items()),
        "Origin": origin,
        "X-CSRF-Token": cookies["__Host-zecsolve_csrf"].value,
    }
    path = f"/api/cases/{identity['case_id']}"
    claim = {
        "note": "Synthetic recovery claim: no customer information",
        "processing_authorized": True,
        "disclosure_version": "claim-disclosure-v1",
        "share_with_reviewers": False,
    }
    status, _, body = http(
        path + "/claims",
        method="POST",
        body=claim,
        headers={**customer, "Idempotency-Key": "recovery-claim"},
    )
    assert status == 201
    # The test oracle retains responses; the simulated client loses them before retrying.
    claim_ack = json.loads(body)
    scoped = {
        **legacy,
        "disclosure_version": "evidence-disclosure-v2",
        "source_kind": "customer_submission",
        "share_with_reviewers": True,
        "claim_id": claim_ack["submission_id"],
    }
    status, _, body = http(
        path + "/evidence",
        method="POST",
        body=scoped,
        headers={**customer, "Idempotency-Key": "recovery-evidence"},
    )
    assert status == 201
    evidence_ack = json.loads(body)
    status, _, body = http(
        path + "/evidence",
        method="POST",
        body={**scoped, "source": "Consented public fixture excluded from reviewer selection"},
        headers={**customer, "Idempotency-Key": "recovery-unselected"},
    )
    assert status == 201
    context = {
        **identity,
        "claim_id": claim_ack["submission_id"],
        "unselected_id": json.loads(body)["submission_id"],
        "evidence_id": evidence_ack["submission_id"],
        "legacy_request": legacy,
        "evidence_request": scoped,
    }
    approval = state("verify", **context)
    status, _, body = http(
        path + "/resolve",
        method="POST",
        body=approval,
        headers={**merchant, "Idempotency-Key": "recovery-offline"},
    )
    assert status == 409 and "CREDIT_INELIGIBLE" in body.decode()
    accepted = state("approve", **context)
    exports = ExportRecovery(root, compose, run, http, origin, context, customer, claim, passed)
    baseline = state("check", **context)
    assert baseline["counts"]["output_allocations"] == 1
    passed("public fixture verifies; offline approval denied; simulated allocation seeded")
    exports.check("before_restart")
    assert state("check", **context) == baseline

    def recovered(stage):
        assert http("/api/session", headers=customer)[0] == 200
        for route, payload, expected in (
            ("claims", claim, claim_ack),
            ("evidence", scoped, evidence_ack),
        ):
            status, headers, body = http(
                path + "/" + route,
                method="POST",
                body=payload,
                headers={
                    **customer,
                    "Idempotency-Key": "recovery-" + ("claim" if route == "claims" else "evidence"),
                },
            )
            assert status == 200 and headers["Idempotency-Replayed"] == "true"
            assert json.loads(body) == expected
        status, headers, body = http(
            path + "/resolve",
            method="POST",
            body=accepted["request"],
            headers={**merchant, "Idempotency-Key": "recovery-approve"},
        )
        assert status == 200 and headers["Idempotency-Replayed"] == "true"
        assert json.loads(body) == accepted["outcome"]
        for route, payload, key in (
            ("claims", {**claim, "note": "changed"}, "recovery-claim"),
            ("evidence", {**scoped, "share_with_reviewers": False}, "recovery-evidence"),
            ("resolve", {**accepted["request"], "reason": "changed"}, "recovery-approve"),
        ):
            status, _, body = http(
                path + "/" + route,
                method="POST",
                body=payload,
                headers={**(merchant if route == "resolve" else customer), "Idempotency-Key": key},
            )
            assert status == 409 and "IDEMPOTENCY_CONFLICT" in body.decode()
        assert http(path + "/report", headers=customer)[0] == 403
        assert http(path + "/report", headers=merchant)[0] == 200
        exports.check(stage)
        assert state("check", **context) == baseline

    # Exercise a real process loss, rather than recreating only Python service objects.
    run(compose + ["kill", "-s", "SIGKILL", "api"])
    run(compose + ["up", "-d", "--wait", "--wait-timeout", "120", "api"])
    recovered("after_api_restart")
    passed("API crash preserves sessions and claim/evidence/approval retries without new rows")
    run(compose + ["stop", "api"])
    run(compose + ["restart", "db"])
    run(compose + ["up", "-d", "--wait", "--wait-timeout", "120", "db"])
    run(compose + ["up", "-d", "--wait", "--wait-timeout", "120", "api"])
    recovered("after_database_restart")
    passed("database restart preserves balances, exact evidence, consent, audit and retry records")

    # Stop the sole writer for a consistent recovery point. Never dump an existing user database.
    run(compose + ["stop", "api"])
    database = compose + ["exec", "-T", "db"]
    dump = run(
        database + ["pg_dump", "-U", "zecsolve", "-d", "zecsolve", "-Fc", "--no-owner", "--no-acl"],
        binary=True,
    )
    dump_hash = hashlib.sha256(dump).hexdigest()
    backup_key = os.urandom(32)  # Separate from the application's evidence key.
    key_file = directory / "recovery-backup.key"
    key_file.write_bytes(backup_key)
    key_file.chmod(0o600)
    container = run(compose + ["ps", "-aq", "api"]).strip()
    image = run(["docker", "inspect", "--format", "{{.Image}}", container]).strip()
    # Decryption stdout contains a full database dump. Disable Docker logging as well
    # as keeping host subprocess pipes private; --rm alone would retain logs until exit.
    crypto_command = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--log-driver",
        "none",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--pids-limit",
        "64",
        image,
        "python",
        "-c",
        crypto,
    ]

    def transform(action, data, key):
        return json.loads(
            run(
                crypto_command,
                input=json.dumps(
                    {
                        "action": action,
                        "key": base64.b64encode(key).decode(),
                        "data": base64.b64encode(data).decode(),
                    }
                ),
            )
        )

    encrypted = transform("seal", dump, backup_key)
    assert encrypted["ok"]
    archive = directory / "recovery.pgdump.aesgcm"
    archive.write_bytes(base64.b64decode(encrypted["data"]))
    archive.chmod(0o600)
    del dump, encrypted
    stored = archive.read_bytes()
    assert transform("unseal", stored, os.urandom(32)) == {"ok": False}
    damaged = stored[:-1] + bytes([stored[-1] ^ 1])
    assert transform("unseal", damaged, backup_key) == {"ok": False}
    plaintext = transform("unseal", stored, key_file.read_bytes())
    assert plaintext["ok"]
    restored = base64.b64decode(plaintext["data"])
    assert hashlib.sha256(restored).hexdigest() == dump_hash
    passed("encrypted full-database archive rejects wrong backup key and tampering before restore")
    run(database + ["createdb", "-U", "zecsolve", "--template=template0", "recovery_restored"])
    run(
        database
        + [
            "pg_restore",
            "-U",
            "zecsolve",
            "-d",
            "recovery_restored",
            "--single-transaction",
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
        ],
        input=restored,
        binary=True,
    )
    del restored, plaintext, backup_key
    # Recreate the app against the new database, retaining the independent evidence key.
    database_secret = directory / "database_url"
    source_url = database_secret.read_text()
    assert source_url.endswith("/zecsolve")
    database_secret.write_text(source_url.removesuffix("/zecsolve") + "/recovery_restored")
    run(compose + ["up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120", "api"])
    recovered("after_encrypted_restore")
    passed("fresh-database restore preserves every application row, decryption and retry outcome")
    passed("restored constraints/triggers reject invalid writes; missing/wrong evidence keys fail")
    exports.revoke_restored()
    # A final role revocation confirms restored access is still actively enforced.
    assert http(path + "/grants/" + identity["grant_id"], method="DELETE", headers=merchant)[0] in (
        200,
        204,
    )
    assert (
        http(
            path + "/claims",
            method="POST",
            body=claim,
            headers={**customer, "Idempotency-Key": "recovery-claim"},
        )[0]
        == 401
    )
    passed("restored grant revocation blocks even a previously accepted customer retry")
    secrets = [identity["token"], identity["access_code"], claim["note"], source_url]
    secrets += [cookie.value for cookie in cookies.values()]
    secrets += exports.secrets
    logs = run(compose + ["logs", "--no-color", "api", "ingress"])
    assert all(secret not in logs for secret in secrets)
    passed("recovery logs exclude credentials, cookies, claims and database secrets")
    return {
        "scope": "M7.2 backend and export/replay recovery integration",
        "migration": migration,
        "source_kind": "PUBLIC_FIXTURE_AND_SIMULATED_ACCOUNTING",
        "live_confirmation": False,
        "release_complete": False,
        "archive_sha256": hashlib.sha256(stored).hexdigest(),
        "restored_rows_sha256": baseline["rows_sha256"],
        "counts": baseline["counts"],
        "export_replay": {
            "network": "none",
            "checkpoints": exports.checkpoints,
            "restored_reviewer_revocation": "PASS",
        },
        "remaining_gates": [
            "M3.1 live validation",
            "M6 browser acceptance",
            "full M7 release evidence",
        ],
    }
