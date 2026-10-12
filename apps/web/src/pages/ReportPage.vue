<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ExportButton from '@/components/ExportButton.vue'
import { cases, session } from '@/api/store'
import { latestObservation } from '@/api/workflow'
import type { CaseReport } from '@/api/types'
import { formatZat, formatZec } from '@/lib/money'
import {
  actionView,
  caseStateLabel,
  chainView,
  findingView,
  formatWhen,
  memoPreview,
  receiptView,
} from '@/lib/status'

// Reviewer view: read-only, printable, light paper. Shows provenance and limits, never raw evidence.
const props = defineProps<{ id: string }>()
const report = ref<CaseReport | null>(null)
const error = ref<string | null>(null)

watch(
  () => props.id,
  async (id) => {
    try {
      report.value = await cases.report(id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  },
  { immediate: true },
)

const selected = computed(() =>
  report.value?.verifications.find((v) => v.verification_id === report.value?.selected_verification_id),
)
const observation = computed(() => (report.value ? latestObservation(report.value) : undefined))
const findingLabels = computed(() =>
  report.value?.balances.findings.map((f) => findingView[f]?.label ?? f).join('; '),
)

function printReport() {
  window.print()
}

function download() {
  if (!report.value) return
  const blob = new Blob([JSON.stringify(report.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `zecsolve-case-${report.value.case.case_id}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="paper-wrap">
    <div class="toolbar shell">
      <RouterLink :to="`/cases/${id}`" class="btn btn-quiet">Back to case</RouterLink>
      <div class="row">
        <ExportButton v-if="session.mode === 'live'" :id="id" /><button
          v-else
          type="button"
          class="btn"
          @click="download"
        >
          Download demo report (not a replay packet)
        </button>
        <button type="button" class="btn" @click="printReport">Print</button>
      </div>
    </div>

    <p v-if="error" class="shell error" role="alert">{{ error }}</p>
    <article v-else-if="report" class="paper">
      <header class="top">
        <h1>Case report</h1>
        <p>
          Generated {{ formatWhen(report.generated_at) }}. Scope: merchant report. Receipt bytes and keys are
          not included.
        </p>
      </header>

      <section>
        <h2>Invoice</h2>
        <dl>
          <div>
            <dt>Expected</dt>
            <dd class="mono">
              {{ formatZat(report.invoice.terms.expected_zat) }} zat ({{
                formatZec(report.invoice.terms.expected_zat)
              }}
              ZEC)
            </dd>
          </div>
          <div>
            <dt>Network, pool</dt>
            <dd>{{ report.invoice.terms.network }}, {{ report.invoice.terms.pool }}</dd>
          </div>
          <div>
            <dt>Receiver</dt>
            <dd class="mono wrap">{{ report.invoice.terms.receiver_address }}</dd>
          </div>
          <div>
            <dt>Reference</dt>
            <dd>{{ report.invoice.terms.expected_memo ?? 'None' }}</dd>
          </div>
          <div>
            <dt>Snapshot hash</dt>
            <dd class="mono wrap">{{ report.invoice.snapshot_hash }}</dd>
          </div>
        </dl>
      </section>

      <section>
        <h2>Case</h2>
        <dl>
          <div>
            <dt>State</dt>
            <dd>{{ caseStateLabel[report.case.state] }}, version {{ report.case.version }}</dd>
          </div>
          <div>
            <dt>Case id</dt>
            <dd class="mono wrap">{{ report.case.case_id }}</dd>
          </div>
        </dl>
      </section>

      <section>
        <h2>Evidence and verification</h2>
        <p v-if="!selected">No receipt has been verified.</p>
        <dl v-else>
          <div>
            <dt>Receipt</dt>
            <dd>
              {{ receiptView[selected.result.receipt_state].label }} ({{ selected.result.reason_code }})
            </dd>
          </div>
          <div v-if="selected.result.output">
            <dt>Recovered amount</dt>
            <dd class="mono">{{ formatZat(selected.result.output.amount_zat) }} zat</dd>
          </div>
          <div v-if="selected.result.output">
            <dt>Output</dt>
            <dd class="mono wrap">
              {{ selected.result.output.network }}:{{ selected.result.output.pool }}:{{
                selected.result.output.txid
              }}:{{ selected.result.output.output_index }}
            </dd>
          </div>
          <div v-if="selected.result.output">
            <dt>Memo (display only)</dt>
            <dd>{{ memoPreview(selected.result.output.memo_hex) ?? 'Empty' }}</dd>
          </div>
          <div>
            <dt>Receipt SHA-256</dt>
            <dd class="mono wrap">{{ selected.result.receipt_sha256 ?? 'n/a' }}</dd>
          </div>
          <div>
            <dt>Raw tx SHA-256</dt>
            <dd class="mono wrap">{{ selected.result.raw_tx_sha256 ?? 'n/a' }}</dd>
          </div>
          <div>
            <dt>Verifier</dt>
            <dd>
              {{ selected.result.verifier?.name }} {{ selected.result.verifier?.version }}, Glasspane
              {{ selected.result.verifier?.glasspane_revision?.slice(0, 10) }}
            </dd>
          </div>
          <div>
            <dt>Chain</dt>
            <dd>
              {{
                observation?.source_kind === 'SIMULATED'
                  ? 'Simulated confirmation (test/demo only)'
                  : chainView[observation?.state ?? 'UNAVAILABLE'].label
              }}<template v-if="observation"
                >, {{ observation.source }}, {{ formatWhen(observation.observed_at) }}</template
              >
            </dd>
          </div>
        </dl>
      </section>

      <p v-if="report.chain_review?.length" role="alert">
        An approved payment needs chain review. Historical credited balances remain unchanged.
      </p>
      <section>
        <h2>Balances</h2>
        <table>
          <tbody>
            <tr>
              <th scope="row">Approved credit</th>
              <td class="mono">{{ formatZat(report.balances.credited_zat) }}</td>
            </tr>
            <tr>
              <th scope="row">Outstanding</th>
              <td class="mono">{{ formatZat(report.balances.outstanding_zat) }}</td>
            </tr>
            <tr>
              <th scope="row">Candidate (not credited)</th>
              <td class="mono">{{ formatZat(report.balances.candidate_zat) }}</td>
            </tr>
            <tr>
              <th scope="row">Outstanding if approved</th>
              <td class="mono">{{ formatZat(report.balances.projected_outstanding_zat) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="small">
          All amounts in zatoshis. Rules {{ report.balances.rules_version }}. Findings: {{ findingLabels }}.
        </p>
      </section>

      <section>
        <h2>Decisions</h2>
        <p v-if="!report.decisions?.length">No decision recorded.</p>
        <ol v-else class="decisions">
          <li v-for="d in report.decisions" :key="d.resolution_id">
            <strong>{{ actionView[d.action].done }}</strong
            >, {{ formatWhen(d.decided_at) }}, case version {{ d.case_version }}. “{{ d.reason }}”<template
              v-if="d.allocated_zat"
            >
              Allocated <span class="mono">{{ formatZat(d.allocated_zat) }} zat</span>.</template
            >
          </li>
        </ol>
      </section>

      <footer class="limits">
        A valid receipt shows that one output can be recovered from the supplied transaction. It does not
        prove who paid, that the transaction is on chain, or that the merchant's decision was right.
      </footer>
    </article>
  </div>
</template>

<style scoped>
.paper-wrap {
  padding: 2rem 0 0;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}
.row {
  display: flex;
  gap: 0.5rem;
}
.paper {
  width: min(100% - 2rem, 820px);
  margin: 0 auto;
  background: var(--color-paper);
  color: #111;
  border-radius: var(--radius-md);
  padding: clamp(1.5rem, 4vw, 3.5rem);
  display: grid;
  gap: 2rem;
  color-scheme: light;
}
.top h1 {
  font-size: var(--step-3);
}
.top p,
.small {
  color: #555;
  font-size: var(--step--1);
  margin-top: 0.5rem;
}
h2 {
  font-size: var(--step-1);
  margin-bottom: 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid #111;
}
dl > div {
  display: grid;
  grid-template-columns: 11rem minmax(0, 1fr);
  gap: 1rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid #ddd;
}
dt {
  color: #555;
  font-size: var(--step--1);
}
dd {
  font-size: var(--step--1);
}
.wrap {
  overflow-wrap: anywhere;
}
table {
  border-collapse: collapse;
  width: 100%;
  max-width: 420px;
}
th,
td {
  text-align: left;
  padding: 0.4rem 0;
  border-bottom: 1px solid #ddd;
  font-weight: 400;
  font-size: var(--step--1);
}
td {
  text-align: right;
}
.decisions {
  padding-left: 1.2rem;
  display: grid;
  gap: 0.5rem;
  font-size: var(--step--1);
}
.limits {
  font-size: var(--step--1);
  color: #555;
  border-top: 1px solid #ddd;
  padding-top: 1rem;
}
.error {
  color: var(--color-fail);
}
@media (max-width: 560px) {
  dl > div {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }
}
@media print {
  .toolbar {
    display: none;
  }
  .paper {
    width: 100%;
    padding: 0;
    border-radius: 0;
  }
}
</style>
