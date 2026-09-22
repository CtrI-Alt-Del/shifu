import { expect, navigateAuthenticatedPage, test } from '../playwright'

test.describe('AppLayout', () => {
  test('navigates between the shared desktop destinations', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setViewportSize({ width: 1280, height: 800 })
    await navigateAuthenticatedPage(authenticatedPage, '/gamification/')

    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Navegação principal',
    })
    await expect(navigation.getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    await navigation.getByRole('link', { name: 'Mentor' }).click()
    await expect(authenticatedPage).toHaveURL(/\/intelligence\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', {
        level: 1,
        name: 'Mais clareza para continuar.',
      }),
    ).toBeVisible()

    await navigation.getByRole('link', { name: 'Objetivos' }).click()
    await expect(authenticatedPage).toHaveURL(/\/$/)
    await expect(
      authenticatedPage.getByRole('heading', {
        level: 1,
        name: 'O que você quer aprender?',
      }),
    ).toBeVisible()
  })

  test('opens and dismisses the mobile navigation', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, '/gamification/')
    await authenticatedPage.waitForLoadState('networkidle')

    const menuButton = authenticatedPage.getByRole('button', { name: 'Abrir menu' })
    await menuButton.click()

    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Navegação móvel',
    })
    await expect(navigation).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
      'href',
      '/',
    )

    await authenticatedPage.keyboard.press('Escape')
    await expect(navigation).not.toBeVisible()

    await menuButton.click()
    await authenticatedPage.mouse.click(20, 200)
    await expect(navigation).not.toBeVisible()
  })
})
