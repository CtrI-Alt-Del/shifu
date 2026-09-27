import { expect, test } from '../../playwright'

import { ROUTES } from '../../../src/constants/routes'

test.describe('ForgotPasswordPage route with mocked transport', () => {
  test('renders the public request form without horizontal overflow on mobile', async ({
    page,
  }) => {
    await page.setViewportSize({ height: 812, width: 375 })
    await page.goto(`${ROUTES.forgotPassword}/`)

    await expect(
      page.getByRole('heading', { level: 1, name: 'Esqueci minha senha' }),
    ).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Enviar link de recuperação' }),
    ).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(375)
  })

  test('preserves valid input and announces malformed e-mail without calling the BFF', async ({
    page,
  }) => {
    let didCallBff = false
    await page.route('**/api/auth/password-recovery', async (route) => {
      didCallBff = true
      await route.abort()
    })
    await page.goto(`${ROUTES.forgotPassword}/`)
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox', { name: 'E-mail' }).fill('invalid-email')
    await page.getByRole('button', { name: 'Enviar link de recuperação' }).click()

    await expect(page.getByRole('alert')).toHaveText('Revise o campo destacado.')
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveValue(
      'invalid-email',
    )
    await expect(page.getByText('Informe um e-mail válido.')).toBeVisible()
    expect(didCallBff).toBe(false)
  })

  test('posts only the e-mail to the same-origin BFF and renders generic status', async ({
    page,
  }) => {
    let requestBody: unknown
    await page.route('**/api/auth/password-recovery', async (route) => {
      requestBody = route.request().postDataJSON()
      await route.fulfill({
        body: JSON.stringify({ accepted: true }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/password-recovery/status', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ retryAfterSeconds: null, state: 'ready' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.forgotPassword}/`)
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox', { name: 'E-mail' }).fill('ana@example.com')
    await page.getByRole('button', { name: 'Enviar link de recuperação' }).click()

    await expect(
      page.getByRole('heading', { name: 'Verifique seu e-mail' }),
    ).toBeVisible()
    await expect(page).toHaveURL(/\/forgot-password\/?$/)
    expect(requestBody).toEqual({ email: 'ana@example.com' })
  })

  test('offers a generic retry after a terminal delivery issue', async ({ page }) => {
    let statusCalls = 0
    await page.route('**/api/auth/password-recovery', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ accepted: true }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/password-recovery/status', async (route) => {
      statusCalls += 1
      await route.fulfill({
        body: JSON.stringify(
          statusCalls === 1
            ? { retryAfterSeconds: null, state: 'delivery_issue' }
            : { retryAfterSeconds: null, state: 'ready' },
        ),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/password-recovery/retry', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ retryAfterSeconds: null, state: 'ready' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto(`${ROUTES.forgotPassword}/`)
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox', { name: 'E-mail' }).fill('ana@example.com')
    await page.getByRole('button', { name: 'Enviar link de recuperação' }).click()
    await page.getByRole('button', { name: 'Tentar novamente' }).click()

    await expect(
      page.getByRole('heading', { name: 'Verifique seu e-mail' }),
    ).toBeVisible()
    expect(statusCalls).toBeGreaterThanOrEqual(2)
  })
})
