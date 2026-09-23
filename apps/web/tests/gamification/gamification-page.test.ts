import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('protects gamification and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/gamification/')
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Cada passo merece ser visto.',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/gamification/')
  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})
