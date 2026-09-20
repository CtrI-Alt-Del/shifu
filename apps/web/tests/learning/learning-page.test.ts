import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('protects learning and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/learning/')
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Seu próximo passo começa aqui.',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/learning/')
  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})
