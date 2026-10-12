export type paths = Record<string, never>;
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccessContextV1 */
        accessContext: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Role
             * @enum {string}
             */
            role: "merchant" | "customer" | "reviewer";
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Credential Id
             * @default null
             */
            credential_id: string | null;
            /**
             * Grant Id
             * @default null
             */
            grant_id: string | null;
            /**
             * Session Id
             * @default null
             */
            session_id: string | null;
            /**
             * Case Id
             * @default null
             */
            case_id: string | null;
            /** Permissions */
            permissions: ("case:summary" | "case:manage" | "claim:submit" | "evidence:submit" | "report:read" | "evidence:read" | "case:export" | "case:verify" | "case:resolve")[];
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** CaseCreateRequest */
        caseCreateRequest: {
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
        };
        /** CaseOpeningEventV1 */
        caseDetail_CaseOpeningEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Sequence
             * @default 1
             * @constant
             */
            sequence: 1;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default CASE_OPENED
             * @constant
             */
            action: "CASE_OPENED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: string;
            };
            /** Payload Hash */
            payload_hash: string;
            /**
             * Previous Hash
             * @default null
             */
            previous_hash: null;
            /** Event Hash */
            event_hash: string;
        };
        /**
         * CaseState
         * @enum {string}
         */
        caseDetail_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseDetailV1 */
        caseDetail: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            state: components["schemas"]["caseDetail_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            opening_event: components["schemas"]["caseDetail_CaseOpeningEventV1"];
        };
        /**
         * CaseState
         * @enum {string}
         */
        caseListQuery_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseListQuery */
        caseListQuery: {
            /**
             * Limit
             * @default 50
             */
            limit: number;
            /** @default null */
            state: components["schemas"]["caseListQuery_CaseState"] | null;
            /**
             * Cursor
             * @default null
             */
            cursor: string | null;
        };
        /**
         * CaseState
         * @enum {string}
         */
        caseList_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseSummaryV1 */
        caseList_CaseSummaryV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            state: components["schemas"]["caseList_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** CaseListV1 */
        caseList: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Items */
            items: components["schemas"]["caseList_CaseSummaryV1"][];
            /**
             * Next Cursor
             * @default null
             */
            next_cursor: string | null;
        };
        /** CaseOpeningEventV1 */
        caseOpened_CaseOpeningEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Sequence
             * @default 1
             * @constant
             */
            sequence: 1;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default CASE_OPENED
             * @constant
             */
            action: "CASE_OPENED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: string;
            };
            /** Payload Hash */
            payload_hash: string;
            /**
             * Previous Hash
             * @default null
             */
            previous_hash: null;
            /** Event Hash */
            event_hash: string;
        };
        /** CaseOpenedV1 */
        caseOpened: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * State
             * @default OPEN
             * @constant
             */
            state: "OPEN";
            /**
             * Version
             * @default 1
             * @constant
             */
            version: 1;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            opening_event: components["schemas"]["caseOpened_CaseOpeningEventV1"];
        };
        /** CaseOpeningEventV1 */
        casePacket_CaseOpeningEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Sequence
             * @default 1
             * @constant
             */
            sequence: 1;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default CASE_OPENED
             * @constant
             */
            action: "CASE_OPENED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: string;
            };
            /** Payload Hash */
            payload_hash: string;
            /**
             * Previous Hash
             * @default null
             */
            previous_hash: null;
            /** Event Hash */
            event_hash: string;
        };
        /**
         * CaseState
         * @enum {string}
         */
        casePacket_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseSummaryV1 */
        casePacket_CaseSummaryV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            state: components["schemas"]["casePacket_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ChainReviewV1 */
        casePacket_ChainReviewV1: {
            /**
             * Code
             * @default APPROVED_OUTPUT_CHAIN_REVIEW
             * @constant
             */
            code: "APPROVED_OUTPUT_CHAIN_REVIEW";
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
        };
        /**
         * ChainState
         * @enum {string}
         */
        casePacket_ChainState: "CONFIRMED" | "UNCONFIRMED" | "UNAVAILABLE";
        /** ClaimViewV1 */
        casePacket_ClaimViewV1: {
            /**
             * Claim Id
             * Format: uuid
             */
            claim_id: string;
            /** Claimant Role */
            claimant_role: string;
            /** Reported Txid */
            reported_txid: string | null;
            /** Note */
            note: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** DecisionEvaluationV1 */
        casePacket_DecisionEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /** Eligible For Credit */
            eligible_for_credit: boolean;
        };
        /** DecisionObservationV1 */
        casePacket_DecisionObservationV1: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["casePacket_ChainState"];
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "OFFLINE" | "RPC" | "SIMULATED";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
        };
        /** DecisionObservationV2 */
        casePacket_DecisionObservationV2: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v2";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["casePacket_ChainState"];
            /**
             * Source Kind
             * @default RPC
             * @constant
             */
            source_kind: "RPC";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /** Rpc */
            rpc: {
                [key: string]: unknown;
            };
        };
        /** DecisionSnapshotV1 */
        casePacket_DecisionSnapshotV1: {
            /**
             * Schema Version
             * @default decision-evaluation-v1
             * @constant
             */
            schema_version: "decision-evaluation-v1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            invoice: components["schemas"]["casePacket_InvoiceSnapshotV1"];
            /** Verification Id */
            verification_id: string | null;
            verification: components["schemas"]["casePacket_VerificationReport"] | null;
            /** Observation */
            observation: (components["schemas"]["casePacket_DecisionObservationV1"] | components["schemas"]["casePacket_DecisionObservationV2"]) | null;
            /** Source Authorized */
            source_authorized: boolean;
            /** Approved Allocations */
            approved_allocations: components["schemas"]["casePacket_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            result: components["schemas"]["casePacket_DecisionEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** EvaluationInputsV1 */
        casePacket_EvaluationInputsV1: {
            invoice: components["schemas"]["casePacket_InvoiceSnapshotV1"];
            verification: components["schemas"]["casePacket_VerificationReport"];
            /** Approved Allocations */
            approved_allocations: components["schemas"]["casePacket_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
        };
        /** EvaluationSnapshotV1 */
        casePacket_EvaluationSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            inputs: components["schemas"]["casePacket_EvaluationInputsV1"];
            result: components["schemas"]["casePacket_OfflineEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** EvidenceStoredV1 */
        casePacket_EvidenceStoredV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Submitted By
             * Format: uuid
             */
            submitted_by: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @constant
             */
            share_with_reviewers: false;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["casePacket_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** EvidenceStoredV2 */
        casePacket_EvidenceStoredV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /** Submitted By */
            submitted_by: string | null;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission" | "customer_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v2";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /** Share With Reviewers */
            share_with_reviewers: boolean;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["casePacket_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Actor Grant Id */
            actor_grant_id: string | null;
            /**
             * Consent Id
             * Format: uuid
             */
            consent_id: string;
            /** Claim Id */
            claim_id: string | null;
        };
        /** EvidenceSubmittedEventV1 */
        casePacket_EvidenceSubmittedEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default EVIDENCE_SUBMITTED
             * @constant
             */
            action: "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** InvoicePolicyV1 */
        casePacket_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceSnapshotV1 */
        casePacket_InvoiceSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["casePacket_InvoiceTermsV1"];
            policy: components["schemas"]["casePacket_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoiceTermsV1 */
        casePacket_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** MerchantCaseReportV1 */
        casePacket_MerchantCaseReportV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Report Scope
             * @default INITIAL_OFFLINE
             * @enum {string}
             */
            report_scope: "INITIAL_OFFLINE" | "MERCHANT_DECISIONS" | "SIMULATED_DECISIONS";
            /**
             * Disclosure Scope
             * @default MERCHANT
             * @constant
             */
            disclosure_scope: "MERCHANT";
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            case: components["schemas"]["casePacket_CaseSummaryV1"];
            invoice: components["schemas"]["casePacket_InvoiceSnapshotV1"];
            policy: components["schemas"]["casePacket_InvoicePolicyV1"];
            /** Claims */
            claims: components["schemas"]["casePacket_ClaimViewV1"][];
            /** Evidence */
            evidence: (components["schemas"]["casePacket_EvidenceStoredV1"] | components["schemas"]["casePacket_EvidenceStoredV2"])[];
            /** Verifications */
            verifications: components["schemas"]["casePacket_VerificationAttemptV1"][];
            /** Chain Observations */
            chain_observations: components["schemas"]["casePacket_OfflineObservationV1"][];
            /** Evaluations */
            evaluations: components["schemas"]["casePacket_EvaluationSnapshotV1"][];
            /** Selected Verification Id */
            selected_verification_id: string | null;
            balances: components["schemas"]["casePacket_OfflineEvaluationV1"];
            /** Resolutions */
            resolutions: components["schemas"]["casePacket_ResolutionViewV1"][];
            /** Events */
            events: (components["schemas"]["casePacket_CaseOpeningEventV1"] | components["schemas"]["casePacket_EvidenceSubmittedEventV1"] | components["schemas"]["casePacket_VerificationEventV1"] | components["schemas"]["casePacket_ResolutionEventV1"] | components["schemas"]["casePacket_SubmissionEventV2"])[];
            /** Chain Review */
            chain_review?: components["schemas"]["casePacket_ChainReviewV1"][];
            /** Decision Observations */
            decision_observations?: (components["schemas"]["casePacket_DecisionObservationV1"] | components["schemas"]["casePacket_DecisionObservationV2"])[];
            /** Decision Evaluations */
            decision_evaluations?: components["schemas"]["casePacket_DecisionSnapshotV1"][];
            /** Decisions */
            decisions?: components["schemas"]["casePacket_ResolutionOutcomeV1"][];
        };
        /** OfflineEvaluationV1 */
        casePacket_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /** OfflineObservationV1 */
        casePacket_OfflineObservationV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * State
             * @default UNAVAILABLE
             * @constant
             */
            state: "UNAVAILABLE";
            /**
             * Source
             * @default offline
             * @constant
             */
            source: "offline";
            /**
             * Reason Code
             * @default NO_CHAIN_OBSERVER
             * @constant
             */
            reason_code: "NO_CHAIN_OBSERVER";
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: null;
            /**
             * Block Height
             * @default null
             */
            block_height: null;
        };
        /** OwnedAllocationV1 */
        casePacket_OwnedAllocationV1: {
            /** Output Id */
            output_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /** Amount Zat */
            amount_zat: number;
        };
        /** PacketBalanceContextV1 */
        casePacket_PacketBalanceContextV1: {
            /** Selected Verification Id */
            selected_verification_id: string | null;
            /** Approved Allocations */
            approved_allocations: components["schemas"]["casePacket_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            /**
             * Foreign Conflict Basis
             * @default opaque-external-assertion
             * @constant
             */
            foreign_conflict_basis: "opaque-external-assertion";
        };
        /** PacketComponentV1 */
        casePacket_PacketComponentV1: {
            /**
             * Availability
             * @enum {string}
             */
            availability: "PRESENT" | "NOT_SUBMITTED" | "OMITTED";
            /**
             * Encoding
             * @default base64-utf8
             * @constant
             */
            encoding: "base64-utf8";
            /** Data */
            data: string | null;
            /** Sha256 */
            sha256: string | null;
            /**
             * Hash Basis
             * @default original-utf8-bytes
             * @constant
             */
            hash_basis: "original-utf8-bytes";
        };
        /** PacketEvidenceV1 */
        casePacket_PacketEvidenceV1: {
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            provenance: components["schemas"]["casePacket_PacketProvenanceV1"];
            receipt: components["schemas"]["casePacket_PacketComponentV1"];
            raw_transaction_hex: components["schemas"]["casePacket_PacketComponentV1"];
            submission_payload: components["schemas"]["casePacket_PacketComponentV1"];
            /** Decoded Transaction Sha256 */
            decoded_transaction_sha256: string | null;
            /**
             * Decoded Transaction Hash Basis
             * @default decoded-transaction-bytes
             * @constant
             */
            decoded_transaction_hash_basis: "decoded-transaction-bytes";
        };
        /** PacketImplementationsV1 */
        casePacket_PacketImplementationsV1: {
            /** Verifiers */
            verifiers: components["schemas"]["casePacket_PacketVerifierV1"][];
            /** Rules */
            rules: string[];
        };
        /** PacketIntegrityV1 */
        casePacket_PacketIntegrityV1: {
            /**
             * Algorithm
             * @default SHA-256
             * @constant
             */
            algorithm: "SHA-256";
            /**
             * Canonicalization
             * @default zecsolve-json-v1
             * @constant
             */
            canonicalization: "zecsolve-json-v1";
            /**
             * Hash Basis
             * @default canonical-json-payload-excluding-integrity
             * @constant
             */
            hash_basis: "canonical-json-payload-excluding-integrity";
            /** Payload Sha256 */
            payload_sha256: string;
        };
        /** PacketPayloadV1 */
        casePacket_PacketPayloadV1: {
            /**
             * Disclosure Scope
             * @enum {string}
             */
            disclosure_scope: "MERCHANT" | "REVIEWER_SCOPED";
            /**
             * Replay Scope
             * @enum {string}
             */
            replay_scope: "FULL_HISTORY" | "LIMITED";
            /** Omissions */
            omissions: string[];
            /** Assertions */
            assertions: ("INVOICE_AND_CLAIMS_ARE_BUSINESS_ASSERTIONS" | "OBSERVATIONS_ARE_HISTORICAL_EXTERNAL_ASSERTIONS" | "ALLOCATION_AND_SOURCE_AUTHORITY_ARE_EXTERNAL_ASSERTIONS" | "HASHES_DO_NOT_AUTHENTICATE_AUTHOR")[];
            /** Report */
            report: components["schemas"]["casePacket_MerchantCaseReportV1"] | components["schemas"]["casePacket_ReviewerReportV1"];
            /** Evidence */
            evidence: components["schemas"]["casePacket_PacketEvidenceV1"][];
            balance_context: components["schemas"]["casePacket_PacketBalanceContextV1"] | null;
            implementations: components["schemas"]["casePacket_PacketImplementationsV1"];
        };
        /** PacketProvenanceV1 */
        casePacket_PacketProvenanceV1: {
            /** Source */
            source: string;
            /** Source Kind */
            source_kind: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /**
             * Assertion
             * @default true
             * @constant
             */
            assertion: true;
        };
        /** PacketVerifierV1 */
        casePacket_PacketVerifierV1: {
            /** Name */
            name: string;
            /** Version */
            version: string | null;
            /** Result Schema Version */
            result_schema_version: string | null;
            /** Glasspane Revision */
            glasspane_revision: string | null;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        casePacket_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        casePacket_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** ResolutionEventV1 */
        casePacket_ResolutionEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default RESOLUTION_RECORDED
             * @constant
             */
            action: "RESOLUTION_RECORDED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** ResolutionOutcomeV1 */
        casePacket_ResolutionOutcomeV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "APPROVE_OUTPUT" | "REQUEST_EVIDENCE" | "REJECT_EVIDENCE" | "CLOSE_UNRESOLVED";
            /** Reason */
            reason: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
            /** Verification Id */
            verification_id: string | null;
            /** Output Id */
            output_id: string | null;
            /** Allocated Zat */
            allocated_zat: number;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["casePacket_CaseState"];
            evaluation: components["schemas"]["casePacket_DecisionSnapshotV1"];
            balances: components["schemas"]["casePacket_OfflineEvaluationV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** ResolutionViewV1 */
        casePacket_ResolutionViewV1: {
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /** Outcome */
            outcome: string;
            /** Reason */
            reason: string;
            /** Approved By */
            approved_by: string;
            /**
             * Approved At
             * Format: date-time
             */
            approved_at: string;
        };
        /** ReviewerCaseV1 */
        casePacket_ReviewerCaseV1: {
            state: components["schemas"]["casePacket_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ReviewerClaimV1 */
        casePacket_ReviewerClaimV1: {
            /**
             * Claim Id
             * Format: uuid
             */
            claim_id: string;
            /** Reported Txid */
            reported_txid: string | null;
            /** Note */
            note: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Assertion
             * @default true
             * @constant
             */
            assertion: true;
        };
        /** ReviewerDecisionV1 */
        casePacket_ReviewerDecisionV1: {
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /** Verification Id */
            verification_id: string | null;
            /** Action */
            action: string;
            /** Reason */
            reason: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
            /** Allocated Zat */
            allocated_zat: number;
            /** Source Kind */
            source_kind: ("OFFLINE" | "SIMULATED" | "RPC") | null;
        };
        /** ReviewerEvaluationV1 */
        casePacket_ReviewerEvaluationV1: {
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            result: components["schemas"]["casePacket_OfflineEvaluationV1"];
            /**
             * Historical
             * @default true
             * @constant
             */
            historical: true;
        };
        /** ReviewerEventV1 */
        casePacket_ReviewerEventV1: {
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Action */
            action: string;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Projection
             * @default true
             * @constant
             */
            projection: true;
        };
        /** ReviewerEvidenceV1 */
        casePacket_ReviewerEvidenceV1: {
            /**
             * Schema Version
             * @default reviewer-evidence-v1
             * @constant
             */
            schema_version: "reviewer-evidence-v1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /** Source Kind */
            source_kind: string;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /**
             * Disclosure
             * @default SELECTED_CONSENTED_EVIDENCE
             * @constant
             */
            disclosure: "SELECTED_CONSENTED_EVIDENCE";
        };
        /** ReviewerInvoiceV1 */
        casePacket_ReviewerInvoiceV1: {
            terms: components["schemas"]["casePacket_InvoiceTermsV1"];
            policy: components["schemas"]["casePacket_InvoicePolicyV1"];
        };
        /** ReviewerObservationV1 */
        casePacket_ReviewerObservationV1: {
            /**
             * Schema Version
             * @default reviewer-observation-v1
             * @constant
             */
            schema_version: "reviewer-observation-v1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["casePacket_ChainState"];
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "OFFLINE" | "RPC" | "SIMULATED";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /**
             * Projection
             * @default true
             * @constant
             */
            projection: true;
        };
        /** ReviewerReportV1 */
        casePacket_ReviewerReportV1: {
            /**
             * Schema Version
             * @default reviewer-report-v1
             * @constant
             */
            schema_version: "reviewer-report-v1";
            /**
             * Disclosure Scope
             * @default REVIEWER_SCOPED
             * @constant
             */
            disclosure_scope: "REVIEWER_SCOPED";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Sections */
            sections: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Limitations */
            limitations?: string[];
            /** @default null */
            case: components["schemas"]["casePacket_ReviewerCaseV1"] | null;
            /** @default null */
            invoice: components["schemas"]["casePacket_ReviewerInvoiceV1"] | null;
            /**
             * Claims
             * @default null
             */
            claims: components["schemas"]["casePacket_ReviewerClaimV1"][] | null;
            /**
             * Evidence
             * @default null
             */
            evidence: components["schemas"]["casePacket_ReviewerEvidenceV1"][] | null;
            /**
             * Verifications
             * @default null
             */
            verifications: components["schemas"]["casePacket_ReviewerVerificationV1"][] | null;
            /**
             * Observations
             * @default null
             */
            observations: components["schemas"]["casePacket_ReviewerObservationV1"][] | null;
            /**
             * Evaluations
             * @default null
             */
            evaluations: components["schemas"]["casePacket_ReviewerEvaluationV1"][] | null;
            /** @default null */
            balances: components["schemas"]["casePacket_OfflineEvaluationV1"] | null;
            /**
             * Decisions
             * @default null
             */
            decisions: components["schemas"]["casePacket_ReviewerDecisionV1"][] | null;
            /**
             * Events
             * @default null
             */
            events: components["schemas"]["casePacket_ReviewerEventV1"][] | null;
        };
        /** ReviewerVerificationV1 */
        casePacket_ReviewerVerificationV1: {
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            result: components["schemas"]["casePacket_VerificationReport"];
        };
        /** SubmissionEventV2 */
        casePacket_SubmissionEventV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @enum {string}
             */
            action: "CLAIM_SUBMITTED" | "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationAttemptV1 */
        casePacket_VerificationAttemptV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["casePacket_CaseState"];
            result: components["schemas"]["casePacket_VerificationReport"];
            observation: components["schemas"]["casePacket_OfflineObservationV1"];
            evaluation: components["schemas"]["casePacket_EvaluationSnapshotV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** VerificationEventV1 */
        casePacket_VerificationEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default VERIFICATION_RECORDED
             * @constant
             */
            action: "VERIFICATION_RECORDED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationReport */
        casePacket_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["casePacket_VerifierIdentity"];
            receipt_state: components["schemas"]["casePacket_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["casePacket_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        casePacket_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** CasePacketV1 */
        casePacket: {
            /**
             * Schema Version
             * @default case-packet-v1
             * @constant
             */
            schema_version: "case-packet-v1";
            payload: components["schemas"]["casePacket_PacketPayloadV1"];
            integrity: components["schemas"]["casePacket_PacketIntegrityV1"];
        };
        /** ReplayCheckV1 */
        caseReplay_ReplayCheckV1: {
            /**
             * Category
             * @enum {string}
             */
            category: "integrity" | "cryptographic_recovery" | "rules" | "context";
            /** Reference */
            reference: string;
            /**
             * Status
             * @enum {string}
             */
            status: "PASS" | "FAIL" | "MISSING" | "UNSUPPORTED" | "EXTERNAL";
            /** Code */
            code: string;
        };
        /** ReplayResultV1 */
        caseReplay: {
            /**
             * Schema Version
             * @default case-replay-v1
             * @constant
             */
            schema_version: "case-replay-v1";
            /**
             * Status
             * @enum {string}
             */
            status: "REPRODUCED" | "LIMITED" | "UNSUPPORTED" | "FAILED";
            /** Full Replay */
            full_replay: boolean;
            /** Packet File Sha256 */
            packet_file_sha256: string;
            /** Checks */
            checks: components["schemas"]["caseReplay_ReplayCheckV1"][];
            /** External Assertions */
            external_assertions: string[];
        };
        /** CaseOpeningEventV1 */
        caseReport_CaseOpeningEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Sequence
             * @default 1
             * @constant
             */
            sequence: 1;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default CASE_OPENED
             * @constant
             */
            action: "CASE_OPENED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: string;
            };
            /** Payload Hash */
            payload_hash: string;
            /**
             * Previous Hash
             * @default null
             */
            previous_hash: null;
            /** Event Hash */
            event_hash: string;
        };
        /**
         * CaseState
         * @enum {string}
         */
        caseReport_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseSummaryV1 */
        caseReport_CaseSummaryV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            state: components["schemas"]["caseReport_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ClaimViewV1 */
        caseReport_ClaimViewV1: {
            /**
             * Claim Id
             * Format: uuid
             */
            claim_id: string;
            /** Claimant Role */
            claimant_role: string;
            /** Reported Txid */
            reported_txid: string | null;
            /** Note */
            note: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** EvaluationInputsV1 */
        caseReport_EvaluationInputsV1: {
            invoice: components["schemas"]["caseReport_InvoiceSnapshotV1"];
            verification: components["schemas"]["caseReport_VerificationReport"];
            /** Approved Allocations */
            approved_allocations: components["schemas"]["caseReport_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
        };
        /** EvaluationSnapshotV1 */
        caseReport_EvaluationSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            inputs: components["schemas"]["caseReport_EvaluationInputsV1"];
            result: components["schemas"]["caseReport_OfflineEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** EvidenceStoredV1 */
        caseReport_EvidenceStoredV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Submitted By
             * Format: uuid
             */
            submitted_by: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @constant
             */
            share_with_reviewers: false;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["caseReport_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** EvidenceStoredV2 */
        caseReport_EvidenceStoredV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /** Submitted By */
            submitted_by: string | null;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission" | "customer_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v2";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /** Share With Reviewers */
            share_with_reviewers: boolean;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["caseReport_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Actor Grant Id */
            actor_grant_id: string | null;
            /**
             * Consent Id
             * Format: uuid
             */
            consent_id: string;
            /** Claim Id */
            claim_id: string | null;
        };
        /** EvidenceSubmittedEventV1 */
        caseReport_EvidenceSubmittedEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default EVIDENCE_SUBMITTED
             * @constant
             */
            action: "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** InvoicePolicyV1 */
        caseReport_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceSnapshotV1 */
        caseReport_InvoiceSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["caseReport_InvoiceTermsV1"];
            policy: components["schemas"]["caseReport_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoiceTermsV1 */
        caseReport_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** OfflineEvaluationV1 */
        caseReport_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /** OfflineObservationV1 */
        caseReport_OfflineObservationV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * State
             * @default UNAVAILABLE
             * @constant
             */
            state: "UNAVAILABLE";
            /**
             * Source
             * @default offline
             * @constant
             */
            source: "offline";
            /**
             * Reason Code
             * @default NO_CHAIN_OBSERVER
             * @constant
             */
            reason_code: "NO_CHAIN_OBSERVER";
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: null;
            /**
             * Block Height
             * @default null
             */
            block_height: null;
        };
        /** OwnedAllocationV1 */
        caseReport_OwnedAllocationV1: {
            /** Output Id */
            output_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /** Amount Zat */
            amount_zat: number;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        caseReport_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        caseReport_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** ResolutionViewV1 */
        caseReport_ResolutionViewV1: {
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /** Outcome */
            outcome: string;
            /** Reason */
            reason: string;
            /** Approved By */
            approved_by: string;
            /**
             * Approved At
             * Format: date-time
             */
            approved_at: string;
        };
        /** SubmissionEventV2 */
        caseReport_SubmissionEventV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @enum {string}
             */
            action: "CLAIM_SUBMITTED" | "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationAttemptV1 */
        caseReport_VerificationAttemptV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["caseReport_CaseState"];
            result: components["schemas"]["caseReport_VerificationReport"];
            observation: components["schemas"]["caseReport_OfflineObservationV1"];
            evaluation: components["schemas"]["caseReport_EvaluationSnapshotV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** VerificationEventV1 */
        caseReport_VerificationEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default VERIFICATION_RECORDED
             * @constant
             */
            action: "VERIFICATION_RECORDED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationReport */
        caseReport_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["caseReport_VerifierIdentity"];
            receipt_state: components["schemas"]["caseReport_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["caseReport_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        caseReport_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** CaseReportV1 */
        caseReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Report Scope
             * @default INITIAL_OFFLINE
             * @constant
             */
            report_scope: "INITIAL_OFFLINE";
            /**
             * Disclosure Scope
             * @default MERCHANT
             * @constant
             */
            disclosure_scope: "MERCHANT";
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            case: components["schemas"]["caseReport_CaseSummaryV1"];
            invoice: components["schemas"]["caseReport_InvoiceSnapshotV1"];
            policy: components["schemas"]["caseReport_InvoicePolicyV1"];
            /** Claims */
            claims: components["schemas"]["caseReport_ClaimViewV1"][];
            /** Evidence */
            evidence: (components["schemas"]["caseReport_EvidenceStoredV1"] | components["schemas"]["caseReport_EvidenceStoredV2"])[];
            /** Verifications */
            verifications: components["schemas"]["caseReport_VerificationAttemptV1"][];
            /** Chain Observations */
            chain_observations: components["schemas"]["caseReport_OfflineObservationV1"][];
            /** Evaluations */
            evaluations: components["schemas"]["caseReport_EvaluationSnapshotV1"][];
            /** Selected Verification Id */
            selected_verification_id: string | null;
            balances: components["schemas"]["caseReport_OfflineEvaluationV1"];
            /** Resolutions */
            resolutions: components["schemas"]["caseReport_ResolutionViewV1"][];
            /** Events */
            events: (components["schemas"]["caseReport_CaseOpeningEventV1"] | components["schemas"]["caseReport_EvidenceSubmittedEventV1"] | components["schemas"]["caseReport_VerificationEventV1"] | components["schemas"]["caseReport_SubmissionEventV2"])[];
        };
        /** ResolveRequest */
        caseResolveRequest: {
            /**
             * Action
             * @enum {string}
             */
            action: "APPROVE_OUTPUT" | "REQUEST_EVIDENCE" | "REJECT_EVIDENCE" | "CLOSE_UNRESOLVED";
            /**
             * Verification Id
             * @default null
             */
            verification_id: string | null;
            /** Expected Case Version */
            expected_case_version: number;
            /** Reason */
            reason: string;
        };
        /** CaseVerifyRequest */
        caseVerifyRequest: {
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
        };
        /** RefreshChainRequest */
        chainRefreshRequest: {
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
        };
        /** ClaimSubmitRequest */
        claimSubmitRequest: {
            /**
             * Reported Txid
             * @default null
             */
            reported_txid: string | null;
            /**
             * Note
             * @default null
             */
            note: string | null;
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "claim-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @default false
             */
            share_with_reviewers: boolean;
        };
        /** EvidenceContentV1 */
        evidenceContent: {
            /**
             * Schema Version
             * @default evidence-content-v1
             * @constant
             */
            schema_version: "evidence-content-v1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /** Receipt Json */
            receipt_json: string | null;
            /** Raw Tx Hex */
            raw_tx_hex: string | null;
        };
        /**
         * CaseState
         * @enum {string}
         */
        evidenceStoredV2_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** EvidenceStoredV2 */
        evidenceStoredV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /** Submitted By */
            submitted_by: string | null;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission" | "customer_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v2";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /** Share With Reviewers */
            share_with_reviewers: boolean;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["evidenceStoredV2_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Actor Grant Id */
            actor_grant_id: string | null;
            /**
             * Consent Id
             * Format: uuid
             */
            consent_id: string;
            /** Claim Id */
            claim_id: string | null;
        };
        /**
         * CaseState
         * @enum {string}
         */
        evidenceStored_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** EvidenceStoredV1 */
        evidenceStored: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Submitted By
             * Format: uuid
             */
            submitted_by: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @constant
             */
            share_with_reviewers: false;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["evidenceStored_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /**
         * EvidenceSubmitRequestV2
         * @description Explicit disclosure opt-in; old merchant requests keep their exact v1 representation.
         */
        evidenceSubmitRequestV2: {
            /**
             * Receipt Json
             * @default null
             */
            receipt_json: string | null;
            /**
             * Raw Tx Hex
             * @default null
             */
            raw_tx_hex: string | null;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @default customer_submission
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission" | "customer_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v2";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @default false
             */
            share_with_reviewers: boolean;
            /**
             * Claim Id
             * @default null
             */
            claim_id: string | null;
        };
        /** EvidenceSubmitRequest */
        evidenceSubmitRequest: {
            /**
             * Receipt Json
             * @default null
             */
            receipt_json: string | null;
            /**
             * Raw Tx Hex
             * @default null
             */
            raw_tx_hex: string | null;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @default merchant_submission
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission";
            /**
             * Disclosure Version
             * @default evidence-disclosure-v1
             * @constant
             */
            disclosure_version: "evidence-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @default false
             * @constant
             */
            share_with_reviewers: false;
        };
        /** EvidenceSubmittedEventV1 */
        evidenceSubmittedEvent: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default EVIDENCE_SUBMITTED
             * @constant
             */
            action: "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** GrantScopeV1 */
        grantCreateRequest_GrantScopeV1: {
            /**
             * Role
             * @enum {string}
             */
            role: "customer" | "reviewer";
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** GrantCreateRequest */
        grantCreateRequest: {
            scope: components["schemas"]["grantCreateRequest_GrantScopeV1"];
            /**
             * Ttl Hours
             * @default 24
             */
            ttl_hours: number;
        };
        /** GrantMetadataV1 */
        grantCreated_GrantMetadataV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Grant Id
             * Format: uuid
             */
            grant_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Issued By
             * Format: uuid
             */
            issued_by: string;
            scope: components["schemas"]["grantCreated_GrantScopeV1"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Revoked At */
            revoked_at: string | null;
        };
        /** GrantScopeV1 */
        grantCreated_GrantScopeV1: {
            /**
             * Role
             * @enum {string}
             */
            role: "customer" | "reviewer";
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** GrantCreatedV1 */
        grantCreated: {
            grant: components["schemas"]["grantCreated_GrantMetadataV1"];
            /**
             * Access Code
             * @default null
             */
            access_code: string | null;
        };
        /** GrantMetadataV1 */
        grantList_GrantMetadataV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Grant Id
             * Format: uuid
             */
            grant_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Issued By
             * Format: uuid
             */
            issued_by: string;
            scope: components["schemas"]["grantList_GrantScopeV1"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Revoked At */
            revoked_at: string | null;
        };
        /** GrantScopeV1 */
        grantList_GrantScopeV1: {
            /**
             * Role
             * @enum {string}
             */
            role: "customer" | "reviewer";
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** GrantListV1 */
        grantList: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Items */
            items: components["schemas"]["grantList_GrantMetadataV1"][];
        };
        /** GrantScopeV1 */
        grantScope: {
            /**
             * Role
             * @enum {string}
             */
            role: "customer" | "reviewer";
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** InvoiceCreateRequest */
        invoiceCreateRequest: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
        };
        /** InvoicePolicyV1 */
        invoiceSnapshot_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceTermsV1 */
        invoiceSnapshot_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** InvoiceSnapshotV1 */
        invoiceSnapshot: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["invoiceSnapshot_InvoiceTermsV1"];
            policy: components["schemas"]["invoiceSnapshot_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** CaseOpeningEventV1 */
        merchantCaseReport_CaseOpeningEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Sequence
             * @default 1
             * @constant
             */
            sequence: 1;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default CASE_OPENED
             * @constant
             */
            action: "CASE_OPENED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: string;
            };
            /** Payload Hash */
            payload_hash: string;
            /**
             * Previous Hash
             * @default null
             */
            previous_hash: null;
            /** Event Hash */
            event_hash: string;
        };
        /**
         * CaseState
         * @enum {string}
         */
        merchantCaseReport_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** CaseSummaryV1 */
        merchantCaseReport_CaseSummaryV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            state: components["schemas"]["merchantCaseReport_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ChainReviewV1 */
        merchantCaseReport_ChainReviewV1: {
            /**
             * Code
             * @default APPROVED_OUTPUT_CHAIN_REVIEW
             * @constant
             */
            code: "APPROVED_OUTPUT_CHAIN_REVIEW";
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
        };
        /**
         * ChainState
         * @enum {string}
         */
        merchantCaseReport_ChainState: "CONFIRMED" | "UNCONFIRMED" | "UNAVAILABLE";
        /** ClaimViewV1 */
        merchantCaseReport_ClaimViewV1: {
            /**
             * Claim Id
             * Format: uuid
             */
            claim_id: string;
            /** Claimant Role */
            claimant_role: string;
            /** Reported Txid */
            reported_txid: string | null;
            /** Note */
            note: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** DecisionEvaluationV1 */
        merchantCaseReport_DecisionEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /** Eligible For Credit */
            eligible_for_credit: boolean;
        };
        /** DecisionObservationV1 */
        merchantCaseReport_DecisionObservationV1: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["merchantCaseReport_ChainState"];
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "OFFLINE" | "RPC" | "SIMULATED";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
        };
        /** DecisionObservationV2 */
        merchantCaseReport_DecisionObservationV2: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v2";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["merchantCaseReport_ChainState"];
            /**
             * Source Kind
             * @default RPC
             * @constant
             */
            source_kind: "RPC";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /** Rpc */
            rpc: {
                [key: string]: unknown;
            };
        };
        /** DecisionSnapshotV1 */
        merchantCaseReport_DecisionSnapshotV1: {
            /**
             * Schema Version
             * @default decision-evaluation-v1
             * @constant
             */
            schema_version: "decision-evaluation-v1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            invoice: components["schemas"]["merchantCaseReport_InvoiceSnapshotV1"];
            /** Verification Id */
            verification_id: string | null;
            verification: components["schemas"]["merchantCaseReport_VerificationReport"] | null;
            /** Observation */
            observation: (components["schemas"]["merchantCaseReport_DecisionObservationV1"] | components["schemas"]["merchantCaseReport_DecisionObservationV2"]) | null;
            /** Source Authorized */
            source_authorized: boolean;
            /** Approved Allocations */
            approved_allocations: components["schemas"]["merchantCaseReport_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            result: components["schemas"]["merchantCaseReport_DecisionEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** EvaluationInputsV1 */
        merchantCaseReport_EvaluationInputsV1: {
            invoice: components["schemas"]["merchantCaseReport_InvoiceSnapshotV1"];
            verification: components["schemas"]["merchantCaseReport_VerificationReport"];
            /** Approved Allocations */
            approved_allocations: components["schemas"]["merchantCaseReport_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
        };
        /** EvaluationSnapshotV1 */
        merchantCaseReport_EvaluationSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            inputs: components["schemas"]["merchantCaseReport_EvaluationInputsV1"];
            result: components["schemas"]["merchantCaseReport_OfflineEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** EvidenceStoredV1 */
        merchantCaseReport_EvidenceStoredV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Submitted By
             * Format: uuid
             */
            submitted_by: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v1";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /**
             * Share With Reviewers
             * @constant
             */
            share_with_reviewers: false;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["merchantCaseReport_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** EvidenceStoredV2 */
        merchantCaseReport_EvidenceStoredV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /** Submitted By */
            submitted_by: string | null;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "public_fixture" | "merchant_submission" | "customer_submission";
            /**
             * Disclosure Version
             * @constant
             */
            disclosure_version: "evidence-disclosure-v2";
            /**
             * Processing Authorized
             * @constant
             */
            processing_authorized: true;
            /** Share With Reviewers */
            share_with_reviewers: boolean;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /** Payload Sha256 */
            payload_sha256: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["merchantCaseReport_CaseState"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Actor Grant Id */
            actor_grant_id: string | null;
            /**
             * Consent Id
             * Format: uuid
             */
            consent_id: string;
            /** Claim Id */
            claim_id: string | null;
        };
        /** EvidenceSubmittedEventV1 */
        merchantCaseReport_EvidenceSubmittedEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default EVIDENCE_SUBMITTED
             * @constant
             */
            action: "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** InvoicePolicyV1 */
        merchantCaseReport_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceSnapshotV1 */
        merchantCaseReport_InvoiceSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["merchantCaseReport_InvoiceTermsV1"];
            policy: components["schemas"]["merchantCaseReport_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoiceTermsV1 */
        merchantCaseReport_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** OfflineEvaluationV1 */
        merchantCaseReport_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /** OfflineObservationV1 */
        merchantCaseReport_OfflineObservationV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * State
             * @default UNAVAILABLE
             * @constant
             */
            state: "UNAVAILABLE";
            /**
             * Source
             * @default offline
             * @constant
             */
            source: "offline";
            /**
             * Reason Code
             * @default NO_CHAIN_OBSERVER
             * @constant
             */
            reason_code: "NO_CHAIN_OBSERVER";
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: null;
            /**
             * Block Height
             * @default null
             */
            block_height: null;
        };
        /** OwnedAllocationV1 */
        merchantCaseReport_OwnedAllocationV1: {
            /** Output Id */
            output_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /** Amount Zat */
            amount_zat: number;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        merchantCaseReport_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        merchantCaseReport_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** ResolutionEventV1 */
        merchantCaseReport_ResolutionEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default RESOLUTION_RECORDED
             * @constant
             */
            action: "RESOLUTION_RECORDED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** ResolutionOutcomeV1 */
        merchantCaseReport_ResolutionOutcomeV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "APPROVE_OUTPUT" | "REQUEST_EVIDENCE" | "REJECT_EVIDENCE" | "CLOSE_UNRESOLVED";
            /** Reason */
            reason: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
            /** Verification Id */
            verification_id: string | null;
            /** Output Id */
            output_id: string | null;
            /** Allocated Zat */
            allocated_zat: number;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["merchantCaseReport_CaseState"];
            evaluation: components["schemas"]["merchantCaseReport_DecisionSnapshotV1"];
            balances: components["schemas"]["merchantCaseReport_OfflineEvaluationV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** ResolutionViewV1 */
        merchantCaseReport_ResolutionViewV1: {
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /** Outcome */
            outcome: string;
            /** Reason */
            reason: string;
            /** Approved By */
            approved_by: string;
            /**
             * Approved At
             * Format: date-time
             */
            approved_at: string;
        };
        /** SubmissionEventV2 */
        merchantCaseReport_SubmissionEventV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @enum {string}
             */
            action: "CLAIM_SUBMITTED" | "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationAttemptV1 */
        merchantCaseReport_VerificationAttemptV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["merchantCaseReport_CaseState"];
            result: components["schemas"]["merchantCaseReport_VerificationReport"];
            observation: components["schemas"]["merchantCaseReport_OfflineObservationV1"];
            evaluation: components["schemas"]["merchantCaseReport_EvaluationSnapshotV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** VerificationEventV1 */
        merchantCaseReport_VerificationEventV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @default VERIFICATION_RECORDED
             * @constant
             */
            action: "VERIFICATION_RECORDED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /** VerificationReport */
        merchantCaseReport_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["merchantCaseReport_VerifierIdentity"];
            receipt_state: components["schemas"]["merchantCaseReport_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["merchantCaseReport_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        merchantCaseReport_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** MerchantCaseReportV1 */
        merchantCaseReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Report Scope
             * @default INITIAL_OFFLINE
             * @enum {string}
             */
            report_scope: "INITIAL_OFFLINE" | "MERCHANT_DECISIONS" | "SIMULATED_DECISIONS";
            /**
             * Disclosure Scope
             * @default MERCHANT
             * @constant
             */
            disclosure_scope: "MERCHANT";
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            case: components["schemas"]["merchantCaseReport_CaseSummaryV1"];
            invoice: components["schemas"]["merchantCaseReport_InvoiceSnapshotV1"];
            policy: components["schemas"]["merchantCaseReport_InvoicePolicyV1"];
            /** Claims */
            claims: components["schemas"]["merchantCaseReport_ClaimViewV1"][];
            /** Evidence */
            evidence: (components["schemas"]["merchantCaseReport_EvidenceStoredV1"] | components["schemas"]["merchantCaseReport_EvidenceStoredV2"])[];
            /** Verifications */
            verifications: components["schemas"]["merchantCaseReport_VerificationAttemptV1"][];
            /** Chain Observations */
            chain_observations: components["schemas"]["merchantCaseReport_OfflineObservationV1"][];
            /** Evaluations */
            evaluations: components["schemas"]["merchantCaseReport_EvaluationSnapshotV1"][];
            /** Selected Verification Id */
            selected_verification_id: string | null;
            balances: components["schemas"]["merchantCaseReport_OfflineEvaluationV1"];
            /** Resolutions */
            resolutions: components["schemas"]["merchantCaseReport_ResolutionViewV1"][];
            /** Events */
            events: (components["schemas"]["merchantCaseReport_CaseOpeningEventV1"] | components["schemas"]["merchantCaseReport_EvidenceSubmittedEventV1"] | components["schemas"]["merchantCaseReport_VerificationEventV1"] | components["schemas"]["merchantCaseReport_ResolutionEventV1"] | components["schemas"]["merchantCaseReport_SubmissionEventV2"])[];
            /** Chain Review */
            chain_review?: components["schemas"]["merchantCaseReport_ChainReviewV1"][];
            /** Decision Observations */
            decision_observations?: (components["schemas"]["merchantCaseReport_DecisionObservationV1"] | components["schemas"]["merchantCaseReport_DecisionObservationV2"])[];
            /** Decision Evaluations */
            decision_evaluations?: components["schemas"]["merchantCaseReport_DecisionSnapshotV1"][];
            /** Decisions */
            decisions?: components["schemas"]["merchantCaseReport_ResolutionOutcomeV1"][];
        };
        /** NormalizeAddressRequest */
        normalizeAddressRequest: {
            /** Address */
            address: string;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
        };
        /** NormalizedReceiver */
        normalizeAddressResult_NormalizedReceiver: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Hex */
            receiver_hex: string;
        };
        /** AddressNormalizationReport */
        normalizeAddressResult: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * State
             * @enum {string}
             */
            state: "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
            /** Reason Code */
            reason_code: string;
            /**
             * Input Sha256
             * @default null
             */
            input_sha256: string | null;
            /** @default null */
            receiver: components["schemas"]["normalizeAddressResult_NormalizedReceiver"] | null;
        };
        /**
         * CaseState
         * @enum {string}
         */
        resolutionOutcome_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /**
         * ChainState
         * @enum {string}
         */
        resolutionOutcome_ChainState: "CONFIRMED" | "UNCONFIRMED" | "UNAVAILABLE";
        /** DecisionEvaluationV1 */
        resolutionOutcome_DecisionEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /** Eligible For Credit */
            eligible_for_credit: boolean;
        };
        /** DecisionObservationV1 */
        resolutionOutcome_DecisionObservationV1: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["resolutionOutcome_ChainState"];
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "OFFLINE" | "RPC" | "SIMULATED";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
        };
        /** DecisionObservationV2 */
        resolutionOutcome_DecisionObservationV2: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            schema_version: "decision-observation-v2";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["resolutionOutcome_ChainState"];
            /**
             * Source Kind
             * @default RPC
             * @constant
             */
            source_kind: "RPC";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /** Rpc */
            rpc: {
                [key: string]: unknown;
            };
        };
        /** DecisionSnapshotV1 */
        resolutionOutcome_DecisionSnapshotV1: {
            /**
             * Schema Version
             * @default decision-evaluation-v1
             * @constant
             */
            schema_version: "decision-evaluation-v1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            invoice: components["schemas"]["resolutionOutcome_InvoiceSnapshotV1"];
            /** Verification Id */
            verification_id: string | null;
            verification: components["schemas"]["resolutionOutcome_VerificationReport"] | null;
            /** Observation */
            observation: (components["schemas"]["resolutionOutcome_DecisionObservationV1"] | components["schemas"]["resolutionOutcome_DecisionObservationV2"]) | null;
            /** Source Authorized */
            source_authorized: boolean;
            /** Approved Allocations */
            approved_allocations: components["schemas"]["resolutionOutcome_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            result: components["schemas"]["resolutionOutcome_DecisionEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoicePolicyV1 */
        resolutionOutcome_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceSnapshotV1 */
        resolutionOutcome_InvoiceSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["resolutionOutcome_InvoiceTermsV1"];
            policy: components["schemas"]["resolutionOutcome_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoiceTermsV1 */
        resolutionOutcome_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** OfflineEvaluationV1 */
        resolutionOutcome_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /** OwnedAllocationV1 */
        resolutionOutcome_OwnedAllocationV1: {
            /** Output Id */
            output_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /** Amount Zat */
            amount_zat: number;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        resolutionOutcome_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        resolutionOutcome_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** VerificationReport */
        resolutionOutcome_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["resolutionOutcome_VerifierIdentity"];
            receipt_state: components["schemas"]["resolutionOutcome_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["resolutionOutcome_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        resolutionOutcome_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** ResolutionOutcomeV1 */
        resolutionOutcome: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "APPROVE_OUTPUT" | "REQUEST_EVIDENCE" | "REJECT_EVIDENCE" | "CLOSE_UNRESOLVED";
            /** Reason */
            reason: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
            /** Verification Id */
            verification_id: string | null;
            /** Output Id */
            output_id: string | null;
            /** Allocated Zat */
            allocated_zat: number;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["resolutionOutcome_CaseState"];
            evaluation: components["schemas"]["resolutionOutcome_DecisionSnapshotV1"];
            balances: components["schemas"]["resolutionOutcome_OfflineEvaluationV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /** ReviewerEvidenceV1 */
        reviewerEvidence: {
            /**
             * Schema Version
             * @default reviewer-evidence-v1
             * @constant
             */
            schema_version: "reviewer-evidence-v1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /** Source Kind */
            source_kind: string;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /**
             * Disclosure
             * @default SELECTED_CONSENTED_EVIDENCE
             * @constant
             */
            disclosure: "SELECTED_CONSENTED_EVIDENCE";
        };
        /**
         * CaseState
         * @enum {string}
         */
        reviewerReport_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /**
         * ChainState
         * @enum {string}
         */
        reviewerReport_ChainState: "CONFIRMED" | "UNCONFIRMED" | "UNAVAILABLE";
        /** InvoicePolicyV1 */
        reviewerReport_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceTermsV1 */
        reviewerReport_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** OfflineEvaluationV1 */
        reviewerReport_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        reviewerReport_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        reviewerReport_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** ReviewerCaseV1 */
        reviewerReport_ReviewerCaseV1: {
            state: components["schemas"]["reviewerReport_CaseState"];
            /** Version */
            version: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ReviewerClaimV1 */
        reviewerReport_ReviewerClaimV1: {
            /**
             * Claim Id
             * Format: uuid
             */
            claim_id: string;
            /** Reported Txid */
            reported_txid: string | null;
            /** Note */
            note: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Assertion
             * @default true
             * @constant
             */
            assertion: true;
        };
        /** ReviewerDecisionV1 */
        reviewerReport_ReviewerDecisionV1: {
            /**
             * Resolution Id
             * Format: uuid
             */
            resolution_id: string;
            /** Verification Id */
            verification_id: string | null;
            /** Action */
            action: string;
            /** Reason */
            reason: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
            /** Allocated Zat */
            allocated_zat: number;
            /** Source Kind */
            source_kind: ("OFFLINE" | "SIMULATED" | "RPC") | null;
        };
        /** ReviewerEvaluationV1 */
        reviewerReport_ReviewerEvaluationV1: {
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            result: components["schemas"]["reviewerReport_OfflineEvaluationV1"];
            /**
             * Historical
             * @default true
             * @constant
             */
            historical: true;
        };
        /** ReviewerEventV1 */
        reviewerReport_ReviewerEventV1: {
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Action */
            action: string;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Projection
             * @default true
             * @constant
             */
            projection: true;
        };
        /** ReviewerEvidenceV1 */
        reviewerReport_ReviewerEvidenceV1: {
            /**
             * Schema Version
             * @default reviewer-evidence-v1
             * @constant
             */
            schema_version: "reviewer-evidence-v1";
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Source */
            source: string;
            /** Source Kind */
            source_kind: string;
            /** Receipt Sha256 */
            receipt_sha256: string | null;
            /** Raw Tx Hex Sha256 */
            raw_tx_hex_sha256: string | null;
            /**
             * Disclosure
             * @default SELECTED_CONSENTED_EVIDENCE
             * @constant
             */
            disclosure: "SELECTED_CONSENTED_EVIDENCE";
        };
        /** ReviewerInvoiceV1 */
        reviewerReport_ReviewerInvoiceV1: {
            terms: components["schemas"]["reviewerReport_InvoiceTermsV1"];
            policy: components["schemas"]["reviewerReport_InvoicePolicyV1"];
        };
        /** ReviewerObservationV1 */
        reviewerReport_ReviewerObservationV1: {
            /**
             * Schema Version
             * @default reviewer-observation-v1
             * @constant
             */
            schema_version: "reviewer-observation-v1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["reviewerReport_ChainState"];
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "OFFLINE" | "RPC" | "SIMULATED";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /**
             * Projection
             * @default true
             * @constant
             */
            projection: true;
        };
        /** ReviewerVerificationV1 */
        reviewerReport_ReviewerVerificationV1: {
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            result: components["schemas"]["reviewerReport_VerificationReport"];
        };
        /** VerificationReport */
        reviewerReport_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["reviewerReport_VerifierIdentity"];
            receipt_state: components["schemas"]["reviewerReport_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["reviewerReport_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        reviewerReport_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** ReviewerReportV1 */
        reviewerReport: {
            /**
             * Schema Version
             * @default reviewer-report-v1
             * @constant
             */
            schema_version: "reviewer-report-v1";
            /**
             * Disclosure Scope
             * @default REVIEWER_SCOPED
             * @constant
             */
            disclosure_scope: "REVIEWER_SCOPED";
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Sections */
            sections: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Limitations */
            limitations?: string[];
            /** @default null */
            case: components["schemas"]["reviewerReport_ReviewerCaseV1"] | null;
            /** @default null */
            invoice: components["schemas"]["reviewerReport_ReviewerInvoiceV1"] | null;
            /**
             * Claims
             * @default null
             */
            claims: components["schemas"]["reviewerReport_ReviewerClaimV1"][] | null;
            /**
             * Evidence
             * @default null
             */
            evidence: components["schemas"]["reviewerReport_ReviewerEvidenceV1"][] | null;
            /**
             * Verifications
             * @default null
             */
            verifications: components["schemas"]["reviewerReport_ReviewerVerificationV1"][] | null;
            /**
             * Observations
             * @default null
             */
            observations: components["schemas"]["reviewerReport_ReviewerObservationV1"][] | null;
            /**
             * Evaluations
             * @default null
             */
            evaluations: components["schemas"]["reviewerReport_ReviewerEvaluationV1"][] | null;
            /** @default null */
            balances: components["schemas"]["reviewerReport_OfflineEvaluationV1"] | null;
            /**
             * Decisions
             * @default null
             */
            decisions: components["schemas"]["reviewerReport_ReviewerDecisionV1"][] | null;
            /**
             * Events
             * @default null
             */
            events: components["schemas"]["reviewerReport_ReviewerEventV1"][] | null;
        };
        /**
         * ChainState
         * @enum {string}
         */
        rpcObservation_ChainState: "CONFIRMED" | "UNCONFIRMED" | "UNAVAILABLE";
        /** DecisionObservationV2 */
        rpcObservation: {
            /**
             * Schema Version
             * @default decision-observation-v2
             * @constant
             */
            schema_version: "decision-observation-v2";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            state: components["schemas"]["rpcObservation_ChainState"];
            /**
             * Source Kind
             * @default RPC
             * @constant
             */
            source_kind: "RPC";
            /** Source */
            source: string;
            /** Reason Code */
            reason_code: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: number | null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: string | null;
            /**
             * Block Height
             * @default null
             */
            block_height: number | null;
            /** Rpc */
            rpc: {
                [key: string]: unknown;
            };
        };
        /** SessionExchangeRequest */
        sessionExchangeRequest: {
            /** Code */
            code: string;
        };
        /** AccessContextV1 */
        sessionInfo_AccessContextV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Role
             * @enum {string}
             */
            role: "merchant" | "customer" | "reviewer";
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Credential Id
             * @default null
             */
            credential_id: string | null;
            /**
             * Grant Id
             * @default null
             */
            grant_id: string | null;
            /**
             * Session Id
             * @default null
             */
            session_id: string | null;
            /**
             * Case Id
             * @default null
             */
            case_id: string | null;
            /** Permissions */
            permissions: ("case:summary" | "case:manage" | "claim:submit" | "evidence:submit" | "report:read" | "evidence:read" | "case:export" | "case:verify" | "case:resolve")[];
            /** Report Sections */
            report_sections?: ("case" | "invoice" | "claims" | "evidence" | "verifications" | "observations" | "evaluations" | "balances" | "decisions" | "events")[];
            /** Evidence Ids */
            evidence_ids?: string[];
            /**
             * Allow Export
             * @default false
             */
            allow_export: boolean;
        };
        /** SessionInfoV1 */
        sessionInfo: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Session Id
             * Format: uuid
             */
            session_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            access: components["schemas"]["sessionInfo_AccessContextV1"];
            /**
             * Csrf Header
             * @default X-CSRF-Token
             * @constant
             */
            csrf_header: "X-CSRF-Token";
            /**
             * Csrf Cookie
             * @default __Host-zecsolve_csrf
             * @constant
             */
            csrf_cookie: "__Host-zecsolve_csrf";
        };
        /** SubmissionAcknowledgementV1 */
        submissionAcknowledgement: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Status
             * @default accepted
             * @constant
             */
            status: "accepted";
            /**
             * Operation
             * @enum {string}
             */
            operation: "claim" | "evidence";
            /**
             * Submission Id
             * Format: uuid
             */
            submission_id: string;
            /**
             * Accepted At
             * Format: date-time
             */
            accepted_at: string;
        };
        /** SubmissionEventV2 */
        submissionEventV2: {
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: "2";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /** Sequence */
            sequence: number;
            /** Actor */
            actor: string;
            /**
             * Action
             * @enum {string}
             */
            action: "CLAIM_SUBMITTED" | "EVIDENCE_SUBMITTED";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Payload Hash */
            payload_hash: string;
            /** Previous Hash */
            previous_hash: string;
            /** Event Hash */
            event_hash: string;
        };
        /**
         * CaseState
         * @enum {string}
         */
        verificationAttempt_CaseState: "OPEN" | "AWAITING_EVIDENCE" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED_UNRESOLVED";
        /** EvaluationInputsV1 */
        verificationAttempt_EvaluationInputsV1: {
            invoice: components["schemas"]["verificationAttempt_InvoiceSnapshotV1"];
            verification: components["schemas"]["verificationAttempt_VerificationReport"];
            /** Approved Allocations */
            approved_allocations: components["schemas"]["verificationAttempt_OwnedAllocationV1"][];
            /** Foreign Conflict */
            foreign_conflict: boolean;
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
        };
        /** EvaluationSnapshotV1 */
        verificationAttempt_EvaluationSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Evaluation Id
             * Format: uuid
             */
            evaluation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            inputs: components["schemas"]["verificationAttempt_EvaluationInputsV1"];
            result: components["schemas"]["verificationAttempt_OfflineEvaluationV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoicePolicyV1 */
        verificationAttempt_InvoicePolicyV1: {
            /**
             * Policy Version
             * @default invoice-policy-v1
             * @constant
             */
            policy_version: "invoice-policy-v1";
            /**
             * Rules Version
             * @default 0.1.0
             */
            rules_version: string;
            /**
             * Minimum Confirmations
             * @default 10
             */
            minimum_confirmations: number;
            /**
             * Max Observation Age Seconds
             * @default 60
             */
            max_observation_age_seconds: number;
            /**
             * Memo Binding
             * @default exact
             * @constant
             */
            memo_binding: "exact";
            /**
             * Allow Overpayment
             * @default false
             * @constant
             */
            allow_overpayment: false;
            /**
             * Unique Receiver Binding
             * @default false
             * @constant
             */
            unique_receiver_binding: false;
        };
        /** InvoiceSnapshotV1 */
        verificationAttempt_InvoiceSnapshotV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            terms: components["schemas"]["verificationAttempt_InvoiceTermsV1"];
            policy: components["schemas"]["verificationAttempt_InvoicePolicyV1"];
            /** Snapshot Hash */
            snapshot_hash: string;
        };
        /** InvoiceTermsV1 */
        verificationAttempt_InvoiceTermsV1: {
            /** Expected Zat */
            expected_zat: number;
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Receiver Address */
            receiver_address: string;
            /**
             * Expected Memo
             * @default null
             */
            expected_memo: string | null;
            /**
             * Expires At
             * @default null
             */
            expires_at: string | null;
            /** Receiver Hex */
            receiver_hex: string;
            /** Memo Hex */
            memo_hex: string | null;
        };
        /** OfflineEvaluationV1 */
        verificationAttempt_OfflineEvaluationV1: {
            /** Rules Version */
            rules_version: string;
            /** Findings */
            findings: string[];
            /** Credited Zat */
            credited_zat: number;
            /** Outstanding Zat */
            outstanding_zat: number;
            /** Excess Zat */
            excess_zat: number;
            /** Candidate Zat */
            candidate_zat: number;
            /** Projected Outstanding Zat */
            projected_outstanding_zat: number;
            /**
             * Eligible For Credit
             * @default false
             * @constant
             */
            eligible_for_credit: false;
        };
        /** OfflineObservationV1 */
        verificationAttempt_OfflineObservationV1: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Observation Id
             * Format: uuid
             */
            observation_id: string;
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * State
             * @default UNAVAILABLE
             * @constant
             */
            state: "UNAVAILABLE";
            /**
             * Source
             * @default offline
             * @constant
             */
            source: "offline";
            /**
             * Reason Code
             * @default NO_CHAIN_OBSERVER
             * @constant
             */
            reason_code: "NO_CHAIN_OBSERVER";
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /**
             * Network
             * @default mainnet
             * @constant
             */
            network: "mainnet";
            /**
             * Txid
             * @default null
             */
            txid: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /**
             * Confirmations
             * @default null
             */
            confirmations: null;
            /**
             * Block Hash
             * @default null
             */
            block_hash: null;
            /**
             * Block Height
             * @default null
             */
            block_height: null;
        };
        /** OwnedAllocationV1 */
        verificationAttempt_OwnedAllocationV1: {
            /** Output Id */
            output_id: string;
            /**
             * Invoice Id
             * Format: uuid
             */
            invoice_id: string;
            /** Amount Zat */
            amount_zat: number;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        verificationAttempt_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        verificationAttempt_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** VerificationReport */
        verificationAttempt_VerificationReport: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["verificationAttempt_VerifierIdentity"];
            receipt_state: components["schemas"]["verificationAttempt_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["verificationAttempt_RecoveredOutput"] | null;
        };
        /** VerifierIdentity */
        verificationAttempt_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** VerificationAttemptV1 */
        verificationAttempt: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Verification Id
             * Format: uuid
             */
            verification_id: string;
            /**
             * Evidence Id
             * Format: uuid
             */
            evidence_id: string;
            /**
             * Case Id
             * Format: uuid
             */
            case_id: string;
            /**
             * Merchant Id
             * Format: uuid
             */
            merchant_id: string;
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Case Version */
            case_version: number;
            case_state: components["schemas"]["verificationAttempt_CaseState"];
            result: components["schemas"]["verificationAttempt_VerificationReport"];
            observation: components["schemas"]["verificationAttempt_OfflineObservationV1"];
            evaluation: components["schemas"]["verificationAttempt_EvaluationSnapshotV1"];
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
        };
        /**
         * ReceiptState
         * @enum {string}
         */
        verifierResult_ReceiptState: "NONE" | "VALID" | "INVALID" | "UNSUPPORTED" | "UNAVAILABLE" | "ERROR";
        /** RecoveredOutput */
        verifierResult_RecoveredOutput: {
            /**
             * Network
             * @constant
             */
            network: "mainnet";
            /**
             * Pool
             * @enum {string}
             */
            pool: "orchard" | "sapling";
            /** Txid */
            txid: string;
            /** Output Index */
            output_index: number;
            /** Amount Zat */
            amount_zat: number;
            /** Receiver Hex */
            receiver_hex: string;
            /** Receiver Address */
            receiver_address: string;
            /** Memo Hex */
            memo_hex: string;
        };
        /** VerifierIdentity */
        verifierResult_VerifierIdentity: {
            /**
             * Name
             * @default zecsolve-verifier
             * @constant
             */
            name: "zecsolve-verifier";
            /**
             * Version
             * @default 0.1.0
             */
            version: string;
            /**
             * Glasspane Revision
             * @default f6468e6d08a7adad53bf2991a311358dc84e869b
             * @constant
             */
            glasspane_revision: "f6468e6d08a7adad53bf2991a311358dc84e869b";
        };
        /** VerificationReport */
        verifierResult: {
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            verifier?: components["schemas"]["verifierResult_VerifierIdentity"];
            receipt_state: components["schemas"]["verifierResult_ReceiptState"];
            /**
             * Chain State
             * @default UNAVAILABLE
             * @constant
             */
            chain_state: "UNAVAILABLE";
            /** Reason Code */
            reason_code: string;
            /**
             * Raw Tx Verified
             * @default false
             */
            raw_tx_verified: boolean;
            /**
             * Signature State
             * @default NONE
             * @enum {string}
             */
            signature_state: "NONE" | "VALID" | "INVALID";
            /**
             * Receipt Sha256
             * @default null
             */
            receipt_sha256: string | null;
            /**
             * Raw Tx Sha256
             * @default null
             */
            raw_tx_sha256: string | null;
            /** @default null */
            output: components["schemas"]["verifierResult_RecoveredOutput"] | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export type operations = Record<string, never>;
