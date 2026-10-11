<script setup lang="ts">
import { RouterLink } from 'vue-router'
import LayersSection from '@/components/landing/LayersSection.vue'

// The journey is a real sequence (PRD §5), so it is numbered.
const steps = [
  { title: 'The merchant opens a case', body: 'From a frozen invoice snapshot: amount, receiver, reference. Later edits make a new snapshot.' },
  { title: 'The customer shares a receipt', body: 'Through a case link, after seeing exactly what the receipt discloses. No receipt is a valid answer too.' },
  { title: 'The verifier recovers one output', body: 'A pinned Rust verifier built on Glasspane binds the receipt to the raw transaction and returns amount, receiver and memo.' },
  { title: 'Rules compare it to the invoice', body: 'Receiver, reference, earlier allocations and chain status become findings. Nothing is credited yet.' },
  { title: 'A merchant decides, with a reason', body: 'Approval, allocation and the audit event commit together, checked against the case version they reviewed.' },
  { title: 'A reviewer reads the report', body: 'A replayable packet with hashes and provenance, without the customer’s keys or wallet.' },
]
</script>

<template>
  <div class="page">
    <section class="shell top">
      <h1>How zecsolve resolves a shielded payment.</h1>
      <p class="lede">
        Built for the moment a shielded payment and an invoice disagree. It uses voluntarily shared, output-specific receipts,
        never spending keys or wallet-wide viewing keys.
      </p>
      <ol class="steps">
        <li v-for="(s, i) in steps" :key="s.title">
          <span class="n mono">{{ i + 1 }}</span>
          <div>
            <h2>{{ s.title }}</h2>
            <p>{{ s.body }}</p>
          </div>
        </li>
      </ol>
      <RouterLink to="/cases/shortfall" class="btn btn-primary">Open the demo case</RouterLink>
    </section>
    <LayersSection />
    <section class="shell limits">
      <h2>What it does not do</h2>
      <ul>
        <li>It is not a wallet, gateway, checkout or custodian, and it never moves ZEC.</li>
        <li>It never asks for seed phrases, spending keys or wallet-wide viewing keys.</li>
        <li>A verified receipt is never credited automatically.</li>
        <li>It does not prove who paid. A receipt can be forwarded, so treat it as disclosed.</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.page { padding-top: 3rem; }
.top { display: grid; gap: 2rem; justify-items: start; }
h1 { font-size: var(--step-5); max-width: 16ch; }
.lede { color: var(--color-mute); font-size: var(--step-1); line-height: 1.45; max-width: 52ch; }
.steps { list-style: none; padding: 0; margin: 1rem 0; display: grid; gap: 0; width: 100%; max-width: 760px; border-top: 1px solid var(--color-line-strong); }
.steps li { display: grid; grid-template-columns: 3rem minmax(0, 1fr); gap: 1rem; padding: 1.25rem 0; border-bottom: 1px solid var(--color-line); }
.n { color: var(--color-zec); font-size: var(--step-1); }
.steps h2 { font-size: var(--step-1); margin-bottom: 0.35rem; }
.steps p { color: var(--color-mute); }
.limits { padding: 2rem 0; display: grid; gap: 1rem; }
.limits h2 { font-size: var(--step-3); }
.limits ul { display: grid; gap: 0.6rem; padding-left: 1.1rem; color: var(--color-mute); max-width: 60ch; }
</style>
