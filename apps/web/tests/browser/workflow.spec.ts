import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import AxeBuilder from '@axe-core/playwright'
const root = path.resolve(import.meta.dirname, '../../../..')
const statePath = process.env.ZECSOLVE_BROWSER_STATE
if (!statePath) throw new Error('Set ZECSOLVE_BROWSER_STATE to the private browser-server state.json file.')
const { merchant_code: merchantCode, simulated } = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'fixtures/manifest.json'), 'utf8'))
const receipt = fs.readFileSync(path.join(root, 'fixtures/mainnet/receipt.json'), 'utf8')
const transaction = fs.readFileSync(path.join(root, 'fixtures/mainnet/transaction.hex'), 'utf8')

async function login(page: Page, code: string) {
  await page.goto('/connect')
  if (await page.getByRole('button', { name: 'Use another access code' }).isVisible())
    await page.getByRole('button', { name: 'Use another access code' }).click()
  await page.getByLabel('Access code', { exact: true }).fill(code)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/connect$/)
}
async function checkAccessibility(page: Page) {
  await expect(page.locator('.route-enter-active, .route-leave-active')).toHaveCount(0)
  const result = await new AxeBuilder({ page }).analyze()
  expect(result.violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) }))).toEqual([])
}
async function createCase(page: Page) {
  const invoice = await call(page, '/api/invoices', {
    expected_zat: 200000,
    network: 'mainnet',
    pool: 'orchard',
    receiver_address: fixture.expected.receiver_address,
    expected_memo: fixture.expected.memo_text,
  })
  expect(invoice.status).toBe(201)
  const opened = await call(page, '/api/cases', { invoice_id: invoice.data.invoice_id })
  expect(opened.status).toBe(201)
  return opened.data.case_id as string
}
async function upload(page: Page, id: string, receipt_json: string | null, raw_tx_hex: string | null) {
  const response = await call(page, `/api/cases/${id}/evidence`, {
    receipt_json,
    raw_tx_hex,
    source: 'Public browser fixture',
    source_kind: 'public_fixture',
    disclosure_version: 'evidence-disclosure-v2',
    processing_authorized: true,
    share_with_reviewers: false,
  })
  expect(response.status).toBe(201)
  return response.data.submission_id as string
}
async function call(page: Page, route: string, body?: unknown, method = body ? 'POST' : 'GET') {
  return page.evaluate(
    async ({ route, body, method }) => {
      const csrf =
        document.cookie
          .split(';')
          .map((s) => s.trim())
          .find((s) => s.startsWith('__Host-zecsolve_csrf='))
          ?.split('=')[1] ?? ''
      const response = await fetch(route, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
          'Idempotency-Key': crypto.randomUUID(),
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      return { status: response.status, data: response.status === 204 ? null : await response.json() }
    },
    { route, body, method },
  )
}

test('three roles complete the real HTTPS submission and merchant review flow', async ({ page, browser }) => {
  test.setTimeout(180_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await login(page, merchantCode)
  await page.reload()
  await expect(page.getByRole('link', { name: 'Create invoice and case' })).toBeVisible()
  const cookies = await page.context().cookies()
  expect(cookies.find((c) => c.name === '__Host-zecsolve_session')).toMatchObject({
    secure: true,
    httpOnly: true,
    sameSite: 'Strict',
  })
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
  const customerContext = await browser.newContext({
    ignoreHTTPSErrors: true,
    baseURL: 'https://localhost:8443',
  })
  const customer = await customerContext.newPage()
  const customerReads: string[] = []
  customer.on('request', (r) => {
    if (r.method() === 'GET' && r.url().includes('/api/cases')) customerReads.push(r.url())
  })
  await login(customer, customerCode)
  await expect(customer).toHaveURL(`/submit/${caseId}`)
  await customer.getByLabel('Include receipt JSON').check()
  await customer
    .getByLabel('Receipt file', { exact: true })
    .setInputFiles(path.join(root, 'fixtures/mainnet/receipt.json'))
  await customer.getByLabel('Include raw transaction', { exact: true }).check()
  await customer
    .getByLabel('Transaction file', { exact: true })
    .setInputFiles(path.join(root, 'fixtures/mainnet/transaction.hex'))
  await expect(customer.getByLabel(/Also allow sharing/)).not.toBeChecked()
  await expect(customer.getByRole('button', { name: 'Submit for review' })).toBeDisabled()
  await customer.getByLabel('I authorize this processing.').check()
  await customer.getByLabel(/Also allow sharing/).check()
  // Drop only the response after the actual backend commits, then retry unchanged.
  let dropped = false
  const keys: string[] = []
  await customer.route(`**/api/cases/${caseId}/evidence`, async (route) => {
    keys.push(route.request().headers()['idempotency-key'])
    if (!dropped) {
      dropped = true
      await route.fetch()
      await route.abort('failed')
    } else await route.continue()
  })
  await customer.getByRole('button', { name: 'Submit for review' }).click()
  await expect(customer.getByRole('alert')).toBeVisible()
  await customer.getByRole('button', { name: 'Submit for review' }).click()
  await expect(customer.getByRole('heading', { name: 'Submission accepted' })).toBeVisible()
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBe(keys[1])
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
  await expect(page.getByText('100,000 zat', { exact: true }).first()).toBeVisible()
  const report = (await call(page, `/api/cases/${caseId}/report`)).data
  expect(report.verifications[0].result.receipt_state).toBe('VALID')
  expect(report.balances.credited_zat).toBe(0)
  expect(report.balances.candidate_zat).toBe(100000)
  expect(report.chain_observations[0].state).toBe('UNAVAILABLE')
  await page.getByRole('link', { name: 'Manage access' }).click()
  await page.getByRole('combobox', { name: 'Role', exact: true }).selectOption('reviewer')
  await page.getByLabel('case', { exact: true }).check()
  await page.getByLabel('claims', { exact: true }).check()
  await page.getByLabel('balances', { exact: true }).check()
  await page.getByLabel('evidence', { exact: true }).check()
  await page.getByLabel(/Sharing authorized/).check()
  await page.getByRole('button', { name: 'Create access code' }).click()
  const reviewerCode = await page.getByLabel('Private access code').inputValue()
  const reviewerContext = await browser.newContext({
    ignoreHTTPSErrors: true,
    baseURL: 'https://localhost:8443',
  })
  const reviewer = await reviewerContext.newPage()
  await login(reviewer, reviewerCode)
  await expect(reviewer.getByRole('heading', { name: 'Shared case report' })).toBeVisible()
  await expect(reviewer.getByText('Report-only access. Packet export is not permitted.')).toBeVisible()
  await expect(reviewer.getByText(note, { exact: true })).toHaveCount(0)
  await expect(reviewer.getByRole('heading', { name: 'Invoice', exact: true })).toHaveCount(0)
  await reviewer.getByRole('button', { name: /^Read / }).click()
  await expect(reviewer.getByLabel('Receipt preview')).toHaveValue(receipt.replaceAll('\r\n', '\n'))
  const originalDownload = reviewer.waitForEvent('download')
  await reviewer.getByRole('button', { name: 'Download original receipt', exact: true }).click()
  const originalPath = await (await originalDownload).path()
  expect(originalPath).toBeTruthy()
  expect(fs.readFileSync(originalPath!, 'utf8')).toBe(receipt)
  expect((await call(reviewer, `/api/cases/${caseId}/export`)).status).toBe(403)
  expect(
    (await call(reviewer, `/api/cases/${caseId}/verify`, { evidence_id: report.evidence[0].evidence_id }))
      .status,
  ).toBe(403)
  const issued = (await call(page, `/api/cases/${caseId}/grants`)).data.items
  const reviewerGrant = issued.find((g: { scope: { role: string } }) => g.scope.role === 'reviewer')
  await page
    .locator('article')
    .filter({ hasText: reviewerGrant.grant_id })
    .getByRole('button', { name: 'Revoke access' })
    .click()
  await reviewer.getByRole('button', { name: 'Refresh report' }).click()
  await expect(reviewer).toHaveURL('/connect')
  await page.getByLabel(/Permit export/).check()
  await page.getByRole('button', { name: 'Create access code' }).click()
  const exportCode = await page.getByLabel('Private access code').inputValue()
  await login(reviewer, exportCode)
  const packetDownload = reviewer.waitForEvent('download')
  await reviewer.getByRole('button', { name: 'Download authorized packet' }).click()
  const scopedPacket = JSON.parse(fs.readFileSync((await (await packetDownload).path()) as string, 'utf8'))
  expect(scopedPacket.schema_version).toBe('case-packet-v1')
  expect(scopedPacket.payload.disclosure_scope).toBe('REVIEWER_SCOPED')
  expect(scopedPacket.payload.replay_scope).toBe('LIMITED')
  expect(scopedPacket.payload.report.claims).toEqual([])
  expect(Buffer.from(scopedPacket.payload.evidence[0].receipt.data, 'base64').toString('utf8')).toBe(receipt)
  await expect(reviewer.getByText(/^Scoped packet downloaded/)).toBeVisible()
  await page.goto(`/report/${caseId}`)
  const merchantDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download authorized packet' }).click()
  const merchantPacket = JSON.parse(
    fs.readFileSync((await (await merchantDownload).path()) as string, 'utf8'),
  )
  expect(merchantPacket.payload.disclosure_scope).toBe('MERCHANT')
  expect(merchantPacket.payload.replay_scope).toBe('FULL_HISTORY')
  expect(Buffer.from(merchantPacket.payload.evidence[0].receipt.data, 'base64').toString('utf8')).toBe(
    receipt,
  )
  const python =
    process.env.ZECSOLVE_BROWSER_PYTHON ??
    path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const replay = JSON.parse(
    execFileSync(
      python,
      [
        path.join(root, 'apps/web/tests/replay_download.py'),
        (await (await merchantDownload).path()) as string,
      ],
      { encoding: 'utf8', cwd: root },
    ),
  )
  expect(replay.status).toBe('REPRODUCED')
  await page.goto('/connect')
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.goto('/cases')
  await expect(page).toHaveURL('/connect')
  expect(errors).toEqual([])
  await customerContext.close()
  await reviewerContext.close()
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
  await page.reload()
  await expect(page.getByRole('button', { name: 'Reset demo data' })).toBeVisible()
})

test('merchant sees tampered and missing evidence without credit', async ({ page }) => {
  await login(page, merchantCode)
  for (const scenario of [
    {
      receipt: fs.readFileSync(path.join(root, 'fixtures/negative/tampered-ock.json'), 'utf8'),
      raw: transaction,
      state: 'INVALID',
      label: 'Evidence rejected',
    },
    { receipt: null, raw: transaction, state: 'NONE', label: 'No receipt yet' },
    { receipt, raw: null, state: 'UNAVAILABLE', label: 'Data unavailable' },
  ]) {
    const id = await createCase(page)
    await upload(page, id, scenario.receipt, scenario.raw)
    await page.goto(`/cases/${id}`)
    const verified = page.waitForResponse(
      (r) => r.url().endsWith(`/api/cases/${id}/verify`) && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: 'Verify evidence', exact: true }).click()
    expect((await verified).status()).toBe(201)
    await expect(page.getByText(scenario.label, { exact: true }).first()).toBeVisible()
    const report = (await call(page, `/api/cases/${id}/report`)).data
    expect(report.verifications[0].result.receipt_state).toBe(scenario.state)
    expect(report.balances.credited_zat).toBe(0)
    await expect(page.getByRole('radio', { name: /^Approve output/ })).toBeDisabled()
  }
})

test('stale merchant decisions refresh for explicit review and noncredit decisions retry safely', async ({
  page,
}) => {
  await login(page, merchantCode)
  const id = await createCase(page)
  await page.goto(`/cases/${id}`)
  await page.getByLabel('Reason, kept in the audit trail').fill('Please send the missing payment receipt.')
  await page.getByRole('button', { name: 'Review decision' }).click()
  expect(
    (
      await call(page, `/api/cases/${id}/claims`, {
        note: 'Another accepted claim changes this version',
        reported_txid: null,
        disclosure_version: 'claim-disclosure-v1',
        processing_authorized: true,
        share_with_reviewers: false,
      })
    ).status,
  ).toBe(201)
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByText(/Review the refreshed case before another decision/)).toBeVisible()
  expect((await call(page, `/api/cases/${id}/report`)).data.decisions).toHaveLength(0)
  await page.getByRole('button', { name: 'Review decision' }).click()
  let dropped = false
  const keys: string[] = []
  await page.route(`**/api/cases/${id}/resolve`, async (route) => {
    keys.push(route.request().headers()['idempotency-key'])
    if (!dropped) {
      dropped = true
      await route.fetch()
      await route.abort('failed')
    } else await route.continue()
  })
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByText('Evidence requested.', { exact: true })).toBeVisible()
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBe(keys[1])
  const report = (await call(page, `/api/cases/${id}/report`)).data
  expect(report.decisions).toHaveLength(1)
  expect(report.case.state).toBe('AWAITING_EVIDENCE')
  expect(report.balances.credited_zat).toBe(0)
})

test('lost grant creation responses expose no replacement secret', async ({ page }) => {
  await login(page, merchantCode)
  const id = await createCase(page)
  await page.goto(`/cases/${id}/grants`)
  let dropped = false
  await page.route(`**/api/cases/${id}/grants`, async (route) => {
    if (route.request().method() !== 'POST') return route.continue()
    if (!dropped) {
      dropped = true
      await route.fetch()
      await route.abort('failed')
    } else await route.continue()
  })
  await page.getByRole('button', { name: 'Create access code' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name: 'Create access code' }).click()
  await expect(page.getByText(/its code cannot be recovered/)).toBeVisible()
  await expect(page.getByLabel('Private access code')).toHaveCount(0)
  expect((await call(page, `/api/cases/${id}/grants`)).data.items).toHaveLength(1)
  await page.getByRole('button', { name: 'Revoke access' }).click()
  await expect(page.getByText(/Access revoked/)).toBeVisible()
})

test('simulated approval retries once and a second invoice cannot reuse its output', async ({ page }) => {
  test.skip(!simulated, 'Requires the explicitly isolated --simulated-chain browser server.')
  await login(page, merchantCode)
  const id = await createCase(page)
  await upload(page, id, receipt, transaction)
  await page.goto(`/cases/${id}`)
  await page.getByRole('button', { name: 'Verify evidence', exact: true }).click()
  await expect(page.getByText('Output recovered', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Check chain now', exact: true }).click()
  await expect(page.getByText('Simulated confirmation', { exact: true })).toBeVisible()
  await page.getByRole('radio', { name: /^Approve output/ }).check()
  await page
    .getByLabel('Reason, kept in the audit trail')
    .fill('Public fixture simulated approval for browser acceptance.')
  await page.getByRole('button', { name: 'Review decision' }).click()
  let dropped = false
  const keys: string[] = []
  await page.route(`**/api/cases/${id}/resolve`, async (route) => {
    keys.push(route.request().headers()['idempotency-key'])
    if (!dropped) {
      dropped = true
      await route.fetch()
      await route.abort('failed')
    } else await route.continue()
  })
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByText('Output approved.', { exact: true })).toBeVisible()
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBe(keys[1])
  const report = (await call(page, `/api/cases/${id}/report`)).data
  expect(report.balances.credited_zat).toBe(100000)
  expect(report.balances.outstanding_zat).toBe(100000)
  expect(report.balances.candidate_zat).toBe(0)
  expect(report.case.state).toBe('UNDER_REVIEW')
  expect(report.decisions).toHaveLength(1)
  const second = await createCase(page)
  await upload(page, second, receipt, transaction)
  await page.goto(`/cases/${second}`)
  const secondVerified = page.waitForResponse(
    (r) => r.url().endsWith(`/api/cases/${second}/verify`) && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Verify evidence', exact: true }).click()
  expect((await secondVerified).status()).toBe(201)
  await expect(page.getByRole('radio', { name: /^Approve output/ })).toBeDisabled()
  const conflict = (await call(page, `/api/cases/${second}/report`)).data
  expect(conflict.balances.findings).toContain('DUPLICATE_CLAIM')
  expect(conflict.balances.credited_zat).toBe(0)
  expect(conflict.balances).not.toHaveProperty('foreign_invoice_id')
})

test('keyboard and accessibility checks cover login, invoice and scoped submission on mobile', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/connect')
  await page.getByLabel('Access code', { exact: true }).focus()
  await expect(page.getByLabel('Access code', { exact: true })).toBeFocused()
  await checkAccessibility(page)
  await page.goto('/connect?code=ignored')
  await expect(page).toHaveURL('/connect')
  await expect(page.getByLabel('Access code', { exact: true })).toHaveValue('')
  // Fragment is removed before exchange and never treated as a CSS selector.
  await page.goto(`/connect#code=${merchantCode}`)
  await expect.poll(() => page.evaluate(() => location.hash === '')).toBe(true)
  await page.getByLabel('Access code', { exact: true }).press('Enter')
  await expect(page).toHaveURL('/cases')
  await page.goto('/cases/new')
  await checkAccessibility(page)
  const id = await createCase(page)
  const grant = await call(page, `/api/cases/${id}/grants`, { scope: { role: 'customer' }, ttl_hours: 1 })
  await login(page, grant.data.access_code)
  await expect(page).toHaveURL(`/submit/${id}`)
  await checkAccessibility(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('case listing paginates and filters the server summaries', async ({ page }) => {
  await login(page, merchantCode)
  const ids: string[] = []
  for (let i = 0; i < 26; i++) ids.push(await createCase(page))
  const closedId = ids[0]!
  expect((await call(page, `/api/cases/${closedId}/resolve`, { action: 'CLOSE_UNRESOLVED', expected_case_version: 1, verification_id: null, reason: 'Public fixture case closed for browser filter test.' })).status).toBe(201)
  await page.goto('/cases')
  await expect(page.locator('tbody tr')).toHaveCount(25)
  await page.getByRole('button', { name: 'Load more cases' }).click()
  await expect.poll(() => page.locator('tbody tr').count()).toBeGreaterThan(25)
  await page.getByRole('combobox', { name: 'Filter state' }).selectOption('CLOSED_UNRESOLVED')
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await expect(page.getByRole('link', { name: closedId, exact: true })).toBeVisible()
})

test('local expiry returns to login and missing CSRF can recover with a new session', async ({ page }) => {
  await page.clock.install()
  await login(page, merchantCode)
  const id = await createCase(page)
  await page.goto(`/submit/${id}`)
  await page.context().clearCookies({ name: '__Host-zecsolve_csrf' })
  await page.getByLabel('I authorize this processing.').check()
  await page.getByRole('button', { name: 'Submit for review' }).click()
  await expect(page.getByRole('alert')).toContainText('Session protection is missing')
  await login(page, merchantCode)
  await page.clock.fastForward(8 * 60 * 60 * 1000 + 1000)
  await expect(page).toHaveURL('/connect')
  await expect(page.getByRole('alert')).toContainText('expired or was revoked')
})
