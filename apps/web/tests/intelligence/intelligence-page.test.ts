import { test, expect } from '../playwright'

test('protects intelligence and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.goto('/intelligence/')
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Mais clareza para continuar.',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/intelligence/')
  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})
