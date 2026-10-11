// One interface for both modes. Demo mode replays recorded fixture outcomes in memory;
// live mode calls the FastAPI workflow with the merchant credential.

import { reactive, readonly } from 'vue'
import { api, idempotencyKey, readCredential, writeCredential } from './client'
import {
  DEMO_CREDENTIAL,
  FIXTURE,
  createDemoCases,
  demoUuid,
  noReceiptReport,
  tamperedReport,
  toReport,
  validReport,
  type DemoCase,
} from './fixtures'
import { evaluate } from './rules'
import type { CaseReport, CaseState, ChainObservation, ResolveRequest, VerificationReport } from './types'

export type Mode = 'demo' | 'live'

export interface CaseListItem {
  caseId: string
  title: string
  customer: string
  state: CaseState
  expectedZat: number
  candidateZat: number
  creditedZat: number
  receipt: VerificationReport['receipt_state']
  chain: ChainObservation['state']
  updatedAt: string
}

const KNOWN_CASES_KEY = 'zecsolve.knownCases'

const state = reactive({
  mode: (readCredential() ? 'live' : 'demo') as Mode,
  demo: createDemoCases(),
})

export const session = readonly(state)

export function setLiveCredential(token: string | null): void {
  writeCredential(token)
  state.mode = token ? 'live' : 'demo'
}

export function resetDemo(): void {
  state.demo = createDemoCases()
}

function knownLiveCases(): string[] {
  try {
    return JSON.parse(localStorage.getItem(KNOWN_CASES_KEY) ?? '[]') as string[]
  } catch {
    return []
  }
}

export function rememberLiveCase(caseId: string): void {
  const ids = new Set(knownLiveCases())
  ids.add(caseId)
  try {
    localStorage.setItem(KNOWN_CASES_KEY, JSON.stringify([...ids]))
  } catch {
    /* ignore */
  }
}

function demoCase(caseId: string): DemoCase {
  const found = state.demo.find((c) => c.caseId === caseId || c.key === caseId)
  if (!found) throw new Error('This case does not exist in the demo data.')
  return found
}

function summarize(report: CaseReport, title: string, customer: string): CaseListItem {
  const latest = report.verifications[report.verifications.length - 1]
  const obs = report.chain_observations[report.chain_observations.length - 1]
  const lastEvent = report.events[report.events.length - 1]
  return {
    caseId: report.case.case_id,
    title,
    customer,
    state: report.case.state,
    expectedZat: report.invoice.terms.expected_zat,
    candidateZat: report.balances.candidate_zat,
    creditedZat: report.balances.credited_zat,
    receipt: latest?.result.receipt_state ?? 'NONE',
    chain: obs?.state ?? 'UNAVAILABLE',
    updatedAt: lastEvent?.at ?? report.case.created_at,
  }
}

function pushEvent(c: DemoCase, action: string, at: string): void {
  const sequence = c.events.length + 1
  c.events.push({
    event_id: demoUuid(`${c.caseId}:event:${sequence}`),
    sequence,
    actor: DEMO_CREDENTIAL,
    action,
    at,
    event_hash: demoUuid(`${c.caseId}:hash:${sequence}`).replace(/-/g, '').padEnd(64, '0'),
  })
  c.version += 1
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export const cases = {
  async list(): Promise<CaseListItem[]> {
    if (state.mode === 'demo') return state.demo.map((c) => summarize(toReport(c), c.title, c.customer))
    const reports = await Promise.allSettled(knownLiveCases().map((id) => api.report(id)))
    return reports.flatMap((r) =>
      r.status === 'fulfilled' ? [summarize(r.value, 'Merchant case', r.value.invoice.invoice_id.slice(0, 8))] : [],
    )
  },

  async report(caseId: string, verificationId?: string | null): Promise<CaseReport> {
    if (state.mode === 'demo') return toReport(demoCase(caseId), verificationId)
    const report = await api.report(caseId, verificationId)
    rememberLiveCase(report.case.case_id)
    return report
  },

  /** Synchronous demo report for previews (landing page). */
  demoReport(key: string): CaseReport | null {
    const c = state.demo.find((d) => d.key === key)
    return c ? toReport(c) : null
  },

  demoMeta(caseId: string): { title: string; summary: string; customer: string; key: string } | null {
    const c = state.demo.find((d) => d.caseId === caseId || d.key === caseId)
    return c ? { title: c.title, summary: c.summary, customer: c.customer, key: c.key } : null
  },

  /**
   * Customer submission. Demo mode recognises the bundled historical receipt by its
   * output key and replays the verifier's recorded result; anything else is rejected.
   */
  async submitAndVerify(
    caseId: string,
    input: { receiptJson: string | null; rawTxHex: string | null; source: string },
  ): Promise<{ verificationId: string | null; report: VerificationReport }> {
    if (state.mode === 'live') {
      const stored = await api.submitEvidence(
        caseId,
        {
          receipt_json: input.receiptJson,
          raw_tx_hex: input.rawTxHex,
          source: input.source,
          source_kind: 'merchant_submission',
          disclosure_version: 'evidence-disclosure-v1',
          processing_authorized: true,
          share_with_reviewers: false,
        },
        idempotencyKey(),
      )
      const attempt = await api.verify(caseId, stored.evidence_id, idempotencyKey())
      return { verificationId: attempt.verification_id, report: attempt.result }
    }

    const c = demoCase(caseId)
    await wait(900) // the real verifier takes about this long on the fixture
    const at = new Date().toISOString()
    let report: VerificationReport = noReceiptReport
    if (input.receiptJson) {
      report = input.receiptJson.includes('pNVZw22HvhbkKcYDNV_bo6eMjukjcfaxMDQYOEF1mkI') ? validReport : tamperedReport
    }
    const n = c.evidence.length + 1
    const evidenceId = demoUuid(`${c.caseId}:evidence:${n}:${at}`)
    c.evidence.push({
      evidence_id: evidenceId,
      submitted_by: 'customer:demo',
      submitted_at: at,
      source: input.source,
      source_kind: 'merchant_submission',
      receipt_sha256: report.receipt_sha256 ?? null,
      raw_tx_hex_sha256: input.rawTxHex ? FIXTURE.rawTxSha256 : null,
      payload_sha256: demoUuid(`${evidenceId}:payload`).replace(/-/g, '').padEnd(64, '0'),
    })
    pushEvent(c, 'EVIDENCE_SUBMITTED', at)
    if (report.receipt_state === 'NONE') {
      c.state = 'AWAITING_EVIDENCE'
      return { verificationId: null, report }
    }
    const verificationId = demoUuid(`${c.caseId}:verification:${n}:${at}`)
    c.verifications.push({ verification_id: verificationId, evidence_id: evidenceId, created_at: at, result: report })
    c.observations.push({
      observation_id: demoUuid(`${verificationId}:offline`),
      verification_id: verificationId,
      state: 'UNAVAILABLE',
      source: 'Offline verifier (no chain source configured)',
      reason_code: 'CHAIN_SOURCE_UNAVAILABLE',
      observed_at: at,
    })
    pushEvent(c, 'VERIFICATION_RECORDED', at)
    c.state = 'UNDER_REVIEW'
    return { verificationId, report }
  },

  /** Demo mode records a clearly labelled simulated confirmation. */
  async refreshChain(caseId: string, verificationId: string): Promise<void> {
    if (state.mode === 'live') {
      await api.refreshChain(caseId, verificationId, idempotencyKey())
      return
    }
    const c = demoCase(caseId)
    await wait(700)
    const at = new Date().toISOString()
    c.observations.push({
      observation_id: demoUuid(`${verificationId}:confirmed:${at}`),
      verification_id: verificationId,
      state: 'CONFIRMED',
      source: 'Simulated chain source (demo only)',
      reason_code: 'CONFIRMATIONS_MET',
      observed_at: at,
      confirmations: 12,
      block_height: null,
    })
    pushEvent(c, 'CHAIN_OBSERVED', at)
  },

  async resolve(caseId: string, request: ResolveRequest): Promise<void> {
    if (state.mode === 'live') {
      await api.resolve(caseId, request, idempotencyKey())
      return
    }
    const c = demoCase(caseId)
    if (request.expected_case_version !== c.version) {
      throw new Error('This case changed while you were reviewing it. Reload and review the new version.')
    }
    if (!request.reason.trim()) throw new Error('Write a reason before recording a decision.')
    await wait(500)
    const at = new Date().toISOString()
    const verification = c.verifications.find((v) => v.verification_id === request.verification_id)
    let allocated = 0
    let outputId: string | null = null
    if (request.action === 'APPROVE_OUTPUT') {
      const obs = verification
        ? [...c.observations].reverse().find((o) => o.verification_id === verification.verification_id)
        : undefined
      if (!verification?.result.output) throw new Error('Pick a verified output before approving.')
      const balances = evaluate(c.invoiceId, c.terms, verification.result, c.ledger, obs?.state ?? 'UNAVAILABLE')
      if (!balances.eligible_for_credit) {
        throw new Error('This output is not eligible for credit. Check the findings first.')
      }
      const o = verification.result.output
      outputId = `${o.network}:${o.pool}:${o.txid}:${o.output_index}`
      allocated = o.amount_zat
      c.ledger.push({ output_id: outputId, invoice_id: c.invoiceId, amount_zat: allocated })
    }
    const nextState: CaseState =
      request.action === 'APPROVE_OUTPUT'
        ? 'RESOLVED'
        : request.action === 'REQUEST_EVIDENCE'
          ? 'AWAITING_EVIDENCE'
          : request.action === 'CLOSE_UNRESOLVED'
            ? 'CLOSED_UNRESOLVED'
            : 'UNDER_REVIEW'
    pushEvent(c, `RESOLUTION_${request.action}`, at)
    c.state = nextState
    c.decisions.push({
      resolution_id: demoUuid(`${c.caseId}:resolution:${at}`),
      action: request.action,
      reason: request.reason.trim(),
      decided_at: at,
      actor_id: DEMO_CREDENTIAL,
      verification_id: request.verification_id,
      output_id: outputId,
      allocated_zat: allocated,
      case_version: c.version,
      case_state: nextState,
    })
  },
}
