<script setup lang="ts">
import { session } from '@/api/session'
import SubmissionForm from '@/components/SubmissionForm.vue'
import DemoSubmissionPage from './DemoSubmissionPage.vue'
defineProps<{ id: string }>()
</script>
<template>
  <DemoSubmissionPage v-if="session.mode === 'demo'" :id="id" /><SubmissionForm v-else :key="id" :id="id" />
</template>
