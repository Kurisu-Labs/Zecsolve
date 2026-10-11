import type { CaseState, ChainState, Finding, ReceiptState, ResolveAction } from '@/api/types'

// Four layers stay separate: a valid receipt never reads as "paid",
// and unavailable data never reads as tampering (PRD A-08).

export type Tone = 'ok' | 'warn' | 'fail' | 'unknown' | 'zec' | 'neutral'
export type Glyph = 'open' | 'cracked' | 'empty' | 'info' | 'clock' | 'retry' | 'check' | 'dash' | 'lock'

export interface StatusView {
  label: string
  detail: string
  tone: Tone
  glyph: Glyph
}

export const receiptView: Record<ReceiptState, StatusView> = {
  VALID: {
    label: 'Output recovered',
    detail: 'The receipt opens exactly one output of the supplied transaction.',
    tone: 'ok',
    glyph: 'open',
  },
  INVALID: {
    label: 'Evidence rejected',
    detail: 'The receipt does not decrypt an output of this transaction.',
    tone: 'fail',
    glyph: 'cracked',
  },
  NONE: {
    label: 'No receipt yet',
    detail: 'The customer has not shared an output receipt. This is not a failed payment.',
    tone: 'unknown',
    glyph: 'empty',
  },
  UNSUPPORTED: {
    label: 'Format not supported',
    detail: 'The receipt or transaction version is outside what the verifier handles.',
    tone: 'unknown',
    glyph: 'info',
  },
  UNAVAILABLE: {
    label: 'Data unavailable',
    detail: 'The verifier or a required input was not available.',
    tone: 'unknown',
    glyph: 'clock',
  },
  ERROR: {
    label: 'Verification failed to run',
    detail: 'A timeout or malformed transaction stopped verification. Try again.',
    tone: 'warn',
    glyph: 'retry',
  },
}

export const chainView: Record<ChainState, StatusView> = {
  CONFIRMED: {
    label: 'Confirmed on chain',
    detail: 'A trusted chain source reported enough confirmations.',
    tone: 'ok',
    glyph: 'check',
  },
  UNCONFIRMED: {
    label: 'Not yet confirmed',
    detail: 'A chain source saw the transaction without enough confirmations.',
    tone: 'warn',
    glyph: 'clock',
  },
  UNAVAILABLE: {
    label: 'Not checked',
    detail: 'No trusted chain observation exists. A valid receipt can still be true.',
    tone: 'unknown',
    glyph: 'dash',
  },
}

export const caseStates: { state: CaseState; label: string }[] = [
  { state: 'OPEN', label: 'Opened' },
  { state: 'AWAITING_EVIDENCE', label: 'Awaiting evidence' },
  { state: 'UNDER_REVIEW', label: 'Under review' },
  { state: 'RESOLVED', label: 'Resolved' },
]

export const caseStateLabel: Record<CaseState, string> = {
  OPEN: 'Opened',
  AWAITING_EVIDENCE: 'Awaiting evidence',
  UNDER_REVIEW: 'Under review',
  RESOLVED: 'Resolved',
  CLOSED_UNRESOLVED: 'Closed unresolved',
}

export const findingView: Record<Finding, { label: string; tone: Tone; help: string }> = {
  INVALID_EVIDENCE: { label: 'Invalid evidence', tone: 'fail', help: 'The receipt failed to recover an output.' },
  UNSUPPORTED_EVIDENCE: { label: 'Unsupported evidence', tone: 'unknown', help: 'The verifier cannot read this format.' },
  INSUFFICIENT_EVIDENCE: { label: 'Not enough evidence', tone: 'unknown', help: 'Nothing has been verified yet.' },
  RECIPIENT_MISMATCH: { label: 'Different receiver', tone: 'fail', help: 'The output paid an address other than the invoice receiver.' },
  MEMO_MISMATCH: { label: 'Memo does not match', tone: 'warn', help: 'The recovered memo differs from the invoice reference.' },
  NEEDS_REVIEW: { label: 'Needs manual review', tone: 'warn', help: 'Nothing binds this output to this invoice yet.' },
  ALREADY_ALLOCATED: { label: 'Already credited here', tone: 'neutral', help: 'This output is already credited to this invoice. No double credit.' },
  DUPLICATE_CLAIM: { label: 'Credited to another invoice', tone: 'fail', help: 'This output already settled a different invoice.' },
  OVERPAYMENT_REVIEW: { label: 'Would overpay', tone: 'warn', help: 'Crediting this output exceeds the invoice amount.' },
  CHAIN_UNVERIFIED: { label: 'Chain not verified', tone: 'unknown', help: 'Approval waits for a trusted confirmation.' },
  UNDERPAID: { label: 'Invoice underpaid', tone: 'warn', help: 'Approved credit is below the invoice amount.' },
  OVERPAID: { label: 'Invoice overpaid', tone: 'warn', help: 'Approved credit exceeds the invoice amount.' },
  MATCH: { label: 'Invoice settled', tone: 'ok', help: 'Approved credit equals the invoice amount.' },
  ELIGIBLE_FOR_CREDIT: { label: 'Eligible for credit', tone: 'zec', help: 'All checks pass. A merchant can approve.' },
}

export const actionView: Record<ResolveAction, { label: string; done: string; help: string }> = {
  APPROVE_OUTPUT: {
    label: 'Approve output',
    done: 'Output approved',
    help: 'Credit the recovered amount to this invoice.',
  },
  REQUEST_EVIDENCE: {
    label: 'Request evidence',
    done: 'Evidence requested',
    help: 'Ask the customer for a receipt or a corrected one.',
  },
  REJECT_EVIDENCE: {
    label: 'Reject evidence',
    done: 'Evidence rejected',
    help: 'Record why this receipt cannot settle the invoice.',
  },
  CLOSE_UNRESOLVED: {
    label: 'Close unresolved',
    done: 'Case closed unresolved',
    help: 'Stop work on the case without crediting anything.',
  },
}

/** "a1b2c3d4…9f0e" — keeps both ends of a hash readable. */
export function shortHash(value: string, head = 8, tail = 6): string {
  if (value.length <= head + tail + 1) return value
  return `${value.slice(0, head)}…${value.slice(-tail)}`
}

export function outputId(network: string, pool: string, txid: string, index: number): string {
  return `${network}:${pool}:${txid}:${index}`
}

const dateFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})
export function formatWhen(iso: string): string {
  return dateFormat.format(new Date(iso))
}

/** Decode a 512-byte memo hex for display only: printable ASCII, nulls trimmed. Never executed. */
export function memoPreview(hex: string | null | undefined): string | null {
  if (!hex) return null
  let out = ''
  for (let i = 0; i + 1 < hex.length; i += 2) {
    const code = parseInt(hex.slice(i, i + 2), 16)
    if (code === 0) break
    out += code >= 32 && code < 127 ? String.fromCharCode(code) : '·'
  }
  return out || null
}
