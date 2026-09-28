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

test('redirects authenticated learning visitors to Home and protects anonymous visitors', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/learning/')
  await expect(authenticatedPage).toHaveURL(/\/$/)
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'O que você quer aprender?',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/learning/')
  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})

test('starts an interrupted diagnostic and opens its next Activity', async ({
  authenticatedPage,
}) => {
  const diagnosticRunId = 'b2a3f497-7f4b-4d5e-8bc0-a984e6c04c98'
  let diagnosticRequests = 0
  let startRequests = 0
  let activityRequestPayload = ''
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getGoalDetail_')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'success',
            detail: {
              goalId: GOAL_ID,
              title: 'Aprender lógica',
              description: 'Praticar os fundamentos.',
              relations: [],
              skills: [
                {
                  skillExperienceId: '01SHF000000000000000000006',
                  skillId: SKILL_ID,
                  name: 'Lógica',
                  skillName: 'Lógica',
                  status: 'diagnosing',
                  progress: null,
                  inclusionReason: null,
                  policyId: 'learning-adaptive-v2',
                },
              ],
            },
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (fn?.startsWith('getDiagnosticAction_')) {
      diagnosticRequests += 1
      await route.fulfill({
        body: JSON.stringify({
          result: {
            status: 'diagnosing',
            runState: diagnosticRequests === 1 ? 'requires_entry' : 'active',
            readyToComplete: false,
            nextCompetencyId: COMPETENCY_ID,
            nextActivityId: ACTIVITY_ID,
            pendingAttemptId: null,
            pendingAttemptStatus: null,
            focusCompetencyId: null,
            activitySequence: [{ competencyId: COMPETENCY_ID, activityId: ACTIVITY_ID }],
            competencies: [],
            initialOverallResult: null,
            overallCoverageComplete: false,
            directCompletion: false,
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (fn?.startsWith('startSkillAction_')) {
      startRequests += 1
      await route.fulfill({
        body: JSON.stringify({ result: { diagnosticRunId } }),
        contentType: 'application/json',
      })
      return
    }
    if (fn?.startsWith('getActivityAction_')) {
      activityRequestPayload = decodeURIComponent(
        `${route.request().url()} ${route.request().postData() ?? ''}`,
      )
      await route.fulfill({
        body: JSON.stringify({
          result: {
            activityId: ACTIVITY_ID,
            title: 'Somar os números pares',
            difficulty: 'medium',
            activityRevision: 'revision-1',
            canSubmit: true,
            latestAttemptId: null,
            unresolvedAttemptId: null,
            isDiagnostic: true,
            questions: [
              {
                key: 'q1',
                kind: 'single_choice',
                prompt: 'Qual é o resultado?',
                options: [
                  { key: 'a', text: '4' },
                  { key: 'b', text: '6' },
                ],
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
  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage).toHaveURL(
    `${skillPath}/competencies/${COMPETENCY_ID}/activities/${ACTIVITY_ID}`,
  )
  await expect(authenticatedPage.getByText('Qual é o resultado?')).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar diagnóstico' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(/nota de|resposta correta/i)).not.toBeVisible()
  expect(diagnosticRequests).toBeGreaterThanOrEqual(2)
  expect(startRequests).toBe(1)
  expect(activityRequestPayload).toContain(diagnosticRunId)
})

test('redirects anonymous visitors before the Skill contract loader', async ({
  page,
}) => {
  await page.goto(skillPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.locator('body')).not.toContainText('Not Found')
})
