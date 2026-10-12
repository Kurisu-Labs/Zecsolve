import { setRetryPrincipal } from './retry'
import { reactive, readonly } from 'vue'
import { api, ApiError } from './client'
import type { SessionInfo } from './access'

const state = reactive({
  mode: 'live' as 'live' | 'demo',
  info: null as SessionInfo | null,
  ready: false,
  error: '',
})
export const session = readonly(state)
let restore: Promise<void> | null = null
let expiry: ReturnType<typeof setTimeout> | undefined

function assign(info: SessionInfo | null) {
  clearTimeout(expiry)
  state.info = info
  setRetryPrincipal(info?.access.grant_id ?? info?.access.credential_id ?? 'anonymous')
  state.ready = true
  if (info) expiry = setTimeout(expireSession, Math.max(0, Date.parse(info.expires_at) - Date.now()))
}

export function expireSession() {
  assign(null)
  state.mode = 'live'
  state.error = 'Your access expired or was revoked. Sign in again.'
  window.dispatchEvent(new Event('zecsolve:session-ended'))
}

export async function restoreSession() {
  if (state.ready) return
  if (!restore)
    restore = (async () => {
      try {
        assign(await api.session())
        state.mode = 'live'
      } catch (e) {
        assign(null)
        try {
          if (sessionStorage.getItem('zecsolve.demo') === 'selected') state.mode = 'demo'
        } catch {
          /* storage disabled */
        }
        if (!(e instanceof ApiError && e.status === 401))
          state.error = 'Unable to restore access. Try signing in again.'
      }
    })().finally(() => {
      restore = null
    })
  await restore
}

export async function connect(code: string) {
  const info = await api.connect(code)
  state.mode = 'live'
  try {
    sessionStorage.removeItem('zecsolve.demo')
  } catch {
    /* storage disabled */
  }
  state.error = ''
  assign(info)
  return info
}

export async function logout() {
  if (state.info) {
    try {
      await api.logout()
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 401)) throw e
    }
  }
  assign(null)
  state.mode = 'live'
  try {
    sessionStorage.removeItem('zecsolve.demo')
  } catch {
    /* storage disabled */
  }
  state.error = ''
}

export async function useDemo() {
  await logout()
  state.mode = 'demo'
  try {
    sessionStorage.setItem('zecsolve.demo', 'selected')
  } catch {
    /* storage disabled */
  }
}

// Remove credentials stored by the previous bearer-based frontend; never reuse them.
try {
  localStorage.removeItem('zecsolve.merchantCredential')
  localStorage.removeItem('zecsolve.knownCases')
} catch {
  /* storage disabled */
}
window.addEventListener('zecsolve:unauthorized', expireSession)
