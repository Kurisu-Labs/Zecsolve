// Demo data. Every recovered value below comes from the real historical mainnet
// fixture in fixtures/manifest.json (Glasspane receipt, Orchard output #1).
// Invoices, merchants, events and chain observations are synthetic and labelled so in the UI.

import { evaluate, type Allocation } from './rules'
import type {
  CaseEvent,
  CaseReport,
  CaseState,
  ChainObservation,
  ClaimView,
  EvidenceStored,
  InvoiceTerms,
  VerificationAttempt,
  VerificationReport,
} from './types'

export const FIXTURE = {
  network: 'mainnet',
  pool: 'orchard',
  txid: '66167cd3020eb329446e86d80ccd0494baa3959bf9a0e586dbdccd204b6dcfd0',
  outputIndex: 1,
  amountZat: 100_000,
  memoText: 'glasspane first receipt',
  receiverAddress:
    'u1ug9ltzk9y74pgqtc7mtwnc8vsnlqlsalhamkfd4lyhegrfv6ff5znwr4syzylrpta36ehs3jjm3c4ssvpfar8zq2hamg35wwzqxqemeu',
  receiverHex: 'ab7196fa80c61c65508be3923dbb8b416fc9fc50516e33e7be761e5da01b35a857f1770483a36b0f2b07ad',
  receiptSha256: 'd7caf254a40320441e930b24d114b5aeaa9d566f5f472d36ef15ffaf1eeefcb4',
  tamperedSha256: '57025034d2d5e54e7dddd4a0f83d25ac6592e39bc1afc0bac32eb0e751ea0ca2',
  rawTxSha256: 'a8e89cb90511d6bf54beb26eb73cd980e676301fea9ce3f7464fe79931c72e39',
  glasspaneRevision: 'f6468e6d08a7adad53bf2991a311358dc84e869b',
} as const

export const FIXTURE_OUTPUT_ID = `${FIXTURE.network}:${FIXTURE.pool}:${FIXTURE.txid}:${FIXTURE.outputIndex}`

function asciiMemoHex(text: string): string {
  let hex = ''
  for (const ch of text) hex += ch.charCodeAt(0).toString(16).padStart(2, '0')
  return hex.padEnd(1024, '0')
}

export const FIXTURE_MEMO_HEX = asciiMemoHex(FIXTURE.memoText)

/** Deterministic pseudo-hash for synthetic events (FNV-1a, widened). Not cryptographic. */
export function demoHash(seed: string): string {
  let out = ''
  let h = 0x811c9dc5
  for (let round = 0; round < 8; round++) {
    for (const ch of `${seed}:${round}`) {
      h ^= ch.charCodeAt(0)
      h = Math.imul(h, 0x01000193) >>> 0
    }
    out += h.toString(16).padStart(8, '0')
  }
  return out
}

export function demoUuid(seed: string): string {
  const h = demoHash(seed)
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`
}

const MERCHANT_ID = demoUuid('merchant')
const CREDENTIAL = `credential:${demoUuid('credential')}`

export const validReport: VerificationReport = {
  receipt_state: 'VALID',
  chain_state: 'UNAVAILABLE',
  reason_code: 'OUTPUT_RECOVERED',
  raw_tx_verified: true,
  receipt_sha256: FIXTURE.receiptSha256,
  raw_tx_sha256: FIXTURE.rawTxSha256,
  verifier: { name: 'zecsolve-verifier', version: '0.1.0', glasspane_revision: FIXTURE.glasspaneRevision },
  output: {
    network: FIXTURE.network,
    pool: FIXTURE.pool,
    txid: FIXTURE.txid,
    output_index: FIXTURE.outputIndex,
    amount_zat: FIXTURE.amountZat,
    receiver_hex: FIXTURE.receiverHex,
    receiver_address: FIXTURE.receiverAddress,
    memo_hex: FIXTURE_MEMO_HEX,
  },
}

export const tamperedReport: VerificationReport = {
  receipt_state: 'INVALID',
  chain_state: 'UNAVAILABLE',
  reason_code: 'OUTPUT_DECRYPTION_FAILED',
  raw_tx_verified: true,
  receipt_sha256: FIXTURE.tamperedSha256,
  raw_tx_sha256: FIXTURE.rawTxSha256,
  verifier: { name: 'zecsolve-verifier', version: '0.1.0', glasspane_revision: FIXTURE.glasspaneRevision },
  output: null,
}

export const noReceiptReport: VerificationReport = {
  receipt_state: 'NONE',
  chain_state: 'UNAVAILABLE',
  reason_code: 'NO_RECEIPT',
  output: null,
}

export interface DemoCase {
  key: string
  title: string
  summary: string
  customer: string
  terms: InvoiceTerms
  invoiceId: string
  caseId: string
  createdAt: string
  state: CaseState
  version: number
  claims: ClaimView[]
  evidence: EvidenceStored[]
  verifications: VerificationAttempt[]
  observations: ChainObservation[]
  /** Allocations already approved in this deployment (any invoice). */
  ledger: Allocation[]
  decisions: NonNullable<CaseReport['decisions']>
  events: CaseEvent[]
}

function terms(expectedZat: number, memo = true): InvoiceTerms {
  return {
    expected_zat: expectedZat,
    network: 'mainnet',
    pool: 'orchard',
    receiver_address: FIXTURE.receiverAddress,
    expected_memo: memo ? FIXTURE.memoText : null,
    expires_at: null,
    receiver_hex: FIXTURE.receiverHex,
    memo_hex: memo ? FIXTURE_MEMO_HEX : null,
  }
}

function event(caseId: string, sequence: number, action: string, at: string): CaseEvent {
  return {
    event_id: demoUuid(`${caseId}:event:${sequence}`),
    sequence,
    actor: CREDENTIAL,
    action,
    at,
    event_hash: demoHash(`${caseId}:${sequence}:${action}`),
  }
}

function evidence(caseId: string, n: number, at: string, tampered: boolean): EvidenceStored {
  return {
    evidence_id: demoUuid(`${caseId}:evidence:${n}`),
    submitted_by: CREDENTIAL,
    submitted_at: at,
    source: tampered ? 'Customer upload (tampered fixture)' : 'Customer upload (historical fixture)',
    source_kind: 'merchant_submission',
    receipt_sha256: tampered ? FIXTURE.tamperedSha256 : FIXTURE.receiptSha256,
    raw_tx_hex_sha256: FIXTURE.rawTxSha256,
    payload_sha256: demoHash(`${caseId}:payload:${n}`),
  }
}

function attempt(caseId: string, n: number, evidenceId: string, at: string, report: VerificationReport): VerificationAttempt {
  return { verification_id: demoUuid(`${caseId}:verification:${n}`), evidence_id: evidenceId, created_at: at, result: report }
}

function offline(verificationId: string, at: string): ChainObservation {
  return {
    observation_id: demoUuid(`${verificationId}:observation:offline`),
    verification_id: verificationId,
    state: 'UNAVAILABLE',
    source: 'Offline verifier (no chain source configured)',
    reason_code: 'CHAIN_SOURCE_UNAVAILABLE',
    observed_at: at,
    confirmations: null,
    block_height: null,
  }
}

function build(): DemoCase[] {
  const t0 = '2026-10-11T02:14:00Z'
  const t1 = '2026-10-11T02:31:00Z'
  const t2 = '2026-10-11T02:32:00Z'

  // 1. Partial payment: the receipt is real, the invoice asked for twice as much.
  const shortfallId = demoUuid('case:shortfall')
  const shortfallEv = evidence(shortfallId, 1, t1, false)
  const shortfallAt = attempt(shortfallId, 1, shortfallEv.evidence_id, t2, validReport)

  // 2. The same output already settled another invoice in this deployment.
  const duplicateId = demoUuid('case:duplicate')
  const duplicateEv = evidence(duplicateId, 1, t1, false)
  const duplicateAt = attempt(duplicateId, 1, duplicateEv.evidence_id, t2, validReport)

  // 3. A tampered receipt against the same transaction.
  const invalidId = demoUuid('case:invalid')
  const invalidEv = evidence(invalidId, 1, t1, true)
  const invalidAt = attempt(invalidId, 1, invalidEv.evidence_id, t2, tamperedReport)

  // 4. A claim with no receipt yet.
  const waitingId = demoUuid('case:waiting')

  const claim = (caseId: string, note: string, txid: string | null): ClaimView => ({
    claim_id: demoUuid(`${caseId}:claim`),
    claimant_role: 'customer',
    reported_txid: txid,
    note,
    created_at: t0,
  })

  const otherInvoice = demoUuid('invoice:earlier-order')

  return [
    {
      key: 'shortfall',
      title: 'Half the invoice arrived',
      summary: 'A real receipt recovers 100,000 zatoshis against a 200,000 invoice.',
      customer: 'Order 4021',
      terms: terms(200_000),
      invoiceId: demoUuid('invoice:shortfall'),
      caseId: shortfallId,
      createdAt: t0,
      state: 'UNDER_REVIEW',
      version: 3,
      claims: [claim(shortfallId, 'I paid from my shielded wallet but the store says unpaid.', FIXTURE.txid)],
      evidence: [shortfallEv],
      verifications: [shortfallAt],
      observations: [offline(shortfallAt.verification_id, t2)],
      ledger: [],
      decisions: [],
      events: [
        event(shortfallId, 1, 'CASE_OPENED', t0),
        event(shortfallId, 2, 'EVIDENCE_SUBMITTED', t1),
        event(shortfallId, 3, 'VERIFICATION_RECORDED', t2),
      ],
    },
    {
      key: 'duplicate',
      title: 'One payment, two invoices',
      summary: 'The output already settled an earlier order. Crediting it again is blocked.',
      customer: 'Order 4188',
      terms: terms(100_000),
      invoiceId: demoUuid('invoice:duplicate'),
      caseId: duplicateId,
      createdAt: t0,
      state: 'UNDER_REVIEW',
      version: 3,
      claims: [claim(duplicateId, 'Same transaction as my last order, please check.', FIXTURE.txid)],
      evidence: [duplicateEv],
      verifications: [duplicateAt],
      observations: [offline(duplicateAt.verification_id, t2)],
      ledger: [{ output_id: FIXTURE_OUTPUT_ID, invoice_id: otherInvoice, amount_zat: FIXTURE.amountZat }],
      decisions: [],
      events: [
        event(duplicateId, 1, 'CASE_OPENED', t0),
        event(duplicateId, 2, 'EVIDENCE_SUBMITTED', t1),
        event(duplicateId, 3, 'VERIFICATION_RECORDED', t2),
      ],
    },
    {
      key: 'invalid',
      title: 'A receipt that does not open',
      summary: 'The output key was altered. The verifier rejects it without guessing why.',
      customer: 'Order 4203',
      terms: terms(100_000),
      invoiceId: demoUuid('invoice:invalid'),
      caseId: invalidId,
      createdAt: t0,
      state: 'UNDER_REVIEW',
      version: 3,
      claims: [claim(invalidId, 'Here is my receipt.', FIXTURE.txid)],
      evidence: [invalidEv],
      verifications: [invalidAt],
      observations: [offline(invalidAt.verification_id, t2)],
      ledger: [],
      decisions: [],
      events: [
        event(invalidId, 1, 'CASE_OPENED', t0),
        event(invalidId, 2, 'EVIDENCE_SUBMITTED', t1),
        event(invalidId, 3, 'VERIFICATION_RECORDED', t2),
      ],
    },
    {
      key: 'waiting',
      title: 'A claim with nothing to check',
      summary: 'The customer reported a transaction but has not shared a receipt.',
      customer: 'Order 4230',
      terms: terms(100_000),
      invoiceId: demoUuid('invoice:waiting'),
      caseId: waitingId,
      createdAt: t0,
      state: 'AWAITING_EVIDENCE',
      version: 1,
      claims: [claim(waitingId, 'Paid an hour ago, nothing shows on my order.', null)],
      evidence: [],
      verifications: [],
      observations: [],
      ledger: [],
      decisions: [],
      events: [event(waitingId, 1, 'CASE_OPENED', t0)],
    },
  ]
}

export function createDemoCases(): DemoCase[] {
  return build()
}

/** Assemble the same report shape GET /api/cases/{id}/report returns. */
export function toReport(c: DemoCase, selectedId?: string | null): CaseReport {
  const selected =
    c.verifications.find((v) => v.verification_id === selectedId) ?? c.verifications[c.verifications.length - 1] ?? null
  const report = selected?.result ?? noReceiptReport
  const observation = selected
    ? [...c.observations].reverse().find((o) => o.verification_id === selected.verification_id)
    : undefined
  const balances = evaluate(c.invoiceId, c.terms, report, c.ledger, observation?.state ?? 'UNAVAILABLE')
  return {
    generated_at: new Date().toISOString(),
    case: {
      case_id: c.caseId,
      invoice_id: c.invoiceId,
      merchant_id: MERCHANT_ID,
      state: c.state,
      version: c.version,
      created_at: c.createdAt,
    },
    invoice: {
      invoice_id: c.invoiceId,
      merchant_id: MERCHANT_ID,
      policy_id: demoUuid('policy:v1'),
      created_at: c.createdAt,
      terms: c.terms,
      snapshot_hash: demoHash(`${c.invoiceId}:snapshot`),
    },
    claims: c.claims,
    evidence: c.evidence,
    verifications: c.verifications,
    chain_observations: c.observations,
    selected_verification_id: selected?.verification_id ?? null,
    balances,
    decisions: c.decisions,
    events: c.events,
  }
}

export { CREDENTIAL as DEMO_CREDENTIAL }
