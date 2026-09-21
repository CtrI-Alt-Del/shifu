import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('renders the planner placeholder with the routed planningId for an authenticated session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/intelligence/planner/planning-42/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Seu planejamento está sendo preparado.',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Planejamento planning-42')).toBeVisible()
})

test('redirects an anonymous visitor before the placeholder renders', async ({
  page,
}) => {
  await page.goto('/intelligence/planner/planning-42/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Seu planejamento está sendo preparado.',
    }),
  ).not.toBeVisible()
})
