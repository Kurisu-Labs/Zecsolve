// Mirrors the CSS custom properties in styles/main.css for GSAP timelines (seconds).
export const dur = {
  instant: 0.07,
  fast: 0.15,
  base: 0.24,
  slow: 0.4,
  story: 0.9,
} as const

export const ease = {
  standard: 'power2.out',
  enter: 'expo.out',
  exit: 'power2.in',
  story: 'expo.inOut',
} as const
