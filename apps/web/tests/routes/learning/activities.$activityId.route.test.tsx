import { expect, navigateAuthenticatedPage, test } from '../../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
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
      key: 'question-1',
      kind: 'single_choice',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    },
  ],
}

test.describe('Activity route parent', () => {
  test('redirects anonymous visitors before rendering a nested child', async ({
    page,
  }) => {
    await page.goto(`${activityPath}/attempts/01SHF000000000000000000009`)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(
      page.getByRole('heading', { name: 'Somar os números pares' }),
    ).not.toBeVisible()
  })

  test('authenticates once and renders the selected nested Activity through Outlet', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activityResponse }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { name: activityResponse.title }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('heading', {
        name: activityResponse.questions[0].prompt,
      }),
    ).toBeVisible()
  })
})
