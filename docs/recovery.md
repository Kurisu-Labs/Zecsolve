# M7.2 backend recovery rehearsal

Person 3 owns this backend preparation slice on `test/m7-release-rehearsal`. It exercises the current application and PostgreSQL in an isolated deployment. Full M7.2 remains open for trusted live validation, scoped reports/export/replay, Person 4's browser acceptance, and the complete release evidence bundle.

## Run and inspect

Use the repository Python environment, a running Docker daemon with Compose, and OpenSSL:

```sh
uv run --locked python scripts/check_deployment.py --recovery
```

The command first runs the existing ten TLS deployment checks, then the recovery scenarios below. It creates its own randomly named Compose project, loopback listeners, private secret directory and database volume. It does not accept an existing database or deployment as a target. `--keep-on-failure` retains that disposable project for diagnosis; its reported directory contains private credentials and must not be uploaded. The default removes its test containers, volumes and private files on either success or failure.

The sanitized `.cache/recovery-result.json` records check names, UTC time, Git revision, dirty-tree indicator, host/Python/Docker versions, migration baseline/head, archive and restored-row hashes, table counts, and incomplete release gates. The [deployment workflow](../.github/workflows/deployment.yml) runs the same command and retains only this JSON as `backend-recovery-evidence`. A failed command is not a successful rehearsal; use the artifact from the matching CI revision. Never attach dumps, key files or private diagnostic logs.

## What is exercised

| Scenario | Required result |
|---|---|
| Populated forward migration | A fresh private schema starts at `0008`, receives synthetic legacy rows including encrypted content and a 100,000-zatoshi allocation, then upgrades to the packaged head. Original columns/bytes are unchanged, nullable attribution stays unknown, and repeating `upgrade head` changes nothing. The schema is removed. No downgrade is used. |
| Current workflow | The public historical receipt passes the real packaged Rust verifier. The production API rejects offline approval. A separate, injected test process uses explicitly `SIMULATED` observations to create one accepted allocation through the existing resolution service. Production routes and settings are unchanged. |
| API crash and lost responses | Customer claim/evidence responses and a simulated merchant approval are retained only as test oracles while modeling client response loss. After SIGKILL and API restart, the same keys/bodies reproduce their exact original outcomes; changed bodies return conflicts. This tests committed-response loss, not a crash at every possible transaction instruction. |
| Database restart | Stop the API, restart PostgreSQL, then restart the API through its migration entry point. Session restoration, retries, merchant reports and customer role restrictions still work. |
| Encrypted backup | Stop the sole application writer; take a PostgreSQL custom-format dump. Encrypt the entire dump with a new AES-256-GCM backup key, independent of the evidence key. No plaintext dump is written to a host file. Archive helpers use the built image with networking and Docker logging disabled, so decrypted stdout is not retained in container logs. |
| Invalid archive | Wrong backup keys and modified ciphertext are rejected before any restore begins. Unit coverage also rejects changed headers/nonces, truncation, non-archives and oversized plaintext. |
| Fresh-database restore | Create a separate empty database with `template0`; restore with `--single-transaction --exit-on-error --no-owner --no-acl`. Recreate the deployed API against it with the preserved evidence key and run forward startup migrations. |
| Recovery invariants | Every application-table row has the same logical digest as the checkpoint, including nonces/ciphertext, consent, attribution, session/revocation state, histories, idempotency records and allocations. Exact v1/v2 evidence decrypts; the credited/outstanding balances remain 100,000/100,000. Retries add no rows. |
| Restored protections | Duplicate output allocation, missing foreign references and immutable invoice edits still fail. Missing/wrong evidence keys cannot decrypt. Revoking the restored customer grant prevents even an accepted retry. |
| Logs | Application and ingress logs omit the rehearsal's credential, session, claim-text and database-URL canaries. PostgreSQL raw logs remain disabled by the deployment composition. |

The migration fixture represents legacy storage preservation; it does not invent missing historical policy, attribution or verification context. The current workflow separately checks real application reads and retries. Simulated accounting evidence never closes M3.1 or proves live payment inclusion.

## Recovery procedure and limits

For an operator-reviewed deployment recovery, stop writes and retain the current database before selecting a backup. Verify the selected archive's provenance, recovery point, key identifiers and integrity. Recover the independent backup key and every evidence key required by the stored key IDs from external secret storage. Restore into a fresh isolated database, apply supported forward migrations with the matching application image, and compare reports, accepted allocations, audit/consent history, exact evidence and retry outcomes before routing traffic to it. Check access revocations against records newer than the backup before reopening access. Keep the prior database until recovery is accepted.

Do not restore over the running database, delete accepted allocations, or downgrade the schema to make an older image start. An application rollback is permitted only after establishing schema compatibility; otherwise stop approvals and recover forward. A database dump alone cannot recover evidence when its external key is lost. An evidence key alone cannot decrypt the independently encrypted backup.

This small-fixture envelope buffers at most 64 MiB of archive payload. It is a rehearsal aid, not a general backup service, key-management system, off-site retention policy, continuous WAL/PITR backup, or measured recovery-time/recovery-point guarantee. The host's database volume encryption and external key custody are operator responsibilities. Writes after the chosen backup are outside this recovery point. These requirements and retention/deletion terms still apply before private-customer use.

## Release acceptance tracking

This matrix locates evidence and remaining work; it does not mark all PRD scenarios passed. Existing tests remain attributable to their own recorded runs in [DEVELOPMENT.md](DEVELOPMENT.md).

| PRD row | Backend evidence / contribution here | Remaining release evidence |
|---|---|---|
| A-01 | Real public-fixture verification in the current rehearsal | Final assembled release trace |
| A-02 | Existing verifier and resolution safety suites | P4 negative-path browser results |
| A-03 | Existing invoice-to-report workflow and arithmetic suites | P4 first workflow |
| A-04 | Existing synthetic aggregation/service tests | Final evidence reference |
| A-05 | Exact approval replay after API crash, DB restart and restore | P4 retry flow |
| A-06 | Existing approval race/conflict tests; restored output uniqueness checked here | P4 conflict flow and final release trace |
| A-07 | Existing distinct-output database test | Final evidence reference |
| A-08 | Existing adapter/verification/RPC negative tests | P4 status displays and M3.1 |
| A-09 | Existing binding/policy/approval safety tests | P4 presentation |
| A-10 | Production offline approval remains blocked in the rehearsal | M3.1 actual-node observation/approval |
| A-11 | Existing M4.0–M4.4 isolation; restored customer cannot read merchant report | P2 M4.5/M5 route matrix and P4 browser results |
| A-12 | Restored revocation denies accepted retry; existing grant/consent tests | P2 scoped reads and P4 disclosure/access screens |
| A-13 | No packet/replay completion claimed | P2 M5 and P4 authorized export UI |
| A-14 | Existing rollback/stale-version tests; migration/restore preserves immutable rows and accepted allocation | Final assembled evidence; corrections remain outside P0 |
| A-15 | Actual TLS controls, restart/restore and secret-canary checks | P2 export redaction, P4 browser evidence, operator controls and final demo |

The remaining owners retain their scopes. P2 can now start M4.5 because M4.4 merged in [PR #18](https://github.com/Kurisu-Labs/zecsolve/pull/18). P4 supplies browser results and screenshots; P3 records them without independently implementing frontend work.
