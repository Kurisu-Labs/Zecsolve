<script setup lang="ts">
import { computed } from 'vue'
import { formatZat, formatZec } from '@/lib/money'

const props = defineProps<{ zat: number; size?: 'sm' | 'md' | 'lg'; emphasis?: boolean }>()
const zat = computed(() => formatZat(props.zat))
const zec = computed(() => formatZec(props.zat))
</script>

<template>
  <span class="money" :class="[`size-${size ?? 'md'}`, { emphasis }]">
    <span class="zat mono">{{ zat }}<span class="unit"> zat</span></span>
    <span class="zec mono">{{ zec }} ZEC</span>
  </span>
</template>

<style scoped>
.money { display: inline-flex; flex-direction: column; gap: 0.15rem; white-space: nowrap; }
.zat { color: var(--color-snow); letter-spacing: -0.01em; }
.unit { color: var(--color-mute); font-size: 0.7em; }
.zec { color: var(--color-mute); font-size: var(--step--1); }
.size-sm .zat { font-size: var(--step-0); }
.size-md .zat { font-size: var(--step-1); }
.size-lg .zat { font-size: var(--step-3); font-weight: 500; }
.emphasis .zat { color: var(--color-zec); }
</style>
