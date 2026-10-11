<script setup lang="ts">
import mark from '@/assets/zecsolve-mark.png'
import wordmark from '@/assets/zecsolve-wordmark.png'

defineProps<{ compact?: boolean }>()
</script>

<template>
  <span class="brand" :class="{ compact }">
    <img :src="mark" alt="" width="32" height="29" class="mark" />
    <img v-if="!compact" :src="wordmark" alt="zecsolve" width="94" height="18" class="word" />
    <span v-else class="sr-only">zecsolve</span>
  </span>
</template>

<style scoped>
.brand { display: inline-flex; align-items: center; gap: 0.55rem; }
.mark { width: 30px; height: auto; }
.word { width: 92px; height: auto; margin-top: 2px; }
</style>
