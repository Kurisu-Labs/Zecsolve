<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import markUrl from '@/assets/zecsolve-mark.png'
import { countUp, decrypt } from '@/motion/decrypt'
import { isReducedMotion } from '@/motion/reduced'
import { formatZat } from '@/lib/money'

// One orchestrated moment for the whole site: scroll moves a single note out of the
// shielded pool and assembles it into the mark. Text frames explain each stage in the DOM.

const section = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const headline = ref<HTMLElement | null>(null)
const amount = ref<HTMLElement | null>(null)
const frames = ref<HTMLElement[]>([])
const staticMode = ref(isReducedMotion())

const cleanups: (() => void)[] = []

function frameRef(index: number) {
  return (el: unknown) => {
    if (el instanceof HTMLElement) frames.value[index] = el
  }
}

function setFrame(el: HTMLElement | undefined, visibility: number) {
  if (!el) return
  el.style.opacity = String(visibility)
  el.style.transform = `translate3d(0, ${(1 - visibility) * 18}px, 0)`
  el.style.visibility = visibility < 0.02 ? 'hidden' : 'visible'
  el.toggleAttribute('inert', visibility < 0.5)
}

/** 0 → 1 → 0 across [a, b, c, d]. */
function window4(p: number, a: number, b: number, c: number, d: number): number {
  if (p <= a || p >= d) return a === 0 && p <= a ? 1 : 0
  if (p < b) return (p - a) / (b - a)
  if (p <= c) return 1
  return 1 - (p - c) / (d - c)
}

onMounted(async () => {
  if (headline.value) cleanups.push(decrypt(headline.value, { duration: 1000, delay: 150 }))
  if (isReducedMotion() || !canvas.value || !section.value) return

  try {
    const [{ createPixelField }, { createScrollStack }] = await Promise.all([
      import('@/gl/pixelField'),
      import('@/motion/scroll'),
    ])
    const field = await createPixelField({ canvas: canvas.value, markUrl })
    const stack = createScrollStack()

    let counted = false
    stack.ScrollTrigger.create({
      trigger: section.value,
      start: 'top top',
      end: 'bottom bottom',
      scrub: true,
      onUpdate(self) {
        const p = self.progress
        // Stage timing: pool 0–0.22, assemble 0.22–0.6, hold, release 0.78–1.
        const assemble = Math.min(Math.max((p - 0.22) / 0.38, 0), 1)
        const release = Math.min(Math.max((p - 0.78) / 0.22, 0), 1)
        field.setProgress(assemble)
        field.setRelease(release)
        setFrame(frames.value[0], p < 0.18 ? 1 : Math.max(0, 1 - (p - 0.18) / 0.08))
        setFrame(frames.value[1], window4(p, 0.3, 0.42, 0.66, 0.74))
        setFrame(frames.value[2], window4(p, 0.76, 0.86, 1.01, 1.02))
        if (!counted && p > 0.36 && amount.value) {
          counted = true
          cleanups.push(countUp(amount.value, 100_000, formatZat))
        }
      },
    })

    const visible = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) field.start()
      else field.stop()
    })
    visible.observe(section.value)

    const onResize = () => {
      field.resize()
      stack.ScrollTrigger.refresh()
    }
    window.addEventListener('resize', onResize)

    cleanups.push(() => {
      visible.disconnect()
      window.removeEventListener('resize', onResize)
      stack.destroy()
      field.dispose()
    })
  } catch (error) {
    // No WebGL, or it failed: the static poster stays. The story still reads top to bottom.
    console.warn('[zecsolve] hero scene unavailable, using static poster', error)
    staticMode.value = true
  }
})

onBeforeUnmount(() => cleanups.splice(0).forEach((fn) => fn()))
</script>

<template>
  <section ref="section" class="hero" :class="{ static: staticMode }" aria-label="What zecsolve does">
    <div class="stage">
      <canvas ref="canvas" class="field" aria-hidden="true" />
      <div class="poster" aria-hidden="true">
        <img :src="markUrl" alt="" width="212" height="192" />
      </div>

      <div class="frames shell">
        <div :ref="frameRef(0)" class="frame first">
          <h1 ref="headline" class="headline">A payment arrived. Nobody can see it.</h1>
          <p class="sub">
            Shielded Zcash hides the amount, the receiver and the memo. That's the point, until an order doesn't match the
            money and support has to work out what happened.
          </p>
          <div class="ctas">
            <RouterLink to="/cases/shortfall" class="btn btn-primary">Open the demo case</RouterLink>
            <RouterLink to="/how-it-works" class="btn">How it works</RouterLink>
          </div>
          <p class="scroll-hint" aria-hidden="true">Scroll to open one payment</p>
        </div>

        <div :ref="frameRef(1)" class="frame">
          <h2>One receipt opens one output.</h2>
          <p class="sub">
            The customer shares a key for a single payment. zecsolve recovers that output and nothing else in the wallet:
            no spending key, no viewing key.
          </p>
          <p class="amount">
            <span ref="amount" class="mono">100,000</span>
            <span class="unit">zatoshis recovered from mainnet transaction 66167cd3…cfd0</span>
          </p>
        </div>

        <div :ref="frameRef(2)" class="frame">
          <h2>Then a person decides.</h2>
          <p class="sub">
            The amount lands on a case next to the invoice and the chain status, kept apart. The merchant approves it with a
            reason, or asks for more. Nothing is credited on its own.
          </p>
          <div class="ctas">
            <RouterLink to="/cases" class="btn btn-primary">See the cases</RouterLink>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero { position: relative; height: 420vh; }
.stage { position: sticky; top: 0; height: 100vh; height: 100svh; overflow: hidden; }
.field { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.poster { display: none; }
.frames { position: relative; height: 100%; display: grid; align-items: center; }
.frame {
  grid-area: 1 / 1;
  max-width: 34rem;
  display: grid;
  gap: 1.25rem;
  justify-items: start;
  will-change: opacity, transform;
}
.frame:not(.first) { opacity: 0; visibility: hidden; }
.headline { font-size: min(var(--step-6), 11svh); letter-spacing: -0.045em; line-height: 0.98; font-weight: 650; max-width: 12ch; }
h2 { font-size: min(var(--step-5), 9svh); letter-spacing: -0.04em; line-height: 1; max-width: 12ch; }
.sub { color: var(--color-mute); font-size: var(--step-1); line-height: 1.45; max-width: 36ch; }
.ctas { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.5rem; }
.scroll-hint { color: var(--color-faint); font-size: var(--step--1); margin-top: 2rem; }
.amount { display: grid; gap: 0.35rem; }
.amount .mono { font-size: var(--step-5); color: var(--color-zec); letter-spacing: -0.03em; font-weight: 500; line-height: 1; }
.unit { color: var(--color-mute); font-size: var(--step--1); }

@media (max-width: 860px) {
  .frames { align-items: end; padding-bottom: 12vh; }
  .headline { font-size: min(var(--step-5), 8svh); }
  h2 { font-size: min(var(--step-4), 7svh); }
  .sub { font-size: var(--step-0); }
}

/* Static poster: reduced motion or no WebGL. Frames stack as ordinary sections. */
.hero.static { height: auto; }
.hero.static .stage { position: relative; height: auto; overflow: visible; }
.hero.static .field { display: none; }
.hero.static .poster {
  display: grid; place-items: center; position: absolute; inset: 0 0 auto auto; width: min(46vw, 560px); height: 100vh;
  background-image: radial-gradient(circle, #3a3a3a 1px, transparent 1.4px);
  background-size: 10px 10px;
  mask-image: radial-gradient(closest-side, #000 55%, transparent);
}
.hero.static .poster img { width: 46%; height: auto; }
.hero.static .frames { display: grid; gap: 8rem; padding: 9rem 0 4rem; align-items: start; }
.hero.static .frame { grid-area: auto; opacity: 1 !important; visibility: visible !important; transform: none !important; }
@media (max-width: 860px) { .hero.static .poster { position: relative; width: 100%; height: 40vh; } .hero.static .frames { padding-top: 2rem; } }
</style>
