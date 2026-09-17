import { test, expect } from '../playwright'

test('uses the public shell on the sign-in route', async ({ page }) => {
  await page.goto('/login/')

  await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()
  await expect(
    page.getByRole('navigation', { name: 'Navegação principal' }),
  ).not.toBeVisible()
})
