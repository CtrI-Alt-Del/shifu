import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { PlanningFaker } from '@/core/intelligence/fakers/planning-faker'

test('renders the planner placeholder with the routed planningId for an authenticated session', async ({
  authenticatedPage,
}) => {
  const { planningId } = PlanningFaker.fake()
  await navigateAuthenticatedPage(
    authenticatedPage,
    `/intelligence/planner/${planningId}/`,
  )

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Seu planejamento está sendo preparado.',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(`Planejamento ${planningId}`)).toBeVisible()
})

test('redirects an anonymous visitor before the placeholder renders', async ({
  page,
}) => {
  const { planningId } = PlanningFaker.fake()
  await page.goto(`/intelligence/planner/${planningId}/`)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Seu planejamento está sendo preparado.',
    }),
  ).not.toBeVisible()
})
