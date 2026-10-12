<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { cases, resetDemo, session, type CaseListItem } from '@/api/store'
import { api, type Contract } from '@/api/client'
import MoneyAmount from '@/components/ui/MoneyAmount.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { caseStateLabel, chainView, formatWhen, receiptView } from '@/lib/status'

const items = ref<CaseListItem[]>([])
const liveItems = ref<Contract['caseList']['items']>([])
const cursor = ref<string | null>(null)
const filter = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

async function load(more = false) {
  loading.value = true
  error.value = null
  try {
    if (session.mode === 'demo') items.value = await cases.list()
    else {
      const page = await api.list(more ? cursor.value ?? undefined : undefined, filter.value || undefined)
      liveItems.value = more ? [...liveItems.value, ...page.items] : page.items
      cursor.value = page.next_cursor ?? null
    }
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

onMounted(() => load())
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

    <div v-if="session.mode === 'live'" class="head">
      <RouterLink to="/cases/new" class="btn btn-primary">Create invoice and case</RouterLink>
      <label>Filter state <select v-model="filter" class="field" :disabled="loading" @change="load()"><option value="">All states</option><option v-for="s in ['OPEN','AWAITING_EVIDENCE','UNDER_REVIEW','RESOLVED','CLOSED_UNRESOLVED']" :key="s">{{ s }}</option></select></label>
      <button class="btn" :disabled="loading" @click="load()">Refresh</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Loading cases…</p>
    <div v-else-if="session.mode === 'demo' ? items.length === 0 : liveItems.length === 0" class="empty">
      <p>No cases yet.</p>
      <p class="muted">
        Create an invoice to open your first case.
      </p>
    </div>

    <div v-else-if="session.mode === 'live'" class="table-wrap">
      <table><caption class="sr-only">Merchant cases</caption><thead><tr><th>Case</th><th>Invoice</th><th>State</th><th>Version</th><th>Created</th></tr></thead>
      <tbody><tr v-for="item in liveItems" :key="item.case_id"><td><RouterLink :to="`/cases/${item.case_id}`">{{ item.case_id }}</RouterLink></td><td>{{ item.invoice_id }}</td><td>{{ caseStateLabel[item.state] }}</td><td>{{ item.version }}</td><td>{{ formatWhen(item.created_at) }}</td></tr></tbody></table>
      <button v-if="cursor" class="btn" :disabled="loading" @click="load(true)">Load more cases</button>
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
