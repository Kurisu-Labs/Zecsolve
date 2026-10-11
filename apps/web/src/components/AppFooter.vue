<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useReducedMotion } from '@/motion/reduced'

const { reduced, system, setMotionOverride } = useReducedMotion()

function onToggle(event: Event) {
  setMotionOverride((event.target as HTMLInputElement).checked)
}
</script>

<template>
  <footer class="footer">
    <div class="shell grid">
      <p class="honest">
        Hackathon build for the Colosseum Crypto World's Fair, Zcash track. The demo replays a real
        historical mainnet receipt against synthetic invoices. No live checkout, no funds move.
      </p>
      <div class="links">
        <RouterLink to="/how-it-works">How it works</RouterLink>
        <a href="https://github.com/Kurisu-Labs/zecsolve" rel="noopener">Source on GitHub</a>
        <label class="toggle">
          <input
            type="checkbox"
            :checked="reduced"
            :disabled="system"
            @change="onToggle"
          />
          <span>Reduce motion{{ system ? ' (set by your system)' : '' }}</span>
        </label>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer { border-top: 1px solid var(--color-line); padding: 2.5rem 0 3rem; margin-top: 6rem; color: var(--color-mute); font-size: var(--step--1); }
.grid { display: grid; gap: 1.5rem; grid-template-columns: minmax(0, 1fr); }
@media (min-width: 860px) { .grid { grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); } }
.honest { max-width: 60ch; }
.links { display: flex; flex-wrap: wrap; gap: 1rem 1.5rem; align-items: center; justify-content: flex-start; }
@media (min-width: 860px) { .links { justify-content: flex-end; } }
a { text-decoration: none; }
a:hover { color: var(--color-snow); }
.toggle { display: inline-flex; gap: 0.5rem; align-items: center; cursor: pointer; }
.toggle input { accent-color: var(--color-zec); width: 16px; height: 16px; }
</style>
