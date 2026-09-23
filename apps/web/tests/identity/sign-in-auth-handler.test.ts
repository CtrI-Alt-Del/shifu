import { createHash } from 'node:crypto'

import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'

const DATABASE_URL =
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
    await seedPendingConfirmationToken(pendingAccount)
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

  test('creates a session only after the activating browser presents its matching pending context', async ({
    browser,
    pendingAccount,
  }) => {
    const confirmationToken = await seedPendingConfirmationToken(pendingAccount)
    const pendingBrowser = await browser.newContext()

    try {
      const signIn = await pendingBrowser.request.post('/api/auth/sign-in/identity', {
        data: { email: pendingAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': pendingAccount.ipAddress },
      })
      expect(signIn.status()).toBe(200)

      const confirmation = await pendingBrowser.request.post('/api/auth/confirm-email', {
        data: { token: confirmationToken },
      })
      expect(confirmation.status()).toBe(200)
      expect(await confirmation.json()).toEqual({
        result: 'activated',
        redirectTo: '/',
      })
      await expect(
        pendingBrowser
          .cookies()
          .then((cookies) =>
            cookies.some((cookie) => cookie.name === 'better-auth.session_token'),
          ),
      ).resolves.toBe(true)
    } finally {
      await pendingBrowser.close()
    }
  })

  test('activates from another browser without creating a session', async ({
    browser,
    pendingAccount,
  }) => {
    const confirmationToken = await seedPendingConfirmationToken(pendingAccount)
    const pendingBrowser = await browser.newContext()
    const otherBrowser = await browser.newContext()

    try {
      const signIn = await pendingBrowser.request.post('/api/auth/sign-in/identity', {
        data: { email: pendingAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': pendingAccount.ipAddress },
      })
      expect(signIn.status()).toBe(200)

      const confirmation = await otherBrowser.request.post('/api/auth/confirm-email', {
        data: { token: confirmationToken },
      })
      expect(confirmation.status()).toBe(200)
      expect(await confirmation.json()).toEqual({
        result: 'activated',
        redirectTo: '/login',
      })
      expect(
        (await otherBrowser.cookies()).some(
          (cookie) => cookie.name === 'better-auth.session_token',
        ),
      ).toBe(false)
    } finally {
      await Promise.all([pendingBrowser.close(), otherBrowser.close()])
    }
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

async function seedPendingConfirmationToken(account: {
  accountId: string
  email: string
}) {
  const pool = new Pool({ connectionString: DATABASE_URL })
  const confirmationToken = `${account.accountId.slice(0, 5)}${'a'.repeat(38)}`
  const tokenId = `${account.accountId.slice(0, 5)}${'b'.repeat(21)}`
  const communicationId = `${account.accountId.slice(0, 5)}${'c'.repeat(21)}`

  try {
    await pool.query(
      `
        insert into identity_account_action_tokens (
          id, account_id, type, status, token_hash, issued_at, expires_at, updated_at,
          communication_id, pending_handle_hash, delivery_status
        ) values ($1, $2, 'email-confirmation', 'pending', $3, now(), now() + interval '24 hours',
          now(), $4, $5, null)
      `,
      [
        tokenId,
        account.accountId,
        hash(confirmationToken),
        communicationId,
        hash(`${account.email}-pending-handle`),
      ],
    )
  } finally {
    await pool.end()
  }

  return confirmationToken
}

function hash(value: string) {
  return createHash('sha256').update(value).digest('hex')
}
