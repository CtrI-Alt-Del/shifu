import { expect, test } from '../../playwright'

test.describe('PendingConfirmationPage route with mocked transport', () => {
  test('renders the restricted public state and cooldown from the BFF', async ({
    page,
  }) => {
    await page.route('**/api/auth/pending-confirmation*', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        body: JSON.stringify({ state: 'cooldown', retryAfterSeconds: 60 }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.goto('/pending-confirmation/')

    await expect(page.getByRole('heading', { name: 'Confirme seu e-mail' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Reenviar link em 60s' }),
    ).toBeDisabled()
    await expect(page.getByRole('link', { name: 'Voltar para entrar' })).toHaveAttribute(
      'href',
      '/login',
    )
  })

  test('maps a resend delivery failure to an announced recoverable state', async ({
    page,
  }) => {
    await page.route('**/api/auth/pending-confirmation*', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        body: JSON.stringify({ state: 'ready', retryAfterSeconds: null }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.route('**/api/auth/pending-confirmation/resend', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ code: 'identity_unavailable' }),
        contentType: 'application/json',
        status: 503,
      })
    })
    await page.goto('/pending-confirmation/')
    await expect(page.getByRole('button', { name: 'Reenviar link' })).toBeEnabled()
    await page.getByRole('button', { name: 'Reenviar link' }).click()

    await expect(page.getByRole('alert')).toHaveText(
      'Não foi possível reenviar agora. Tente novamente.',
    )
    await expect(page.getByRole('button', { name: 'Reenviar link' })).toBeEnabled()
  })
})
