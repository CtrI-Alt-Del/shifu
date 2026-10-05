import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'
import {
  IdentityActionTokenFaker,
  IdentityEmailFaker,
  IdentityRegistrationDataFaker,
} from '../../src/core/identity/fakers'

const DATABASE_URL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test.describe('same-origin registration confirmation auth handlers', () => {
  test('creates a pending handoff and preserves its cooldown through the BFF', async ({
    request,
  }, testInfo) => {
    const registration = IdentityRegistrationDataFaker.fake({
      email: IdentityEmailFaker.fake({
        domain: 'shifu.local',
        suffix: `${testInfo.parallelIndex}-${testInfo.retry}`,
      }),
    })
    const response = await request.post('/api/auth/register/identity', {
      data: {
        password: 'shifu-test-password',
        ...registration,
      },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ redirectTo: '/pending-confirmation' })
    expect(response.headers()['set-cookie']).toContain('shifu-pending-flow=')

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
      data: { token: IdentityActionTokenFaker.fake() },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ result: 'invalid', redirectTo: '/login' })
  })

  test('clears only the pending verification context without creating a session', async ({
    pendingAccount,
    request,
  }, testInfo) => {
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
        headers: {
          cookie,
          origin: new URL(testInfo.project.use.baseURL as string).origin,
        },
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
