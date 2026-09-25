import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'

const databaseURL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

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

  test('signs out only the current cookie-selected session', async ({
    activeAccount,
    browser,
    request,
  }) => {
    const secondContext = await browser.newContext()
    const pool = new Pool({ connectionString: databaseURL })
    const secondIpAddress = '198.51.100.250'

    try {
      const secondRequest = secondContext.request
      const signInHeaders = { 'x-forwarded-for': activeAccount.ipAddress }

      const firstSignIn = await request.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: signInHeaders,
      })
      const secondSignIn = await secondRequest.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': secondIpAddress },
      })

      expect(firstSignIn.status()).toBe(200)
      expect(secondSignIn.status()).toBe(200)

      const sessionsBefore = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [activeAccount.accountId],
      )
      expect(sessionsBefore.rows).toHaveLength(2)

      const signOut = await request.post(
        '/api/auth/sign-out?accountId=must-not-select-a-session',
        {
          data: { accountId: activeAccount.accountId },
          headers: {
            cookie:
              firstSignIn
                .headers()
                ['set-cookie']?.match(/better-auth\.session_token=[^;]+/)?.[0] ?? '',
            origin: 'http://localhost:7000',
          },
        },
      )

      expect(signOut.status()).toBe(200)
      expect(await signOut.json()).toEqual({ success: true })
      expect(signOut.headers()['set-cookie']).toMatch(
        /better-auth\.session_token=; Max-Age=0; Path=\//,
      )

      const sessionsAfter = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [activeAccount.accountId],
      )
      expect(sessionsAfter.rows).toHaveLength(1)
      expect(
        await request.get('/api/auth/get-session').then((response) => response.json()),
      ).toBe(null)
      const secondSession = await secondRequest.get('/api/auth/get-session')
      expect(secondSession.status()).toBe(200)
      expect(await secondSession.json()).not.toBe(null)
    } finally {
      await pool.query('delete from better_auth_rate_limits where key like $1', [
        `${secondIpAddress}%`,
      ])
      await pool.end()
      await secondContext.close()
    }
  })
})
