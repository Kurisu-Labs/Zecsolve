<script setup lang="ts">
import { computed } from 'vue'
import type { CaseState } from '@/api/types'
import { caseStates } from '@/lib/status'

const props = defineProps<{ state: CaseState }>()
const steps = computed(() => {
  const closed = props.state === 'CLOSED_UNRESOLVED'
  const list = closed ? [...caseStates.slice(0, 3), { state: 'CLOSED_UNRESOLVED' as const, label: 'Closed unresolved' }] : caseStates
  const at = list.findIndex((s) => s.state === props.state)
  return list.map((s, i) => ({ ...s, done: i < at, current: i === at }))
})
</script>

<template>
  <ol class="stepper" aria-label="Case progress">
    <li v-for="s in steps" :key="s.state" :class="{ done: s.done, current: s.current }" :aria-current="s.current ? 'step' : undefined">
      <span class="pip" aria-hidden="true" />
      <span class="label">{{ s.label }}</span>
    </li>
  </ol>
</template>

<style scoped>
.stepper { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.5rem; }
li { display: grid; gap: 0.5rem; color: var(--color-faint); font-size: var(--step--1); }
.pip { height: 4px; border-radius: 2px; background: var(--color-line-strong); transition: background-color var(--dur-slow) var(--ease-standard); }
.done { color: var(--color-mute); }
.done .pip { background: var(--color-snow); }
.current { color: var(--color-snow); font-weight: 550; }
.current .pip { background: var(--color-zec); }
</style>
