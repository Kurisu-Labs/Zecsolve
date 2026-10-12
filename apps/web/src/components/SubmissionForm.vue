<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, idempotencyKey, type Contract } from '@/api/client'
import { session } from '@/api/session'
const props = defineProps<{ id: string }>()
const kind = ref<'evidence' | 'claim'>('evidence')
const receipt = ref('')
const raw = ref('')
const receiptPresent = ref(false)
const rawPresent = ref(false)
const note = ref('')
const txid = ref('')
const consent = ref(false)
const sharing = ref(false)
const busy = ref(false)
const error = ref('')
const acknowledgement = ref<Contract['submissionAcknowledgement'] | null>(null)
const merchant = computed(() => session.info?.access.role === 'merchant')
function resetConsent() {
  consent.value = false
  sharing.value = false
}
async function readFile(event: Event, target: 'receipt' | 'raw') {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const limit = target === 'receipt' ? 16384 : 4000002
  if (file.size > limit) {
    error.value = `File exceeds ${limit.toLocaleString()} bytes.`
    return
  }
  const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true })
  try {
    const value = text.decode(await file.arrayBuffer())
    if (target === 'receipt') {
      receipt.value = value
      receiptPresent.value = true
    } else {
      raw.value = value
      rawPresent.value = true
    }
  } catch {
    error.value = 'The file must contain UTF-8 text.'
  }
}
async function submit() {
  if (busy.value || !consent.value) return
  busy.value = true
  error.value = ''
  try {
    if (kind.value === 'claim') {
      if (!note.value.trim() && !txid.value) throw new Error('Provide a note or transaction ID.')
      if (txid.value && !/^[0-9a-f]{64}$/.test(txid.value))
        throw new Error('Transaction ID must be 64 lowercase hexadecimal characters.')
      if (new TextEncoder().encode(note.value).length > 4096)
        throw new Error('Note exceeds 4,096 UTF-8 bytes.')
      acknowledgement.value = await api.claim(
        props.id,
        {
          reported_txid: txid.value || null,
          note: note.value || null,
          disclosure_version: 'claim-disclosure-v1',
          processing_authorized: true,
          share_with_reviewers: sharing.value,
        },
        idempotencyKey(),
      )
    } else {
      if (
        new TextEncoder().encode(receipt.value).length > 16384 ||
        new TextEncoder().encode(raw.value).length > 4000002
      )
        throw new Error('Evidence exceeds the allowed size.')
      acknowledgement.value = await api.evidence(
        props.id,
        {
          receipt_json: receiptPresent.value ? receipt.value : null,
          raw_tx_hex: rawPresent.value ? raw.value : null,
          source: merchant.value ? 'Merchant submission' : 'Customer submission',
          source_kind: merchant.value ? 'merchant_submission' : 'customer_submission',
          disclosure_version: 'evidence-disclosure-v2',
          processing_authorized: true,
          share_with_reviewers: sharing.value,
          claim_id: null,
        },
        idempotencyKey(),
      )
    }
    receipt.value = ''
    raw.value = ''
    note.value = ''
    txid.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Submission failed. Retry the same form.'
  } finally {
    busy.value = false
  }
}
function another() {
  acknowledgement.value = null
  consent.value = false
  sharing.value = false
  receiptPresent.value = false
  rawPresent.value = false
}
</script>
<template>
  <div class="shell workflow-page">
    <RouterLink v-if="merchant" :to="`/cases/${id}`">Back to case</RouterLink>
    <h1>{{ merchant ? 'Submit case evidence' : 'Share payment details' }}</h1>
    <p>Your submission goes to the merchant for review. It does not verify payment or credit an invoice.</p>
    <section v-if="acknowledgement" class="workflow-card" role="status">
      <h2>Submission accepted</h2>
      <p>
        {{ acknowledgement.operation }} received {{ new Date(acknowledgement.accepted_at).toLocaleString() }}.
      </p>
      <p class="mono">Reference: {{ acknowledgement.submission_id }}</p>
      <p>Keep this reference. The merchant will review your submission.</p>
      <button class="btn" @click="another">Submit another item</button>
    </section>
    <form v-else class="workflow-card" @submit.prevent="submit">
      <fieldset :disabled="busy" class="workflow-fields">
        <legend>Submission details</legend>
        <label
          >What are you submitting?<select v-model="kind" class="field" @change="resetConsent">
            <option value="evidence">Receipt / raw transaction</option>
            <option value="claim">Transaction ID / note</option>
          </select></label
        >
        <template v-if="kind === 'evidence'">
          <label class="check"><input v-model="receiptPresent" type="checkbox" /> Include receipt JSON</label>
          <template v-if="receiptPresent"
            ><label
              >Receipt file<input
                type="file"
                accept=".json,.txt,application/json,text/plain"
                @change="readFile($event, 'receipt')" /></label
            ><label
              >Receipt contents (maximum 16,384 UTF-8 bytes)<textarea
                v-model="receipt"
                class="field mono"
                rows="7"
                spellcheck="false"
              /></label
          ></template>
          <label class="check"><input v-model="rawPresent" type="checkbox" /> Include raw transaction</label>
          <template v-if="rawPresent"
            ><label
              >Transaction file<input
                type="file"
                accept=".hex,.txt,text/plain"
                @change="readFile($event, 'raw')" /></label
            ><label
              >Raw transaction hex<textarea
                v-model="raw"
                class="field mono"
                rows="4"
                spellcheck="false"
              /></label
          ></template>
          <p v-if="!receiptPresent || !rawPresent">
            Missing components remain explicitly missing. You can submit without them.
          </p>
          <p>
            I am authorized to submit these selected payment details for processing in this merchant case. The
            merchant can read them. A receipt can disclose its selected amount, recipient and memo. Reviewer
            sharing is a separate choice and is off by default. Copies already shared cannot be recalled.
            Submission does not prove payment.
          </p>
        </template>
        <template v-else>
          <label
            >Reported transaction ID (optional)<input v-model="txid" class="field mono" maxlength="64"
          /></label>
          <label
            >Note (optional, maximum 4,096 UTF-8 bytes)<textarea v-model="note" class="field" rows="5" />
          </label>
          <p>
            I am authorized to submit this transaction ID and note for processing in this merchant case. The
            merchant can read them. Reviewer sharing is a separate choice and is off by default. Copies
            already shared cannot be recalled. My claim does not prove payment.
          </p>
        </template>
        <label class="check"
          ><input v-model="consent" type="checkbox" required /> I authorize this processing.</label
        >
        <label class="check"
          ><input v-model="sharing" type="checkbox" /> Also allow sharing this submission with selected
          reviewers (optional).</label
        >
        <p v-if="merchant">
          This records your authorization as the merchant, not consent obtained directly from a customer.
        </p>
      </fieldset>
      <p v-if="error" class="error" role="alert">
        {{ error }} Your unchanged submission can be retried safely.
      </p>
      <button class="btn btn-primary" :disabled="busy || !consent">
        {{ busy ? 'Submitting…' : 'Submit for review' }}
      </button>
    </form>
  </div>
</template>
