// Store only a request digest and random retry key, never access codes or evidence.
const pending = new Map<string, string>()
let principal = 'anonymous'
export function setRetryPrincipal(value: string) {
  principal = value
}
export async function retryIdentity(path: string, body: string) {
  const bytes = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(`${principal}\n${path}\n${body}`),
  )
  return `zecsolve.retry.${Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, '0')).join('')}`
}
export function pendingKey(identity: string, suggested: string): string {
  let key = pending.get(identity)
  try {
    key ??= sessionStorage.getItem(identity) ?? undefined
  } catch {
    /* in-memory fallback */
  }
  key ??= suggested
  pending.set(identity, key)
  try {
    sessionStorage.setItem(identity, key)
  } catch {
    /* in-memory fallback */
  }
  return key
}
export function finishRequest(identity: string) {
  pending.delete(identity)
  try {
    sessionStorage.removeItem(identity)
  } catch {
    /* storage disabled */
  }
}
