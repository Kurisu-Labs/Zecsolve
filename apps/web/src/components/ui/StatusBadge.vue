<script setup lang="ts">
import StatusGlyph from './StatusGlyph.vue'

defineProps<{
  label: string
  tone: 'ok' | 'warn' | 'fail' | 'unknown' | 'zec' | 'neutral'
  glyph?: 'open' | 'cracked' | 'empty' | 'info' | 'clock' | 'retry' | 'check' | 'dash' | 'lock'
  size?: 'sm' | 'md'
}>()
</script>

<template>
  <span class="badge" :class="[`tone-${tone}`, `size-${size ?? 'sm'}`]">
    <StatusGlyph v-if="glyph" :name="glyph" />
    <span>{{ label }}</span>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 999px;
  border: 1px solid currentColor;
  white-space: nowrap;
  font-weight: 500;
  line-height: 1;
}
.size-sm { padding: 0.3rem 0.6rem 0.3rem 0.45rem; font-size: var(--step--1); }
.size-md { padding: 0.45rem 0.8rem 0.45rem 0.6rem; font-size: var(--step-0); }
.tone-ok { color: var(--color-ok); }
.tone-warn { color: var(--color-warn); }
.tone-fail { color: var(--color-fail); }
.tone-unknown { color: var(--color-unknown); border-style: dashed; }
.tone-neutral { color: var(--color-mute); }
.tone-zec { color: var(--color-ink); background: var(--color-zec); border-color: var(--color-zec); }
</style>
