import { expect, test } from '@playwright/test'

test('renders the account route', async ({ page }) => {
  await page.goto('/account/')

  await expect(page.getByRole('heading', { level: 1, name: 'Minha conta' })).toBeVisible()
  await expect(
    page.getByRole('heading', { level: 2, name: 'Cuide do seu espaço' }),
  ).toBeVisible()
})
