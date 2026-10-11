<script setup lang="ts">
import { computed, ref } from 'vue'
import { shortHash } from '@/lib/status'

const props = defineProps<{ value: string; head?: number; tail?: number; label?: string }>()
const short = computed(() => shortHash(props.value, props.head, props.tail))
const copied = ref(false)
let timer = 0

async function copy() {
  try {
    await navigator.clipboard.writeText(props.value)
    copied.value = true
    clearTimeout(timer)
    timer = window.setTimeout(() => (copied.value = false), 1400)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <span class="hash">
    <code class="mono" :title="value">{{ short }}</code>
    <button type="button" class="copy" :aria-label="`Copy ${label ?? 'value'}`" @click="copy">
      <svg v-if="!copied" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" />
        <path d="M10.5 3.5v-.5A1.5 1.5 0 0 0 9 1.5H4A1.5 1.5 0 0 0 2.5 3v5A1.5 1.5 0 0 0 4 9.5h.5" />
      </svg>
      <svg v-else viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
        <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
      </svg>
    </button>
    <span class="sr-only" aria-live="polite">{{ copied ? 'Copied' : '' }}</span>
  </span>
</template>

<style scoped>
.hash { display: inline-flex; align-items: center; gap: 0.35rem; min-width: 0; }
code { font-size: 0.92em; color: var(--color-snow); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.copy {
  display: inline-grid; place-items: center;
  width: 28px; height: 28px; border-radius: 6px;
  border: 0; background: transparent; color: var(--color-mute); cursor: pointer;
  transition: color var(--dur-fast) var(--ease-standard), background-color var(--dur-fast) var(--ease-standard);
}
.copy:hover { color: var(--color-snow); background: var(--color-line); }
</style>
