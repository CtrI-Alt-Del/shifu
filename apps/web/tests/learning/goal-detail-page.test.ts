import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillExperienceId: '01SHF000000000000000000004',
  skillId: '01SHF000000000000000000005',
}

const detailPath = `/learning/goals/${ids.goalId}/`

const detailResponse = {
  goalId: ids.goalId,
  title: 'Fundamentos de programação',
  description: 'Construa uma base sólida para resolver problemas.',
  skills: [
    {
      skillExperienceId: ids.skillExperienceId,
      skillId: ids.skillId,
      name: 'Lógica de programação',
      status: 'learning',
      progress: 60,
      inclusionReason: 'Base para programação',
    },
  ],
  relations: [],
}

test('renders the real goal detail and preserves the skill destination through mocked BFF transport', async ({
  authenticatedPage,
}) => {
  let goalDetailRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    goalDetailRequests += 1
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'success', detail: detailResponse } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: detailResponse.title }),
  ).toBeVisible()
  await authenticatedPage.getByRole('tab', { name: 'Lista' }).click()
  await expect(
    authenticatedPage.getByRole('link', { name: 'Lógica de programação' }),
  ).toHaveAttribute(
    'href',
    `/learning/goals/${ids.goalId}/skills/${ids.skillExperienceId}`,
  )
  await expect(
    authenticatedPage.getByRole('button', {
      name: 'Mais ações de Lógica de programação',
    }),
  ).toBeDisabled()
  expect(goalDetailRequests).toBe(1)
})

test('shows private absence without objective data through mocked BFF transport', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'not-found' } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('heading', { name: 'Objetivo não encontrado' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { name: detailResponse.title }),
  ).not.toBeVisible()
})

test('redirects anonymous visitors before a goal detail request', async ({ page }) => {
  await page.goto(detailPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { name: detailResponse.title }),
  ).not.toBeVisible()
})
