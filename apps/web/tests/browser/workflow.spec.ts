import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '../../../..')
const statePath = process.env.ZECSOLVE_BROWSER_STATE
if (!statePath) throw new Error('Set ZECSOLVE_BROWSER_STATE to the private browser-server state.json file.')
const { merchant_code: merchantCode } = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'fixtures/manifest.json'), 'utf8'))
const receipt = fs.readFileSync(path.join(root, 'fixtures/mainnet/receipt.json'), 'utf8')
const transaction = fs.readFileSync(path.join(root, 'fixtures/mainnet/transaction.hex'), 'utf8')

async function login(page: Page, code: string) {
  await page.goto('/connect')
  await page.getByLabel('Access code', { exact: true }).fill(code)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/connect$/)
}
async function call(page: Page, route: string, body?: unknown, method = body ? 'POST' : 'GET') {
  return page.evaluate(async ({ route, body, method }) => {
    const csrf = document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('__Host-zecsolve_csrf='))?.split('=')[1] ?? ''
    const response = await fetch(route, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': crypto.randomUUID() }, body: body ? JSON.stringify(body) : undefined })
    return { status: response.status, data: response.status === 204 ? null : await response.json() }
  }, { route, body, method })
}

test('three roles complete the real HTTPS submission and merchant review flow', async ({ page, browser }) => {
  test.setTimeout(180_000)
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await login(page, merchantCode)
  const cookies = await page.context().cookies()
  expect(cookies.find(c => c.name === '__Host-zecsolve_session')).toMatchObject({ secure: true, httpOnly: true, sameSite: 'Strict' })
  expect(await page.evaluate(() => localStorage.getItem('zecsolve.merchantCredential'))).toBeNull()
  await page.getByRole('link', { name: 'Create invoice and case' }).click()
  await page.getByLabel('Expected amount (ZEC)').fill('0.002')
  await page.getByLabel('Mainnet receiver address').fill(fixture.expected.receiver_address)
  await page.getByLabel('Expected memo (optional)').fill(fixture.expected.memo_text)
  await page.getByRole('button', { name: 'Create invoice and open case' }).click()
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/)
  const caseId = page.url().split('/').pop()!
  await page.getByRole('link', { name: 'Manage access' }).click()
  await page.getByRole('button', { name: 'Create access code' }).click()
  const customerCode = await page.getByLabel('Private access code').inputValue()
  const customerContext = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: 'https://localhost:8443' })
  const customer = await customerContext.newPage()
  const customerReads: string[] = []
  customer.on('request', r => { if (r.method() === 'GET' && r.url().includes('/api/cases')) customerReads.push(r.url()) })
  await login(customer, customerCode)
  await expect(customer).toHaveURL(`/submit/${caseId}`)
  await customer.getByLabel('Include receipt JSON').check()
  await customer.getByLabel('Receipt contents').fill(receipt)
  await customer.getByLabel('Include raw transaction', { exact: true }).check()
  await customer.getByLabel('Raw transaction hex', { exact: true }).fill(transaction)
  await expect(customer.getByLabel(/Also allow sharing/)).not.toBeChecked()
  await expect(customer.getByRole('button', { name: 'Submit for review' })).toBeDisabled()
  await customer.getByLabel('I authorize this processing.').check()
  await customer.getByLabel(/Also allow sharing/).check()
  // Drop only the response after the actual backend commits, then retry unchanged.
  let dropped = false
  const keys: string[] = []
  await customer.route(`**/api/cases/${caseId}/evidence`, async route => {
    keys.push(route.request().headers()['idempotency-key'])
    if (!dropped) { dropped = true; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await customer.getByRole('button', { name: 'Submit for review' }).click()
  await expect(customer.getByRole('alert')).toBeVisible()
  await customer.getByRole('button', { name: 'Submit for review' }).click()
  await expect(customer.getByRole('heading', { name: 'Submission accepted' })).toBeVisible()
  expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1])
  expect(customerReads).toEqual([])
  await customer.getByRole('button', { name: 'Submit another item' }).click()
  await customer.getByLabel('What are you submitting?').selectOption('claim')
  const note = '<img src=x onerror=alert(1)> customer assertion'
  await customer.getByLabel('Note (optional').fill(note)
  await customer.getByLabel('I authorize this processing.').check()
  await customer.getByRole('button', { name: 'Submit for review' }).click()
  await expect(customer.getByRole('heading', { name: 'Submission accepted' })).toBeVisible()
  await customer.goto(`/cases/${caseId}`)
  await expect(customer).toHaveURL(`/submit/${caseId}`)
  expect((await call(customer, `/api/cases/${caseId}/report`)).status).toBe(403)

  await page.goto(`/cases/${caseId}`)
  await expect(page.getByText(note, { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Verify evidence', exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Verify evidence', exact: true }).click()
  await expect(page.getByText('100,000', { exact: true }).first()).toBeVisible()
  const report = (await call(page, `/api/cases/${caseId}/report`)).data
  expect(report.verifications[0].result.receipt_state).toBe('VALID')
  expect(report.balances.credited_zat).toBe(0)
  expect(report.balances.candidate_zat).toBe(100000)
  expect(report.chain_observations[0].state).toBe('UNAVAILABLE')
  await page.getByRole('link', { name: 'Manage access' }).click()
  await page.getByLabel('Role', { exact: true }).selectOption('reviewer')
  await page.getByLabel('case', { exact: true }).check()
  await page.getByLabel('claims', { exact: true }).check()
  await page.getByLabel('balances', { exact: true }).check()
  await page.getByLabel('evidence', { exact: true }).check()
  await page.getByLabel(/Sharing authorized/).check()
  await page.getByRole('button', { name: 'Create access code' }).click()
  const reviewerCode = await page.getByLabel('Private access code').inputValue()
  const reviewerContext = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: 'https://localhost:8443' })
  const reviewer = await reviewerContext.newPage()
  await login(reviewer, reviewerCode)
  await expect(reviewer.getByRole('heading', { name: 'Shared case report' })).toBeVisible()
  await expect(reviewer.getByText('Report-only access. Packet export is not permitted.')).toBeVisible()
  await expect(reviewer.getByText(note, { exact: true })).toHaveCount(0)
  await expect(reviewer.getByRole('heading', { name: 'Invoice', exact: true })).toHaveCount(0)
  await reviewer.getByRole('button', { name: /^Read / }).click()
  await expect(reviewer.getByLabel('Receipt (exact text)')).toHaveValue(receipt)
  expect((await call(reviewer, `/api/cases/${caseId}/verify`, { evidence_id: report.evidence[0].evidence_id })).status).toBe(403)
  const issued = (await call(page, `/api/cases/${caseId}/grants`)).data.items
  const reviewerGrant = issued.find((g: { scope: { role: string } }) => g.scope.role === 'reviewer')
  await page.locator('article').filter({ hasText: reviewerGrant.grant_id }).getByRole('button', { name: 'Revoke access' }).click()
  await reviewer.getByRole('button', { name: 'Refresh report' }).click()
  await expect(reviewer).toHaveURL('/connect')
  await page.goto('/connect')
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.goto('/cases')
  await expect(page).toHaveURL('/connect')
  expect(errors).toEqual([])
  await customerContext.close(); await reviewerContext.close()
})

test('mobile login, invalid access and explicitly selected demo', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/connect')
  await page.getByLabel('Access code', { exact: true }).fill('invalid-access-code')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByLabel('Access code', { exact: true })).toHaveValue('')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Use demo data' }).click()
  await expect(page.getByRole('button', { name: 'Reset demo data' })).toBeVisible()
  await expect(page.getByText('Demo data', { exact: true })).toBeVisible()
})
