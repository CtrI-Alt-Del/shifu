import { expect, navigateAuthenticatedPage, test } from '../playwright'

const skillPath =
  '/learning/goals/01SHF000000000000000000003/skills/01SHF000000000000000000004'

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

test('protects the Skill contract route before its generic not-found boundary', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage.locator('body')).toContainText('Not Found')
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Estruturas de repetição' }),
  ).not.toBeVisible()
})

test('redirects anonymous visitors before the Skill contract loader', async ({
  page,
}) => {
  await page.goto(skillPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.locator('body')).not.toContainText('Not Found')
})
