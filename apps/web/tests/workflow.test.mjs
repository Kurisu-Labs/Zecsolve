import assert from 'node:assert/strict'
import test from 'node:test'
import { approvalReady, decisionRequest, latestObservation, approvalState } from '../src/api/workflow.ts'

const report = {
  case: { version: 3, state: 'UNDER_REVIEW' },
  selected_verification_id: 'v1',
  verifications: [{ verification_id: 'v1', result: { receipt_state: 'VALID' } }],
  chain_observations: [{ observation_id: 'initial', verification_id: 'v1', observed_at: '2026-10-11T00:00:00Z', state: 'UNAVAILABLE' }],
  decision_observations: [{ observation_id: 'refresh', verification_id: 'v1', observed_at: '2026-10-11T01:00:00Z', state: 'CONFIRMED', source_kind: 'RPC' }],
  balances: { candidate_zat: 100000, eligible_for_credit: false, findings: ['CHAIN_UNVERIFIED', 'UNDERPAID'] },
}
test('live approval requests server evaluation instead of trusting offline eligibility', () => {
  assert.equal(approvalReady(report, 'live'), true)
  assert.equal(approvalReady(report, 'demo'), false)
  assert.equal(approvalReady({ ...report, chain_review: [{}] }, 'live'), false)
  assert.equal(approvalReady({ ...report, balances: { ...report.balances, candidate_zat: 0 } }, 'live'), false)
})
test('only approval and rejection include a verification reference', () => {
  for (const action of ['REQUEST_EVIDENCE', 'CLOSE_UNRESOLVED']) {
    assert.equal(decisionRequest(report, action, 'Reason').verification_id, null)
  }
  assert.equal(decisionRequest(report, 'APPROVE_OUTPUT', 'Reason').verification_id, 'v1')
})
test('latest decision observation replaces initial offline status without mutating history', () => {
  assert.equal(latestObservation(report)?.observation_id, 'refresh')
  assert.equal(latestObservation({ ...report, decision_observations: [] })?.state, 'UNAVAILABLE')
  assert.equal(report.chain_observations[0].state, 'UNAVAILABLE')
})
test('partial demo allocation leaves the case open', () => {
  assert.equal(approvalState(100000, 200000), 'UNDER_REVIEW')
  assert.equal(approvalState(200000, 200000), 'RESOLVED')
})
