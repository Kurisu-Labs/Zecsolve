// Money is integer zatoshis everywhere. 1 ZEC = 100,000,000 zatoshis.
// Never multiply or divide currency as binary floating point.

export const ZAT_PER_ZEC = 100_000_000n

const zatFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

export function assertZat(value: number): number {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`Expected a non-negative integer zatoshi amount, received ${value}`)
  }
  return value
}

/** 100000 → "100,000" */
export function formatZat(zat: number): string {
  return zatFormat.format(assertZat(zat))
}

/** 100000 → "0.001" (exact decimal from integers, trailing zeros trimmed). */
export function formatZec(zat: number): string {
  const value = BigInt(assertZat(zat))
  const whole = value / ZAT_PER_ZEC
  const fraction = (value % ZAT_PER_ZEC).toString().padStart(8, '0').replace(/0+$/, '')
  return fraction ? `${whole}.${fraction}` : whole.toString()
}

/**
 * Parse a decimal ZEC string exactly into zatoshis.
 * "0.001" → 100000. Returns null for anything that is not a plain decimal with ≤ 8 places.
 */
export function parseZec(input: string): number | null {
  const text = input.trim()
  const match = /^(\d+)(?:\.(\d{0,8}))?$/.exec(text)
  if (!match) return null
  const whole = BigInt(match[1] ?? '0')
  const fraction = BigInt((match[2] ?? '').padEnd(8, '0') || '0')
  const zat = whole * ZAT_PER_ZEC + fraction
  if (zat > BigInt(Number.MAX_SAFE_INTEGER)) return null
  return Number(zat)
}

/** Share of `part` in `whole`, 0–1, for bar widths only (never for money). */
export function ratio(part: number, whole: number): number {
  if (whole <= 0) return 0
  return Math.min(Math.max(part / whole, 0), 1)
}
