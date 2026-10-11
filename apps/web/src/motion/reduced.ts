import { onMounted, readonly, ref } from 'vue'

// Reduced motion = the OS setting OR the in-page "Reduce motion" switch.
const OVERRIDE_KEY = 'zecsolve.reduceMotion'

const query = typeof window !== 'undefined' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null
const system = ref(query?.matches ?? false)
const override = ref(readOverride())
const reduced = ref(system.value || override.value)

function readOverride(): boolean {
  try {
    return localStorage.getItem(OVERRIDE_KEY) === '1'
  } catch {
    return false
  }
}

function sync(): void {
  reduced.value = system.value || override.value
  document.documentElement.classList.toggle('reduce-motion', reduced.value)
}

query?.addEventListener('change', (event) => {
  system.value = event.matches
  sync()
})
if (typeof document !== 'undefined') sync()

export function isReducedMotion(): boolean {
  return reduced.value
}

export function setMotionOverride(value: boolean): void {
  override.value = value
  try {
    localStorage.setItem(OVERRIDE_KEY, value ? '1' : '0')
  } catch {
    /* ignore */
  }
  sync()
}

export function useReducedMotion() {
  onMounted(sync)
  return { reduced: readonly(reduced), override: readonly(override), system: readonly(system), setMotionOverride }
}
