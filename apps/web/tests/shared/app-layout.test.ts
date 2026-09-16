import { expect, test } from '@playwright/test'

test.describe('AppLayout', () => {
  test('navigates between the shared desktop destinations', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/gamification/')

    const navigation = page.getByRole('navigation', { name: 'Navegação principal' })
    await expect(navigation.getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    await navigation.getByRole('link', { name: 'Mentor' }).click()
    await expect(page).toHaveURL(/\/intelligence\/?$/)
    await expect(
      page.getByRole('heading', { level: 1, name: 'Mais clareza para continuar.' }),
    ).toBeVisible()

    await navigation.getByRole('link', { name: 'Objetivos' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Dê forma ao que você quer aprender.',
      }),
    ).toBeVisible()
  })

  test('opens and dismisses the mobile navigation', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/gamification/')

    const menuButton = page.getByRole('button', { name: 'Abrir menu' })
    await menuButton.click()

    const navigation = page.getByRole('navigation', { name: 'Navegação móvel' })
    await expect(navigation).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
      'href',
      '/',
    )

    await page.keyboard.press('Escape')
    await expect(navigation).not.toBeVisible()

    await menuButton.click()
    await page.mouse.click(20, 200)
    await expect(navigation).not.toBeVisible()
  })
})
