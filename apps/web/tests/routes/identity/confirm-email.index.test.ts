import { expect, test } from '../../playwright'

const validToken = 'a'.repeat(43)

test.describe('ConfirmEmailPage route with mocked transport', () => {
  test('settles malformed input locally without calling the BFF', async ({ page }) => {
    let didCallConfirmation = false
    await page.route('**/api/auth/confirm-email*', async (route) => {
      didCallConfirmation = true
      await route.abort()
    })
    await page.goto('/confirm-email/?token=invalid')

    await expect(page).toHaveURL(/\/confirm-email\/?$/)
    await expect(page.getByRole('heading', { name: 'Link inválido' })).toBeFocused()
    expect(didCallConfirmation).toBe(false)
  })

  test('removes a valid token from the URL before rendering an expired recovery', async ({
    page,
  }) => {
    await page.route('**/api/auth/confirm-email*', async (route) => {
      expect(route.request().postDataJSON()).toEqual({ token: validToken })
      await route.fulfill({
        body: JSON.stringify({ result: 'expired', redirectTo: '/login' }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await page.goto(`/confirm-email/?token=${validToken}`)

    await expect(page).toHaveURL(/\/confirm-email\/?$/)
    await expect(page.getByRole('heading', { name: 'Link expirado' })).toBeFocused()
    await expect(page.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })
})
