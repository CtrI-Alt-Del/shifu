import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('renders the manual-creation placeholder for an authenticated session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/learning/goals/new/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'A criação manual de Objetivos está sendo preparada.',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Em preparação')).toBeVisible()
})

test('redirects an anonymous visitor before the placeholder renders', async ({
  page,
}) => {
  await page.goto('/learning/goals/new/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'A criação manual de Objetivos está sendo preparada.',
    }),
  ).not.toBeVisible()
})
