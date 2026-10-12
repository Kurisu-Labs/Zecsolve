"""Scoped HTTPS reads and offline replay across the disposable recovery checkpoints."""

import base64
import copy
import hashlib
import json
from http.cookies import SimpleCookie

SECTIONS = [
    "case",
    "invoice",
    "claims",
    "evidence",
    "verifications",
    "observations",
    "evaluations",
    "balances",
    "decisions",
    "events",
]


def history_digest(payload):
    """Compare every payload field except the fresh report-generation timestamp."""
    value = copy.deepcopy(payload)
    del value["report"]["generated_at"]
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


class ExportRecovery:
    def __init__(self, root, compose, run, http, origin, context, customer, claim, passed):
        self.http, self.run, self.passed = http, run, passed
        self.path = f"/api/cases/{context['case_id']}"
        self.context, self.customer, self.claim = context, customer, claim
        self.merchant = {"Authorization": "Bearer " + context["token"]}
        self.secrets, self.actors, self.grants = [], {}, {}
        self.baseline, self.checkpoints = {}, []
        container = run(compose + ["ps", "-q", "api"]).strip()
        image = run(["docker", "inspect", "--format", "{{.Image}}", container]).strip()
        self.command = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=80m",
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
            (root / "scripts/recovery_replay.py").read_text(),
        ]
        for role in ("reviewer", "report_only", "case_only", "revoked"):
            scope = {
                "role": "reviewer",
                "report_sections": ["case"] if role == "case_only" else SECTIONS,
                "evidence_ids": [] if role == "case_only" else [context["evidence_id"]],
                "allow_export": role != "report_only",
            }
            status, _, body = http(
                self.path + "/grants",
                method="POST",
                body={"scope": scope},
                headers={**self.merchant, "Idempotency-Key": "recovery-" + role},
            )
            assert status == 201
            grant = json.loads(body)
            self.grants[role] = grant["grant"]["grant_id"]
            self.secrets.append(grant["access_code"])
            status, headers, _ = http(
                "/api/session",
                method="POST",
                body={"code": grant["access_code"]},
                headers={"Origin": origin},
            )
            assert status == 201
            cookies = SimpleCookie()
            for value in headers.get_all("Set-Cookie", []):
                cookies.load(value)
            assert set(cookies) == {"__Host-zecsolve_session", "__Host-zecsolve_csrf"}
            self.secrets.extend(cookie.value for cookie in cookies.values())
            self.actors[role] = {
                "Cookie": "; ".join(f"{name}={cookie.value}" for name, cookie in cookies.items()),
            }
        self.revoke("revoked")

    def revoke(self, role):
        assert (
            self.http(
                self.path + "/grants/" + self.grants[role],
                method="DELETE",
                headers=self.merchant,
            )[0]
            == 200
        )

    def restricted(self, value):
        serialized = json.dumps(value)
        for hidden in (
            self.claim["note"],
            self.context["claim_id"],
            self.context["legacy_id"],
            self.context["unselected_id"],
            self.context["merchant_id"],
            self.context["credential_id"],
            self.context["grant_id"],
            "actor_id",
            "ciphertext",
            *self.secrets,
        ):
            assert hidden not in serialized, "Restricted disclosure contains a private canary"

    def replay(self, raw, status, exit_code):
        outcome = json.loads(self.run(self.command, input=raw.decode()))
        result = outcome["result"]
        assert outcome["exit_code"] == exit_code and result["status"] == status
        assert result["full_replay"] is (status == "REPRODUCED")
        assert result["packet_file_sha256"] == hashlib.sha256(raw).hexdigest()
        assert "OBSERVATIONS_ARE_HISTORICAL_EXTERNAL_ASSERTIONS" in result["external_assertions"]
        return result

    def check(self, stage):
        # Existing legacy evidence has no reviewer-sharing consent. Refusal must
        # survive recovery; a failed grant request must not create any rows.
        status, _, body = self.http(
            self.path + "/grants",
            method="POST",
            body={
                "scope": {
                    "role": "reviewer",
                    "report_sections": ["evidence"],
                    "evidence_ids": [self.context["legacy_id"]],
                    "allow_export": True,
                }
            },
            headers={**self.merchant, "Idempotency-Key": "recovery-no-consent"},
        )
        assert status == 403 and b"EVIDENCE_SHARING_NOT_AUTHORIZED" in body
        for actor, expected in (({}, 401), (self.customer, 403), (self.actors["revoked"], 401)):
            for route in ("/report", "/export", f"/evidence/{self.context['evidence_id']}/content"):
                assert self.http(self.path + route, headers=actor)[0] == expected
        assert self.http(self.path + "/export", headers=self.actors["report_only"])[0] == 403
        for role in ("reviewer", "report_only", "case_only"):
            actor = self.actors[role]
            assert self.http("/api/session", headers=actor)[0] == 200
            status, _, body = self.http(self.path + "/report", headers=actor)
            assert status == 200
            report = json.loads(body)
            self.restricted(report)
            if role == "case_only":
                assert "evidence" not in report and "claims" not in report
            else:
                assert report["claims"] == []
                assert [item["evidence_id"] for item in report["evidence"]] == [
                    self.context["evidence_id"]
                ]
                status, _, body = self.http(
                    self.path + f"/evidence/{self.context['evidence_id']}/content", headers=actor
                )
                assert status == 200
                content = json.loads(body)
                self.restricted(content)
                for field in ("receipt_json", "raw_tx_hex"):
                    assert content[field] == self.context["legacy_request"][field]
            for hidden in (self.context["legacy_id"], self.context["unselected_id"]):
                for suffix in ("", "/content"):
                    assert (
                        self.http(self.path + f"/evidence/{hidden}" + suffix, headers=actor)[0]
                        == 403
                    )
        status, _, body = self.http(self.path + "/report", headers=self.merchant)
        assert status == 200
        merchant_report = json.loads(body)
        assert merchant_report["balances"]["credited_zat"] == 100_000
        assert merchant_report["balances"]["outstanding_zat"] == 100_000
        assert merchant_report["claims"][0]["note"] == self.claim["note"]
        artifacts = {}
        for role, actor, status, code in (
            ("merchant", self.merchant, "REPRODUCED", 0),
            ("reviewer", self.actors["reviewer"], "LIMITED", 2),
            ("case_only", self.actors["case_only"], "LIMITED", 2),
        ):
            response, headers, raw = self.http(self.path + "/export", headers=actor)
            assert response == 200 and headers["Cache-Control"] == "no-store"
            assert (
                headers["Content-Disposition"]
                == f'attachment; filename="zecsolve-{self.context["case_id"]}.json"'
            )
            packet = json.loads(raw)
            payload = packet["payload"]
            if role == "merchant":
                assert payload["replay_scope"] == "FULL_HISTORY"
                expected = {
                    self.context[key] for key in ("legacy_id", "evidence_id", "unselected_id")
                }
                assert {item["evidence_id"] for item in payload["evidence"]} == expected
                assert history_digest({"report": merchant_report}) == history_digest(
                    {"report": payload["report"]}
                )
            else:
                assert payload["replay_scope"] == "LIMITED" and payload["omissions"]
                assert payload["balance_context"] is None
                self.restricted(payload)
                expected = [] if role == "case_only" else [self.context["evidence_id"]]
                assert [item["evidence_id"] for item in payload["evidence"]] == expected
                assert all(
                    item["submission_payload"]["availability"] == "OMITTED"
                    for item in payload["evidence"]
                )
            for item in payload["evidence"]:
                for component, field in (
                    ("receipt", "receipt_json"),
                    ("raw_transaction_hex", "raw_tx_hex"),
                ):
                    original = self.context["legacy_request"][field].encode()
                    assert base64.b64decode(item[component]["data"], validate=True) == original
                    assert item[component]["sha256"] == hashlib.sha256(original).hexdigest()
            result = self.replay(raw, status, code)
            if role != "case_only":
                assert any(
                    item["code"] == "OUTPUT_RECOVERY_REPRODUCED" for item in result["checks"]
                )
            if role == "merchant":
                assert any(
                    item["category"] == "rules" and item["status"] == "PASS"
                    for item in result["checks"]
                )
                # Mutate one ASCII byte in a business assertion without recomputing hashes.
                before = self.claim["note"].encode()
                assert raw.count(before) == 1
                tampered = raw.replace(before, before[:-1] + b"!", 1)
                failed = self.replay(tampered, "FAILED", 1)
                assert len(failed["checks"]) == 1 and failed["checks"][0]["category"] == "integrity"
            stable = history_digest(payload)
            if stage == "before_restart":
                self.baseline[role] = stable
            else:
                assert stable == self.baseline[role], "Exported history changed across recovery"
            # Store only hashes/statuses, never packets, cookies, IDs or claim text.
            artifacts[role] = {
                "packet_sha256": result["packet_file_sha256"],
                "history_sha256": stable,
                "replay_status": status,
                "exit_code": code,
            }
        self.checkpoints.append({"stage": stage, "exports": artifacts, "tampered_replay": "FAILED"})
        self.passed(f"{stage}: scoped HTTPS permissions, exact exports and isolated offline replay")

    def revoke_restored(self):
        self.revoke("reviewer")
        for route in ("/report", "/export", f"/evidence/{self.context['evidence_id']}/content"):
            assert self.http(self.path + route, headers=self.actors["reviewer"])[0] == 401
        self.passed("restored reviewer revocation prevents new reports, evidence reads and exports")
