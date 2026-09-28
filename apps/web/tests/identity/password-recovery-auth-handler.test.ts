import { createHash } from 'node:crypto'

import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'

const DATABASE_URL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test.describe('same-origin password recovery auth handlers', () => {
  test('returns a generic result with an opaque context for an unknown address', async ({
    request,
  }, testInfo) => {
    const email = `unknown-recovery-${testInfo.testId}@shifu.local`
    const response = await request.post('/api/auth/password-recovery', {
      data: { email },
    })

    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ accepted: true })
    const cookie = response.headers()['set-cookie'] ?? ''
    expect(cookie).toMatch(/shifu-password-recovery=[^;]+; Max-Age=3600; Path=\//)
    expect(cookie).not.toContain(email)

    const status = await request.get('/api/auth/password-recovery/status')
    expect(status.status()).toBe(200)
    expect(await status.json()).toEqual({ retryAfterSeconds: 60, state: 'cooldown' })
  })

  test('matches eligible and decoy context status after cooldown', async ({
    activeAccount,
    browser,
  }, testInfo) => {
    const pool = new Pool({ connectionString: DATABASE_URL })
    const realContext = await browser.newContext()
    const decoyContext = await browser.newContext()
    const decoyIpAddress = '198.51.100.253'
    const startedAt = new Date()

    try {
      const [realRequest, decoyRequest] = await Promise.all([
        realContext.request.post('/api/auth/password-recovery', {
          data: { email: activeAccount.email },
          headers: { 'x-forwarded-for': activeAccount.ipAddress },
        }),
        decoyContext.request.post('/api/auth/password-recovery', {
          data: { email: `unknown-recovery-${testInfo.testId}@shifu.local` },
          headers: { 'x-forwarded-for': decoyIpAddress },
        }),
      ])
      expect(realRequest.status()).toBe(200)
      expect(decoyRequest.status()).toBe(200)
      expect(await realRequest.json()).toEqual({ accepted: true })
      expect(await decoyRequest.json()).toEqual({ accepted: true })

      await pool.query(
        `
          update identity_account_action_tokens
          set delivery_status = 'delivered', issued_at = now() - interval '61 seconds',
            updated_at = now()
          where account_id = $1 and type = 'password-recovery'
        `,
        [activeAccount.accountId],
      )
      const decoyContextUpdate = await pool.query(
        `
          update better_auth_verifications
          set expires_at = now() + interval '59 minutes', updated_at = now()
          where id = (
            select id from better_auth_verifications
            where value like '%"isDecoy":true%' and created_at >= $1
            order by created_at desc
            limit 1
          )
        `,
        [startedAt],
      )
      expect(decoyContextUpdate.rowCount).toBe(1)

      const [realStatus, decoyStatus] = await Promise.all([
        realContext.request.get('/api/auth/password-recovery/status'),
        decoyContext.request.get('/api/auth/password-recovery/status'),
      ])
      const realBody = await realStatus.json()
      const decoyBody = await decoyStatus.json()
      expect(realStatus.status()).toBe(200)
      expect(decoyStatus.status()).toBe(200)
      expect(decoyBody).toEqual(realBody)
      expect(realBody).toEqual({ retryAfterSeconds: null, state: 'ready' })
    } finally {
      await pool.query('delete from better_auth_rate_limits where key like $1', [
        `${decoyIpAddress}%`,
      ])
      await pool.end()
      await realContext.close()
      await decoyContext.close()
    }
  })

  test('rejects a malformed reset token without clearing an existing session', async ({
    activeAccount,
    request,
  }, testInfo) => {
    const signIn = await request.post('/api/auth/sign-in/identity', {
      data: { email: activeAccount.email, password: signInPassword },
      headers: { 'x-forwarded-for': activeAccount.ipAddress },
    })
    expect(signIn.status()).toBe(200)

    const reset = await request.post('/api/auth/password-reset', {
      data: {
        password: 'password-123',
        passwordConfirmation: 'password-123',
        token: 'invalid',
      },
      headers: { origin: new URL(testInfo.project.use.baseURL as string).origin },
    })

    expect(reset.status()).toBe(200)
    expect(await reset.json()).toEqual({ redirectTo: '/login', result: 'invalid' })
    expect(
      await request.get('/api/auth/get-session').then((response) => response.json()),
    ).not.toBe(null)
  })

  test('deletes all technical sessions and clears the current cookie after reset', async ({
    activeAccount,
    browser,
    request,
  }, testInfo) => {
    const token = `${activeAccount.accountId.slice(0, 5)}${'r'.repeat(38)}`
    const pool = new Pool({ connectionString: DATABASE_URL })
    const secondBrowser = await browser.newContext()
    const secondIpAddress = '198.51.100.252'

    try {
      await seedRecoveryToken(pool, activeAccount.accountId, token)
      const firstSignIn = await request.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': activeAccount.ipAddress },
      })
      const secondSignIn = await secondBrowser.request.post(
        '/api/auth/sign-in/identity',
        {
          data: { email: activeAccount.email, password: signInPassword },
          headers: { 'x-forwarded-for': secondIpAddress },
        },
      )
      expect(firstSignIn.status()).toBe(200)
      expect(secondSignIn.status()).toBe(200)

      const reset = await request.post('/api/auth/password-reset', {
        data: {
          password: 'new-password-123',
          passwordConfirmation: 'new-password-123',
          token,
        },
        headers: { origin: new URL(testInfo.project.use.baseURL as string).origin },
      })

      expect(reset.status()).toBe(200)
      expect(await reset.json()).toEqual({
        redirectTo: '/login',
        requiresEmailConfirmation: false,
        result: 'reset',
      })
      expect(reset.headers()['set-cookie']).toMatch(
        /better-auth\.session_token=; Max-Age=0; Path=\//,
      )

      const sessions = await pool.query(
        'select token from better_auth_sessions where user_id = $1',
        [activeAccount.accountId],
      )
      expect(sessions.rows).toHaveLength(0)
      expect(
        await request.get('/api/auth/get-session').then((response) => response.json()),
      ).toBe(null)
      expect(
        await secondBrowser.request
          .get('/api/auth/get-session')
          .then((response) => response.json()),
      ).toBe(null)
    } finally {
      await pool.query('delete from better_auth_rate_limits where key like $1', [
        `${secondIpAddress}%`,
      ])
      await pool.end()
      await secondBrowser.close()
    }
  })

  test('keeps reset successful and clears the current cookie when session cleanup fails', async ({
    activeAccount,
    request,
  }, testInfo) => {
    const token = `${activeAccount.accountId.slice(0, 5)}${'s'.repeat(38)}`
    const pool = new Pool({ connectionString: DATABASE_URL })

    try {
      await seedRecoveryToken(pool, activeAccount.accountId, token)
      await request.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': activeAccount.ipAddress },
      })
      await createSessionDeletionFailureTrigger(pool, activeAccount.accountId)

      const reset = await request.post('/api/auth/password-reset', {
        data: {
          password: 'new-password-123',
          passwordConfirmation: 'new-password-123',
          token,
        },
        headers: { origin: new URL(testInfo.project.use.baseURL as string).origin },
      })

      expect(reset.status()).toBe(200)
      expect(await reset.json()).toEqual({
        redirectTo: '/login',
        requiresEmailConfirmation: false,
        result: 'reset',
      })
      expect(reset.headers()['set-cookie']).toMatch(
        /better-auth\.session_token=; Max-Age=0; Path=\//,
      )
      expect(
        await request.get('/api/auth/get-session').then((response) => response.json()),
      ).toBe(null)
    } finally {
      await removeSessionDeletionFailureTrigger(pool)
      await pool.end()
    }
  })
})

async function createSessionDeletionFailureTrigger(pool: Pool, accountId: string) {
  await pool.query(`
    create or replace function shifu_password_reset_session_cleanup_failure()
    returns trigger language plpgsql as $$
    begin
      if old.user_id = '${accountId}' then
        raise exception 'password_reset_session_cleanup_failed';
      end if;
      return old;
    end;
    $$;
    create trigger shifu_password_reset_session_cleanup_failure
    before delete on better_auth_sessions
    for each row execute function shifu_password_reset_session_cleanup_failure();
  `)
}

async function removeSessionDeletionFailureTrigger(pool: Pool) {
  await pool.query(`
    drop trigger if exists shifu_password_reset_session_cleanup_failure on better_auth_sessions;
    drop function if exists shifu_password_reset_session_cleanup_failure();
  `)
}

async function seedRecoveryToken(pool: Pool, accountId: string, token: string) {
  const tokenId = `${accountId.slice(0, 5)}${'t'.repeat(21)}`
  const communicationId = `${accountId.slice(0, 5)}${'c'.repeat(21)}`
  await pool.query(
    `
      insert into identity_account_action_tokens (
        id, account_id, type, status, token_hash, issued_at, expires_at, updated_at,
        communication_id, pending_handle_hash, delivery_status
      ) values ($1, $2, 'password-recovery', 'pending', $3, now(),
        now() + interval '1 hour', now(), $4, null, 'delivered')
    `,
    [tokenId, accountId, hash(token), communicationId],
  )
}

function hash(value: string) {
  return createHash('sha256').update(value).digest('hex')
}
