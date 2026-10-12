import { restoreSession, session } from './api/session'
import { homeFor, mayVisit } from './api/access'
import { createRouter, createWebHistory } from 'vue-router'

// Pages are split so the app never downloads the landing page's WebGL.
export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, _from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'landing', component: () => import('./pages/LandingPage.vue') },
    { path: '/how-it-works', name: 'how', component: () => import('./pages/HowItWorksPage.vue') },
    { path: '/cases', name: 'cases', component: () => import('./pages/CasesPage.vue') },
    { path: '/cases/new', name: 'new-case', component: () => import('./pages/NewCasePage.vue') },
    { path: '/cases/:id', name: 'case', component: () => import('./pages/CaseDetailPage.vue'), props: true },
    { path: '/submit/:id', name: 'submit', component: () => import('./pages/SubmitEvidencePage.vue'), props: true },
    { path: '/report/:id', name: 'report', component: () => import('./pages/ReportPage.vue'), props: true },
    { path: '/cases/:id/grants', name: 'grants', component: () => import('./pages/GrantsPage.vue'), props: true },
    { path: '/review/:id', name: 'review', component: () => import('./pages/ReviewerPage.vue'), props: true },
    { path: '/connect', name: 'connect', component: () => import('./pages/ConnectPage.vue') },
    { path: '/:pathMatch(.*)*', name: 'missing', component: () => import('./pages/NotFoundPage.vue') },
  ],
})

router.beforeEach(async (to) => {
  await restoreSession()
  if (['landing', 'how', 'connect', 'missing'].includes(String(to.name))) return true
  if (session.mode === 'demo') return ['grants', 'new-case', 'review'].includes(String(to.name)) ? '/cases' : true
  if (!session.info) return '/connect'
  if (!mayVisit(session.info.access, String(to.name), String(to.params.id ?? ''))) return homeFor(session.info.access)
  return true
})
window.addEventListener('zecsolve:session-ended', () => { void router.replace('/connect') })

router.afterEach((to) => {
  const titles: Record<string, string> = {
    landing: 'zecsolve',
    how: 'How it works · zecsolve',
    cases: 'Cases · zecsolve',
    case: 'Case · zecsolve',
    submit: 'Share a receipt · zecsolve',
    report: 'Case report · zecsolve',
    connect: 'Connect · zecsolve',
  }
  document.title = titles[String(to.name)] ?? 'zecsolve'
})
