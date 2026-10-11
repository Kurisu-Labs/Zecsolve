<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="shell page">
    <h1>Nothing here</h1>
    <p>This address does not open a page. It may have been a case link from a different deployment.</p>
    <RouterLink to="/cases" class="btn btn-primary">Go to cases</RouterLink>
  </div>
</template>

<style scoped>
.page { padding: 6rem 0; display: grid; gap: 1rem; justify-items: start; }
h1 { font-size: var(--step-5); }
p { color: var(--color-mute); max-width: 50ch; }
</style>
