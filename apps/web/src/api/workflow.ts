import type { CaseReport, CaseState, ResolveAction, ResolveRequest } from './types'

export function latestObservation(report: CaseReport) {
  return [...report.chain_observations, ...(report.decision_observations ?? [])]
    .filter((o) => o.verification_id === report.selected_verification_id)
    .sort((a, b) => b.observed_at.localeCompare(a.observed_at) || b.observation_id.localeCompare(a.observation_id))[0]
}

/** Live readiness only permits a request; the server refreshes and authorizes credit. */
export function approvalReady(report: CaseReport, mode: 'live' | 'demo'): boolean {
  if (['RESOLVED', 'CLOSED_UNRESOLVED'].includes(report.case.state) || report.chain_review?.length) return false
  if (mode === 'demo') return report.balances.eligible_for_credit === true
  const selected = report.verifications.find((v) => v.verification_id === report.selected_verification_id)
  return selected?.result.receipt_state === 'VALID' && report.balances.candidate_zat > 0 &&
    !report.balances.findings.some((f) => ['OVERPAYMENT_REVIEW', 'RECIPIENT_MISMATCH', 'MEMO_MISMATCH', 'NEEDS_REVIEW', 'DUPLICATE_CLAIM', 'ALREADY_ALLOCATED'].includes(f))
}

export function decisionRequest(report: CaseReport, action: ResolveAction, reason: string): ResolveRequest {
  return {
    action,
    verification_id: action === 'APPROVE_OUTPUT' || action === 'REJECT_EVIDENCE'
      ? report.selected_verification_id : null,
    expected_case_version: report.case.version,
    reason: reason.trim(),
  }
}

export function approvalState(credited: number, expected: number): CaseState {
  return credited >= expected ? 'RESOLVED' : 'UNDER_REVIEW'
}
