// "Decrypt" text reveal: characters start as quadrant blocks (the logo's dissolving
// squares) and resolve left to right. Screen readers get the final text immediately.
import { isReducedMotion } from './reduced'

const BLOCKS = '▖▗▘▝▚▞'

export function decrypt(el: HTMLElement, options: { duration?: number; delay?: number } = {}): () => void {
  const finalText = el.dataset.text ?? el.textContent ?? ''
  el.dataset.text = finalText
  el.setAttribute('aria-label', finalText)
  if (isReducedMotion()) {
    el.textContent = finalText
    return () => {}
  }
  const duration = options.duration ?? 900
  const delay = options.delay ?? 0
  const chars = [...finalText]
  // Each character resolves at its own moment, biased left to right.
  const reveal = chars.map((_, i) => (i / Math.max(chars.length, 1)) * 0.75 + Math.random() * 0.25)
  let frame = 0
  let start = 0
  const tick = (now: number) => {
    if (!start) start = now + delay
    const t = Math.min(Math.max((now - start) / duration, 0), 1)
    el.textContent = chars
      .map((ch, i) => {
        if (ch === ' ' || t >= (reveal[i] ?? 1)) return ch
        return BLOCKS[Math.floor(Math.random() * BLOCKS.length)] ?? ch
      })
      .join('')
    if (t < 1) frame = requestAnimationFrame(tick)
    else el.textContent = finalText
  }
  frame = requestAnimationFrame(tick)
  return () => {
    cancelAnimationFrame(frame)
    el.textContent = finalText
  }
}

/** Integer count-up for zatoshi amounts. Never interpolates money as a float value that is shown. */
export function countUp(el: HTMLElement, to: number, format: (n: number) => string, ms = 1100): () => void {
  if (isReducedMotion()) {
    el.textContent = format(to)
    return () => {}
  }
  let frame = 0
  const start = performance.now()
  const tick = (now: number) => {
    const t = Math.min((now - start) / ms, 1)
    const eased = 1 - Math.pow(1 - t, 4)
    el.textContent = format(Math.round(to * eased))
    if (t < 1) frame = requestAnimationFrame(tick)
  }
  frame = requestAnimationFrame(tick)
  return () => cancelAnimationFrame(frame)
}
