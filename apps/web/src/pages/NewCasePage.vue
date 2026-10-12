<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, idempotencyKey } from '@/api/client'
import { parseZec } from '@/lib/money'
const router = useRouter()
const amount = ref('')
const pool = ref<'orchard' | 'sapling'>('orchard')
const receiver = ref('')
const memo = ref('')
const expires = ref('')
const invoiceId = ref('')
const busy = ref(false)
const error = ref('')
const invoiceKey = idempotencyKey()
const caseKey = idempotencyKey()
async function create() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    if (!invoiceId.value) {
      const zat = parseZec(amount.value)
      if (zat === null || zat <= 0 || zat > 2_100_000_000_000_000) throw new Error('Enter a positive ZEC amount with at most eight decimal places (maximum 21 million ZEC).')
      const invoice = await api.invoice({ expected_zat: zat, network: 'mainnet', pool: pool.value, receiver_address: receiver.value.trim(), expected_memo: memo.value || null, expires_at: expires.value ? new Date(expires.value).toISOString() : null }, invoiceKey)
      invoiceId.value = invoice.invoice_id
    }
    const opened = await api.openCase(invoiceId.value, caseKey)
    await router.push(`/cases/${opened.case_id}`)
  } catch (e) { error.value = e instanceof Error ? e.message : 'Could not create case.' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="shell workflow-page">
    <RouterLink to="/cases">All cases</RouterLink>
    <h1>Create invoice and case</h1>
    <p>Invoice terms are fixed once saved. Credit requires a separate merchant decision after verification.</p>
    <form class="workflow-card" @submit.prevent="create">
      <fieldset :disabled="busy || !!invoiceId" class="workflow-fields">
        <label>Expected amount (ZEC)<input v-model="amount" class="field" inputmode="decimal" required placeholder="0.002" /></label>
        <label>Pool<select v-model="pool" class="field"><option value="orchard">Orchard</option><option value="sapling">Sapling</option></select></label>
        <label>Mainnet receiver address<textarea v-model="receiver" class="field mono" required maxlength="1024" rows="3" /></label>
        <label>Expected memo (optional)<textarea v-model="memo" class="field" maxlength="512" rows="3" /></label>
        <label>Invoice expiry (optional, your local time)<input v-model="expires" class="field" type="datetime-local" /></label>
      </fieldset>
      <p v-if="invoiceId" role="status">Invoice {{ invoiceId }} was saved. Retry opening its case without creating another invoice.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="btn btn-primary" :disabled="busy">{{ busy ? 'Saving…' : invoiceId ? 'Open case for saved invoice' : 'Create invoice and open case' }}</button>
    </form>
  </div>
</template>
