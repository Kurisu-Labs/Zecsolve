<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, idempotencyKey, request, type Contract } from '@/api/client'
const props = defineProps<{ id: string }>()
type Section = NonNullable<Contract['grantScope']['report_sections']>[number]
const sections: Section[] = ['case','invoice','claims','evidence','verifications','observations','evaluations','balances','decisions','events']
const selected = ref<Section[]>([])
const role = ref<'customer' | 'reviewer'>('customer')
const ttl = ref(24)
const exportAllowed = ref(false)
const evidence = ref<(Contract['evidenceStored'] | Contract['evidenceStoredV2'])[]>([])
const selectedEvidence = ref<string[]>([])
const grants = ref<Contract['grantList']['items']>([])
const code = ref<string | null>(null)
const notice = ref('')
const error = ref('')
const busy = ref(false)
const loading = ref(true)
async function load() {
  loading.value = true; error.value = ''
  try {
    grants.value = (await api.grants(props.id)).items
    const report = await api.report(props.id)
    evidence.value = await Promise.all(report.evidence.map(e => request<Contract['evidenceStored'] | Contract['evidenceStoredV2']>(`/api/cases/${encodeURIComponent(props.id)}/evidence/${encodeURIComponent(e.evidence_id)}`)))
  } catch (e) { error.value = e instanceof Error ? e.message : 'Unable to load access.' }
  finally { loading.value = false }
}
function shareable(e: Contract['evidenceStored'] | Contract['evidenceStoredV2']) {
  return e.schema_version === '2' && e.processing_authorized && e.share_with_reviewers
}
async function create() {
  if (busy.value) return
  busy.value = true; error.value = ''; code.value = null; notice.value = ''
  try {
    const scope: Contract['grantScope'] = { role: role.value, report_sections: role.value === 'reviewer' ? selected.value : [], evidence_ids: role.value === 'reviewer' ? selectedEvidence.value : [], allow_export: role.value === 'reviewer' && exportAllowed.value }
    const result = await api.grant(props.id, { scope, ttl_hours: ttl.value }, idempotencyKey())
    code.value = result.access_code
    notice.value = result.access_code ? 'Copy this code now and send it privately. It is displayed only once.' : 'This grant was already created, but its code cannot be recovered. Revoke it and create a new grant.'
    grants.value = (await api.grants(props.id)).items
  } catch (e) { error.value = e instanceof Error ? e.message : 'Unable to create access.' }
  finally { busy.value = false }
}
async function revoke(id: string) {
  busy.value = true; error.value = ''; code.value = null
  try { await api.revoke(props.id, id); grants.value = (await api.grants(props.id)).items; notice.value = 'Access revoked. Already downloaded copies cannot be recalled.' }
  catch (e) { error.value = e instanceof Error ? e.message : 'Unable to revoke access.' }
  finally { busy.value = false }
}
function selectCode(event: FocusEvent) { (event.target as HTMLInputElement).select() }
onMounted(load)
</script>
<template>
  <div class="shell workflow-page">
    <RouterLink :to="`/cases/${id}`">Back to case</RouterLink>
    <h1>Case access</h1>
    <p>Choose exactly what to share. Expiry and revocation stop future access; downloaded copies cannot be recalled.</p>
    <p v-if="loading" role="status">Loading access and evidence consent…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="notice" class="workflow-card" role="status"><p>{{ notice }}</p><label v-if="code">Private access code<input class="field mono" :value="code" readonly @focus="selectCode" /></label><button v-if="code" class="btn" @click="code = null">Hide code</button></section>
    <form class="workflow-card" @submit.prevent="create">
      <fieldset :disabled="busy || loading" class="workflow-fields">
        <legend>Create access</legend>
        <label>Role<select v-model="role" class="field"><option value="customer">Customer — submissions only</option><option value="reviewer">Reviewer — selected read access</option></select></label>
        <label>Expires after (hours, 1–168)<input v-model.number="ttl" type="number" min="1" max="168" step="1" class="field" required /></label>
        <template v-if="role === 'reviewer'">
          <p>Choose at least one report section. Invoice terms include recipient and memo; balances disclose approved totals; decisions include written reasons.</p>
          <label v-for="section in sections" :key="section" class="check"><input v-model="selected" type="checkbox" :value="section" /> {{ section }}</label>
          <h2>Original evidence access</h2>
          <p>Only evidence explicitly authorized for reviewer sharing can be selected. This also controls which evidence appears in selected report sections.</p>
          <p v-if="!evidence.length">No evidence submitted yet.</p>
          <label v-for="item in evidence" :key="item.evidence_id" class="check"><input v-model="selectedEvidence" type="checkbox" :value="item.evidence_id" :disabled="!shareable(item)" /> {{ item.evidence_id }} — {{ shareable(item) ? 'Sharing authorized' : 'No reviewer sharing consent' }}</label>
          <label class="check"><input v-model="exportAllowed" type="checkbox" /> Permit export of the selected scope when export is available.</label>
        </template>
      </fieldset>
      <button class="btn btn-primary" :disabled="busy || loading || (role === 'reviewer' && !selected.length)">{{ busy ? 'Saving…' : 'Create access code' }}</button>
    </form>
    <section class="workflow-card"><h2>Issued access</h2><p v-if="!grants.length">No access grants.</p>
      <article v-for="grant in grants" :key="grant.grant_id" class="workflow-card"><h3>{{ grant.scope.role }}</h3><p>{{ grant.grant_id }}</p><p>Expires {{ new Date(grant.expires_at).toLocaleString() }}. {{ grant.revoked_at ? 'Revoked' : Date.parse(grant.expires_at) <= Date.now() ? 'Expired' : 'Active' }}</p><p v-if="grant.scope.role === 'reviewer'">Sections: {{ grant.scope.report_sections?.join(', ') }}. Export: {{ grant.scope.allow_export ? 'permitted' : 'not permitted' }}.</p><button class="btn" :disabled="busy || !!grant.revoked_at" @click="revoke(grant.grant_id)">Revoke access</button></article>
    </section>
  </div>
</template>
