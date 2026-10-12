<script setup lang="ts">
defineProps<{ value: unknown }>()
function label(key: string) {
  return key.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase())
}
function entries(value: object) {
  return Object.entries(value)
}
</script>
<template>
  <p v-if="value === null || value === undefined">Not recorded</p>
  <ol v-else-if="Array.isArray(value) && value.length" class="records">
    <li v-for="(item, index) in value" :key="index"><ReportFields :value="item" /></li>
  </ol>
  <p v-else-if="Array.isArray(value)">No disclosed records</p>
  <dl v-else-if="typeof value === 'object'" class="fields">
    <div v-for="[key, item] in entries(value)" :key="key">
      <dt>{{ label(key) }}</dt>
      <dd><ReportFields :value="item" /></dd>
    </div>
  </dl>
  <span v-else class="text">{{ value }}</span>
</template>
<style scoped>
.fields > div {
  display: grid;
  grid-template-columns: minmax(100px, 1fr) minmax(0, 3fr);
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-line);
}
dt {
  color: var(--color-mute);
}
dd {
  min-width: 0;
}
.text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.records {
  padding-left: 1rem;
  display: grid;
  gap: 1rem;
}
@media (max-width: 560px) {
  .fields > div {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}
</style>
