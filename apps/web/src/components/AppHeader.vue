<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BrandLogo from './ui/BrandLogo.vue'
import { session } from '@/api/session'
import { homeFor } from '@/api/access'

const route = useRoute()
const scrolled = ref(false)
const onScroll = () => (scrolled.value = window.scrollY > 24)
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

// Transparent only over the top of the landing hero; solid as soon as content scrolls under it.
const onLanding = computed(() => route.name === 'landing')
</script>

<template>
  <header class="header" :class="{ floating: onLanding, clear: onLanding && !scrolled }">
    <a href="#main" class="skip sr-only-focusable">Skip to content</a>
    <div class="shell row">
      <RouterLink to="/" class="home" aria-label="zecsolve home"><BrandLogo /></RouterLink>
      <nav aria-label="Primary">
        <RouterLink
          :to="session.info ? homeFor(session.info.access) : session.mode === 'demo' ? '/cases' : '/connect'"
          class="nav"
          >{{
            session.info?.access.role === 'customer'
              ? 'Submit'
              : session.info?.access.role === 'reviewer'
                ? 'Report'
                : 'Cases'
          }}</RouterLink
        >
        <RouterLink to="/how-it-works" class="nav hide-sm">How it works</RouterLink>
        <RouterLink to="/connect" class="mode" :class="session.mode">
          <span class="dot" aria-hidden="true" />
          {{ session.mode === 'demo' ? 'Demo data' : session.info ? session.info.access.role : 'Sign in' }}
        </RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: color-mix(in oklab, var(--color-ink) 82%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-line);
}
.header {
  transition:
    background-color var(--dur-base) var(--ease-standard),
    border-color var(--dur-base) var(--ease-standard);
}
.header.floating {
  position: fixed;
  inset: 0 0 auto 0;
}
.header.clear {
  background: transparent;
  backdrop-filter: none;
  border-color: transparent;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}
.home {
  display: inline-flex;
  text-decoration: none;
}
nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.nav {
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  text-decoration: none;
  color: var(--color-mute);
  transition: color var(--dur-fast) var(--ease-standard);
}
.nav:hover,
.nav.router-link-active {
  color: var(--color-snow);
}
.mode {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-left: 0.5rem;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--color-line-strong);
  font-size: var(--step--1);
  text-decoration: none;
  color: var(--color-snow);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  background: var(--color-unknown);
}
.mode.live .dot {
  background: var(--color-zec);
}
.skip {
  position: absolute;
  left: 1rem;
  top: 0.75rem;
  background: var(--color-zec);
  color: var(--color-ink);
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
}
@media (max-width: 640px) {
  .hide-sm {
    display: none;
  }
}
</style>
