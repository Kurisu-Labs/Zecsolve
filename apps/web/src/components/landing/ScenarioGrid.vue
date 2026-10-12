<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { demoState } from '@/api/store'

const scenarios = computed(() =>
  demoState.demo.map((c) => ({ key: c.key, title: c.title, summary: c.summary })),
)
</script>

<template>
  <section class="scenarios shell" aria-labelledby="scenarios-title">
    <h2 id="scenarios-title">Try the cases a support desk actually gets.</h2>
    <p class="lede">
      Each one runs the real receipt from mainnet transaction 66167cd3…cfd0 against a synthetic invoice.
    </p>
    <ul class="list">
      <li v-for="s in scenarios" :key="s.key">
        <RouterLink :to="`/cases/${s.key}?demo=1`" class="row">
          <span class="title">{{ s.title }}</span>
          <span class="summary">{{ s.summary }}</span>
          <span class="open">Open case</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.scenarios {
  padding: 4rem 0;
  display: grid;
  gap: 1rem;
}
h2 {
  font-size: var(--step-4);
  max-width: 22ch;
}
.lede {
  color: var(--color-mute);
  margin-bottom: 1.5rem;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--color-line-strong);
}
.row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr) auto;
  gap: 1.5rem;
  align-items: baseline;
  padding: 1.4rem 0;
  border-bottom: 1px solid var(--color-line);
  text-decoration: none;
}
.title {
  font-size: var(--step-2);
  font-weight: 600;
  letter-spacing: -0.02em;
  transition: color var(--dur-fast) var(--ease-standard);
}
.summary {
  color: var(--color-mute);
}
.open {
  color: var(--color-faint);
  font-size: var(--step--1);
  transition: color var(--dur-fast) var(--ease-standard);
}
.row:hover .title,
.row:focus-visible .title {
  color: var(--color-zec);
}
.row:hover .open {
  color: var(--color-snow);
}
@media (max-width: 760px) {
  .row {
    grid-template-columns: 1fr;
    gap: 0.4rem;
  }
}
</style>
