<script setup lang="ts">
import { computed } from 'vue'
import { latestObservation } from '@/api/workflow'
import type { CaseReport } from '@/api/types'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { actionView, chainView, receiptView, shortHash } from '@/lib/status'

// The four layers of a case, side by side and never merged (PRD §0).
const props = defineProps<{ report: CaseReport }>()

const selected = computed(() =>
  props.report.verifications.find((v) => v.verification_id === props.report.selected_verification_id),
)
const receipt = computed(() => receiptView[selected.value?.result.receipt_state ?? 'NONE'])
const observation = computed(() => latestObservation(props.report))
const chain = computed(() =>
  observation.value?.source_kind === 'SIMULATED'
    ? {
        label: 'Simulated confirmation',
        detail: 'A test source supplied this observation. Live chain inclusion has not been checked.',
        tone: 'warn' as const,
        glyph: 'info' as const,
      }
    : chainView[observation.value?.state ?? 'UNAVAILABLE'],
)
const claim = computed(() => props.report.claims[0])
const decision = computed(() => {
  const list = props.report.decisions ?? []
  return list[list.length - 1]
})
</script>

<template>
  <section class="tiles" aria-label="Case evidence by layer">
    <article class="tile">
      <h3>Customer claim</h3>
      <StatusBadge
        :label="claim ? 'Claim recorded' : 'No claim'"
        :tone="claim ? 'neutral' : 'unknown'"
        :glyph="claim ? 'info' : 'empty'"
      />
      <p v-if="claim?.note" class="quote">“{{ claim.note }}”</p>
      <p v-if="claim?.reported_txid" class="meta">
        Reported tx <span class="mono">{{ shortHash(claim.reported_txid) }}</span>
      </p>
      <p class="scope">What someone says happened. Proves nothing alone.</p>
    </article>

    <article class="tile">
      <h3>Receipt</h3>
      <StatusBadge :label="receipt.label" :tone="receipt.tone" :glyph="receipt.glyph" />
      <p class="detail">{{ receipt.detail }}</p>
      <p v-if="selected" class="meta">
        Reason <span class="mono">{{ selected.result.reason_code }}</span>
      </p>
      <p class="scope">Proves one output can be recovered. Not who paid, not chain inclusion.</p>
    </article>

    <article class="tile">
      <h3>Chain</h3>
      <StatusBadge :label="chain.label" :tone="chain.tone" :glyph="chain.glyph" />
      <p class="detail">{{ chain.detail }}</p>
      <p v-if="observation" class="meta">{{ observation.source }}</p>
      <p v-if="report.chain_review?.length" role="alert">
        An approved payment needs chain review. Its historical credit has not been reversed.
      </p>
      <p v-if="observation" class="meta">
        {{ observation.observed_at }} · {{ observation.confirmations ?? 'Unknown' }} confirmations
      </p>
      <p class="scope">What a named source reported, and when. Not the business decision.</p>
    </article>

    <article class="tile" :class="{ decided: decision }">
      <h3>Merchant decision</h3>
      <StatusBadge
        v-if="decision"
        :label="actionView[decision.action].done"
        :tone="decision.action === 'APPROVE_OUTPUT' ? 'zec' : 'neutral'"
        glyph="lock"
      />
      <StatusBadge
        v-else
        :label="report.balances.eligible_for_credit ? 'Ready to decide' : 'No decision yet'"
        :tone="report.balances.eligible_for_credit ? 'ok' : 'unknown'"
        :glyph="report.balances.eligible_for_credit ? 'check' : 'empty'"
      />
      <p v-if="decision" class="quote">“{{ decision.reason }}”</p>
      <p class="scope">An authorised call with a reason. Not a cryptographic guarantee.</p>
    </article>
  </section>
</template>

<style scoped>
.tiles {
  display: grid;
  gap: 1px;
  background: var(--color-line);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  overflow: hidden;
  grid-template-columns: minmax(0, 1fr);
}
@media (min-width: 560px) {
  .tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 1100px) {
  .tiles {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.tile {
  background: var(--color-ink-raised);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  align-items: flex-start;
}
.tile.decided {
  background: color-mix(in oklab, var(--color-zec) 5%, var(--color-ink-raised));
}
h3 {
  font-size: var(--step-0);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.detail {
  color: var(--color-snow);
  font-size: var(--step--1);
}
.quote {
  color: var(--color-snow);
  font-size: var(--step--1);
}
.meta {
  color: var(--color-mute);
  font-size: var(--step--1);
  overflow-wrap: anywhere;
}
.scope {
  margin-top: auto;
  padding-top: 0.5rem;
  color: var(--color-faint);
  font-size: var(--step--1);
}
</style>
