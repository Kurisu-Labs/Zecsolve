<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { connect, logout, session, useDemo } from '@/api/session'
import { homeFor } from '@/api/access'

const router = useRouter()
const token = ref('')
const error = ref('')
const busy = ref(false)
// A pasted link may carry a code in its fragment. Remove it before any exchange.
const fragment = new URLSearchParams(window.location.hash.slice(1))
if (fragment.has('code')) {
  token.value = fragment.get('code') ?? ''
  window.history.replaceState(null, '', window.location.pathname)
}
async function signIn() {
  busy.value = true; error.value = ''
  const code = token.value.trim(); token.value = ''
  try { await router.replace(homeFor((await connect(code)).access)) }
  catch (e) { error.value = e instanceof Error ? e.message : 'Sign in failed.' }
  finally { busy.value = false }
}
async function leave(demo = false) {
  busy.value = true; error.value = ''
  try { if (demo) { await useDemo(); await router.push('/cases') } else await logout() }
  catch (e) { error.value = e instanceof Error ? e.message : 'Sign out failed.' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="shell page">
    <h1>Connect</h1>
    <p class="lede">Enter the private access code supplied to you. Your access determines which case and actions you can see.</p>
    <section class="card">
      <template v-if="session.info">
        <h2>Signed in as {{ session.info.access.role }}</h2>
        <p>Access expires {{ new Date(session.info.expires_at).toLocaleString() }}.</p>
        <RouterLink :to="homeFor(session.info.access)" class="btn">Continue to workspace</RouterLink>
        <button class="btn" :disabled="busy" @click="leave()">Sign out</button>
      </template>
      <form v-else class="form" @submit.prevent="signIn">
        <label for="token" class="label">Access code</label>
        <input id="token" v-model="token" class="field mono" type="password" autocomplete="off" required />
        <button class="btn btn-primary" :disabled="busy || !token.trim()">{{ busy ? 'Connecting…' : 'Sign in' }}</button>
      </form>
      <p v-if="error || session.error" class="error" role="alert">{{ error || session.error }}</p>
    </section>
    <section class="card">
      <h2>Explore the demo</h2>
      <p class="lede">Public fixture examples with simulated decisions. No live payment is credited.</p>
      <button class="btn btn-quiet" :disabled="busy" @click="leave(true)">Use demo data</button>
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
