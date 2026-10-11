// TypeScript port of apps/api/src/zecsolve/domain/rules.py (RULES_VERSION 0.1.0).
// Used only by demo mode so the offline demo shows the same findings the API would.
// In live mode the server's evaluation is the source of truth.

import type { Balances, ChainState, Finding, InvoiceTerms, VerificationReport } from './types'

export const RULES_VERSION = '0.1.0'

export interface Allocation {
  output_id: string
  invoice_id: string
  amount_zat: number
}

export function evaluate(
  invoiceId: string,
  terms: InvoiceTerms,
  report: VerificationReport,
  allocations: Allocation[],
  chainState: ChainState,
): Balances {
  const unique = new Map<string, Allocation>()
  for (const a of allocations) unique.set(a.output_id, a)
  let credited = 0
  for (const a of unique.values()) if (a.invoice_id === invoiceId) credited += a.amount_zat

  const findings: Finding[] = []
  let candidate = 0
  let eligible = false

  if (report.receipt_state !== 'VALID' || !report.output) {
    findings.push(
      report.receipt_state === 'INVALID'
        ? 'INVALID_EVIDENCE'
        : report.receipt_state === 'UNSUPPORTED'
          ? 'UNSUPPORTED_EVIDENCE'
          : 'INSUFFICIENT_EVIDENCE',
    )
  } else {
    const output = report.output
    const match =
      output.network === terms.network && output.pool === terms.pool && output.receiver_hex === terms.receiver_hex
    if (!match) findings.push('RECIPIENT_MISMATCH')
    const memoMatch = terms.memo_hex !== null && output.memo_hex === terms.memo_hex
    const referenceBound = memoMatch
    if (terms.memo_hex !== null && !memoMatch) findings.push('MEMO_MISMATCH')
    if (!referenceBound) findings.push('NEEDS_REVIEW')
    const identity = `${output.network}:${output.pool}:${output.txid}:${output.output_index}`
    const allocated = unique.get(identity)
    if (allocated) findings.push(allocated.invoice_id === invoiceId ? 'ALREADY_ALLOCATED' : 'DUPLICATE_CLAIM')
    if (match && referenceBound && !allocated) {
      candidate = output.amount_zat
      eligible = chainState === 'CONFIRMED'
      if (credited + candidate > terms.expected_zat) {
        findings.push('OVERPAYMENT_REVIEW')
        eligible = false
      }
    }
  }
  if (chainState !== 'CONFIRMED') findings.push('CHAIN_UNVERIFIED')
  findings.push(credited < terms.expected_zat ? 'UNDERPAID' : credited > terms.expected_zat ? 'OVERPAID' : 'MATCH')
  if (eligible) findings.push('ELIGIBLE_FOR_CREDIT')

  return {
    rules_version: RULES_VERSION,
    findings,
    credited_zat: credited,
    outstanding_zat: Math.max(terms.expected_zat - credited, 0),
    excess_zat: Math.max(credited - terms.expected_zat, 0),
    candidate_zat: candidate,
    projected_outstanding_zat: Math.max(terms.expected_zat - credited - candidate, 0),
    eligible_for_credit: eligible,
  }
}
