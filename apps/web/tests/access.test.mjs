import assert from 'node:assert/strict'
import test from 'node:test'
import { homeFor, mayVisit, csrfToken } from '../src/api/access.ts'
import { retryIdentity, pendingKey, finishRequest, setRetryPrincipal } from '../src/api/retry.ts'
import { parseZec } from '../src/lib/money.ts'

test('scoped roles cannot navigate to merchant or foreign-case pages', () => {
  for (const role of ['customer', 'reviewer']) {
    const access = { role, case_id: 'own' }
    for (const page of ['cases', 'case', 'grants', 'new-case', 'report'])
      assert.equal(mayVisit(access, page, 'own'), false)
    assert.equal(mayVisit(access, role === 'customer' ? 'submit' : 'review', 'foreign'), false)
    assert.equal(mayVisit(access, role === 'customer' ? 'submit' : 'review', 'own'), true)
    assert.equal(homeFor(access), role === 'customer' ? '/submit/own' : '/review/own')
  }
})
test('CSRF parsing matches exact cookie name', () => {
  assert.equal(csrfToken('other__Host-zecsolve_csrf=bad'), null)
  assert.equal(csrfToken('other=x; __Host-zecsolve_csrf=correct; last=y'), 'correct')
})
test('lost responses reuse pending keys, scoped by actor, route and unchanged body', async () => {
  setRetryPrincipal('grant-a')
  const id = await retryIdentity('/case/evidence', '{"receipt":"private"}')
  assert.equal(pendingKey(id, 'first'), 'first')
  assert.equal(pendingKey(id, 'second'), 'first')
  assert.notEqual(id, await retryIdentity('/case/evidence', '{"receipt":"changed"}'))
  setRetryPrincipal('grant-b')
  assert.notEqual(id, await retryIdentity('/case/evidence', '{"receipt":"private"}'))
  assert.equal(id.includes('private'), false)
  finishRequest(id)
  assert.equal(pendingKey(id, 'third'), 'third')
})
test('ZEC input retains exact zatoshis without float rounding', () => {
  assert.equal(parseZec('0.00000001'), 1)
  assert.equal(parseZec('21000000'), 2100000000000000)
  assert.equal(parseZec('0.000000001'), null)
  assert.equal(parseZec('1e3'), null)
})
