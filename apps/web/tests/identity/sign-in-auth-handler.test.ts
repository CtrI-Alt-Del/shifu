import { expect, signInPassword, test } from '../playwright'

test.describe('same-origin sign-in auth handler', () => {
  test('creates a fixed-lifetime technical session for an active account', async ({
    request,
    activeAccount,
  }) => {
    const response = await request.post('/api/auth/sign-in/identity', {
      data: { email: activeAccount.email, password: signInPassword },
      headers: { 'x-forwarded-for': activeAccount.ipAddress },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ access: 'protected', redirectTo: '/' })
    expect(response.headers()['set-cookie']).toMatch(
      /better-auth\.session_token=[^;]+; Max-Age=2592000; Path=\//,
    )
  })

  test('isolates a pending account in an opaque fifteen-minute handoff', async ({
    request,
    pendingAccount,
  }) => {
    const response = await request.post('/api/auth/sign-in/identity', {
      data: { email: pendingAccount.email, password: signInPassword },
      headers: { 'x-forwarded-for': pendingAccount.ipAddress },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({
      access: 'activation-only',
      redirectTo: '/pending-confirmation',
    })
    const cookie = response.headers()['set-cookie']
    expect(cookie).toMatch(/shifu-pending-flow=[^;]+; Max-Age=900; Path=\//)
    expect(cookie).not.toContain(pendingAccount.email)
    expect(cookie).not.toContain(pendingAccount.accountId)
    expect(cookie).not.toContain('better-auth.session_token=')
  })

  test('returns the generic rejection contract without a session cookie', async ({
    request,
  }) => {
    const response = await request.post('/api/auth/sign-in/identity', {
      data: { email: 'unknown@shifu.local', password: 'not-a-real-password' },
      headers: { 'x-forwarded-for': '10.0.0.254' },
    })

    expect(response.status()).toBe(401)
    expect(response.headers()['content-type']).toMatch(/application\/json/)
    expect(await response.json()).toEqual({
      code: 'invalid_credentials',
      message: 'E-mail ou senha inválidos.',
    })
    expect(response.headers()['set-cookie'] ?? '').not.toContain(
      'better-auth.session_token=',
    )
  })

  test('does not expose the internal API token endpoint to the browser', async ({
    request,
  }) => {
    const response = await request.get('/api/auth/token')

    expect(response.status()).toBe(404)
  })
})
