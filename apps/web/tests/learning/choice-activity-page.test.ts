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
