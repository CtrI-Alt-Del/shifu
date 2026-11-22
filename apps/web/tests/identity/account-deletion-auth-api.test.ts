import type { APIRequestContext } from '@playwright/test'

import { expect, signInPassword, test } from '../playwright'
import type { SignInHandlerAccount } from '../fixtures/identity-module-fixture'

function sameOriginHeaders() {
  return { origin: new URL(test.info().project.use.baseURL as string).origin }
}

async function signIn(request: APIRequestContext, account: SignInHandlerAccount) {
  const response = await request.post('/api/auth/sign-in/identity', {
    data: { email: account.email, password: signInPassword },
    headers: { ...sameOriginHeaders(), 'x-forwarded-for': account.ipAddress },
  })
  expect(response.status()).toBe(200)
  return response
}

async function setAccountProxyScenario(
  request: APIRequestContext,
  accountId: string,
  scenario: 'account-erasure-ack-unavailable' | 'account-erasure-target-gone',
) {
  const proxyPort = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
  if (!proxyPort) {
    throw new Error('The account test requires SHIFU_ACCOUNT_TEST_PROXY_PORT.')
  }
  const controlURL = `http://127.0.0.1:${proxyPort}/__account-control/${accountId}`
  const response = await request.post(controlURL, { data: { scenario } })
  expect(response.status()).toBe(200)
  return controlURL
}

test.describe('account deletion BFF handlers', () => {
  test('requires same-origin preparation and preserves the account after a wrong password', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    expect(
      (
        await request.post('/api/auth/account/deletion/prepare', {
          data: {},
          headers: sameOriginHeaders(),
        })
      ).status(),
    ).toBe(401)
    expect(
      (
        await request.post('/api/internal/identity/account-closure', {
          data: {
            account_id: activeAccount.accountId,
            erasure_id: 'e46f9b09-1454-4849-a1d1-ed3e62635ca6',
          },
        })
      ).status(),
    ).toBe(401)

    await signIn(request, activeAccount)
    const foreign = await request.post('/api/auth/account/deletion/prepare', {
      data: {},
      headers: { origin: 'https://foreign.invalid' },
    })
    expect(foreign.status()).toBe(403)

    const prepared = await request.post('/api/auth/account/deletion/prepare', {
      data: {},
      headers: sameOriginHeaders(),
    })
    expect(prepared.status()).toBe(201)
    expect(prepared.headers()['cache-control']).toBe('no-store')
    const preparedBody: unknown = await prepared.json()
    expect(preparedBody).toEqual({ state: 'prepared' })
    expect(prepared.headers()['set-cookie']).toContain('HttpOnly')
    expect(prepared.headers()['set-cookie']).toContain('Secure')
    expect(prepared.headers()['set-cookie']).toContain('SameSite=Strict')
    expect(prepared.headers()['set-cookie']).toContain('Max-Age=86400')
    expect(JSON.stringify(preparedBody)).not.toContain(activeAccount.accountId)
    expect(JSON.stringify(preparedBody)).not.toContain(activeAccount.email)

    const wrongPassword = await request.post('/api/auth/account/deletion', {
      data: { currentPassword: 'incorrect-password', confirmed: true },
      headers: sameOriginHeaders(),
    })
    expect(wrongPassword.status()).toBe(403)
    expect((await wrongPassword.json()).code).toBe('invalid_current_password')
    expect((await request.get('/api/auth/account')).status()).toBe(200)
    expect(
      (
        await request.post('/api/auth/delete-user', {
          data: { userId: activeAccount.accountId },
        })
      ).status(),
    ).toBe(404)
  })

  test('closes the canonical identity, revokes browser capability and returns minimal recovery status', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    await signIn(request, activeAccount)

    const issuedCapability = await request.post(
      '/api/identity/browser-data-capabilities',
      { data: {}, headers: sameOriginHeaders() },
    )
    expect(issuedCapability.status()).toBe(201)
    expect(issuedCapability.headers()['cache-control']).toBe('no-store')
    const capabilityBody: unknown = await issuedCapability.json()
    expect(capabilityBody).toEqual({ capability: expect.any(String) })
    const capability = (capabilityBody as { capability: string }).capability
    expect(capability).toMatch(/^[A-Za-z0-9_-]{32,256}$/)
    expect(issuedCapability.url()).not.toContain(capability)

    const activeCapability = await request.post(
      '/api/identity/browser-data-validations',
      { data: { capability } },
    )
    expect(activeCapability.status()).toBe(200)
    expect(activeCapability.headers()['cache-control']).toBe('no-store')
    expect(await activeCapability.json()).toEqual({ state: 'active' })

    const prepared = await request.post('/api/auth/account/deletion/prepare', {
      data: {},
      headers: sameOriginHeaders(),
    })
    expect(prepared.status()).toBe(201)

    const closed = await request.post('/api/auth/account/deletion', {
      data: { currentPassword: signInPassword, confirmed: true },
      headers: sameOriginHeaders(),
    })
    expect(closed.status()).toBe(202)
    expect(closed.headers()['cache-control']).toBe('no-store')
    const closureBody: unknown = await closed.json()
    expect(closureBody).toMatchObject({
      state: 'closed',
      closedAt: expect.any(String),
      erasure: expect.stringMatching(/^(pending|completed)$/),
    })
    expect(JSON.stringify(closureBody)).not.toContain(activeAccount.accountId)
    expect(JSON.stringify(closureBody)).not.toContain(activeAccount.email)

    const oldSession = await request.get('/api/auth/account')
    expect(oldSession.status()).toBe(401)
    const revokedCapability = await request.post(
      '/api/identity/browser-data-validations',
      { data: { capability } },
    )
    expect(revokedCapability.status()).toBe(200)
    expect(await revokedCapability.json()).toEqual({ state: 'revoked' })

    const recovery = await request.get('/api/auth/account/deletion')
    expect(recovery.status()).toBe(200)
    expect(recovery.headers()['cache-control']).toBe('no-store')
    const recoveryBody: unknown = await recovery.json()
    expect(recoveryBody).toMatchObject({
      state: 'closed',
      erasure: expect.stringMatching(/^(pending|completed)$/),
    })
    expect(JSON.stringify(recoveryBody)).not.toContain(activeAccount.accountId)
    expect(JSON.stringify(recoveryBody)).not.toContain(activeAccount.email)

    const unknownCapability = await request.post(
      '/api/identity/browser-data-validations',
      { data: { capability: `${capability}unknown` } },
    )
    expect(unknownCapability.status()).toBe(200)
    expect(await unknownCapability.json()).toEqual({ state: 'revoked' })
  })

  test('recovers a signed status after cleanup acknowledgement fails', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    await signIn(request, activeAccount)
    const prepared = await request.post('/api/auth/account/deletion/prepare', {
      data: {},
      headers: sameOriginHeaders(),
    })
    expect(prepared.status()).toBe(201)

    const controlURL = await setAccountProxyScenario(
      request,
      activeAccount.accountId,
      'account-erasure-ack-unavailable',
    )
    const interrupted = await request.post('/api/auth/account/deletion', {
      data: { currentPassword: signInPassword, confirmed: true },
      headers: sameOriginHeaders(),
    })
    expect(interrupted.status()).toBe(503)

    const unavailableStatus = await request.get('/api/auth/account/deletion')
    expect(unavailableStatus.status()).toBe(503)

    expect((await request.delete(controlURL)).status()).toBe(200)
    const recovered = await request.get('/api/auth/account/deletion')
    expect(recovered.status()).toBe(200)
    expect(recovered.headers()['cache-control']).toBe('no-store')
    expect(await recovered.json()).toMatchObject({
      state: 'closed',
      erasure: 'completed',
    })

    await setAccountProxyScenario(
      request,
      activeAccount.accountId,
      'account-erasure-target-gone',
    )
    const completedWithoutTarget = await request.get('/api/auth/account/deletion')
    expect(completedWithoutTarget.status()).toBe(200)
    expect(await completedWithoutTarget.json()).toMatchObject({
      state: 'closed',
      erasure: 'completed',
    })
  })
})
