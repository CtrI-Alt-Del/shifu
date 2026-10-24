import {
  exerciseDictationStates,
  exerciseBrowserManagedControls,
} from '../support/native-dictation'
import {
  exerciseSummaryFailure,
  exerciseSummaryJourney,
} from '../support/mentor-summary-journey'
import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import {
  installMentorMemoriesBackend,
  MEMORY_IDS,
  openMentorFabConversation,
  searchOf,
} from '../support/mentor-memories-backend'

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    return JSON.parse(Buffer.from(segment, 'base64').toString('utf-8')).export
  } catch {
    return null
  }
}

test.describe('AppLayout', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // The gamification page stands in here as a generic, already-authenticated
    // destination for layout/navigation assertions unrelated to Gamification
    // itself; its own achievements fetch is mocked so a real unauthorized
    // response never fires the page's unrelated redirect-to-login effect.
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
      const fn = serverFnExport(route.request().url())
      if (fn?.startsWith('getAchievements_')) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              kind: 'success',
              overview: { level: 1, totalXp: 0, xpForNextLevel: 100, achievements: [] },
            },
          }),
          contentType: 'application/json',
          status: 200,
        })
        return
      }
      await route.fallback()
    })
  })

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
        name: 'Nova conversa',
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
      .filter({ hasText: 'Gamificação' })
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

    await expect(
      authenticatedPage.getByRole('menu', { name: 'Menu da conta' }).getByRole('alert'),
    ).toHaveText(/Não foi possível sair agora\. Tente novamente\./)
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

test('renders native dictation states on fab at 1440', async ({ authenticatedPage }) => {
  await exerciseDictationStates(authenticatedPage, 'fab', 1440)
})
test('renders native dictation states on fab at 390', async ({ authenticatedPage }) => {
  await exerciseDictationStates(authenticatedPage, 'fab', 390)
})

test('renders native dictation states without a local language pack on fab', async ({
  authenticatedPage,
}) => {
  await exerciseBrowserManagedControls(authenticatedPage, 'fab')
})

test('summarizes the context, reads the summary and reveals the originals on fab at 1440', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryJourney(authenticatedPage, 'fab', 1440)
})
test('summarizes the context, reads the summary and reveals the originals on fab at 390', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryJourney(authenticatedPage, 'fab', 390)
})
test('shows the summarization failure notice after its learner message on fab', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryFailure(authenticatedPage, 'fab')
})

// SHIFU-101: markers inside the floating Mentor panel (mocked transport).
test('shows the memory marker in the floating Mentor and closes the panel when following "Ver memória"', async ({
  authenticatedPage: page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await installMentorMemoriesBackend(page)
  await openMentorFabConversation(page)

  const panel = page.getByRole('dialog', { name: 'Painel do Mentor' })
  const marker = panel.getByRole('list', { name: 'Memórias desta resposta' })
  await expect(marker).toContainText('Memória atualizada')
  await expect(marker).toContainText('Antes: Prefiro exemplos curtos em JavaScript.')
  await expect(panel.getByRole('link', { name: 'Memórias' })).toHaveCount(0)

  await marker.getByRole('link', { name: 'Ver memória' }).click()

  await expect(page).toHaveURL(/\/intelligence\/memories\/?\?/)
  expect(searchOf(page).get('memory')).toBe(MEMORY_IDS.preference)
  await expect(
    page
      .getByRole('region', { name: 'Detalhes da memória' })
      .getByRole('heading', { level: 2, name: 'Agora prefiro exemplos em Python.' }),
  ).toBeVisible()
  await expect(panel).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Abrir Mentor' })).toBeVisible()
})
