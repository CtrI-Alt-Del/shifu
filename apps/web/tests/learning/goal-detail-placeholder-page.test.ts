import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('renders the objective-detail placeholder with the routed goalId for an authenticated session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/learning/goals/goal-42/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Este Objetivo ainda está sendo preparado.',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Objetivo goal-42')).toBeVisible()
})

test('redirects an anonymous visitor before the placeholder renders', async ({
  page,
}) => {
  await page.goto('/learning/goals/goal-42/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Este Objetivo ainda está sendo preparado.',
    }),
  ).not.toBeVisible()
})
