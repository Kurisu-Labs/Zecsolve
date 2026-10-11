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
    { path: '/cases/:id', name: 'case', component: () => import('./pages/CaseDetailPage.vue'), props: true },
    { path: '/submit/:id', name: 'submit', component: () => import('./pages/SubmitEvidencePage.vue'), props: true },
    { path: '/report/:id', name: 'report', component: () => import('./pages/ReportPage.vue'), props: true },
    { path: '/connect', name: 'connect', component: () => import('./pages/ConnectPage.vue') },
    { path: '/:pathMatch(.*)*', name: 'missing', component: () => import('./pages/NotFoundPage.vue') },
  ],
})

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
