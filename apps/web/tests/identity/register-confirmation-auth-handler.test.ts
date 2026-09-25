import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'

const DATABASE_URL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test.describe('same-origin registration confirmation auth handlers', () => {
  test('creates a pending handoff and preserves its cooldown through the BFF', async ({
    request,
  }, testInfo) => {
    const email = `registration-handler-${testInfo.parallelIndex}-${testInfo.retry}@shifu.local`
    const registration = await request.post('/api/auth/register/identity', {
      data: {
        displayName: 'Registration Handler Learner',
        email,
        password: 'shifu-test-password',
      },
    })

    expect(registration.status()).toBe(200)
    expect(await registration.json()).toEqual({ redirectTo: '/pending-confirmation' })
    expect(registration.headers()['set-cookie']).toContain('shifu-pending-flow=')

    const status = await request.get('/api/auth/pending-confirmation')
    expect(status.status()).toBe(200)
    expect(await status.json()).toEqual({
      state: 'cooldown',
      retryAfterSeconds: expect.any(Number),
    })
  })

  test('maps an unknown confirmation token through the registered BFF handler', async ({
    request,
  }) => {
    const response = await request.post('/api/auth/confirm-email', {
      data: { token: 'A'.repeat(43) },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ result: 'invalid', redirectTo: '/login' })
  })

  test('clears only the pending verification context without creating a session', async ({
    pendingAccount,
    request,
  }) => {
    const pool = new Pool({ connectionString: DATABASE_URL })

    try {
      const signIn = await request.post('/api/auth/sign-in/identity', {
        data: { email: pendingAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': pendingAccount.ipAddress },
      })
      const cookie =
        signIn.headers()['set-cookie']?.match(/shifu-pending-flow=[^;]+/)?.[0] ?? ''

      const signOut = await request.post('/api/auth/pending-confirmation/sign-out', {
        data: {},
        headers: { cookie, origin: 'http://localhost:7000' },
      })

      expect(signOut.status()).toBe(200)
      expect(await signOut.json()).toEqual({})
      expect(signOut.headers()['set-cookie']).toMatch(
        /shifu-pending-flow=[^;]+; Max-Age=0; Path=\//,
      )
      const sessions = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [pendingAccount.accountId],
      )
      expect(sessions.rows).toHaveLength(0)
    } finally {
      await pool.end()
    }
  })
})
