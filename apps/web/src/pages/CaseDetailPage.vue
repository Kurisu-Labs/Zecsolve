<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { cases, session } from '@/api/store'
import type { CaseReport } from '@/api/types'
import AuditTimeline from '@/components/case/AuditTimeline.vue'
import BalanceBar from '@/components/case/BalanceBar.vue'
import CaseStepper from '@/components/case/CaseStepper.vue'
import DecisionPanel from '@/components/case/DecisionPanel.vue'
import FindingsList from '@/components/case/FindingsList.vue'
import OutputDetails from '@/components/case/OutputDetails.vue'
import StatusTiles from '@/components/case/StatusTiles.vue'
import HashText from '@/components/ui/HashText.vue'

const props = defineProps<{ id: string }>()

const report = ref<CaseReport | null>(null)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const meta = computed(() => cases.demoMeta(props.id))
const selected = computed(() =>
  report.value?.verifications.find((v) => v.verification_id === report.value?.selected_verification_id),
)

async function load(verificationId?: string | null) {
  error.value = null
  try {
    report.value = await cases.report(props.id, verificationId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function onChanged(message: string) {
  await load()
  notice.value = message
  window.setTimeout(() => (notice.value = null), 4000)
}

watch(() => props.id, () => load(), { immediate: true })
</script>

<template>
  <div class="shell page">
    <RouterLink to="/cases" class="back">All cases</RouterLink>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="!report" class="muted">Loading case…</p>

    <template v-else>
      <header class="head">
        <div class="titles">
          <h1>{{ meta?.title ?? 'Case' }}</h1>
          <p class="lede">{{ meta?.summary ?? `Invoice ${report.invoice.invoice_id}` }}</p>
          <p class="ids">
            <span>Case <HashText :value="report.case.case_id" :head="8" :tail="4" label="case id" /></span>
            <span>Invoice <HashText :value="report.invoice.invoice_id" :head="8" :tail="4" label="invoice id" /></span>
          </p>
        </div>
        <div class="head-actions">
          <RouterLink :to="`/submit/${report.case.case_id}`" class="btn">{{ session.mode === 'demo' ? 'Customer preview' : 'Submit evidence' }}</RouterLink>
          <RouterLink :to="`/report/${report.case.case_id}`" class="btn">Report</RouterLink>
        </div>
      </header>

      <CaseStepper :state="report.case.state" />

      <p v-if="notice" class="notice" role="status">{{ notice }}</p>

      <StatusTiles :report="report" />

      <div class="grid">
        <div class="main">
          <section class="card">
            <h2 class="card-title">Balance</h2>
            <BalanceBar :expected-zat="report.invoice.terms.expected_zat" :balances="report.balances" />
          </section>

          <section class="card">
            <FindingsList :findings="report.balances.findings" :rules-version="report.balances.rules_version" />
          </section>

          <section v-if="selected?.result.output" class="card">
            <OutputDetails :output="selected.result.output" :terms="report.invoice.terms" />
          </section>

          <section v-if="report.verifications.length > 1" class="card">
            <h2 class="card-title">Verification attempts</h2>
            <div class="attempts">
              <button
                v-for="v in report.verifications"
                :key="v.verification_id"
                type="button"
                class="btn"
                :class="{ 'btn-primary': v.verification_id === report.selected_verification_id }"
                @click="load(v.verification_id)"
              >
                {{ v.result.receipt_state }} · {{ v.verification_id.slice(0, 8) }}
              </button>
            </div>
          </section>
        </div>

        <aside class="side">
          <DecisionPanel :report="report" @changed="onChanged" />
          <section class="card">
            <AuditTimeline :events="report.events" />
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 2rem 0; display: grid; gap: 1.5rem; }
.back { color: var(--color-mute); text-decoration: none; font-size: var(--step--1); justify-self: start; }
.back:hover { color: var(--color-snow); }
.head { display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: space-between; align-items: flex-end; }
h1 { font-size: var(--step-4); }
.lede { color: var(--color-mute); margin-top: 0.6rem; max-width: 60ch; }
.ids { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; margin-top: 0.9rem; color: var(--color-mute); font-size: var(--step--1); }
.ids > span { display: inline-flex; align-items: center; gap: 0.4rem; }
.head-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.notice {
  padding: 0.75rem 1rem; border-radius: var(--radius-md); background: var(--color-zec); color: var(--color-ink); font-weight: 550;
  animation: drop var(--dur-base) var(--ease-enter);
}
.grid { display: grid; gap: 1.5rem; grid-template-columns: minmax(0, 1fr); }
@media (min-width: 1000px) { .grid { grid-template-columns: minmax(0, 1.6fr) minmax(320px, 1fr); align-items: start; } }
.main, .side { display: grid; gap: 1.5rem; }
@media (min-width: 1000px) { .side { position: sticky; top: 88px; } }
.card { border: 1px solid var(--color-line); border-radius: var(--radius-lg); padding: 1.25rem; }
.card-title { font-size: var(--step-1); margin-bottom: 1rem; }
.attempts { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.muted { color: var(--color-mute); }
.error { color: var(--color-fail); }
@keyframes drop { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
</style>
