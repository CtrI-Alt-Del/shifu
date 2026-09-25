import { expect, navigateAuthenticatedPage, test } from '../playwright'

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

test('renders the manual Goal form with selectable Curriculum Skills', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (serverFnExport(route.request().url())?.startsWith('getAvailableSkillsAction_')) {
      await route.fulfill({
        body: JSON.stringify({
          result: [
            { id: SKILL_ID, name: 'Lógica', available: true, unavailableReason: null },
          ],
        }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })
  await navigateAuthenticatedPage(authenticatedPage, '/learning/goals/new/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'O que você quer aprender?',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByLabel('Título do Objetivo *')).toBeVisible()
  await expect(authenticatedPage.getByLabel('Descrição *')).toBeVisible()
  await expect(authenticatedPage.getByRole('checkbox', { name: 'Lógica' })).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Criar Objetivo' }),
  ).toBeDisabled()
})

test('redirects an anonymous visitor before the Goal form renders', async ({ page }) => {
  await page.goto('/learning/goals/new/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'O que você quer aprender?',
    }),
  ).not.toBeVisible()
})
