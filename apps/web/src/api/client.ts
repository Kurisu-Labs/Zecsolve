import { retryIdentity, pendingKey, finishRequest } from './retry'
// Thin client for the FastAPI case workflow. Same-origin: Vite proxies /api in development.

import type {
  CaseReport,
  EvidenceStored,
  EvidenceSubmitRequest,
  ResolveRequest,
  ResolutionOutcome,
  VerificationAttempt,
} from './types'

import { csrfToken, type SessionInfo } from './access'
import type { components } from './contracts'
export type Contract = components['schemas']

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** A fresh key per user action; retries of the same action must reuse it. */
export function idempotencyKey(): string {
  return crypto.randomUUID()
}

export async function request<T>(path: string, init: RequestInit & { idempotencyKey?: string } = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  const method = (init.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD'].includes(method) && path !== '/api/session') {
    const csrf = csrfToken(document.cookie)
    if (!csrf) throw new ApiError(403, 'Session protection is missing. Sign in again before retrying.')
    headers.set('X-CSRF-Token', csrf)
  }
  if (method === 'DELETE' && path === '/api/session') {
    const csrf = csrfToken(document.cookie)
    if (csrf) headers.set('X-CSRF-Token', csrf)
  }
  const retry = init.idempotencyKey ? await retryIdentity(path, String(init.body ?? '')) : null
  if (retry) headers.set('Idempotency-Key', pendingKey(retry, init.idempotencyKey!))
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin', cache: 'no-store' })
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/session') window.dispatchEvent(new Event('zecsolve:unauthorized'))
    // Do not echo validation bodies: they can contain submitted secrets or evidence.
    const messages: Record<number, string> = {
      400: 'A secure HTTPS connection is required.',
      401: 'Access expired, was revoked, or is invalid. Sign in again.',
      403: 'This action is not permitted. Check your access and sign in again if needed.',
      404: 'This item is unavailable for your access.',
      409: 'The case or request conflicts with current state. Refresh and review before trying again.',
      413: 'The submission exceeds the allowed size.',
      422: 'Check the input format, required fields, and consent.',
      429: 'The service is busy. Retry the same request shortly.',
      503: 'The service is temporarily unavailable. Retry the same request later.',
    }
    throw new ApiError(response.status, messages[response.status] ?? `Request failed (${response.status}).`)
  }
  if (response.status === 204) return undefined as T
  const result = (await response.json()) as T
  if (retry) finishRequest(retry)
  return result
}

export const api = {
  session: () => request<SessionInfo>('/api/session'),
  connect: (code: string) => request<SessionInfo>('/api/session', { method: 'POST', body: JSON.stringify({ code }) }),
  logout: () => request<void>('/api/session', { method: 'DELETE' }),
  list: (cursor?: string, state?: string) => {
    const query = new URLSearchParams({ limit: '25' })
    if (cursor) query.set('cursor', cursor)
    if (state) query.set('state', state)
    return request<Contract['caseList']>(`/api/cases?${query}`)
  },
  invoice: (body: Contract['invoiceCreateRequest'], key: string) => request<Contract['invoiceSnapshot']>('/api/invoices', { method: 'POST', body: JSON.stringify(body), idempotencyKey: key }),
  openCase: (invoice_id: string, key: string) => request<Contract['caseOpened']>('/api/cases', { method: 'POST', body: JSON.stringify({ invoice_id }), idempotencyKey: key }),
  claim: (id: string, body: Contract['claimSubmitRequest'], key: string) => request<Contract['submissionAcknowledgement']>(`/api/cases/${encodeURIComponent(id)}/claims`, { method: 'POST', body: JSON.stringify(body), idempotencyKey: key }),
  evidence: (id: string, body: Contract['evidenceSubmitRequestV2'], key: string) => request<Contract['submissionAcknowledgement']>(`/api/cases/${encodeURIComponent(id)}/evidence`, { method: 'POST', body: JSON.stringify(body), idempotencyKey: key }),
  grants: (id: string) => request<Contract['grantList']>(`/api/cases/${encodeURIComponent(id)}/grants`),
  grant: (id: string, body: Contract['grantCreateRequest'], key: string) => request<Contract['grantCreated']>(`/api/cases/${encodeURIComponent(id)}/grants`, { method: 'POST', body: JSON.stringify(body), idempotencyKey: key }),
  revoke: (id: string, grant: string) => request<unknown>(`/api/cases/${encodeURIComponent(id)}/grants/${encodeURIComponent(grant)}`, { method: 'DELETE' }),
  reviewerReport: (id: string) => request<Contract['reviewerReport']>(`/api/cases/${encodeURIComponent(id)}/report`),
  content: (id: string, evidence: string) => request<Contract['evidenceContent']>(`/api/cases/${encodeURIComponent(id)}/evidence/${encodeURIComponent(evidence)}/content`),
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
