<script setup lang="ts">
import { ref } from 'vue'
import { request } from '@/api/client'
const props = defineProps<{ id: string }>()
const busy = ref(false)
const error = ref('')
async function download() {
  busy.value = true; error.value = ''
  try {
    const packet = await request<unknown>(`/api/cases/${encodeURIComponent(props.id)}/export`)
    const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a'); a.href = url; a.download = `zecsolve-packet-${props.id}.json`; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { error.value = 'Export is unavailable or not permitted for this access. No packet was downloaded.' }
  finally { busy.value = false }
}
</script>
<template><div><button class="btn" :disabled="busy" @click="download">{{ busy ? 'Preparing export…' : 'Download authorized packet' }}</button><p v-if="error" role="alert">{{ error }}</p></div></template>
