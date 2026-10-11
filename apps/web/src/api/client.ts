// Thin client for the FastAPI case workflow. Same-origin: Vite proxies /api in development.

import type {
  CaseReport,
  EvidenceStored,
  EvidenceSubmitRequest,
  ResolveRequest,
  ResolutionOutcome,
  VerificationAttempt,
} from './types'

const TOKEN_KEY = 'zecsolve.merchantCredential'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail)
  }
}

export function readCredential(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeCredential(value: string | null): void {
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable: live mode lasts for this page only */
  }
}

/** A fresh key per user action; retries of the same action must reuse it. */
export function idempotencyKey(): string {
  return crypto.randomUUID()
}

async function request<T>(path: string, init: RequestInit & { idempotencyKey?: string } = {}): Promise<T> {
  const token = readCredential()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.idempotencyKey) headers.set('Idempotency-Key', init.idempotencyKey)
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail) detail = JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

export const api = {
  async whoami(): Promise<{ merchant_id: string; credential_id: string }> {
    return request('/api/auth/me')
  },

  async report(caseId: string, verificationId?: string | null): Promise<CaseReport> {
    const query = verificationId ? `?verification_id=${encodeURIComponent(verificationId)}` : ''
    return request(`/api/cases/${encodeURIComponent(caseId)}/report${query}`)
  },

  async submitEvidence(caseId: string, body: EvidenceSubmitRequest, key: string): Promise<EvidenceStored> {
    return request(`/api/cases/${encodeURIComponent(caseId)}/evidence`, {
      method: 'POST',
      body: JSON.stringify(body),
      idempotencyKey: key,
    })
  },

  async verify(caseId: string, evidenceId: string, key: string): Promise<VerificationAttempt> {
    return request(`/api/cases/${encodeURIComponent(caseId)}/verify`, {
      method: 'POST',
      body: JSON.stringify({ evidence_id: evidenceId }),
      idempotencyKey: key,
    })
  },

  async refreshChain(caseId: string, verificationId: string, key: string): Promise<unknown> {
    return request(`/api/cases/${encodeURIComponent(caseId)}/chain-observations`, {
      method: 'POST',
      body: JSON.stringify({ verification_id: verificationId }),
      idempotencyKey: key,
    })
  },

  async resolve(caseId: string, body: ResolveRequest, key: string): Promise<ResolutionOutcome> {
    return request(`/api/cases/${encodeURIComponent(caseId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(body),
      idempotencyKey: key,
    })
  },
}
