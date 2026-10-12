<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Contract } from '@/api/client'
import { session } from '@/api/session'
import ReportFields from '@/components/ReportFields.vue'
import ExportButton from '@/components/ExportButton.vue'
const props = defineProps<{ id: string }>()
const report = ref<Contract['reviewerReport'] | null>(null)
const original = ref<Contract['evidenceContent'] | null>(null)
const error = ref('')
const busy = ref(false)
async function load() {
  busy.value = true
  error.value = ''
  report.value = null
  original.value = null
  try {
    report.value = await api.reviewerReport(props.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unable to read report.'
  } finally {
    busy.value = false
  }
}
async function readOriginal(id: string) {
  busy.value = true
  error.value = ''
  original.value = null
  try {
    original.value = await api.content(props.id, id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unable to read evidence.'
  } finally {
    busy.value = false
  }
}
function printReport() {
  window.print()
}
function downloadOriginal(component: 'receipt_json' | 'raw_tx_hex') {
  const value = original.value?.[component]
  if (value === null || value === undefined) return
  const url = URL.createObjectURL(new Blob([value], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `${original.value!.evidence_id}-${component === 'receipt_json' ? 'receipt.json' : 'transaction.hex'}`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
onMounted(load)
</script>
<template>
  <div class="shell workflow-page">
    <h1>Shared case report</h1>
    <p>
      This report contains only the information selected for your access. Hidden sections are not evidence of
      missing records. Receipt validity, historical chain observations, and merchant decisions remain
      separate.
    </p>
    <div class="workflow-row no-print">
      <button class="btn" :disabled="busy" @click="load">Refresh report</button
      ><button class="btn" :disabled="!report" @click="printReport">Print</button
      ><ExportButton v-if="session.info?.access.allow_export" :id="id" />
      <p v-else>Report-only access. Packet export is not permitted.</p>
    </div>
    <p v-if="busy" role="status">Loading authorized information…</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <template v-if="report">
      <p>
        Generated {{ new Date(report.generated_at).toLocaleString() }}. Scoped disclosure; not a complete
        replay packet.
      </p>
      <ul>
        <li v-for="limit in report.limitations" :key="limit">{{ limit }}</li>
      </ul>
      <section v-for="section in report.sections" :key="section" class="workflow-card">
        <h2>{{ section[0]?.toUpperCase() }}{{ section.slice(1) }}</h2>
        <p v-if="section === 'claims'">Customer assertions, not proof of payment.</p>
        <ReportFields :value="report[section]" />
      </section>
    </template>
    <section v-if="session.info?.access.evidence_ids?.length" class="workflow-card no-print">
      <h2>Selected original evidence</h2>
      <p>These originals can disclose amount, recipient, and memo. Copies cannot be recalled.</p>
      <button
        v-for="e in session.info.access.evidence_ids"
        :key="e"
        class="btn"
        :disabled="busy"
        @click="readOriginal(e)"
      >
        Read {{ e }}
      </button>
    </section>
    <section v-if="original" class="workflow-card no-print">
      <h2>Original components</h2>
      <button class="btn" @click="original = null">Hide original</button>
      <p>Preview line endings may differ. Download a component to preserve its exact original text.</p>
      <label
        >Receipt preview<textarea class="field mono" readonly rows="8" :value="original.receipt_json ?? ''" />
      </label>
      <p v-if="original.receipt_json === null">Receipt not supplied.</p>
      <button v-else class="btn" @click="downloadOriginal('receipt_json')">Download original receipt</button
      ><label
        >Raw transaction preview<textarea
          class="field mono"
          readonly
          rows="4"
          :value="original.raw_tx_hex ?? ''"
        />
      </label>
      <p v-if="original.raw_tx_hex === null">Raw transaction not supplied.</p>
      <button v-else class="btn" @click="downloadOriginal('raw_tx_hex')">
        Download original transaction
      </button>
    </section>
  </div>
</template>
<style scoped>
@media print {
  .no-print {
    display: none;
  }
}
</style>
