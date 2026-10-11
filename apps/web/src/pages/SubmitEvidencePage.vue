<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { cases, session } from '@/api/store'
import type { CaseReport, VerificationReport } from '@/api/types'
import MoneyAmount from '@/components/ui/MoneyAmount.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { receiptView } from '@/lib/status'

// Customer-facing: one column, numbered because it is a real sequence,
// and an explicit disclosure step before anything is shared.
const props = defineProps<{ id: string }>()

const EXAMPLE_RECEIPT = `{
  "version": "0",
  "network": "mainnet",
  "pool": "orchard",
  "tx_id": "66167cd3020eb329446e86d80ccd0494baa3959bf9a0e586dbdccd204b6dcfd0",
  "output_index": 1,
  "ock": "pNVZw22HvhbkKcYDNV_bo6eMjukjcfaxMDQYOEF1mkI",
  "label": "glasspane first receipt",
  "issued_at": "2026-05-31T12:07:31.888692288Z"
}`

const report = ref<CaseReport | null>(null)
const loadError = ref<string | null>(null)
const step = ref<1 | 2 | 3>(1)
const hasReceipt = ref(true)
const receiptJson = ref('')
const rawTxHex = ref('')
const consent = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const result = ref<VerificationReport | null>(null)

watch(
  () => props.id,
  async (id) => {
    try {
      report.value = await cases.report(id)
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : String(e)
    }
  },
  { immediate: true },
)

const receiptLooksLikeJson = computed(() => {
  if (!hasReceipt.value) return true
  try {
    const parsed = JSON.parse(receiptJson.value) as Record<string, unknown>
    return typeof parsed === 'object' && parsed !== null && 'tx_id' in parsed && 'output_index' in parsed
  } catch {
    return false
  }
})

const canContinue = computed(() =>
  hasReceipt.value ? receiptLooksLikeJson.value && (session.mode === 'demo' || rawTxHex.value.trim().length > 0) : true,
)

function useExample() {
  receiptJson.value = EXAMPLE_RECEIPT
  rawTxHex.value = session.mode === 'demo' ? '(bundled historical transaction)' : rawTxHex.value
}

function useTampered() {
  receiptJson.value = EXAMPLE_RECEIPT.replace('pNVZw22HvhbkKcYDNV_bo6eMjukjcfaxMDQYOEF1mkI', 'pNVZw22HvhbkKcYDNV_bo6eMjukjcfaxMDQYOEF1mkJ')
  rawTxHex.value = session.mode === 'demo' ? '(bundled historical transaction)' : rawTxHex.value
}

async function submit() {
  busy.value = true
  error.value = null
  try {
    const outcome = await cases.submitAndVerify(props.id, {
      receiptJson: hasReceipt.value ? receiptJson.value : null,
      rawTxHex: hasReceipt.value ? rawTxHex.value || null : null,
      source: hasReceipt.value ? 'Customer receipt via case link' : 'Customer claim without receipt',
    })
    result.value = outcome.report
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="shell page">
    <p v-if="loadError" class="error" role="alert">This link does not open a case: {{ loadError }}</p>
    <p v-else-if="!report" class="muted">Loading…</p>

    <div v-else class="column">
      <header>
        <p v-if="session.mode === 'live'" class="hint">Merchant submission only. Customer grants are not available yet; do not share your merchant credential.</p>
        <h1>Help the store find your payment</h1>
        <p class="lede">
          Shielded payments are private, so the store cannot see yours. A receipt lets it read one payment and nothing else.
        </p>
        <div class="invoice">
          <span class="muted">The store expected</span>
          <MoneyAmount :zat="report.invoice.terms.expected_zat" size="md" />
        </div>
      </header>

      <section v-if="result" class="done" aria-live="polite">
        <StatusBadge size="md" :label="receiptView[result.receipt_state].label" :tone="receiptView[result.receipt_state].tone" :glyph="receiptView[result.receipt_state].glyph" />
        <p v-if="result.receipt_state === 'VALID' && result.output">
          The store can now see a payment of <strong class="mono">{{ result.output.amount_zat.toLocaleString('en-US') }} zat</strong>.
          It will review it against your order; nothing is credited automatically.
        </p>
        <p v-else-if="result.receipt_state === 'NONE'">Your evidence submission is recorded without a receipt. No payment has been verified.</p>
        <p v-else>{{ receiptView[result.receipt_state].detail }} You can share a different receipt.</p>
        <div class="row">
          <button v-if="result.receipt_state !== 'VALID'" type="button" class="btn" @click="(result = null), (step = 1)">Try another receipt</button>
          <RouterLink :to="`/cases/${report.case.case_id}`" class="btn btn-quiet">Open the merchant view</RouterLink>
        </div>
      </section>

      <ol v-else class="steps">
        <li :class="{ active: step === 1, done: step > 1 }">
          <h2>Add your receipt</h2>
          <div v-if="step === 1" class="body">
            <div class="choice" role="radiogroup" aria-label="Do you have a receipt?">
              <label :class="{ on: hasReceipt }"><input v-model="hasReceipt" type="radio" :value="true" /> I have a receipt from my wallet</label>
              <label :class="{ on: !hasReceipt }"><input v-model="hasReceipt" type="radio" :value="false" /> I don't have one yet</label>
            </div>
            <template v-if="hasReceipt">
              <label class="label" for="receipt">Receipt (JSON)</label>
              <textarea id="receipt" v-model="receiptJson" class="field mono" rows="8" spellcheck="false" placeholder='{ "version": "0", "tx_id": "…", "output_index": 1, "ock": "…" }' />
              <p v-if="receiptJson && !receiptLooksLikeJson" class="hint warn">This does not look like a receipt. It needs a transaction id and an output index.</p>
              <label class="label" for="rawtx">Raw transaction (hex)</label>
              <textarea id="rawtx" v-model="rawTxHex" class="field mono" rows="3" spellcheck="false" placeholder="Paste the raw transaction your wallet exported" />
              <div v-if="session.mode === 'demo'" class="row">
                <button type="button" class="btn" @click="useExample">Use the example receipt</button>
                <button type="button" class="btn btn-quiet" @click="useTampered">Use a tampered copy</button>
              </div>
            </template>
            <p v-else class="hint">You can submit without a receipt. This records missing evidence, not a verified payment.</p>
            <button type="button" class="btn btn-primary" :disabled="!canContinue" @click="step = 2">Continue</button>
          </div>
        </li>

        <li :class="{ active: step === 2, done: step > 2 }">
          <h2>Check what you share</h2>
          <div v-if="step === 2" class="body">
            <template v-if="hasReceipt">
              <p>Anyone holding this receipt can read these three things about this one payment:</p>
              <ul class="disclose">
                <li><strong>The amount</strong> you sent</li>
                <li><strong>The address</strong> it went to</li>
                <li><strong>The memo</strong> attached to it</li>
              </ul>
              <p class="muted">
                It cannot spend your funds or reveal your other payments. Once shared it cannot be taken back, because copies
                can be forwarded.
              </p>
              <label class="consent"><input v-model="consent" type="checkbox" /> I understand and want to share this receipt with the store</label>
            </template>
            <p v-else>The store will see your note and the transaction id you reported, if any.</p>
            <div class="row">
              <button type="button" class="btn btn-primary" :disabled="hasReceipt && !consent" @click="step = 3">Continue</button>
              <button type="button" class="btn btn-quiet" @click="step = 1">Back</button>
            </div>
          </div>
        </li>

        <li :class="{ active: step === 3 }">
          <h2>Send to the store</h2>
          <div v-if="step === 3" class="body">
            <p>The store's verifier checks the receipt against the transaction. It takes a few seconds.</p>
            <div class="row">
              <button type="button" class="btn btn-primary" :disabled="busy" @click="submit">
                {{ busy ? 'Verifying…' : hasReceipt ? 'Share receipt' : 'Submit without receipt' }}
              </button>
              <button type="button" class="btn btn-quiet" :disabled="busy" @click="step = 2">Back</button>
            </div>
            <p v-if="error" class="error" role="alert">{{ error }}</p>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 3rem 0; }
.column { max-width: 640px; display: grid; gap: 2.5rem; }
h1 { font-size: var(--step-4); }
.lede { color: var(--color-mute); margin-top: 0.75rem; max-width: 52ch; }
.invoice { display: flex; align-items: center; gap: 1rem; margin-top: 1.5rem; padding: 1rem 1.25rem; border: 1px solid var(--color-line); border-radius: var(--radius-lg); }
.steps { list-style: none; counter-reset: step; padding: 0; margin: 0; display: grid; gap: 0.5rem; }
.steps > li { counter-increment: step; border: 1px solid var(--color-line); border-radius: var(--radius-lg); padding: 1.1rem 1.25rem; color: var(--color-faint); }
.steps > li h2 { font-size: var(--step-1); display: flex; gap: 0.75rem; align-items: baseline; }
.steps > li h2::before { content: counter(step); font-family: var(--font-mono); font-size: var(--step--1); color: inherit; }
.steps > li.active { color: var(--color-snow); border-color: var(--color-line-strong); background: var(--color-ink-raised); }
.steps > li.active h2::before { color: var(--color-zec); }
.steps > li.done { color: var(--color-mute); }
.body { display: grid; gap: 0.9rem; margin-top: 1rem; animation: rise var(--dur-base) var(--ease-enter); }
.choice { display: grid; gap: 0.4rem; }
.choice label, .consent { display: flex; gap: 0.6rem; align-items: center; padding: 0.7rem 0.8rem; border: 1px solid var(--color-line); border-radius: var(--radius-md); cursor: pointer; }
.choice label.on { border-color: var(--color-zec); }
input[type='radio'], input[type='checkbox'] { accent-color: var(--color-zec); width: 16px; height: 16px; }
.label { font-size: var(--step--1); color: var(--color-mute); }
textarea.mono { font-size: var(--step--1); line-height: 1.5; }
.hint { color: var(--color-mute); font-size: var(--step--1); }
.hint.warn { color: var(--color-warn); }
.row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.disclose { display: grid; gap: 0.35rem; padding-left: 1.1rem; }
.disclose strong { color: var(--color-zec); font-weight: 550; }
.done { display: grid; gap: 1rem; justify-items: start; padding: 1.5rem; border: 1px solid var(--color-line-strong); border-radius: var(--radius-lg); }
.muted { color: var(--color-mute); }
.error { color: var(--color-fail); }
button.btn-primary { justify-self: start; }
@keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
</style>
