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
import { expectBox, installAiQuotaReading } from '../support/ai-quota-backend'
import {
  ACTION_IDS,
  ADD_JUSTIFICATION,
  BLOCK_REASON,
  buildProposal,
  GOAL_TITLE,
  installMentorActionsBackend,
  openMentorActionsFab,
  SKILL_NAME,
} from '../support/mentor-actions-backend'
import {
  collectApplicationErrors,
  installBrowserPushStub,
  installStreakReminderBackend,
  pushStubCalls,
  STUB_SUBSCRIPTION,
} from '../support/streak-reminder-backend'
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
    await expect(menu.getByRole('menuitem', { name: 'Sua conta' })).toBeEnabled()
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
    await authenticatedPage.route('**/api/auth/account', (route) =>
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          accountId: 'a',
          displayName: 'Playwright Learner',
          email: 'playwright@shifu.local',
          timeZone: 'UTC',
        }),
      }),
    )
    await trigger.click()
    await menu.getByRole('menuitem', { name: 'Sua conta' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Sua conta' }),
    ).toBeVisible()
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
    await expect(authenticatedPage).toHaveURL(/\/gamification\/overview\/?$/)

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
    await authenticatedPage.route('**/api/auth/account', (route) =>
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          accountId: 'a',
          displayName: 'Playwright Learner',
          email: 'playwright@shifu.local',
          timeZone: 'UTC',
        }),
      }),
    )
    await accountTrigger.click()
    await authenticatedPage.getByRole('menuitem', { name: 'Sua conta' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Sua conta' }),
    ).toBeVisible()
  })

  test('shows the AI quota indicator in the desktop header and opens the usage page (CA-16)', async ({
    authenticatedPage,
  }) => {
    await installAiQuotaReading(authenticatedPage, 42)
    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

    const indicator = authenticatedPage.getByRole('link', {
      name: 'Uso da IA: 42% da cota mensal',
      exact: true,
    })
    await expect(indicator).toBeVisible()
    await expect(indicator).toHaveText('IA · 42%')
    // The normal state has no icon, as on the design board.
    await expect(indicator.locator('svg')).toHaveCount(0)
    await expect(indicator).toHaveAttribute('href', ROUTES.accountAiUsage)
    await expect(
      authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Abrir menu', exact: true }),
    ).toBeHidden()

    await indicator.click()

    await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
    await expect(
      authenticatedPage
        .getByRole('region', { name: 'Uso da IA' })
        .getByText('42%', { exact: true }),
    ).toBeVisible()
  })

  test('shows the AI quota indicator beside the 44 px menu button at 390 x 844 (CA-16, CA-23)', async ({
    authenticatedPage,
  }) => {
    await installAiQuotaReading(authenticatedPage, 42)
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

    const indicator = authenticatedPage.getByRole('link', {
      name: 'Uso da IA: 42% da cota mensal',
      exact: true,
    })
    const menuButton = authenticatedPage.getByRole('button', {
      name: 'Abrir menu',
      exact: true,
    })
    await expect(indicator).toBeVisible()
    await expect(indicator).toHaveText('IA · 42%')
    // The normal state has no icon, as on the design board.
    await expect(indicator.locator('svg')).toHaveCount(0)
    await expectBox(indicator, { height: 44 })
    await expect(menuButton).toBeVisible()
    const menuBox = await menuButton.boundingBox()
    expect(menuBox?.width).toBeGreaterThanOrEqual(44)
    expect(menuBox?.height).toBeGreaterThanOrEqual(44)
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390)

    await indicator.click()

    await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
    await expect(
      authenticatedPage
        .getByRole('region', { name: 'Uso da IA' })
        .getByText('42%', { exact: true }),
    ).toBeVisible()
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

// SHIFU-104: confirmed Mentor actions in the floating Mentor (mocked BFF transport).
test('confirms a removal in the floating Mentor with the keyboard and unblocks the composer at 1440', async ({
  authenticatedPage: page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const backend = await installMentorActionsBackend(page, {
    proposal: buildProposal('remove_skill'),
  })
  await openMentorActionsFab(page)

  const panel = page.getByRole('dialog', { name: 'Painel do Mentor' })
  const card = panel.getByRole('region', { name: `Remover ${SKILL_NAME}?` })
  await expect(card).toContainText(`Objetivo: ${GOAL_TITLE}`)
  await expect(panel.getByText(BLOCK_REASON)).toBeVisible()
  await expect(panel.getByRole('textbox')).toBeDisabled()
  const order = await card.evaluate((element) => {
    const text = element.textContent ?? ''
    return [
      text.indexOf('Você perderá o diagnóstico'),
      text.indexOf('Remover habilidade'),
    ]
  })
  expect(order[0]).toBeGreaterThanOrEqual(0)
  expect(order[0]).toBeLessThan(order[1] ?? 0)
  await expect(page.getByRole('alertdialog')).toHaveCount(0)

  await card.getByRole('button', { name: 'Recusar' }).focus()
  await page.keyboard.press('Tab')
  await expect(card.getByRole('button', { name: 'Remover habilidade' })).toBeFocused()
  await page.keyboard.press('Enter')

  const done = panel.getByRole('region', { name: `${SKILL_NAME} removida` })
  await expect(done.getByRole('status')).toContainText('Remoção concluída')
  await expect(done.getByRole('status')).toBeFocused()
  await expect(done.getByRole('link', { name: 'Ver Objetivo' })).toHaveAttribute(
    'href',
    `/learning/goals/${ACTION_IDS.goal}`,
  )
  expect(backend.callsOf('confirmMentorSkillRemovalServer')).toEqual([
    expect.objectContaining({
      method: 'POST',
      data: {
        goalId: ACTION_IDS.goal,
        confirmationId: ACTION_IDS.proposal,
        skillExperienceId: ACTION_IDS.experience,
      },
    }),
  ])
  await expect(panel.getByRole('textbox')).toBeEnabled({ timeout: 15_000 })
  await page.screenshot({
    path: '.playwright-cli/screenshots/shifu-104-fab-1440-remove-completed.png',
  })

  await done.getByRole('link', { name: 'Ver Objetivo' }).click()

  await expect(page).toHaveURL(new RegExp(`/learning/goals/${ACTION_IDS.goal}/?$`))
})

test('stacks the add card buttons at full width in the floating Mentor at 390', async ({
  authenticatedPage: page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await installMentorActionsBackend(page, { proposal: buildProposal('add_skill') })
  await openMentorActionsFab(page)

  const panel = page.getByRole('dialog', { name: 'Painel do Mentor' })
  const card = panel.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` })
  await expect(card).toContainText(ADD_JUSTIFICATION)
  const decline = await card.getByRole('button', { name: 'Recusar' }).boundingBox()
  const confirm = await card
    .getByRole('button', { name: 'Adicionar habilidade' })
    .boundingBox()
  const cardBox = await card.boundingBox()
  if (!decline || !confirm || !cardBox) throw new Error('The card has no layout box')
  expect(confirm.y).toBeGreaterThan(decline.y + decline.height - 1)
  expect(decline.width).toBeGreaterThan(cardBox.width - 60)
  expect(confirm.width).toBeGreaterThan(cardBox.width - 60)
  expect(decline.height).toBeGreaterThanOrEqual(44)
  expect(confirm.height).toBeGreaterThanOrEqual(44)
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
  await page.screenshot({
    path: '.playwright-cli/screenshots/shifu-104-fab-390-add-proposal.png',
  })
})

test('declines a card in the floating Mentor and releases the composer', async ({
  authenticatedPage: page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const backend = await installMentorActionsBackend(page, {
    proposal: buildProposal('add_skill'),
    readsUntilFinal: 1,
  })
  await openMentorActionsFab(page)
  const panel = page.getByRole('dialog', { name: 'Painel do Mentor' })

  await panel.getByRole('button', { name: 'Recusar' }).click()

  await expect(panel.getByRole('region', { name: 'Adição recusada' })).toBeVisible()
  await expect(panel.getByRole('textbox')).toBeEnabled({ timeout: 15_000 })
  expect(backend.callsOf('declineMentorActionProposalServer')).toHaveLength(1)
  expect(backend.callsOf('confirmMentorSkill')).toHaveLength(0)
})

const INVITE_TITLE = 'Quer um lembrete para manter sua sequência?'

const INVITE_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
] as const

// Browser integration with a mocked transport and a stubbed Push API: proves the
// invite's rendered contract and the order of its requests, not real delivery.
test.describe('AppLayout streak reminder invite', () => {
  for (const viewport of INVITE_VIEWPORTS) {
    test(`opens after the first practice day, enrolls this browser and saves the hour by keyboard at ${viewport.width} x ${viewport.height}`, async ({
      authenticatedPage: page,
    }) => {
      const errors = collectApplicationErrors(page)
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      const backend = await installStreakReminderBackend(page, {
        inviteStatus: 'pending',
        hour: 18,
      })
      await installBrowserPushStub(page, {
        permission: 'default',
        requestResult: 'granted',
      })
      await navigateAuthenticatedPage(page, ROUTES.gamification)

      const invite = page.getByRole('dialog', { name: INVITE_TITLE })
      await expect(invite).toBeVisible()
      await expect(
        invite.getByText('O navegador vai pedir sua permissão.', { exact: false }),
      ).toBeVisible()
      // The benefit is explained before any permission request or answer.
      expect(await pushStubCalls(page)).toEqual([])
      expect(backend.writeOrder()).toEqual([])
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(viewport.width)

      const enable = invite.getByRole('button', { name: 'Ativar lembretes' })
      // The primary action takes the initial focus, not the dialog container.
      await expect(enable).toBeFocused()
      // Visual order and keyboard order agree: "Agora não" comes first on both viewports.
      const [declineBox, enableBox] = await Promise.all([
        invite.getByRole('button', { name: 'Agora não' }).boundingBox(),
        enable.boundingBox(),
      ])
      expect(declineBox?.x).toBeLessThan(enableBox?.x ?? 0)
      expect(Math.abs((declineBox?.y ?? 0) - (enableBox?.y ?? 0))).toBeLessThan(2)
      expect(
        await invite.evaluate((element) => getComputedStyle(element).outlineStyle),
      ).toBe('none')
      await page.keyboard.press('Enter')

      const hourStep = page.getByRole('dialog', { name: 'Lembretes ativados' })
      await expect(hourStep).toBeVisible()
      const hourField = hourStep.getByRole('combobox', { name: 'Horário do lembrete' })
      await expect(hourField).toContainText('18:00')
      await expect(hourField).toBeFocused()
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(viewport.width)

      await hourField.focus()
      await page.keyboard.press('Enter')
      await page.getByRole('option', { name: '19:00' }).click()
      await expect(hourField).toContainText('19:00')
      await hourStep.getByRole('button', { name: 'Salvar horário' }).focus()
      await page.keyboard.press('Enter')

      await expect(hourStep).not.toBeVisible()
      expect(backend.writeOrder()).toEqual([
        'answer',
        'public-key',
        'subscription',
        'preference',
        'hour',
      ])
      expect(backend.callsNamed('subscription')[0].data).toMatchObject({
        accountEmail: 'playwright@shifu.local',
        ...STUB_SUBSCRIPTION,
      })
      expect(backend.callsNamed('preference')[0].data).toMatchObject({ enabled: true })
      expect(backend.callsNamed('hour')[0].data).toMatchObject({ hour: 19 })
      expect(await pushStubCalls(page)).toEqual([
        'requestPermission',
        'register /service-worker.js',
        'subscribe',
      ])
      expect(errors).toEqual([])

      await navigateAuthenticatedPage(page, ROUTES.root)
      await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toHaveCount(0)
    })
  }

  test('answers "Agora não" once, requests no permission and never reopens', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installStreakReminderBackend(page, { inviteStatus: 'pending' })
    await installBrowserPushStub(page)
    await navigateAuthenticatedPage(page, ROUTES.gamification)

    const invite = page.getByRole('dialog', { name: INVITE_TITLE })
    await expect(invite).toBeVisible()
    await invite.getByRole('button', { name: 'Agora não' }).click()

    await expect(invite).not.toBeVisible()
    expect(backend.writeOrder()).toEqual(['answer'])
    expect(await pushStubCalls(page)).toEqual([])
    await navigateAuthenticatedPage(page, ROUTES.root)
    await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toHaveCount(0)
    expect(backend.writeOrder()).toEqual(['answer'])
  })

  test('closes with Escape and records the answer', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installStreakReminderBackend(page, { inviteStatus: 'pending' })
    await installBrowserPushStub(page)
    await navigateAuthenticatedPage(page, ROUTES.gamification)

    const invite = page.getByRole('dialog', { name: INVITE_TITLE })
    await expect(invite).toBeVisible()
    await expect(invite.getByRole('button', { name: 'Fechar' })).toBeVisible()
    await page.keyboard.press('Escape')

    await expect(invite).not.toBeVisible()
    await expect.poll(() => backend.writeOrder()).toEqual(['answer'])
    expect(await pushStubCalls(page)).toEqual([])
  })

  test('closes without enrolling when the browser blocks notifications', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installStreakReminderBackend(page, { inviteStatus: 'pending' })
    await installBrowserPushStub(page, { permission: 'default', requestResult: 'denied' })
    await navigateAuthenticatedPage(page, ROUTES.gamification)

    const invite = page.getByRole('dialog', { name: INVITE_TITLE })
    await invite.getByRole('button', { name: 'Ativar lembretes' }).click()

    await expect(invite).not.toBeVisible()
    await expect(
      page.getByText('Sem problema. Você pode ativar os lembretes depois em Sua conta.'),
    ).toBeVisible()
    expect(backend.writeOrder()).toEqual(['answer'])
    expect(await pushStubCalls(page)).toEqual(['requestPermission'])
  })

  test('does not open and stays unanswered in a browser without push support', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installStreakReminderBackend(page, { inviteStatus: 'pending' })
    await installBrowserPushStub(page, { supported: false })
    await navigateAuthenticatedPage(page, ROUTES.gamification)

    await expect.poll(() => backend.callsNamed('reminder-read').length).toBeGreaterThan(0)
    await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toHaveCount(0)
    expect(backend.writeOrder()).toEqual([])
  })

  test('stays closed before the first practice day and opens after the state refresh on navigation', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installStreakReminderBackend(page, {
      inviteStatus: 'not-eligible',
    })
    await installBrowserPushStub(page)
    await navigateAuthenticatedPage(page, ROUTES.gamification)

    await expect.poll(() => backend.callsNamed('reminder-read').length).toBeGreaterThan(0)
    await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toHaveCount(0)

    backend.state.inviteStatus = 'pending'
    await navigateAuthenticatedPage(page, ROUTES.intelligence)

    await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toBeVisible()
  })

  test('mounts no invite on public routes and requests no reminder state', async ({
    page,
  }) => {
    let reminderReads = 0
    await page.route('**/_serverFn/**', async (route) => {
      if ((serverFnExport(route.request().url()) ?? '').startsWith('getStreakReminder_'))
        reminderReads += 1
      await route.fallback()
    })

    await page.goto('/login/')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('dialog', { name: INVITE_TITLE })).toHaveCount(0)
    expect(reminderReads).toBe(0)
  })
})
