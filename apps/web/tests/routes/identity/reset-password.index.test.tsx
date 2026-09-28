import { expect, test } from '../../playwright'

import { ROUTES } from '../../../src/constants/routes'

const validToken = 'a'.repeat(43)

test.describe('ResetPasswordPage route with mocked transport', () => {
  test('removes a malformed token from the URL and shows a generic invalid outcome', async ({
    page,
  }) => {
    let didCallBff = false
    await page.route('**/api/auth/password-reset', async (route) => {
      didCallBff = true
      await route.abort()
    })
    await page.goto(`${ROUTES.resetPassword}/?token=invalid`)

    await expect(page.getByRole('heading', { name: 'Link inválido' })).toBeFocused()
    await expect(page).toHaveURL(/\/reset-password\/?$/)
    expect(didCallBff).toBe(false)
  })

  test('resolves a valid link through the BFF after removing it from the URL', async ({
    page,
  }) => {
    let statusRequestBody: unknown
    await page.route('**/api/auth/password-reset-link/status', async (route) => {
      statusRequestBody = route.request().postDataJSON()
      await route.fulfill({
        body: JSON.stringify({ result: 'valid' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.resetPassword}/?token=${validToken}`)
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/reset-password\/?$/)
    await expect(page.getByLabel('Nova senha', { exact: true })).toBeVisible()
    expect(statusRequestBody).toEqual({ token: validToken })
  })

  test('shows an expired outcome before rendering the reset form', async ({ page }) => {
    await page.route('**/api/auth/password-reset-link/status', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ result: 'expired' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.resetPassword}/?token=${validToken}`)

    await expect(page.getByRole('heading', { name: 'Link expirado' })).toBeFocused()
    await expect(page.getByLabel('Nova senha', { exact: true })).toHaveCount(0)
  })

  test('automatically navigates to the BFF-provided sign-in destination after reset', async ({
    page,
  }) => {
    await page.route('**/api/auth/password-reset-link/status', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ result: 'valid' }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/password-reset', async (route) => {
      await route.fulfill({
        body: JSON.stringify({
          redirectTo: '/login',
          requiresEmailConfirmation: false,
          result: 'reset',
        }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.resetPassword}/?token=${validToken}`)
    await page.getByLabel('Nova senha', { exact: true }).fill('password-123')
    await page.getByLabel('Confirmar nova senha', { exact: true }).fill('password-123')
    await page.getByRole('button', { name: 'Redefinir senha' }).click()

    await expect(page).toHaveURL(/\/login\/?$/)
  })

  test('offers a new request for an already-used link', async ({ page }) => {
    await page.route('**/api/auth/password-reset-link/status', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ result: 'used' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.resetPassword}/?token=${validToken}`)
    await expect(page.getByRole('heading', { name: 'Link já utilizado' })).toBeFocused()
    await page.getByRole('button', { name: 'Solicitar novo link' }).click()
    await expect(page).toHaveURL(/\/forgot-password\/?$/)
  })

  test('keeps the reset flow recoverable when the BFF is unavailable', async ({
    page,
  }) => {
    await page.route('**/api/auth/password-reset-link/status', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ message: 'unavailable' }),
        contentType: 'application/json',
        status: 503,
      })
    })

    await page.goto(`${ROUTES.resetPassword}/?token=${validToken}`)
    await expect(
      page.getByRole('heading', { name: 'Não foi possível redefinir agora' }),
    ).toBeFocused()
    await page.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(
      page.getByRole('heading', { name: 'Não foi possível redefinir agora' }),
    ).toBeVisible()
  })
})
