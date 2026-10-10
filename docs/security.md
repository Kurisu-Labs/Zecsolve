# zecsolve foundation security boundaries

The current verification service is a development proof of concept with one configured POC bearer token. Health and OpenAPI routes are public; POC verification requires that token and is disabled when none is configured. Operator-provisioned merchant credentials now protect the separate identity endpoint, but case-scoped workflow authorization is not yet implemented. Do not expose the POC publicly before the scoped workflow is complete.

Merchant tokens contain 256 random bits, expire after a configured 1–365 days, and are stored only as SHA-256 digests. The operator CLI discloses a token once, only after a successful database commit, and can revoke individual credentials. `/api/auth/me` checks expiry and revocation against the database on every request and returns only the authenticated merchant/credential IDs. The application derives identity from that credential; it does not accept merchant identity from request fields. This increment does not provide customer/reviewer grants, browser login sessions, or authorization for future case endpoints.

The API limits request bodies to 4,200,000 bytes, receipt files to 16,384 UTF-8 bytes, transaction hex to 4,000,002 bytes, subprocess output to 32,768 bytes, and simultaneous verifiers to two per API process. The default subprocess timeout is ten seconds. Container/process-level memory limits and ingress rate limits remain deployment work.

The adapter invokes a configured local executable with explicit arguments, `shell=False`, no inherited application secrets, no stdin and discarded stderr. It uses a private temporary directory and removes it after processing. No user-specified paths or fetch URLs are accepted. POC evidence is not persisted. Application-level encryption and evidence retention/deletion policies belong to the private-storage milestone.

The API returns generic validation errors rather than echoing submitted receipt fields. Access logs are disabled in the documented run commands. Responses use `Cache-Control: no-store`. The returned recovered fields are themselves disclosures and must be handled accordingly.

Only the selected output's amount, recipient and memo are recovered. The receipt's OCK intentionally permits this disclosure; it is not a seed, spending key or wallet-wide viewing key. Anyone who receives a receipt can forward it and verify it again. Removing a reviewer grant later cannot revoke a previously downloaded receipt.

Receipt validity does not establish the sender's identity or intent. An optional valid receipt signature only demonstrates possession of its signing key. Raw transaction recovery does not perform consensus validation or prove chain inclusion. All current verifier reports carry `chain_state=UNAVAILABLE`.

The allocation primary key prevents reuse inside this database. It does not detect reuse in another deployment or prove that the merchant's invoice is truthful. Append-only triggers resist ordinary application edits, not database-administrator tampering. Case event hashes require an implemented writer and a trusted anchor to provide stronger integrity guarantees.

Before the case workflow ships: implement authenticated merchant scoping, explicit customer/reviewer grants and consent, private evidence storage, atomic approval/idempotency, trusted chain observation provenance, and authorized export. Never infer merchant authority from a valid receipt alone.
