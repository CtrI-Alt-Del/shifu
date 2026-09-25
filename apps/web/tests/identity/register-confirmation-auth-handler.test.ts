import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'

const databaseURL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test.describe('same-origin pending-confirmation auth handler', () => {
  test('clears only the pending verification context without creating a session', async ({
    pendingAccount,
    request,
  }) => {
    const pool = new Pool({ connectionString: databaseURL })

    try {
      const signIn = await request.post('/api/auth/sign-in/identity', {
        data: { email: pendingAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': pendingAccount.ipAddress },
      })

      expect(signIn.status()).toBe(200)
      expect(signIn.headers()['set-cookie']).toMatch(
        /shifu-pending-flow=[^;]+; Max-Age=900; Path=\//,
      )
      expect(signIn.headers()['set-cookie']).not.toContain('better-auth.session_token=')

      const verificationsBefore = await pool.query(
        'select identifier from better_auth_verifications where value like $1',
        [`%${pendingAccount.accountId}%`],
      )
      const sessionsBefore = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [pendingAccount.accountId],
      )
      expect(verificationsBefore.rows).toHaveLength(1)
      expect(sessionsBefore.rows).toHaveLength(0)

      const signOut = await request.post(
        '/api/auth/pending-confirmation/sign-out?accountId=must-not-select-a-session',
        {
          data: { accountId: pendingAccount.accountId },
          headers: {
            cookie:
              signIn.headers()['set-cookie']?.match(/shifu-pending-flow=[^;]+/)?.[0] ??
              '',
            origin: 'http://localhost:7000',
          },
        },
      )

      expect(signOut.status()).toBe(200)
      expect(await signOut.json()).toEqual({})
      expect(signOut.headers()['set-cookie']).toMatch(
        /shifu-pending-flow=[^;]+; Max-Age=0; Path=\//,
      )

      const verificationsAfter = await pool.query(
        'select identifier from better_auth_verifications where value like $1',
        [`%${pendingAccount.accountId}%`],
      )
      const sessionsAfter = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [pendingAccount.accountId],
      )
      expect(verificationsAfter.rows).toHaveLength(0)
      expect(sessionsAfter.rows).toHaveLength(0)

      const repeatedSignOut = await request.post(
        '/api/auth/pending-confirmation/sign-out',
        {
          data: {},
          headers: { origin: 'http://localhost:7000' },
        },
      )
      expect(repeatedSignOut.status()).toBe(200)
      expect(await repeatedSignOut.json()).toEqual({})
    } finally {
      await pool.end()
    }
  })
})
