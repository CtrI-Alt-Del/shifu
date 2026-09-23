import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000009',
  nextCompetencyId: '01SHF000000000000000000002',
  nextActivityId: '01SHF000000000000000000010',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
const activity = {
  activityId: ids.activityId,
  title: 'Somar os números pares',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: ids.attemptId,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'q1',
      kind: 'single_choice',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
        { key: 'c', text: '8' },
      ],
    },
  ],
}
const completedAttempt = {
  attemptId: ids.attemptId,
  activityId: ids.activityId,
  status: 'completed',
  submittedAt: '2026-09-23T12:00:00Z',
  retryAllowed: false,
  score: 0,
  questions: [
    {
      key: 'q1',
      prompt: 'Qual é o resultado?',
      submittedOptionKeys: ['b'],
      score: 0,
      isCorrect: false,
      explanation: 'A soma correta não foi selecionada.',
    },
  ],
  nextAction: {
    competencyId: ids.nextCompetencyId,
    activityId: ids.nextActivityId,
    difficulty: 'easy',
    type: 'reinforcement',
  },
}

test('renders actual result route from safe Activity and Attempt contracts, protects hidden labels, and returns', async ({
  authenticatedPage,
}) => {
  const calls: Array<{ url: string; body: string }> = []
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const url = route.request().url()
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${url} ${body}`)
    calls.push({ url, body: payload })
    if (payload.includes(ids.attemptId)) {
      await route.fulfill({
        body: JSON.stringify({ result: completedAttempt }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.activityId) || payload.includes(ids.nextActivityId)) {
      const nextActivity = payload.includes(ids.nextActivityId)
        ? { ...activity, activityId: ids.nextActivityId, title: 'Reforço recomendado' }
        : activity
      await route.fulfill({
        body: JSON.stringify({ result: nextActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Qual é o resultado?' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('6', { exact: true })).toBeVisible()
  await expect(authenticatedPage.getByText('4', { exact: true })).not.toBeVisible()
  await expect(
    authenticatedPage.getByText('A soma correta não foi selecionada.'),
  ).toBeVisible()
  expect(calls.some(({ body }) => body.includes(ids.activityId))).toBe(true)
  expect(calls.some(({ body }) => body.includes(ids.attemptId))).toBe(true)

  await authenticatedPage.getByRole('button', { name: 'Voltar para Atividade' }).click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  await authenticatedPage.getByRole('button', { name: 'Próxima Atividade' }).click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`${ids.nextCompetencyId}/activities/${ids.nextActivityId}/?$`),
  )
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Reforço recomendado' }),
  ).toBeVisible()
})
