<script setup lang="ts">
import type { Finding } from '@/api/types'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { findingView } from '@/lib/status'

defineProps<{ findings: Finding[]; rulesVersion: string }>()
</script>

<template>
  <section aria-labelledby="findings-title">
    <h2 id="findings-title" class="title">Findings <span class="version">rules {{ rulesVersion }}</span></h2>
    <ul class="list">
      <li v-for="f in findings" :key="f">
        <StatusBadge :label="findingView[f].label" :tone="findingView[f].tone" />
        <span class="help">{{ findingView[f].help }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.title { font-size: var(--step-1); margin-bottom: 0.75rem; display: flex; align-items: baseline; gap: 0.75rem; }
.version { font-size: var(--step--1); font-weight: 400; color: var(--color-faint); letter-spacing: 0; }
.list { display: grid; gap: 0.5rem; list-style: none; padding: 0; margin: 0; }
li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; padding: 0.6rem 0; border-bottom: 1px solid var(--color-line); }
li:last-child { border-bottom: 0; }
.help { color: var(--color-mute); font-size: var(--step--1); }
</style>
