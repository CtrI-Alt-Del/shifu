import { expect, navigateAuthenticatedPage, test } from '../../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000009',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
const activity = {
  activityId: ids.activityId,
  title: 'Somar os números pares',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: ids.attemptId,
  unresolvedAttemptId: ids.attemptId,
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
}
const pending = {
  attemptId: ids.attemptId,
  activityId: ids.activityId,
  status: 'pending',
  submittedAt: '2026-09-23T12:00:00Z',
  retryAllowed: false,
}
const completed = {
  ...pending,
  status: 'completed',
  score: 100,
  progressBefore: 50,
  progressAfter: 55,
  questions: [
    {
      key: 'q1',
      prompt: 'Qual é o resultado?',
      submittedOptionKeys: ['a'],
      score: 100,
      isCorrect: true,
      explanation: 'A soma é 4.',
      correctOptionKeys: ['a'],
    },
  ],
}

test.describe('Attempt index route', () => {
  test('loads Activity and Attempt, announces pending, and refreshes immediately when visible', async ({
    authenticatedPage,
  }) => {
    let attemptReads = 0
    const requestUrls: string[] = []
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      requestUrls.push(route.request().url())
      if (payload.includes(ids.attemptId)) {
        attemptReads += 1
        await route.fulfill({
          body: JSON.stringify({ result: pending }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activity }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, attemptPath)
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
    ).toBeVisible()
    const indicatorDots = authenticatedPage
      .getByRole('heading', { name: 'Avaliação em andamento' })
      .locator('[aria-hidden="true"] span')
    await expect(indicatorDots).toHaveCount(3)
    await expect(indicatorDots.first()).toHaveCSS('animation-name', 'pulse')
    await expect(authenticatedPage.getByRole('status')).toContainText(
      'Estamos avaliando suas respostas.',
    )

    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
    ).toBeVisible()
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
    ).toBeVisible()
    await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
    await expect(indicatorDots.first()).toHaveCSS('animation-name', 'none')

    await authenticatedPage.evaluate(() =>
      document.dispatchEvent(new Event('visibilitychange')),
    )
    await expect.poll(() => attemptReads).toBeGreaterThan(1)
    expect(requestUrls.length).toBeGreaterThanOrEqual(2)
  })

  test('retries a failed evaluation on the same attempt and renders the completed result', async ({
    authenticatedPage,
  }) => {
    let attemptUrl = ''
    let retryUrl = ''
    let attemptReads = 0
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const requestUrl = route.request().url()
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${requestUrl} ${body}`)
      if (payload.includes(ids.attemptId)) {
        if (!attemptUrl) attemptUrl = requestUrl
        if (requestUrl !== attemptUrl) {
          retryUrl = requestUrl
          await route.fulfill({
            body: JSON.stringify({ result: { ok: true } }),
            contentType: 'application/json',
          })
          return
        }
        attemptReads += 1
        await route.fulfill({
          body: JSON.stringify({
            result:
              attemptReads === 1
                ? {
                    ...pending,
                    status: 'failed',
                    retryAllowed: true,
                    failureMessage: 'A avaliação foi interrompida.',
                  }
                : completed,
          }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activity }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, attemptPath)
    await expect(
      authenticatedPage.getByRole('heading', {
        name: 'A avaliação não pôde ser concluída',
      }),
    ).toBeVisible()
    await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
    ).toBeVisible()
    await expect(authenticatedPage.getByText('A soma é 4.')).toBeVisible()
    expect(retryUrl).not.toBe('')
    expect(attemptReads).toBeGreaterThanOrEqual(2)
  })

  test('renders all completed details without a repeat shortcut', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      if (payload.includes(ids.attemptId)) {
        await route.fulfill({
          body: JSON.stringify({ result: completed }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activity }),
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
      authenticatedPage.getByLabel('Nota da Atividade 100 de 100'),
    ).toBeVisible()
    await expect(authenticatedPage.getByText('A soma é 4.')).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Voltar para Atividade' }),
    ).toHaveCount(0)
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
  })
})
