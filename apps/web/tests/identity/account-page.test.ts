import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('renders the account route for an active session', async ({ authenticatedPage }) => {
  await navigateAuthenticatedPage(authenticatedPage, '/account/')

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Minha conta' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { level: 2, name: 'Cuide do seu espaço' }),
  ).toBeVisible()
  const privacyLink = authenticatedPage.getByRole('link', {
    name: 'Ler política de privacidade',
  })
  await expect(privacyLink).toHaveAttribute('href', '/privacy')
  await privacyLink.click()
  await expect(authenticatedPage).toHaveURL(/\/privacy\/?$/)
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Política de privacidade',
    }),
  ).toBeVisible()
})

test('redirects an anonymous visitor before protected content renders', async ({
  page,
}) => {
  await page.goto('/account/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { level: 1, name: 'Minha conta' }),
  ).not.toBeVisible()
})
