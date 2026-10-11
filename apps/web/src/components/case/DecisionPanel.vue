<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { cases, session } from '@/api/store'
import type { CaseReport, ResolveAction } from '@/api/types'
import { formatZat } from '@/lib/money'
import { actionView } from '@/lib/status'

const props = defineProps<{ report: CaseReport }>()
const emit = defineEmits<{ changed: [message: string] }>()

const actions: ResolveAction[] = ['APPROVE_OUTPUT', 'REQUEST_EVIDENCE', 'REJECT_EVIDENCE', 'CLOSE_UNRESOLVED']

const selected = computed(() =>
  props.report.verifications.find((v) => v.verification_id === props.report.selected_verification_id),
)
const observation = computed(() =>
  [...props.report.chain_observations].reverse().find((o) => o.verification_id === selected.value?.verification_id),
)
const closed = computed(() => props.report.case.state === 'RESOLVED' || props.report.case.state === 'CLOSED_UNRESOLVED')
const eligible = computed(() => props.report.balances.eligible_for_credit === true)
const canRefreshChain = computed(
  () => selected.value?.result.receipt_state === 'VALID' && observation.value?.state !== 'CONFIRMED' && !closed.value,
)

const action = ref<ResolveAction>(eligible.value ? 'APPROVE_OUTPUT' : 'REQUEST_EVIDENCE')
const reason = ref('')
const confirming = ref(false)
const busy = ref<'chain' | 'decide' | null>(null)
const error = ref<string | null>(null)

watch(eligible, (now) => {
  if (!now && action.value === 'APPROVE_OUTPUT') action.value = 'REQUEST_EVIDENCE'
})

function disabledReason(a: ResolveAction): string | null {
  if (a === 'APPROVE_OUTPUT' && !eligible.value) {
    if (!selected.value || selected.value.result.receipt_state !== 'VALID') return 'Needs a recovered output.'
    if (props.report.balances.findings.includes('DUPLICATE_CLAIM')) return 'This output already settled another invoice.'
    if (props.report.balances.findings.includes('ALREADY_ALLOCATED')) return 'Already credited to this invoice.'
    if (observation.value?.state !== 'CONFIRMED') return 'Waits for a trusted chain confirmation.'
    return 'Findings block credit.'
  }
  if ((a === 'APPROVE_OUTPUT' || a === 'REJECT_EVIDENCE') && !selected.value) return 'Needs a verification attempt.'
  return null
}

const canSubmit = computed(() => !closed.value && reason.value.trim().length >= 4 && !disabledReason(action.value))

async function refreshChain() {
  if (!selected.value) return
  busy.value = 'chain'
  error.value = null
  try {
    await cases.refreshChain(props.report.case.case_id, selected.value.verification_id)
    emit('changed', 'Chain observation recorded.')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = null
  }
}

async function decide() {
  busy.value = 'decide'
  error.value = null
  try {
    await cases.resolve(props.report.case.case_id, {
      action: action.value,
      verification_id: selected.value?.verification_id ?? null,
      expected_case_version: props.report.case.version,
      reason: reason.value.trim(),
    })
    confirming.value = false
    reason.value = ''
    emit('changed', `${actionView[action.value].done}.`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section class="panel" aria-labelledby="decision-title">
    <h2 id="decision-title" class="title">Decision</h2>

    <p v-if="closed" class="closed">
      This case is {{ report.case.state === 'RESOLVED' ? 'resolved' : 'closed' }}. Decisions are append-only; open a new
      case to revisit it.
    </p>

    <template v-else>
      <div v-if="canRefreshChain" class="chain">
        <p>
          The receipt is valid, but nothing has confirmed the transaction on chain. Approval stays blocked until a trusted
          source does.
        </p>
        <button type="button" class="btn" :disabled="busy !== null" @click="refreshChain">
          {{ busy === 'chain' ? 'Checking chain…' : 'Check chain now' }}
        </button>
        <p v-if="session.mode === 'demo'" class="demo-note">Demo mode records a simulated confirmation, labelled as such.</p>
      </div>

      <form class="form" @submit.prevent="confirming = true">
        <fieldset>
          <legend class="legend">Action</legend>
          <label v-for="a in actions" :key="a" class="option" :class="{ off: !!disabledReason(a), on: action === a }">
            <input v-model="action" type="radio" name="action" :value="a" :disabled="!!disabledReason(a)" />
            <span class="option-text">
              <span class="option-label">{{ actionView[a].label }}</span>
              <span class="option-help">{{ disabledReason(a) ?? actionView[a].help }}</span>
            </span>
          </label>
        </fieldset>

        <label class="reason">
          <span class="legend">Reason, kept in the audit trail</span>
          <textarea
            v-model="reason"
            class="field"
            rows="3"
            maxlength="2000"
            placeholder="For example: customer paid half; asked for a second receipt for the rest."
            required
          />
        </label>

        <div v-if="!confirming" class="actions">
          <button type="submit" class="btn btn-primary" :disabled="!canSubmit">Review decision</button>
          <span class="version">Case version {{ report.case.version }}</span>
        </div>

        <div v-else class="confirm" role="group" aria-label="Confirm decision">
          <p>
            <strong>{{ actionView[action].label }}</strong>
            <template v-if="action === 'APPROVE_OUTPUT'">
              credits <strong class="mono">{{ formatZat(report.balances.candidate_zat) }} zat</strong> to this invoice.
            </template>
            <template v-else> records your reason and changes no balance.</template>
            Recorded against case version {{ report.case.version }}; if the case changes first, nothing is saved.
          </p>
          <div class="actions">
            <button type="button" class="btn btn-primary" :disabled="busy !== null" @click="decide">
              {{ busy === 'decide' ? 'Recording…' : 'Record decision' }}
            </button>
            <button type="button" class="btn btn-quiet" :disabled="busy !== null" @click="confirming = false">Back</button>
          </div>
        </div>
      </form>
    </template>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.panel {
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  background: var(--color-ink-raised);
  display: grid;
  gap: 1rem;
}
.title { font-size: var(--step-1); }
.closed { color: var(--color-mute); }
.chain {
  display: grid; gap: 0.75rem; justify-items: start;
  padding: 1rem; border-radius: var(--radius-md); border: 1px dashed var(--color-unknown);
  font-size: var(--step--1);
}
.demo-note { color: var(--color-faint); }
.form { display: grid; gap: 1rem; }
fieldset { border: 0; padding: 0; margin: 0; display: grid; gap: 0.4rem; }
.legend { display: block; color: var(--color-mute); font-size: var(--step--1); margin-bottom: 0.35rem; }
.option {
  display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.7rem 0.8rem;
  border-radius: var(--radius-md); border: 1px solid var(--color-line); cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-standard), background-color var(--dur-fast) var(--ease-standard);
}
.option:hover { border-color: var(--color-line-strong); }
.option.on { border-color: var(--color-zec); background: color-mix(in oklab, var(--color-zec) 6%, transparent); }
.option.off { cursor: not-allowed; opacity: 0.55; }
.option input { margin-top: 0.25rem; accent-color: var(--color-zec); }
.option-text { display: grid; gap: 0.1rem; }
.option-label { font-weight: 550; }
.option-help { color: var(--color-mute); font-size: var(--step--1); }
.reason textarea { resize: vertical; min-height: 5.5rem; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
.version { color: var(--color-faint); font-size: var(--step--1); }
.confirm {
  display: grid; gap: 0.9rem; padding: 1rem; border-radius: var(--radius-md);
  border: 1px solid var(--color-zec); animation: rise var(--dur-base) var(--ease-enter);
}
.confirm p { font-size: var(--step--1); }
.error { color: var(--color-fail); font-size: var(--step--1); }
@keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
</style>
