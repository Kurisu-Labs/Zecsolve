<script setup lang="ts">
// 16px line glyphs. Every status pairs one of these with text; colour is never alone.
defineProps<{ name: 'open' | 'cracked' | 'empty' | 'info' | 'clock' | 'retry' | 'check' | 'dash' | 'lock' }>()
</script>

<template>
  <svg class="glyph" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <template v-if="name === 'open'">
      <path d="M3 8.5a5 5 0 0 1 9.6-2" />
      <path d="M8 13.5a5 5 0 0 0 5-5" stroke-dasharray="1.5 2" />
      <path d="M5.5 8.5 7.3 10.3 10.8 6.5" />
    </template>
    <template v-else-if="name === 'cracked'">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 2.5 6.6 6.4 9.2 8.4 7.4 13.5" />
    </template>
    <template v-else-if="name === 'empty'">
      <circle cx="8" cy="8" r="5.5" stroke-dasharray="2 2.2" />
    </template>
    <template v-else-if="name === 'info'">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 7.3v3.4M8 5.2v.1" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 5v3.2l2 1.3" />
    </template>
    <template v-else-if="name === 'retry'">
      <path d="M12.8 8A4.8 4.8 0 1 1 11.4 4.6" />
      <path d="M12.6 2.6v2.6H10" />
    </template>
    <template v-else-if="name === 'check'">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M5.6 8.2 7.3 9.9 10.5 6.4" />
    </template>
    <template v-else-if="name === 'lock'">
      <rect x="3.5" y="7" width="9" height="6.5" rx="1.5" />
      <path d="M5.5 7V5.3a2.5 2.5 0 0 1 5 0V7" />
    </template>
    <template v-else>
      <path d="M4.5 8h7" />
    </template>
  </svg>
</template>

<style scoped>
.glyph { flex: none; }
</style>
