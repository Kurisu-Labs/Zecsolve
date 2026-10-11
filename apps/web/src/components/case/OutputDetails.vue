<script setup lang="ts">
import { computed } from 'vue'
import type { InvoiceTerms, RecoveredOutput } from '@/api/types'
import HashText from '@/components/ui/HashText.vue'
import MoneyAmount from '@/components/ui/MoneyAmount.vue'
import { memoPreview, outputId } from '@/lib/status'

const props = defineProps<{ output: RecoveredOutput; terms: InvoiceTerms }>()
const id = computed(() => outputId(props.output.network, props.output.pool, props.output.txid, props.output.output_index))
const memo = computed(() => memoPreview(props.output.memo_hex))
const receiverMatches = computed(() => props.output.receiver_hex === props.terms.receiver_hex)
const memoMatches = computed(() => props.terms.memo_hex !== null && props.output.memo_hex === props.terms.memo_hex)
</script>

<template>
  <section aria-labelledby="output-title" class="output">
    <h2 id="output-title" class="title">Recovered output</h2>
    <dl class="rows">
      <div><dt>Amount</dt><dd><MoneyAmount :zat="output.amount_zat" emphasis /></dd></div>
      <div><dt>Output</dt><dd><HashText :value="id" :head="22" :tail="4" label="output id" /></dd></div>
      <div><dt>Transaction</dt><dd><HashText :value="output.txid" label="transaction id" /></dd></div>
      <div>
        <dt>Receiver</dt>
        <dd>
          <HashText :value="output.receiver_address" :head="10" :tail="8" label="receiver address" />
          <span class="match" :class="receiverMatches ? 'yes' : 'no'">{{ receiverMatches ? 'matches invoice' : 'differs from invoice' }}</span>
        </dd>
      </div>
      <div>
        <dt>Memo</dt>
        <dd>
          <span class="memo">{{ memo ?? 'Empty' }}</span>
          <span class="match" :class="memoMatches ? 'yes' : 'no'">{{ memoMatches ? 'matches reference' : 'no reference match' }}</span>
          <span class="note">Shown as text for reading only. The stored value is hex and is never executed.</span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.title { font-size: var(--step-1); margin-bottom: 0.75rem; }
.rows { display: grid; }
.rows > div { display: grid; grid-template-columns: 7.5rem minmax(0, 1fr); gap: 1rem; padding: 0.7rem 0; border-bottom: 1px solid var(--color-line); align-items: baseline; }
.rows > div:last-child { border-bottom: 0; }
dt { color: var(--color-mute); font-size: var(--step--1); }
dd { display: flex; flex-wrap: wrap; gap: 0.35rem 0.75rem; align-items: center; min-width: 0; }
.memo { font-family: var(--font-mono); font-size: var(--step--1); }
.match { font-size: var(--step--1); }
.match.yes { color: var(--color-ok); }
.match.no { color: var(--color-warn); }
.note { flex-basis: 100%; color: var(--color-faint); font-size: var(--step--1); }
@media (max-width: 520px) { .rows > div { grid-template-columns: 1fr; gap: 0.25rem; } }
</style>
