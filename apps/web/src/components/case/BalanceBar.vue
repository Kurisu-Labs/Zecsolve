<script setup lang="ts">
import { computed } from 'vue'
import type { Balances } from '@/api/types'
import MoneyAmount from '@/components/ui/MoneyAmount.vue'
import { ratio } from '@/lib/money'

// Approved credit and the pending candidate are drawn differently: solid yellow is money
// a merchant approved; the pixel pattern is what a receipt disclosed but nobody credited.
const props = defineProps<{ expectedZat: number; balances: Balances }>()

const credited = computed(() => ratio(props.balances.credited_zat, props.expectedZat))
const candidate = computed(() =>
  Math.min(ratio(props.balances.candidate_zat, props.expectedZat), 1 - credited.value),
)
</script>

<template>
  <section class="balance" aria-label="Invoice balance">
    <div
      class="bar"
      role="img"
      :aria-label="`Approved ${balances.credited_zat} of ${expectedZat} zatoshis; candidate ${balances.candidate_zat}`"
    >
      <span class="credited" :style="{ width: `${credited * 100}%` }" />
      <span class="candidate" :style="{ width: `${candidate * 100}%` }" />
    </div>
    <dl class="legend">
      <div>
        <dt>Invoice</dt>
        <dd><MoneyAmount :zat="expectedZat" size="sm" /></dd>
      </div>
      <div>
        <dt><span class="key key-credited" aria-hidden="true" />Approved credit</dt>
        <dd><MoneyAmount :zat="balances.credited_zat" size="sm" /></dd>
      </div>
      <div>
        <dt><span class="key key-candidate" aria-hidden="true" />Candidate, not credited</dt>
        <dd><MoneyAmount :zat="balances.candidate_zat" size="sm" /></dd>
      </div>
      <div>
        <dt>Still owed if approved</dt>
        <dd><MoneyAmount :zat="balances.projected_outstanding_zat" size="sm" /></dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.balance { display: grid; gap: 1.25rem; }
.bar {
  position: relative; display: flex; height: 18px; border-radius: 4px; overflow: hidden;
  background: var(--color-ink-sunk); box-shadow: inset 0 0 0 1px var(--color-line-strong);
}
.credited { background: var(--color-zec); transition: width var(--dur-slow) var(--ease-enter); }
.candidate {
  background-image: conic-gradient(var(--color-zec) 25%, transparent 0 50%, var(--color-zec) 0 75%, transparent 0);
  background-size: 6px 6px;
  opacity: 0.75;
  transition: width var(--dur-slow) var(--ease-enter);
}
.legend { display: grid; gap: 1rem 1.5rem; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
dt { display: flex; align-items: center; gap: 0.45rem; color: var(--color-mute); font-size: var(--step--1); margin-bottom: 0.3rem; }
.key { width: 10px; height: 10px; border-radius: 2px; }
.key-credited { background: var(--color-zec); }
.key-candidate {
  background-image: conic-gradient(var(--color-zec) 25%, transparent 0 50%, var(--color-zec) 0 75%, transparent 0);
  background-size: 4px 4px;
}
</style>
