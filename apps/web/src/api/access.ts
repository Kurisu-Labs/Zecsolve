import type { components } from './contracts'

export type SessionInfo = components['schemas']['sessionInfo']
export type Access = Pick<SessionInfo['access'], 'role' | 'case_id'>

export function homeFor(access: Access): string {
  if (access.role === 'customer') return `/submit/${access.case_id}`
  if (access.role === 'reviewer') return `/review/${access.case_id}`
  return '/cases'
}

export function mayVisit(access: Access, page: string, caseId?: string): boolean {
  if (['landing', 'how', 'connect', 'missing'].includes(page)) return true
  if (access.role === 'merchant') return page !== 'review'
  if (!caseId || caseId !== access.case_id) return false
  return access.role === 'customer' ? page === 'submit' : page === 'review'
}

export function csrfToken(cookie: string): string | null {
  const value = cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith('__Host-zecsolve_csrf='))
  return value ? decodeURIComponent(value.slice(value.indexOf('=') + 1)) : null
}
