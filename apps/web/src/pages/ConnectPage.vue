<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, readCredential } from '@/api/client'
import { rememberLiveCase, session, setLiveCredential } from '@/api/store'

const router = useRouter()
const token = ref(readCredential() ?? '')
const caseId = ref('')
const status = ref<string | null>(null)
const error = ref<string | null>(null)
const busy = ref(false)

async function connect() {
  busy.value = true
  error.value = null
  status.value = null
  setLiveCredential(token.value.trim() || null)
  try {
    const me = await api.whoami()
    status.value = `Connected as merchant ${me.merchant_id.slice(0, 8)}.`
  } catch (e) {
    setLiveCredential(null)
    error.value = `The API did not accept this credential: ${e instanceof Error ? e.message : String(e)}`
  } finally {
    busy.value = false
  }
}

function useDemo() {
  setLiveCredential(null)
  token.value = ''
  status.value = 'Using demo data.'
}

function openCase() {
  const id = caseId.value.trim()
  if (!id) return
  rememberLiveCase(id)
  void router.push(`/cases/${id}`)
}
</script>

<template>
  <div class="shell page">
    <h1>Connect</h1>
    <p class="lede">
      The app runs on demo data until you add a merchant credential. Credentials are issued by the operator CLI
      (<code class="mono">python -m zecsolve.auth.cli issue-credential</code>) and stay in this browser only.
    </p>

    <section class="card">
      <h2>Data source</h2>
      <p class="now">Now using <strong>{{ session.mode === 'demo' ? 'demo data' : 'the live API' }}</strong>.</p>
      <form class="form" @submit.prevent="connect">
        <label for="token" class="label">Merchant credential</label>
        <input id="token" v-model="token" class="field mono" type="password" autocomplete="off" placeholder="Paste the bearer credential" />
        <div class="row">
          <button type="submit" class="btn btn-primary" :disabled="busy || !token.trim()">{{ busy ? 'Checking…' : 'Use live API' }}</button>
          <button type="button" class="btn btn-quiet" @click="useDemo">Use demo data</button>
        </div>
      </form>
      <p v-if="status" class="ok" role="status">{{ status }}</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </section>

    <section v-if="session.mode === 'live'" class="card">
      <h2>Open a case by id</h2>
      <p class="muted">The API has no list route yet. Cases you open here are remembered in this browser.</p>
      <form class="row" @submit.prevent="openCase">
        <input v-model="caseId" class="field mono grow" placeholder="Case UUID" aria-label="Case id" />
        <button type="submit" class="btn">Open case</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.page { padding: 3rem 0; display: grid; gap: 1.5rem; max-width: 720px; }
h1 { font-size: var(--step-4); }
.lede { color: var(--color-mute); }
code { color: var(--color-snow); font-size: 0.9em; }
.card { border: 1px solid var(--color-line); border-radius: var(--radius-lg); padding: 1.25rem; display: grid; gap: 0.9rem; }
h2 { font-size: var(--step-1); }
.form { display: grid; gap: 0.6rem; }
.label { font-size: var(--step--1); color: var(--color-mute); }
.row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.grow { flex: 1 1 260px; }
.now strong { color: var(--color-zec); font-weight: 550; }
.muted { color: var(--color-mute); font-size: var(--step--1); }
.ok { color: var(--color-ok); }
.error { color: var(--color-fail); }
</style>
