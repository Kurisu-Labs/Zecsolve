<script setup lang="ts">
import type { CaseEvent } from '@/api/types'
import { formatWhen, shortHash } from '@/lib/status'

defineProps<{ events: CaseEvent[] }>()

const labels: Record<string, string> = {
  CASE_OPENED: 'Case opened',
  EVIDENCE_SUBMITTED: 'Evidence stored, encrypted',
  VERIFICATION_RECORDED: 'Verification recorded',
  CHAIN_OBSERVED: 'Chain observation recorded',
  RESOLUTION_APPROVE_OUTPUT: 'Output approved',
  RESOLUTION_REQUEST_EVIDENCE: 'Evidence requested',
  RESOLUTION_REJECT_EVIDENCE: 'Evidence rejected',
  RESOLUTION_CLOSE_UNRESOLVED: 'Closed unresolved',
}
</script>

<template>
  <section aria-labelledby="audit-title">
    <h2 id="audit-title" class="title">Audit trail</h2>
    <ol class="trail">
      <li v-for="e in [...events].reverse()" :key="e.event_id">
        <span class="seq mono">{{ e.sequence }}</span>
        <div class="body">
          <p class="what">{{ labels[e.action] ?? e.action }}</p>
          <p class="when">{{ formatWhen(e.at) }} · hash <span class="mono">{{ shortHash(e.event_hash, 6, 4) }}</span></p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.title { font-size: var(--step-1); margin-bottom: 0.75rem; }
.trail { list-style: none; margin: 0; padding: 0; display: grid; }
li { display: grid; grid-template-columns: 2rem 1fr; gap: 0.75rem; padding: 0.55rem 0; position: relative; }
.seq { color: var(--color-faint); font-size: var(--step--1); padding-top: 0.1rem; }
li:first-child .seq { color: var(--color-zec); }
.what { font-size: var(--step--1); color: var(--color-snow); }
.when { font-size: var(--step--1); color: var(--color-faint); }
</style>
