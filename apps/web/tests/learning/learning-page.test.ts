import { expect, navigateAuthenticatedPage, test } from '../playwright'

const skillPath =
  '/learning/goals/01SHF000000000000000000003/skills/01SHF000000000000000000004'
const GOAL_ID = '01SHF000000000000000000003'
const SKILL_ID = '01SHF000000000000000000004'
const COMPETENCY_ID = '01SHF000000000000000000001'
const ACTIVITY_ID = '01SHF000000000000000000005'

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    return JSON.parse(Buffer.from(segment, 'base64').toString('utf-8')).export
  } catch {
    return null
  }
}

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

test('renders a resumable diagnostic on the protected Skill route', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getGoalDetailAction_')) {
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
                status: 'diagnosing',
                policyId: 'adaptive-v2',
              },
            ],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (fn?.startsWith('getDiagnosticAction_')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            status: 'diagnosing',
            nextCompetencyId: COMPETENCY_ID,
            nextActivityId: ACTIVITY_ID,
            pendingAttemptId: null,
            pendingAttemptStatus: null,
            focusCompetencyId: null,
            competencies: [],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })
  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage.getByRole('heading', { name: 'Lógica' })).toBeVisible()
  await expect(
    authenticatedPage.getByText('As respostas são avaliadas em conjunto.'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar diagnóstico' }),
  ).toHaveAttribute(
    'href',
    `/learning/goals/${GOAL_ID}/skills/${SKILL_ID}/competencies/${COMPETENCY_ID}/activities/${ACTIVITY_ID}`,
  )
  await expect(authenticatedPage.getByText(/nota de|resposta correta/i)).not.toBeVisible()
})

test('redirects anonymous visitors before the Skill contract loader', async ({
  page,
}) => {
  await page.goto(skillPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.locator('body')).not.toContainText('Not Found')
})
