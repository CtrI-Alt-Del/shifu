import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const competencyPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}`
const activity = {
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
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    },
  ],
}

test('runs the actual Activity route, preserves the answer, and blocks unsent in-app navigation', async ({
  authenticatedPage,
}) => {
  const calls: Array<{ url: string; body: string }> = []
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const url = route.request().url()
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${url} ${body}`)
    calls.push({ url, body: payload })
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  await authenticatedPage.getByText('4', { exact: true }).click()
  await expect(authenticatedPage.getByRole('radio', { name: '4' })).toBeChecked()

  const dialogMessage = new Promise<string>((resolve) => {
    authenticatedPage.once('dialog', async (dialog) => {
      resolve(dialog.message())
      await dialog.accept()
    })
  })
  await authenticatedPage.evaluate((to) => {
    const router = (
      window as Window & {
        __TSR_ROUTER__: { navigate: (options: { to: string }) => Promise<void> }
      }
    ).__TSR_ROUTER__
    return router.navigate({ to })
  }, competencyPath)
  expect(await dialogMessage).toContain('respostas não foram enviadas')
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.competencyId}/?$`))
  expect(
    calls.some(
      ({ body }) =>
        body.includes(ids.goalId) &&
        body.includes(ids.skillId) &&
        body.includes(ids.competencyId) &&
        body.includes(ids.activityId),
    ),
  ).toBe(true)
})

test('shows Markdown code and accepts a complete multiple-selection answer', async ({
  authenticatedPage,
}) => {
  const multipleActivity = {
    ...activity,
    questions: [
      {
        key: 'q1',
        kind: 'multiple_selection',
        prompt:
          'Considere o código:\n\n```python\ntem_cracha = True\ntem_senha = False\npode_entrar = tem_cracha and tem_senha\n```\n\nQuais afirmações são verdadeiras?',
        options: [
          { key: 'a', text: 'tem_cracha é True.' },
          { key: 'b', text: 'tem_senha é True.' },
          { key: 'c', text: 'pode_entrar é False.' },
          { key: 'd', text: 'pode_entrar é True.' },
        ],
      },
    ],
  }
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const payload = decodeURIComponent(route.request().url())
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: multipleActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  await expect(authenticatedPage.locator('pre code')).toHaveText(
    /pode_entrar = tem_cracha and tem_senha/,
  )
  const prompt = authenticatedPage.locator('.choice-question-prompt')
  expect(await prompt.evaluate((node) => getComputedStyle(node).animationName)).toBe(
    'choice-prompt-enter',
  )
  await authenticatedPage.getByText('tem_cracha é True.').click()
  await authenticatedPage.getByText('pode_entrar é False.').click()
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_cracha é True.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'pode_entrar é False.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_senha é True.' }),
  ).not.toBeChecked()
  const optionCards = authenticatedPage.locator('.choice-question-option')
  expect(
    await optionCards.evaluateAll((cards) =>
      cards.map((card) => ({
        name: getComputedStyle(card).animationName,
        delay: getComputedStyle(card).animationDelay,
      })),
    ),
  ).toEqual([
    { name: 'choice-option-enter', delay: '0.08s' },
    { name: 'choice-option-enter', delay: '0.14s' },
    { name: 'choice-option-enter', delay: '0.2s' },
    { name: 'choice-option-enter', delay: '0.26s' },
  ])
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  expect(await prompt.evaluate((node) => getComputedStyle(node).animationName)).toBe(
    'none',
  )
  expect(
    await optionCards.evaluateAll((cards) =>
      cards.map((card) => getComputedStyle(card).animationName),
    ),
  ).toEqual(['none', 'none', 'none', 'none'])
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_cracha é True.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toBeEnabled()
})
