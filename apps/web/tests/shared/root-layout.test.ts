import type { Page } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import type { AccountAppearance } from '../../src/core/identity/account-appearance'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'

// Browser integration with mocked transport: the route-protection server functions
// are answered in the browser, so these scenarios prove how the root layout applies
// the account appearance, not server persistence or the first server render.
const DARK_BACKGROUND = 'rgb(10, 10, 12)'
const LIGHT_BACKGROUND = 'rgb(244, 241, 234)'

async function answerProtectedRoutesWith(page: Page, appearance: AccountAppearance) {
  const calls: string[] = []
  await page.route('**/_serverFn/**', async (route) => {
    const serverFunction = Buffer.from(
      new URL(route.request().url()).pathname.split('/').at(-1) ?? '',
      'base64url',
    ).toString()
    if (
      !serverFunction.includes('middlewares/require-auth-middleware.ts') &&
      !serverFunction.includes('middlewares/enter-main-page-middleware.ts') &&
      !serverFunction.includes('routes/account/route.tsx') &&
      !serverFunction.includes('requireAccountAccessOrDeletionStatus')
    ) {
      await route.fallback()
      return
    }
    calls.push(serverFunction)
    const isMainPageEntry = serverFunction.includes(
      'middlewares/enter-main-page-middleware.ts',
    )
    const account = {
      displayName: 'Playwright Learner',
      email: 'playwright@shifu.local',
      appearance,
    }
    await route.fulfill({
      body: JSON.stringify({
        result: isMainPageEntry ? { mode: 'authenticated', account } : account,
      }),
      contentType: 'application/json',
      status: 200,
    })
  })
  return calls
}

test('uses the public shell on the sign-in route', async ({ page }) => {
  await page.goto('/login/')

  await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()
  await expect(
    page.getByRole('navigation', { name: 'Navegação principal' }),
  ).not.toBeVisible()
})

test('keeps public routes dark when the device prefers light', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/login/')

  await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('body')).toHaveCSS('background-color', DARK_BACKGROUND)
})

for (const route of [ROUTES.dashboard, ROUTES.accountProfile]) {
  test(`applies the account appearance returned for ${route}`, async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage, { appearance: 'light' })
    const calls = await answerProtectedRoutesWith(authenticatedPage, 'light')
    await navigateAuthenticatedPage(authenticatedPage, route)

    await expect(authenticatedPage.locator('html')).toHaveAttribute('data-theme', 'light')
    await expect(authenticatedPage.locator('body')).toHaveCSS(
      'background-color',
      LIGHT_BACKGROUND,
    )
    const expectedServerFunction =
      route === ROUTES.dashboard
        ? 'middlewares/enter-main-page-middleware.ts'
        : 'requireAccountAccessOrDeletionStatus'
    expect(calls.some((call) => call.includes(expectedServerFunction))).toBe(true)
  })
}

test('follows the device preference with the system appearance during the session', async ({
  authenticatedPage,
}) => {
  await installAccountBackend(authenticatedPage, { appearance: 'system' })
  const calls = await answerProtectedRoutesWith(authenticatedPage, 'system')
  await authenticatedPage.emulateMedia({ colorScheme: 'light' })
  await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)

  await expect(authenticatedPage.locator('html')).toHaveAttribute('data-theme', 'system')
  await expect(authenticatedPage.locator('body')).toHaveCSS(
    'background-color',
    LIGHT_BACKGROUND,
  )
  const callsBeforeChange = calls.length

  await authenticatedPage.emulateMedia({ colorScheme: 'dark' })
  await expect(authenticatedPage.locator('body')).toHaveCSS(
    'background-color',
    DARK_BACKGROUND,
  )

  await authenticatedPage.emulateMedia({ colorScheme: 'light' })
  await expect(authenticatedPage.locator('body')).toHaveCSS(
    'background-color',
    LIGHT_BACKGROUND,
  )
  expect(calls).toHaveLength(callsBeforeChange)
})
