import { createHash } from 'node:crypto'
import type { Page } from '@playwright/test'
import { Pool } from 'pg'

import { ROUTES } from '../../src/constants/routes'
import { signInPassword, expect, test } from '../playwright'

const databaseURL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test.describe('LandingPage', () => {
  test('presents the public learning journey and its existing destinations', async ({
    page,
  }) => {
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': `203.0.113.${(process.pid % 253) + 1}`,
    })
    const requestedURLs: string[] = []
    page.on('request', (request) => requestedURLs.push(request.url()))
    const response = await page.goto(ROUTES.root)

    expect(response?.status()).toBe(200)
    expect(response?.headers()['cache-control']).toBe('private, no-store')
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()
    await expect(page.getByText('Exemplo ilustrativo')).toBeVisible()
    await expect(page.getByText('Em breve').first()).toBeVisible()
    await expect(page.getByRole('link', { name: 'Criar conta' }).first()).toBeVisible()

    expect(
      requestedURLs.some((url) =>
        /\/api\/(learning|intelligence|gamification)\//.test(url),
      ),
    ).toBe(false)
    expect(
      requestedURLs.every((url) => new URL(url).origin === new URL(page.url()).origin),
    ).toBe(true)

    await page.keyboard.press('Tab')
    const brand = page.getByRole('link', { name: 'Shifu — início' }).first()
    await expect(brand).toBeFocused()
    expect(
      await brand.evaluate((element) => getComputedStyle(element).outlineStyle),
    ).toBe('solid')

    await page
      .context()
      .addCookies([
        { name: 'better-auth.session_token', value: 'invalid-session', url: page.url() },
      ])
    const rejectedSession = await page.goto(ROUTES.root)
    expect(rejectedSession?.status()).toBe(200)
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()

    await page
      .context()
      .addCookies([
        { name: 'shifu-pending-flow', value: 'invalid-pending-context', url: page.url() },
      ])
    const rejectedPendingContext = await page.goto(ROUTES.root)
    expect(rejectedPendingContext?.status()).toBe(200)
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()

    await page.setViewportSize({ width: 390, height: 844 })
    const mobileCta = page.getByRole('link', { name: 'Criar conta' }).first()
    await expect(mobileCta).toBeVisible()
    const ctaBox = await mobileCta.boundingBox()
    expect(ctaBox).not.toBeNull()
    expect((ctaBox?.y ?? 0) + (ctaBox?.height ?? 0)).toBeLessThan(844)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)

    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()

    await page.goto(ROUTES.root)
    await page.getByRole('link', { name: 'Criar conta' }).first().click()
    await expect(page).toHaveURL(/\/register\/?$/)
    await expect(page.getByRole('heading', { name: 'Criar conta' })).toBeVisible()

    await page.goto(ROUTES.root)
    await page
      .getByRole('link', { name: /aviso de privacidade/i })
      .last()
      .click()
    await expect(page).toHaveURL(/\/privacy\/?$/)
    await expect(
      page.getByRole('heading', { name: 'Política de privacidade' }),
    ).toBeVisible()
  })

  test('keeps the protected home on the root route for an active account', async ({
    page,
    activeAccount,
  }) => {
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': activeAccount.ipAddress,
    })
    await page.addInitScript(() => {
      Object.assign(window, { __landingWasRendered: false })
      const observeLanding = () => {
        if (
          document.body.textContent?.includes(
            'Veja sua evolução no que você quer aprender',
          )
        ) {
          Object.assign(window, { __landingWasRendered: true })
        }
      }
      new MutationObserver(observeLanding).observe(document, {
        childList: true,
        characterData: true,
        subtree: true,
      })
    })

    await page.goto(ROUTES.login)
    await waitUntilHydrated(page)
    await page.getByLabel('E-mail').fill(activeAccount.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(signInPassword)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(
      page.getByRole('heading', { name: 'O que você quer aprender?' }),
    ).toBeVisible()
    expect(
      await page.evaluate(
        () =>
          (window as typeof window & { __landingWasRendered: boolean })
            .__landingWasRendered,
      ),
    ).toBe(false)

    const response = await page.goto(ROUTES.root)
    expect(response?.headers()['cache-control']).toBe('private, no-store')
    await expect(
      page.getByRole('heading', { name: 'O que você quer aprender?' }),
    ).toBeVisible()
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toHaveCount(0)
  })

  test('sends a validated pending account to confirmation from the root route', async ({
    page,
    pendingAccount,
  }) => {
    await seedPendingConfirmationToken(pendingAccount)
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': pendingAccount.ipAddress,
    })
    await page.goto(ROUTES.login)
    await waitUntilHydrated(page)
    await page.getByLabel('E-mail').fill(pendingAccount.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(signInPassword)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)

    await page.goto(ROUTES.root)

    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)
    await expect(page.getByRole('heading', { name: 'Confirme seu e-mail' })).toBeVisible()
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toHaveCount(0)

    const pendingCookie = (await page.context().cookies()).find(
      (cookie) => cookie.name === 'shifu-pending-flow',
    )
    expect(pendingCookie).toBeDefined()
    const identifier = decodeURIComponent(pendingCookie?.value ?? '').split('.')[0]
    const pool = new Pool({ connectionString: databaseURL })
    try {
      await pool.query(
        "update better_auth_verifications set expires_at = now() - interval '1 minute' where identifier = $1",
        [identifier],
      )
    } finally {
      await pool.end()
    }

    await page.goto(ROUTES.root)
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()
  })

  test('does not show the landing while Identity cannot validate a pending flow', async ({
    page,
    pendingAccount,
  }) => {
    await seedPendingConfirmationToken(pendingAccount)
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': pendingAccount.ipAddress,
    })
    await page.goto(ROUTES.login)
    await waitUntilHydrated(page)
    await page.getByLabel('E-mail').fill(pendingAccount.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(signInPassword)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)

    const proxyPort = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
    if (!proxyPort) throw new Error('Controlled Identity proxy is not configured')
    const pendingHandle = await readPendingHandle(page)
    const controlURL = `http://127.0.0.1:${proxyPort}/__account-control/${pendingHandle}`
    await page.request.post(controlURL, {
      data: { scenario: 'pending-status-unavailable' },
    })

    try {
      const response = await page.goto(ROUTES.root)
      expect(response?.status()).toBeGreaterThanOrEqual(500)
      await expect(
        page.getByRole('heading', {
          level: 1,
          name: 'Veja sua evolução no que você quer aprender.',
        }),
      ).toHaveCount(0)
    } finally {
      await page.request.delete(controlURL)
    }
  })

  test('does not show the landing when Identity returns an invalid pending status', async ({
    page,
    pendingAccount,
  }) => {
    await seedPendingConfirmationToken(pendingAccount)
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': pendingAccount.ipAddress,
    })
    await page.goto(ROUTES.login)
    await waitUntilHydrated(page)
    await page.getByLabel('E-mail').fill(pendingAccount.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(signInPassword)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)

    const proxyPort = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
    if (!proxyPort) throw new Error('Controlled Identity proxy is not configured')
    const pendingHandle = await readPendingHandle(page)
    const controlURL = `http://127.0.0.1:${proxyPort}/__account-control/${pendingHandle}`
    await page.request.post(controlURL, {
      data: { scenario: 'pending-status-invalid' },
    })

    try {
      const response = await page.goto(ROUTES.root)
      expect(response?.status()).toBeGreaterThanOrEqual(500)
      await expect(
        page.getByRole('heading', {
          level: 1,
          name: 'Veja sua evolução no que você quer aprender.',
        }),
      ).toHaveCount(0)
    } finally {
      await page.request.delete(controlURL)
    }
  })

  test('fails closed when Identity cannot validate an active session', async ({
    page,
    activeAccount,
  }) => {
    await page.context().setExtraHTTPHeaders({
      'x-forwarded-for': activeAccount.ipAddress,
    })
    await page.goto(ROUTES.login)
    await waitUntilHydrated(page)
    await page.getByLabel('E-mail').fill(activeAccount.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(signInPassword)
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)

    const proxyPort = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
    if (!proxyPort) throw new Error('Controlled Identity proxy is not configured')
    const controlURL = `http://127.0.0.1:${proxyPort}/__account-control/${activeAccount.accountId}`
    await page.request.post(controlURL)

    try {
      const response = await page.goto(ROUTES.root)

      expect(response?.status()).toBe(200)
      await expect(
        page.getByRole('heading', { name: 'O que você quer aprender?' }),
      ).toBeVisible()
      await expect(
        page.getByRole('heading', {
          level: 1,
          name: 'Veja sua evolução no que você quer aprender.',
        }),
      ).toHaveCount(0)
    } finally {
      await page.request.delete(controlURL)
    }
  })

  test('keeps the composition within mobile widths and static for reduced motion', async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.setViewportSize({ width: 320, height: 740 })
    await page.goto(ROUTES.root)

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Veja sua evolução no que você quer aprender.',
      }),
    ).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320)
    expect(
      await page
        .locator('.landing-page__ambient')
        .evaluate((element) => getComputedStyle(element).animationName),
    ).toBe('none')

    for (const link of await page.getByRole('link').all()) {
      if (!(await link.isVisible())) continue
      const box = await link.boundingBox()
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44)
    }
  })
})

async function seedPendingConfirmationToken(account: {
  accountId: string
  email: string
}) {
  const pool = new Pool({
    connectionString: databaseURL,
  })
  const confirmationToken = `${account.accountId.slice(0, 5)}${'a'.repeat(38)}`
  const tokenId = `${account.accountId.slice(0, 5)}${'b'.repeat(21)}`
  const communicationId = `${account.accountId.slice(0, 5)}${'c'.repeat(21)}`
  const hash = (value: string) => createHash('sha256').update(value).digest('hex')

  try {
    await pool.query(
      `insert into identity_account_action_tokens (
        id, account_id, type, status, token_hash, issued_at, expires_at, updated_at,
        communication_id, pending_handle_hash, delivery_status
      ) values ($1, $2, 'email-confirmation', 'pending', $3, now(),
        now() + interval '24 hours', now(), $4, $5, null)`,
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
}

async function readPendingHandle(page: Page): Promise<string> {
  const pendingCookie = (await page.context().cookies()).find(
    (cookie) => cookie.name === 'shifu-pending-flow',
  )
  if (!pendingCookie) throw new Error('Pending confirmation cookie was not created')

  const identifier = decodeURIComponent(pendingCookie.value).split('.')[0]
  const pool = new Pool({ connectionString: databaseURL })
  try {
    const result = await pool.query<{ value: string }>(
      'select value from better_auth_verifications where identifier = $1',
      [identifier],
    )
    const value: unknown = JSON.parse(result.rows[0]?.value ?? 'null')
    if (
      typeof value !== 'object' ||
      value === null ||
      !('pendingHandle' in value) ||
      typeof value.pendingHandle !== 'string'
    ) {
      throw new Error('Pending confirmation handle was not persisted')
    }
    return value.pendingHandle
  } finally {
    await pool.end()
  }
}

async function waitUntilHydrated(page: Page) {
  await page.waitForFunction(() => document.body.dataset.hydrated === 'true')
}
