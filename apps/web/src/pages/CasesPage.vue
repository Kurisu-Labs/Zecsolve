<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { cases, resetDemo, session, type CaseListItem } from '@/api/store'
import MoneyAmount from '@/components/ui/MoneyAmount.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { caseStateLabel, chainView, formatWhen, receiptView } from '@/lib/status'

const items = ref<CaseListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await cases.list()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function reset() {
  resetDemo()
  void load()
}

onMounted(load)
</script>

<template>
  <div class="shell page">
    <header class="head">
      <div>
        <h1>Cases</h1>
        <p class="lede">
          Payments that did not match an invoice. Each row keeps the receipt and the chain apart, so a valid receipt never
          reads as paid.
        </p>
      </div>
      <button v-if="session.mode === 'demo'" type="button" class="btn btn-quiet" @click="reset">Reset demo data</button>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Loading cases…</p>
    <div v-else-if="items.length === 0" class="empty">
      <p>No cases yet.</p>
      <p class="muted">
        The API has no list route yet, so live mode shows cases you have opened in this browser. Open one by id from
        <RouterLink to="/connect">Connect</RouterLink>.
      </p>
    </div>

    <div v-else class="table-wrap">
      <table>
        <caption class="sr-only">Cases with receipt, chain and balance status</caption>
        <thead>
          <tr>
            <th scope="col">Case</th>
            <th scope="col">State</th>
            <th scope="col">Receipt</th>
            <th scope="col">Chain</th>
            <th scope="col" class="num">Invoice</th>
            <th scope="col" class="num">Candidate</th>
            <th scope="col">Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.caseId">
            <th scope="row">
              <RouterLink :to="`/cases/${item.caseId}`" class="case-link">
                <span class="case-title">{{ item.title }}</span>
                <span class="case-sub">{{ item.customer }}</span>
              </RouterLink>
            </th>
            <td>{{ caseStateLabel[item.state] }}</td>
            <td>
              <StatusBadge :label="receiptView[item.receipt].label" :tone="receiptView[item.receipt].tone" :glyph="receiptView[item.receipt].glyph" />
            </td>
            <td>
              <StatusBadge :label="chainView[item.chain].label" :tone="chainView[item.chain].tone" :glyph="chainView[item.chain].glyph" />
            </td>
            <td class="num"><MoneyAmount :zat="item.expectedZat" size="sm" /></td>
            <td class="num"><MoneyAmount :zat="item.candidateZat" size="sm" :emphasis="item.candidateZat > 0" /></td>
            <td class="muted">{{ formatWhen(item.updatedAt) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 3rem 0 2rem; }
.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; justify-content: space-between; margin-bottom: 2rem; }
h1 { font-size: var(--step-4); }
.lede { color: var(--color-mute); max-width: 60ch; margin-top: 0.75rem; }
.muted { color: var(--color-mute); }
.error { color: var(--color-fail); }
.empty { border: 1px dashed var(--color-line-strong); border-radius: var(--radius-lg); padding: 2rem; display: grid; gap: 0.5rem; }
.table-wrap { overflow-x: auto; border: 1px solid var(--color-line); border-radius: var(--radius-lg); }
table { width: 100%; border-collapse: collapse; min-width: 880px; }
th, td { white-space: nowrap; text-align: left; padding: 0.9rem 1rem; border-bottom: 1px solid var(--color-line); vertical-align: middle; font-weight: 400; }
thead th { color: var(--color-mute); font-size: var(--step--1); background: var(--color-ink-raised); }
tbody tr { transition: background-color var(--dur-fast) var(--ease-standard); }
tbody tr:hover { background: var(--color-ink-raised); }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
.num { text-align: right; }
.num :deep(.money) { align-items: flex-end; }
.case-link { display: grid; text-decoration: none; min-width: 12rem; }
.case-link:hover .case-title { color: var(--color-zec); }
.case-title { white-space: normal; font-weight: 550; transition: color var(--dur-fast) var(--ease-standard); }
.case-sub { color: var(--color-mute); font-size: var(--step--1); }
</style>
