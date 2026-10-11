<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { cases } from '@/api/store'
import BalanceBar from '@/components/case/BalanceBar.vue'
import StatusTiles from '@/components/case/StatusTiles.vue'

// Where the hero's note lands: the real case UI, rendered from the shortfall fixture.
const report = computed(() => cases.demoReport('shortfall'))
</script>

<template>
  <section v-if="report" class="preview shell" aria-labelledby="preview-title">
    <div class="intro">
      <h2 id="preview-title">This is where the note lands.</h2>
      <p>The same screen a merchant works in. The receipt is valid, the chain is unchecked, and half the invoice is still owed.</p>
    </div>
    <div class="frame">
      <StatusTiles :report="report" />
      <div class="balance">
        <BalanceBar :expected-zat="report.invoice.terms.expected_zat" :balances="report.balances" />
      </div>
      <RouterLink to="/cases/shortfall" class="btn btn-primary open">Work this case</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.preview { padding: 4rem 0; display: grid; gap: 2rem; }
.intro { display: grid; gap: 0.75rem; max-width: 42rem; }
h2 { font-size: var(--step-4); }
.intro p { color: var(--color-mute); font-size: var(--step-1); line-height: 1.45; }
.frame { display: grid; gap: 1.5rem; padding: clamp(1rem, 3vw, 2rem); border: 1px solid var(--color-line-strong); border-radius: 22px; background: var(--color-ink-sunk); }
.balance { padding: 1.25rem; border: 1px solid var(--color-line); border-radius: var(--radius-lg); }
.open { justify-self: start; }
</style>
