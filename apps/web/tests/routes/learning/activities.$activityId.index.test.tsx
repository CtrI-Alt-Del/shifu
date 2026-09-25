import { expect, navigateAuthenticatedPage, test } from '../../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000009',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const activityResponse = {
  activityId: ids.activityId,
  title: 'Somar os números pares',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: null,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'q1',
      kind: 'single_choice',
      prompt: 'Qual é o primeiro resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    },
    {
      key: 'q2',
      kind: 'multiple_selection',
      prompt: 'Selecione os pares',
      options: [
        { key: 'c', text: '2' },
        { key: 'd', text: '3' },
      ],
    },
  ],
}

test.describe('Activity index route', () => {
  test('shows a recoverable load error and retries the same Activity IDs', async ({
    authenticatedPage,
  }) => {
    let activityCalls = 0
    const requests: string[] = []
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      if (!payload.includes(ids.activityId)) return route.fallback()
      requests.push(payload)
      activityCalls += 1
      if (activityCalls === 1) {
        await route.fulfill({
          status: 503,
          body: JSON.stringify({ result: { kind: 'unavailable' } }),
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: activityResponse }),
        contentType: 'application/json',
      })
    })

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    await expect(
      authenticatedPage.getByRole('heading', {
        name: 'Não foi possível carregar esta Atividade',
      }),
    ).toBeVisible()
    await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(
      authenticatedPage.getByRole('heading', { name: activityResponse.title }),
    ).toBeVisible()
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
    expect(activityCalls).toBe(2)
    expect(
      requests.every(
        (body) =>
          body.includes(ids.goalId) &&
          body.includes(ids.skillId) &&
          body.includes(ids.competencyId),
      ),
    ).toBe(true)
  })

  test('submits ordered answers and navigates to the saved attempt URL', async ({
    authenticatedPage,
  }) => {
    const requests: string[] = []
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      if (!payload.includes(ids.activityId)) return route.fallback()
      requests.push(payload)
      if (payload.includes('submissionKey') || payload.includes('submission_key')) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              attemptId: ids.attemptId,
              status: 'pending',
              resultUrl: `${activityPath}/attempts/${ids.attemptId}`,
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: activityResponse }),
        contentType: 'application/json',
      })
    })

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    await authenticatedPage.getByText('4', { exact: true }).click()
    await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()
    await authenticatedPage.getByText('2', { exact: true }).click()
    await authenticatedPage.getByText('3', { exact: true }).click()
    await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
    )
    const submission =
      requests.find(
        (body) => body.includes('submissionKey') || body.includes('submission_key'),
      ) ?? ''
    expect(submission).toContain(ids.goalId)
    expect(submission).toContain('q1')
    expect(submission).toContain('q2')
    expect(submission).toContain('a')
    expect(submission).toContain('c')
    expect(submission).toContain('d')
  })

  test('returns an owner with an unresolved saved attempt to its result route', async ({
    authenticatedPage,
  }) => {
    const savedActivity = { ...activityResponse, unresolvedAttemptId: ids.attemptId }
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const payload = decodeURIComponent(
        `${route.request().url()} ${route.request().postData() ?? ''}`,
      )
      if (payload.includes(ids.attemptId)) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              attemptId: ids.attemptId,
              activityId: ids.activityId,
              status: 'pending',
              submittedAt: '2026-09-23T12:00:00Z',
              retryAllowed: false,
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: savedActivity }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}/?$`),
    )
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
    ).toBeVisible()
  })
})
