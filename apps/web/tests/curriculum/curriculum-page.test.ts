import { test, expect } from '../playwright'

test('protects curriculum and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.goto('/curriculum/')
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Aprenda com um caminho claro.',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/curriculum/')
  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})
