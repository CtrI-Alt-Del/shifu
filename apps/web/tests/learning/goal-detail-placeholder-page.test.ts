import { expect, navigateAuthenticatedPage, test } from '../playwright'

const GOAL_ID = '01SHF000000000000000000003'
const SKILL_ID = '01SHF000000000000000000004'

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    return JSON.parse(Buffer.from(segment, 'base64').toString('utf-8')).export
  } catch {
    return null
  }
}

test('renders the owned Goal and its Skill link for an authenticated session', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (serverFnExport(route.request().url())?.startsWith('getGoalDetailAction_')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            goalId: GOAL_ID,
            title: 'Aprender lógica',
            description: 'Praticar os fundamentos.',
            skills: [
              {
                skillId: SKILL_ID,
                skillName: 'Lógica',
                status: 'not-started',
                policyId: 'adaptive-v2',
              },
            ],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })
  await navigateAuthenticatedPage(authenticatedPage, `/learning/goals/${GOAL_ID}/`)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Aprender lógica',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Praticar os fundamentos.')).toBeVisible()
  await expect(
    authenticatedPage.getByRole('link', { name: /Lógica.*Não iniciada/ }),
  ).toHaveAttribute('href', `/learning/goals/${GOAL_ID}/skills/${SKILL_ID}`)
})

test('redirects an anonymous visitor before the Goal detail renders', async ({
  page,
}) => {
  await page.goto(`/learning/goals/${GOAL_ID}/`)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Aprender lógica',
    }),
  ).not.toBeVisible()
})
