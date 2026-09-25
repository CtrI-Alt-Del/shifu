import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

test.describe('AppLayout', () => {
  test('navigates between the shared desktop destinations', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setViewportSize({ width: 1280, height: 800 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)
    await authenticatedPage.waitForLoadState('networkidle')

    const menuButton = authenticatedPage.getByRole('button', {
      exact: true,
      name: 'Abrir menu',
    })
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

  test('opens the shared account menu at the desktop viewport and restores focus on Escape', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

    const trigger = authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' })
    await trigger.click()

    const menu = authenticatedPage.getByRole('menu', { name: 'Menu da conta' })
    await expect(menu).toBeVisible()
    await expect(menu.getByText('Playwright Learner')).toBeVisible()
    await expect(menu.getByText(/@/)).toBeVisible()
    await expect(menu.getByRole('menuitem', { name: 'Sua conta' })).toBeDisabled()
    await expect(menu.getByRole('menuitem', { name: 'Sair' })).toBeEnabled()

    await authenticatedPage.keyboard.press('Escape')
    await expect(menu).not.toBeVisible()
    await expect(trigger).toBeFocused()

    await trigger.click()
    const gamificationMain = authenticatedPage
      .getByRole('main')
      .filter({ hasText: 'Cada passo merece ser visto.' })
    await expect(gamificationMain).toBeVisible()
    await gamificationMain.click({ position: { x: 20, y: 20 } })
    await expect(menu).not.toBeVisible()
  })

  test('shows logout progress, ignores a duplicate request and reaches Entrar', async ({
    authenticatedPage,
  }) => {
    let requestCount = 0
    const requests: Array<{ method: string; pathname: string }> = []
    let releaseResponse: () => void = () => undefined
    const responseReady = new Promise<void>((resolve) => {
      releaseResponse = resolve
    })

    await authenticatedPage.route('**/api/auth/sign-out', async (route) => {
      requestCount += 1
      requests.push({
        method: route.request().method(),
        pathname: new URL(route.request().url()).pathname,
      })
      await responseReady
      await route.fulfill({
        body: JSON.stringify({ success: true }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)
    await authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' }).click()
    await authenticatedPage.getByRole('menuitem', { name: 'Sair' }).click()

    const pendingLogout = authenticatedPage.getByRole('menuitem', { name: 'Saindo...' })
    await expect(pendingLogout).toBeDisabled()
    await expect.poll(() => requestCount).toBe(1)

    releaseResponse()
    await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
    expect(requests).toEqual([{ method: 'POST', pathname: '/api/auth/sign-out' }])
  })

  test('keeps the session and offers an explicit retry after a safe logout failure', async ({
    authenticatedPage,
  }) => {
    let requestCount = 0
    const requests: Array<{ method: string; pathname: string }> = []
    let releaseFirstResponse: () => void = () => undefined
    const firstResponseReady = new Promise<void>((resolve) => {
      releaseFirstResponse = resolve
    })

    await authenticatedPage.route('**/api/auth/sign-out', async (route) => {
      requestCount += 1
      requests.push({
        method: route.request().method(),
        pathname: new URL(route.request().url()).pathname,
      })
      if (requestCount === 1) {
        await firstResponseReady
        await route.fulfill({
          body: JSON.stringify({ message: 'unavailable' }),
          contentType: 'application/json',
          status: 503,
        })
        return
      }

      await route.fulfill({
        body: JSON.stringify({ success: true }),
        contentType: 'application/json',
        status: 200,
      })
    })
    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)
    await authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' }).click()
    await authenticatedPage.getByRole('menuitem', { name: 'Sair' }).click()

    await expect(
      authenticatedPage.getByRole('menuitem', { name: 'Saindo...' }),
    ).toBeDisabled()
    await expect.poll(() => requestCount).toBe(1)
    releaseFirstResponse()

    await expect(authenticatedPage.getByRole('alert')).toHaveText(
      /Não foi possível sair agora\. Tente novamente\./,
    )
    await expect(authenticatedPage).toHaveURL(/\/gamification\/?$/)

    await authenticatedPage.getByRole('menuitem', { name: 'Sair' }).click()
    await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
    expect(requestCount).toBe(2)
    expect(requests).toEqual([
      { method: 'POST', pathname: '/api/auth/sign-out' },
      { method: 'POST', pathname: '/api/auth/sign-out' },
    ])
  })

  test('keeps account access beside mobile navigation at 390 x 844', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

    const accountTrigger = authenticatedPage.getByRole('button', {
      name: 'Abrir menu da conta',
    })
    await accountTrigger.click()
    await expect(
      authenticatedPage.getByRole('menu', { name: 'Menu da conta' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', {
        exact: true,
        name: 'Abrir menu',
      }),
    ).toBeVisible()

    await authenticatedPage.keyboard.press('Escape')
    await expect(
      authenticatedPage.getByRole('menu', { name: 'Menu da conta' }),
    ).not.toBeVisible()
    await expect(accountTrigger).toBeFocused()
  })
})
