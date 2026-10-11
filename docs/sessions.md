# Secure browser sessions

M4.2 adds `POST`, `GET`, and `DELETE /api/session`. Initial merchant credentials and case-grant codes can be exchanged for revocable browser sessions. Existing merchant bearer clients remain supported. This supplies backend browser authentication, not a frontend login screen or customer/reviewer report/submission routes.

## Operator configuration

Set `ZECSOLVE_BROWSER_ORIGINS` to a JSON list of exact HTTPS origins, for example `["https://app.example"]`. No wildcard, path, credentials, query, fragment, or plain HTTP origin is allowed. Empty (the default) disables new exchanges and cookie-authenticated writes. Compose forwards the setting. Deploy behind TLS with trustworthy proxy scheme handling; never trust arbitrary forwarded headers from untrusted peers. Local browser development needs an HTTPS origin/proxy too; there is no insecure-cookie switch.

## Person 4 browser contract

1. POST `{"code":"<merchant credential or grant access code>"}` as JSON to `/api/session` from a configured HTTPS Origin, with same-origin credentials enabled. Codes must be supplied manually or by an appropriately handled fragment, never query strings, logs, or localStorage. The session endpoint does not interpret fragments.
2. The server returns 201 `SessionInfoV1` after commit and sets two host-only cookies at `/`: `__Host-zecsolve_session` is **Secure, HttpOnly, SameSite=Strict**; `__Host-zecsolve_csrf` is **Secure, SameSite=Strict** and readable by JavaScript. Neither cookie uses Domain. The JSON body contains identity/scope/expiry, not either cookie's secret value.
3. GET `/api/session` reads current role, case scope, allowed report/evidence selections, and expiry. It rechecks the underlying credential/grant and session. It does not make unimplemented data routes available to that role.
4. For every cookie-authenticated POST/PUT/PATCH/DELETE workflow request, send `X-CSRF-Token` equal to the CSRF cookie, along with normal cookies and the browser's trusted Origin. The header/cookie must also match the hash stored for that exact session; a token from another session is rejected. Keep the operation's existing `Idempotency-Key` and reviewed case version where required.
5. DELETE `/api/session` with Origin and CSRF headers revokes that session and clears both cookies. Subsequent access returns 401. Expired/revoked/missing sessions also return 401; the frontend should return to its login state. Simultaneous logout lock conflicts may return a retryable 409.

The frontend's existing merchant bearer mode remains unchanged by this backend task; Person 4 must implement the cookie flow rather than claim the current credential-paste screen is already session-based. Valid explicit merchant bearer authentication takes precedence over cookies and follows its existing non-cookie CSRF behavior; invalid/malformed Authorization never falls back to a valid cookie.

## Lifetime and authorization

Session and CSRF values each contain 256 random bits and are stored only as SHA-256 digests. Each successful exchange creates fresh values; it does not consume or revoke the initial credential/grant. Codes remain reusable until their own expiry/revocation, so keep them private and revoke grants when needed. Session lifetime is the lesser of eight hours and the underlying access expiry. A revoked session does not revoke its parent; a revoked/expired parent blocks all its sessions.

Authentication derives the actor from persisted rows. Transaction-time checks lock the underlying credential/grant before the session and recheck the database clock after waiting. Invoice/evidence/verification/resolution/grant services reauthorize the merchant session inside their existing transactions, including after external normalization/verification. Revocation during external work prevents the later write. Credential identity remains the audit actor for merchant actions, preserving prior hashes and retry scoping; the session is an authentication transport, not a new merchant identity.

Customer/reviewer sessions can currently read their session scope but are denied all existing merchant-only endpoints, including case listing/full reports, verification, decisions, and grant management. Person 3's M4.4 routes should use `require_actor` and `authorize_case_access` for customer submission. Person 2's M4.5 routes must use explicit disclosure projections. Never substitute a grant principal for a merchant principal or authorize from a client-supplied context.

## Failure and deployment boundaries

Untrusted/missing Origin or invalid CSRF returns 403; HTTP session exchange/use returns 400; invalid/expired/revoked codes/session return 401; unconfigured browser origins return 503 on exchange/cookie writes. Unknown input fields and malformed codes return sanitized 422 responses. Database failures remain generic. A failed commit sets no cookies and returns no session secrets. Responses use `Cache-Control: no-store`, and documented API startup disables access logging.

Do not expose the development POC token, real customer evidence, or secrets through frontend builds. TLS/proxy validation, ingress throttling, cookie behavior in the deployed browser, backup/restore, and retention/purge remain deployment/release work. The tests use HTTPS TestClient requests and disposable schemas; they do not constitute a deployed-browser acceptance run.

Published schemas: [exchange request](../contracts/session-exchange-request.schema.json), [session metadata](../contracts/session-info.schema.json), and [shared access context](../contracts/access-context.schema.json). Design references: [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) and [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
