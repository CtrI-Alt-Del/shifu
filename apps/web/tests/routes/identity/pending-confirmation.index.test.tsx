import { ROUTES } from '../../../src/constants/routes'

import { expect, test } from '../../playwright'

test.describe('PendingConfirmationPage route with mocked transport', () => {
  test('renders the restricted public state and cooldown from the BFF', async ({
    page,
  }) => {
    await page.route('**/api/auth/pending-confirmation*', async (route) => {
      if (route.request().method() !== 'GET') return route.fallback()
      await route.fulfill({
        body: JSON.stringify({ state: 'cooldown', retryAfterSeconds: 60 }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.goto(`${ROUTES.pendingConfirmation}/`)

    await expect(page.getByRole('heading', { name: 'Confirme seu e-mail' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Reenviar link em 60s' }),
    ).toBeDisabled()
  })

  test('exits the pending context and redirects to Entrar', async ({ page }) => {
    const requests: Array<{ method: string; pathname: string }> = []
    await page.route('**/api/auth/pending-confirmation', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ state: 'ready', retryAfterSeconds: null }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/pending-confirmation/sign-out', async (route) => {
      requests.push({
        method: route.request().method(),
        pathname: new URL(route.request().url()).pathname,
      })
      await route.fulfill({ body: '{}', contentType: 'application/json', status: 200 })
    })
    await page.goto(`${ROUTES.pendingConfirmation}/`)
    await page.waitForFunction(() => '__TSR_ROUTER__' in window)
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: 'Sair' }).click()

    const expectedRequests = [
      { method: 'POST', pathname: '/api/auth/pending-confirmation/sign-out' },
    ]
    await expect.poll(() => requests).toEqual(expectedRequests)
    await expect(page).toHaveURL(/\/login\/?$/)
  })

  test('maps a resend delivery failure to an announced recoverable state', async ({
    page,
  }) => {
    await page.route('**/api/auth/pending-confirmation', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ state: 'ready', retryAfterSeconds: null }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/pending-confirmation/resend', async (route) => {
      await route.fulfill({ body: '{}', contentType: 'application/json', status: 503 })
    })
    await page.goto(`${ROUTES.pendingConfirmation}/`)
    await page.getByRole('button', { name: 'Reenviar link' }).click()

    await expect(page.getByRole('alert')).toHaveText(
      'Não foi possível reenviar agora. Tente novamente.',
    )
  })
})
