import { expect, navigateAuthenticatedPage, test } from '../playwright'

test('renders the dashboard for an authenticated session', async ({
  authenticatedPage,
}) => {
  const serverFunctionRequest = authenticatedPage.waitForRequest(
    (request) => request.headers()['x-tsr-serverfn'] === 'true',
  )
  await navigateAuthenticatedPage(authenticatedPage, '/')
  const request = await serverFunctionRequest

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Dê forma ao que você quer aprender.',
    }),
  ).toBeVisible()
  expect(request.method()).toBe('GET')
  expect(new URL(request.url()).pathname).toContain('/_serverFn/')
})

test('redirects an anonymous visitor before the dashboard renders', async ({ page }) => {
  await page.goto('/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { level: 1, name: 'Dê forma ao que você quer aprender.' }),
  ).not.toBeVisible()
})
