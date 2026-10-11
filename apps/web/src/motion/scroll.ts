// Landing-only scroll stack: Lenis smoothing driven by GSAP's ticker so ScrollTrigger
// and the WebGL scene read one scroll position. Loaded lazily by the landing page.
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import { isReducedMotion } from './reduced'

gsap.registerPlugin(ScrollTrigger)

export interface ScrollStack {
  gsap: typeof gsap
  ScrollTrigger: typeof ScrollTrigger
  destroy: () => void
}

export function createScrollStack(): ScrollStack {
  if (isReducedMotion()) {
    return { gsap, ScrollTrigger, destroy: () => ScrollTrigger.getAll().forEach((t) => t.kill()) }
  }
  const lenis = new Lenis({ lerp: 0.12, wheelMultiplier: 1 })
  lenis.on('scroll', ScrollTrigger.update)
  const raf = (time: number) => lenis.raf(time * 1000)
  gsap.ticker.add(raf)
  gsap.ticker.lagSmoothing(0)
  return {
    gsap,
    ScrollTrigger,
    destroy() {
      gsap.ticker.remove(raf)
      lenis.destroy()
      ScrollTrigger.getAll().forEach((t) => t.kill())
    },
  }
}
