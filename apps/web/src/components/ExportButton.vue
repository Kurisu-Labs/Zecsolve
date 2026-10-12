<script setup lang="ts">
import { ref } from 'vue'
import { request, type Contract } from '@/api/client'
const props = defineProps<{ id: string }>()
const busy = ref(false)
const error = ref('')
const notice = ref('')
async function download() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const packet = await request<Contract['casePacket']>(`/api/cases/${encodeURIComponent(props.id)}/export`)
    if (packet.schema_version !== 'case-packet-v1') throw new Error('Unsupported packet format')
    const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `zecsolve-packet-${props.id}.json`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    notice.value =
      packet.payload.replay_scope === 'LIMITED'
        ? `Scoped packet downloaded. Replay is limited: ${packet.payload.omissions.join('; ')}.`
        : 'Full-history packet downloaded. Replay verifies recorded inputs; it does not establish live chain inclusion or authenticate its author.'
  } catch {
    error.value = 'Export is unavailable or not permitted for this access. No packet was downloaded.'
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <div>
    <button class="btn" :disabled="busy" @click="download">
      {{ busy ? 'Preparing export…' : 'Download authorized packet' }}
    </button>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
  </div>
</template>
