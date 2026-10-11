// Hand-written mirror of the subset of contracts/*.schema.json the UI reads.
// Regenerate the full set with `npm run types:api` once the workflow contract is frozen.

export type ReceiptState = 'NONE' | 'VALID' | 'INVALID' | 'UNSUPPORTED' | 'UNAVAILABLE' | 'ERROR'
export type ChainState = 'CONFIRMED' | 'UNCONFIRMED' | 'UNAVAILABLE'
export type CaseState = 'OPEN' | 'AWAITING_EVIDENCE' | 'UNDER_REVIEW' | 'RESOLVED' | 'CLOSED_UNRESOLVED'
export type ResolveAction = 'APPROVE_OUTPUT' | 'REQUEST_EVIDENCE' | 'REJECT_EVIDENCE' | 'CLOSE_UNRESOLVED'

export type Finding =
  | 'INVALID_EVIDENCE'
  | 'UNSUPPORTED_EVIDENCE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'RECIPIENT_MISMATCH'
  | 'MEMO_MISMATCH'
  | 'NEEDS_REVIEW'
  | 'ALREADY_ALLOCATED'
  | 'DUPLICATE_CLAIM'
  | 'OVERPAYMENT_REVIEW'
  | 'CHAIN_UNVERIFIED'
  | 'UNDERPAID'
  | 'OVERPAID'
  | 'MATCH'
  | 'ELIGIBLE_FOR_CREDIT'

export interface InvoiceTerms {
  expected_zat: number
  network: 'mainnet'
  pool: 'orchard' | 'sapling'
  receiver_address: string
  expected_memo?: string | null
  expires_at?: string | null
  receiver_hex: string
  memo_hex: string | null
}

export interface InvoiceSnapshot {
  invoice_id: string
  merchant_id: string
  policy_id: string
  created_at: string
  terms: InvoiceTerms
  snapshot_hash: string
}

export interface CaseSummary {
  case_id: string
  invoice_id: string
  merchant_id: string
  state: CaseState
  version: number
  created_at: string
}

export interface RecoveredOutput {
  network: string
  pool: string
  txid: string
  output_index: number
  amount_zat: number
  receiver_hex: string
  receiver_address: string
  memo_hex: string
}

export interface VerificationReport {
  receipt_state: ReceiptState
  chain_state?: ChainState
  reason_code: string
  raw_tx_verified?: boolean
  receipt_sha256?: string | null
  raw_tx_sha256?: string | null
  output?: RecoveredOutput | null
  verifier?: { name?: string; version?: string; glasspane_revision?: string }
}

export interface Balances {
  rules_version: string
  findings: Finding[]
  credited_zat: number
  outstanding_zat: number
  excess_zat: number
  candidate_zat: number
  projected_outstanding_zat: number
  eligible_for_credit?: boolean
}

export interface ChainObservation {
  observation_id: string
  verification_id: string
  state: ChainState
  source: string
  source_kind?: 'OFFLINE' | 'RPC' | 'SIMULATED'
  reason_code: string
  observed_at: string
  confirmations?: number | null
  block_height?: number | null
}

export interface EvidenceStored {
  evidence_id: string
  submitted_by: string
  submitted_at: string
  source: string
  source_kind: 'public_fixture' | 'merchant_submission'
  receipt_sha256: string | null
  raw_tx_hex_sha256: string | null
  payload_sha256: string
}

export interface VerificationAttempt {
  verification_id: string
  evidence_id: string
  created_at: string
  result: VerificationReport
}

export interface ClaimView {
  claim_id: string
  claimant_role: string
  reported_txid: string | null
  note: string | null
  created_at: string
}

export interface ResolutionOutcome {
  resolution_id: string
  action: ResolveAction
  reason: string
  decided_at: string
  actor_id: string
  verification_id: string | null
  output_id: string | null
  allocated_zat: number
  case_version: number
  case_state: CaseState
}

export interface CaseEvent {
  event_id: string
  sequence: number
  actor: string
  action: string
  at: string
  event_hash: string
}

/** GET /api/cases/{id}/report — merchant-case-report.schema.json (fields the UI reads). */
export interface CaseReport {
  generated_at: string
  case: CaseSummary
  invoice: InvoiceSnapshot
  claims: ClaimView[]
  evidence: EvidenceStored[]
  verifications: VerificationAttempt[]
  chain_observations: ChainObservation[]
  decision_observations?: ChainObservation[]
  chain_review?: { code: string; resolution_id: string; observation_id: string }[]
  selected_verification_id: string | null
  balances: Balances
  decisions?: ResolutionOutcome[]
  events: CaseEvent[]
}

export interface ResolveRequest {
  action: ResolveAction
  verification_id: string | null
  expected_case_version: number
  reason: string
}

export interface EvidenceSubmitRequest {
  receipt_json: string | null
  raw_tx_hex: string | null
  source: string
  source_kind: 'merchant_submission'
  disclosure_version: 'evidence-disclosure-v1'
  processing_authorized: true
  share_with_reviewers: false
}
