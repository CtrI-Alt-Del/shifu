import { createHash } from 'node:crypto'
import type { APIRequestContext } from '@playwright/test'
import { Pool } from 'pg'

import { expect, signInPassword, test } from '../playwright'
import {
  cleanupAccountForManualValidation,
  prepareAccountForManualValidation,
  type SignInHandlerAccount,
} from '../fixtures/identity-module-fixture'

const DATABASE_URL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

async function signIn(
  request: APIRequestContext,
  account: SignInHandlerAccount,
  password = signInPassword,
) {
  const response = await request.post('/api/auth/sign-in/identity', {
    data: { email: account.email, password },
    headers: { ...sameOriginHeaders(), 'x-forwarded-for': account.ipAddress },
  })
  expect(response.status()).toBe(200)
  return response
}

function sameOriginHeaders() {
  return { origin: new URL(test.info().project.use.baseURL as string).origin }
}

async function seedAccountToken(
  pool: Pool,
  accountId: string,
  marker: string,
  type: 'email-confirmation' | 'password-recovery' = 'password-recovery',
) {
  const token = createHash('sha256')
    .update(accountId + marker)
    .digest('base64url')
  const identifier = createHash('sha256').update(token).digest('hex').slice(0, 26)
  await pool.query(
    `insert into identity_account_action_tokens
    (id, account_id, type, status, token_hash, issued_at, expires_at, updated_at, communication_id, delivery_status)
    values ($1, $2, $4, 'pending', $3, now(), now() + interval '1 hour', now(), $1, 'delivered')`,
    [identifier, accountId, createHash('sha256').update(token).digest('hex'), type],
  )
  return token
}

test.describe('canonical account auth handlers', () => {
  test('uses server-owned upstream credentials despite forged browser headers', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    const requestId = '6e1c92a9-6232-4f21-9427-641b4e34f70a'
    const headers = {
      'X-Shifu-Bff-Secret': 'forged-browser-secret',
      Authorization: 'Bearer forged-browser-access',
      'X-Request-ID': requestId,
      'X-Custom': 'browser-value',
    }
    // A browser-supplied server marker cannot stand in for a signed-in session.
    const anonymous = await request.get('/api/auth/account', { headers })
    expect(anonymous.status()).toBe(401)
    await signIn(request, activeAccount)
    // The real Identity API accepts the BFF's own secret and session JWT.
    const response = await request.get('/api/auth/account', { headers })
    expect(response.status()).toBe(200)
    expect(response.headers()['cache-control']).toBe('no-store')
    expect(response.headers()['x-request-id']).toBe(requestId)
    expect(await response.json()).toEqual({
      accountId: activeAccount.accountId,
      displayName: 'Handler Test Learner',
      email: activeAccount.email,
      timeZone: 'America/Sao_Paulo',
    })
    expect(response.headers()['x-shifu-bff-secret']).toBeUndefined()
    expect(response.headers().authorization).toBeUndefined()
  })

  test('requires an active authenticated account and rejects methods and foreign origins', async ({
    accountRequest: request,
    activeAccount,
    pendingAccount,
  }) => {
    expect((await request.get('/api/auth/account')).status()).toBe(401)
    const pool = new Pool({ connectionString: DATABASE_URL })
    try {
      await seedAccountToken(
        pool,
        pendingAccount.accountId,
        'confirmation',
        'email-confirmation',
      )
    } finally {
      await pool.end()
    }
    await signIn(request, pendingAccount)
    expect((await request.get('/api/auth/account')).status()).toBe(401)
    const login = await signIn(request, activeAccount)
    expect(login.headers()['set-cookie']).toContain('HttpOnly')
    expect((await request.get('/api/auth/account/password')).status()).toBe(404)
    const foreign = await request.post('/api/auth/account/profile', {
      data: { displayName: 'Foreign', timeZone: 'UTC' },
      headers: { origin: 'https://foreign.invalid' },
    })
    expect(foreign.status()).toBe(403)
    const current = await request.get('/api/auth/account')
    expect(await current.json()).toEqual({
      accountId: activeAccount.accountId,
      displayName: 'Handler Test Learner',
      email: activeAccount.email,
      timeZone: 'America/Sao_Paulo',
    })
  })

  test('persists canonical profile, preserves ownership and exposes only safe no-store data', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    await signIn(request, activeAccount)
    const response = await request.post('/api/auth/account/profile', {
      headers: sameOriginHeaders(),
      data: { displayName: '  Updated Learner  ', timeZone: 'Asia/Kathmandu' },
    })
    expect(response.status()).toBe(200)
    expect(response.headers()['cache-control']).toBe('no-store')
    const profile = {
      accountId: activeAccount.accountId,
      displayName: 'Updated Learner',
      email: activeAccount.email,
      timeZone: 'Asia/Kathmandu',
    }
    expect(await response.json()).toEqual(profile)
    const read = await request.get('/api/auth/account')
    expect(read.headers()['cache-control']).toBe('no-store')
    expect(await read.json()).toEqual(profile)
    const pool = new Pool({ connectionString: DATABASE_URL })
    try {
      const canonical = await pool.query(
        'select display_name, time_zone, email from identity_accounts where id = $1',
        [activeAccount.accountId],
      )
      expect(canonical.rows).toEqual([
        {
          display_name: profile.displayName,
          time_zone: profile.timeZone,
          email: activeAccount.email,
        },
      ])
      const technical = await pool.query(
        'select name from better_auth_users where id = $1',
        [activeAccount.accountId],
      )
      expect(technical.rows).toEqual([{ name: profile.displayName }])
    } finally {
      await pool.end()
    }
  })

  test('returns field-specific rejection and leaves credentials unchanged', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    await signIn(request, activeAccount)
    for (const [body, code] of [
      [{ displayName: '', timeZone: 'UTC' }, 'invalid_display_name'],
      [{ displayName: 'Learner', timeZone: 'invalid/time' }, 'invalid_time_zone'],
    ] as const) {
      const response = await request.post('/api/auth/account/profile', {
        headers: sameOriginHeaders(),
        data: body,
      })
      expect(response.status()).toBe(400)
      expect((await response.json()).code).toBe(code)
    }
    const wrong = await request.post('/api/auth/account/password', {
      headers: sameOriginHeaders(),
      data: { currentPassword: 'wrong-password', newPassword: 'next-password' },
    })
    expect(wrong.status()).toBe(403)
    expect((await wrong.json()).code).toBe('invalid_current_password')
    const short = await request.post('/api/auth/account/password', {
      headers: sameOriginHeaders(),
      data: { currentPassword: signInPassword, newPassword: '1234567' },
    })
    expect(short.status()).toBe(400)
    expect((await short.json()).code).toBe('invalid_new_password')
    await signIn(request, activeAccount)
  })

  test('reads a legacy null timezone without persisting a browser suggestion', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    const pool = new Pool({ connectionString: DATABASE_URL })
    try {
      await pool.query('update identity_accounts set time_zone = null where id = $1', [
        activeAccount.accountId,
      ])
      await signIn(request, activeAccount)
      const response = await request.get('/api/auth/account')
      expect(response.status()).toBe(200)
      expect((await response.json()).timeZone).toBeNull()
      expect(
        (
          await pool.query('select time_zone from identity_accounts where id = $1', [
            activeAccount.accountId,
          ])
        ).rows,
      ).toEqual([{ time_zone: null }])
    } finally {
      await pool.end()
    }
  })

  test('returns a safe unavailable response when a password write rolls back', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    const pool = new Pool({ connectionString: DATABASE_URL })
    const trigger = `account_write_failure_${activeAccount.accountId.toLowerCase()}`
    await signIn(request, activeAccount)
    try {
      const before = await pool.query(
        'select password_hash, access_version from identity_accounts where id = $1',
        [activeAccount.accountId],
      )
      await pool.query(`create function ${trigger}() returns trigger language plpgsql as $$ begin if new.id = '${activeAccount.accountId}' then raise exception 'private-db-failure'; end if; return new; end; $$;
        create trigger ${trigger} before update on identity_accounts for each row execute function ${trigger}()`)
      const response = await request.post('/api/auth/account/password', {
        headers: sameOriginHeaders(),
        data: { currentPassword: signInPassword, newPassword: 'rejected-password' },
      })
      expect(response.status()).toBe(503)
      expect(response.headers()['cache-control']).toBe('no-store')
      expect(await response.json()).toEqual({
        code: 'identity_unavailable',
        message: 'Não foi possível concluir agora. Tente novamente.',
      })
      expect(
        (
          await pool.query(
            'select password_hash, access_version from identity_accounts where id = $1',
            [activeAccount.accountId],
          )
        ).rows,
      ).toEqual(before.rows)
      expect((await request.get('/api/auth/account')).status()).toBe(200)
    } finally {
      await pool.query(
        `drop trigger if exists ${trigger} on identity_accounts; drop function if exists ${trigger}()`,
      )
      await pool.end()
    }
    await signIn(request, activeAccount)
  })

  test('blocks generic mutations and unknown fields without changing canonical or technical identity', async ({
    accountRequest: request,
    activeAccount,
  }) => {
    await signIn(request, activeAccount)
    for (const [path, data] of [
      ['/update-session', { accessVersion: 100 }],
      ['/update-user', { name: 'Bypass' }],
      [
        '/change-password',
        { currentPassword: signInPassword, newPassword: 'bypass-password' },
      ],
    ] as const) {
      expect((await request.post(`/api/auth${path}`, { data })).status()).toBe(404)
    }
    for (const body of [
      { displayName: 'Bypass', timeZone: 'UTC', accountId: 'other' },
      { displayName: 'Bypass', timeZone: 'UTC', accessVersion: 100 },
    ])
      expect(
        (
          await request.post('/api/auth/account/profile', {
            headers: sameOriginHeaders(),
            data: body,
          })
        ).status(),
      ).toBe(400)
    expect(
      (
        await request.post('/api/auth/account/password', {
          headers: sameOriginHeaders(),
          data: {
            currentPassword: signInPassword,
            newPassword: 'next-password',
            sessionId: 'other',
          },
        })
      ).status(),
    ).toBe(400)
    expect(
      (await request.get('/api/auth/account').then((response) => response.json()))
        .displayName,
    ).toBe('Handler Test Learner')
    const pool = new Pool({ connectionString: DATABASE_URL })
    try {
      expect(
        (
          await pool.query('select name from better_auth_users where id = $1', [
            activeAccount.accountId,
          ])
        ).rows,
      ).toEqual([{ name: 'Handler Test Learner' }])
    } finally {
      await pool.end()
    }
  })

  test('preserves the initiating cookie and session through two changes, revokes peers and recovery, and permits fresh login', async ({
    accountRequest: request,
    browser,
    activeAccount,
  }, testInfo) => {
    const otherSession = await browser.newContext({
      extraHTTPHeaders: {
        ...sameOriginHeaders(),
        'x-forwarded-for': activeAccount.ipAddress,
      },
    })
    const freshSession = await browser.newContext({
      extraHTTPHeaders: {
        ...sameOriginHeaders(),
        'x-forwarded-for': activeAccount.ipAddress,
      },
    })
    const controlSession = await browser.newContext({
      extraHTTPHeaders: {
        ...sameOriginHeaders(),
        'x-forwarded-for': activeAccount.ipAddress,
      },
    })
    const controlAccount = await prepareAccountForManualValidation(
      `${testInfo.testId}-control`,
    )
    await controlSession.setExtraHTTPHeaders({
      ...sameOriginHeaders(),
      'x-forwarded-for': controlAccount.ipAddress,
    })
    const pool = new Pool({ connectionString: DATABASE_URL })
    try {
      const login = await signIn(request, activeAccount)
      await signIn(otherSession.request, activeAccount)
      await signIn(controlSession.request, controlAccount)
      await pool.query(
        `update better_auth_sessions set created_at = created_at - interval '2 days', updated_at = updated_at - interval '2 days', expires_at = expires_at - interval '29 days' where user_id = $1`,
        [activeAccount.accountId],
      )
      const before = await pool.query(
        'select id, token, expires_at, access_version from better_auth_sessions where user_id = $1 order by created_at',
        [activeAccount.accountId],
      )
      expect(before.rows).toHaveLength(2)
      const token = await seedAccountToken(pool, activeAccount.accountId, 'before')
      const first = await request.post('/api/auth/account/password', {
        headers: sameOriginHeaders(),
        data: { currentPassword: signInPassword, newPassword: 'new-password-one' },
      })
      expect(first.status()).toBe(200)
      expect(await first.json()).toEqual({ changed: true })
      expect(first.headers()['cache-control']).toBe('no-store')
      expect(first.headers()['set-cookie']).toBeUndefined()
      expect((await request.get('/api/auth/account')).status()).toBe(200)
      expect((await otherSession.request.get('/api/auth/account')).status()).toBe(401)
      expect((await controlSession.request.get('/api/auth/account')).status()).toBe(200)
      const version = await pool.query(
        'select access_version from identity_accounts where id = $1',
        [activeAccount.accountId],
      )
      expect(
        (
          await otherSession.request.post('/api/auth/update-session', {
            data: { accessVersion: version.rows[0].access_version },
          })
        ).status(),
      ).toBe(404)
      expect((await otherSession.request.get('/api/auth/account')).status()).toBe(401)
      const invalidated = await request.post('/api/auth/password-reset-link/status', {
        headers: sameOriginHeaders(),
        data: { token },
      })
      expect(await invalidated.json()).toEqual({ result: 'invalid' })
      const second = await request.post('/api/auth/account/password', {
        headers: sameOriginHeaders(),
        data: { currentPassword: 'new-password-one', newPassword: 'new-password-two' },
      })
      expect(second.status()).toBe(200)
      expect((await request.get('/api/auth/account')).status()).toBe(200)
      expect(
        (
          await freshSession.request.post('/api/auth/sign-in/identity', {
            data: { email: activeAccount.email, password: signInPassword },
            headers: { 'x-forwarded-for': activeAccount.ipAddress },
          })
        ).status(),
      ).toBe(401)
      await signIn(freshSession.request, activeAccount, 'new-password-two')
      const after = await pool.query(
        'select id, token, expires_at, access_version from better_auth_sessions where id = $1',
        [before.rows[0].id],
      )
      expect(after.rows).toEqual([before.rows[0]])
      expect(login.headers()['set-cookie']).toContain('HttpOnly')
      const third = await freshSession.request.post('/api/auth/account/password', {
        headers: sameOriginHeaders(),
        data: { currentPassword: 'new-password-two', newPassword: 'new-password-three' },
      })
      expect(third.status()).toBe(200)
      expect((await request.get('/api/auth/account')).status()).toBe(401)
      expect((await freshSession.request.get('/api/auth/account')).status()).toBe(200)
      const laterToken = await seedAccountToken(pool, activeAccount.accountId, 'later')
      const reset = await freshSession.request.post('/api/auth/password-reset', {
        headers: sameOriginHeaders(),
        data: {
          token: laterToken,
          password: 'recovered-password',
          passwordConfirmation: 'recovered-password',
        },
      })
      expect(reset.status()).toBe(200)
      expect((await freshSession.request.get('/api/auth/account')).status()).toBe(401)
    } finally {
      await pool.end()
      await Promise.all([
        otherSession.close(),
        freshSession.close(),
        controlSession.close(),
      ])
      await cleanupAccountForManualValidation(controlAccount)
    }
  })

  test('reports a lost committed password response without retry and preserves the initiating access', async ({
    page,
    activeAccount,
  }) => {
    await page.context().setExtraHTTPHeaders({
      ...sameOriginHeaders(),
      'x-forwarded-for': activeAccount.ipAddress,
    })
    await signIn(page.request, activeAccount)
    await page.goto('/account')
    await page.getByRole('tab', { name: 'Segurança' }).click()
    let attempts = 0
    await page.route('**/api/auth/account/password', async (route) => {
      attempts += 1
      const committed = await route.fetch()
      expect(committed.status()).toBe(200)
      expect(await committed.json()).toEqual({ changed: true })
      await route.abort('connectionreset')
    })
    await page.getByLabel('Senha atual', { exact: true }).fill(signInPassword)
    await page
      .getByLabel('Nova senha · mínimo de 8 caracteres')
      .fill('after-lost-response')
    await page.getByRole('button', { name: 'Alterar senha', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText(
      'Não foi possível confirmar a troca',
    )
    await expect(page.getByLabel('Senha atual', { exact: true })).toHaveValue('')
    await expect(page.getByLabel('Nova senha · mínimo de 8 caracteres')).toHaveValue('')
    expect(attempts).toBe(1)
    const profile = await page.request.get('/api/auth/account')
    expect(profile.status()).toBe(200)
    expect((await profile.json()).accountId).toBe(activeAccount.accountId)
    const next = await page.request.post('/api/auth/account/password', {
      headers: sameOriginHeaders(),
      data: {
        currentPassword: 'after-lost-response',
        newPassword: 'confirmed-next-password',
      },
    })
    expect(next.status()).toBe(200)
    expect((await page.request.get('/api/auth/account')).status()).toBe(200)
  })

  test('keeps a canonical save successful and uses a neutral menu during a later Identity outage', async ({
    accountRequest: request,
    page,
    activeAccount,
  }) => {
    const pool = new Pool({ connectionString: DATABASE_URL })
    const proxyPort = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
    if (!proxyPort)
      throw new Error(
        'CI-09 outage proof requires SHIFU_ACCOUNT_TEST_PROXY_PORT and its controlled upstream',
      )
    const controlURL = `http://127.0.0.1:${proxyPort}/__account-control/${activeAccount.accountId}`
    await page.context().setExtraHTTPHeaders({
      ...sameOriginHeaders(),
      'x-forwarded-for': activeAccount.ipAddress,
    })
    const suffix = activeAccount.accountId.toLowerCase()
    const trigger = `account_name_failure_${suffix}`
    await signIn(request, activeAccount)
    try {
      await pool.query(`create function ${trigger}() returns trigger language plpgsql as $$ begin if new.id = '${activeAccount.accountId}' then raise exception 'test-copy-failure'; end if; return new; end; $$;
        create trigger ${trigger} before update on better_auth_users for each row execute function ${trigger}()`)
      const save = await request.post('/api/auth/account/profile', {
        headers: sameOriginHeaders(),
        data: { displayName: 'Canonical survives', timeZone: 'Europe/Lisbon' },
      })
      expect(save.status()).toBe(200)
      expect((await save.json()).displayName).toBe('Canonical survives')
      expect(
        (await request.get('/api/auth/account').then((response) => response.json()))
          .displayName,
      ).toBe('Canonical survives')
      expect(
        (
          await pool.query('select name from better_auth_users where id = $1', [
            activeAccount.accountId,
          ])
        ).rows,
      ).toEqual([{ name: 'Handler Test Learner' }])
      expect((await request.post(controlURL)).status()).toBe(200)
      const state = await request.storageState()
      await page.context().addCookies(state.cookies)
      await page.goto('/account')
      await page.waitForFunction(() => document.body.dataset.hydrated === 'true')
      await expect(
        page.getByRole('heading', { name: 'Sua conta', exact: true }),
      ).toBeVisible()
      await expect(
        page.getByRole('button', { name: 'Tentar novamente', exact: true }),
      ).toBeVisible()
      await page.getByRole('button', { name: 'Abrir menu da conta', exact: true }).click()
      const menu = page.getByRole('menu', { name: 'Menu da conta' })
      await expect(menu.getByText('Minha conta', { exact: true })).toBeVisible()
      await expect(menu.getByText('Handler Test Learner', { exact: true })).toHaveCount(0)
      await expect(menu.getByText('Canonical survives', { exact: true })).toHaveCount(0)
      const unavailableRead = await request.get('/api/auth/account')
      expect(unavailableRead.status()).toBe(503)
      expect((await unavailableRead.json()).code).toBe('identity_unavailable')
      const unavailableSave = await request.post('/api/auth/account/profile', {
        headers: sameOriginHeaders(),
        data: { displayName: 'Must not persist', timeZone: 'UTC' },
      })
      expect(unavailableSave.status()).toBe(503)
      const unavailablePassword = await request.post('/api/auth/account/password', {
        headers: sameOriginHeaders(),
        data: { currentPassword: signInPassword, newPassword: 'must-not-persist' },
      })
      expect(unavailablePassword.status()).toBe(503)
      expect(
        (
          await pool.query(
            'select display_name, time_zone, access_version from identity_accounts where id = $1',
            [activeAccount.accountId],
          )
        ).rows,
      ).toEqual([
        {
          display_name: 'Canonical survives',
          time_zone: 'Europe/Lisbon',
          access_version: 1,
        },
      ])
      const observations = await request
        .get(controlURL)
        .then((response) => response.json())
      for (const key of [
        'GET /identity/session',
        'GET /identity/accounts/me',
        'PATCH /identity/accounts/me',
        'POST /identity/accounts/me/password',
      ])
        expect(observations.hits[key]).toBeGreaterThan(0)
      expect((await request.delete(controlURL)).status()).toBe(200)
      await page.reload()
      await page.waitForFunction(() => document.body.dataset.hydrated === 'true')
      await expect(
        page.getByRole('button', { name: 'Salvar', exact: true }),
      ).toBeVisible()
      await page.getByRole('button', { name: 'Abrir menu da conta', exact: true }).click()
      await expect(
        page
          .getByRole('menu', { name: 'Menu da conta' })
          .getByText('Canonical survives', { exact: true }),
      ).toBeVisible()
    } finally {
      await request.delete(controlURL)
      await pool.query(
        `drop trigger if exists ${trigger} on better_auth_users; drop function if exists ${trigger}()`,
      )
      await pool.end()
    }
    expect(
      (await request.get('/api/auth/account').then((response) => response.json()))
        .displayName,
    ).toBe('Canonical survives')
  })
})
