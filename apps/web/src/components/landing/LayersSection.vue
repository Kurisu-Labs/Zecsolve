<script setup lang="ts">
// The PRD's four layers of information. Parallel items, so a grid, not a sequence.
const layers = [
  {
    name: 'Customer claim',
    shows: 'What the customer says happened, and which transaction they think it was.',
    not: 'That any payment happened.',
  },
  {
    name: 'Receipt',
    shows: 'That one specific output decrypts from the supplied transaction: its amount, receiver and memo.',
    not: 'Who paid, or that the transaction is on chain.',
  },
  {
    name: 'Chain observation',
    shows: 'What a named chain source reported, and when it reported it.',
    not: 'Whether the merchant should credit the invoice.',
  },
  {
    name: 'Merchant decision',
    shows: 'An authorised choice with a written reason, committed with the balance change.',
    not: 'A cryptographic guarantee that the business facts are true.',
  },
]
</script>

<template>
  <section class="layers shell" aria-labelledby="layers-title">
    <div class="intro">
      <h2 id="layers-title">Four facts, never merged into one green tick.</h2>
      <p>
        Support tools tend to collapse everything into “paid” or “not paid”. zecsolve keeps each kind of evidence on its own
        line, so a valid receipt with no chain confirmation stays exactly that.
      </p>
    </div>
    <div class="grid">
      <article v-for="layer in layers" :key="layer.name" class="layer">
        <h3>{{ layer.name }}</h3>
        <dl>
          <dt>Shows</dt>
          <dd>{{ layer.shows }}</dd>
          <dt>Does not show</dt>
          <dd class="not">{{ layer.not }}</dd>
        </dl>
      </article>
    </div>
  </section>
</template>

<style scoped>
.layers { padding: 8rem 0 4rem; display: grid; gap: 3rem; }
.intro { display: grid; gap: 1rem; max-width: 46rem; }
h2 { font-size: var(--step-4); }
.intro p { color: var(--color-mute); font-size: var(--step-1); line-height: 1.45; max-width: 52ch; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); border-top: 1px solid var(--color-line-strong); }
.layer { padding: 1.5rem 1.5rem 1.5rem 0; display: grid; gap: 1rem; align-content: start; }
.layer + .layer { padding-left: 1.5rem; border-left: 1px solid var(--color-line); }
@media (max-width: 980px) { .layer + .layer { border-left: 0; padding-left: 0; border-top: 1px solid var(--color-line); } }
h3 { font-size: var(--step-1); }
dl { display: grid; gap: 0.35rem; }
dt { color: var(--color-faint); font-size: var(--step--1); }
dt:not(:first-child) { margin-top: 0.6rem; }
dd { color: var(--color-snow); }
dd.not { color: var(--color-mute); }
</style>
