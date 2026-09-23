import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('protects intelligence and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/intelligence/')
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
